from __future__ import annotations

import asyncio
import hashlib
import re
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .config import DetectorConfig, PaperSummaryStats
from .llm import load_ollama_from_env, ollama_best_effort
from .models import EventItem


@dataclass(frozen=True)
class PaperSummary:
    topic: str
    title: str
    url: str
    pdf_url: str
    published_at: str
    abstract: str
    abstract_summary: str
    pdf_path: str
    pdf_summary: str

    def to_dict(self) -> dict:
        return asdict(self)


_ARXIV_ID_RE = re.compile(
    r"(?:arxiv\.org|export\.arxiv\.org)/(?:abs|pdf)/(?P<id>\d{4}\.\d{4,5})(?:v\d+)?",
    re.IGNORECASE,
)


def arxiv_id_from_url(url: str) -> str:
    match = _ARXIV_ID_RE.search(url or "")
    if not match:
        return ""
    return match.group("id") or ""


def arxiv_pdf_url(url: str, meta_pdf_url: str | None = None) -> str:
    if meta_pdf_url and isinstance(meta_pdf_url, str) and meta_pdf_url.strip():
        return meta_pdf_url.strip()
    paper_id = arxiv_id_from_url(url)
    if not paper_id:
        return ""
    return f"https://arxiv.org/pdf/{paper_id}.pdf"


def _cache_path(cache_dir: Path, pdf_url: str) -> Path:
    digest = hashlib.sha256(pdf_url.encode("utf-8")).hexdigest()[:24]
    return cache_dir / f"{digest}.pdf"


def _is_cache_expired(cache_path: Path, ttl_days: int) -> bool:
    """检查缓存是否过期"""
    if not cache_path.exists():
        return True
    file_mtime = datetime.fromtimestamp(cache_path.stat().st_mtime, tz=timezone.utc)
    now = datetime.now(tz=timezone.utc)
    age_days = (now - file_mtime).days
    return age_days > ttl_days


def _clear_expired_cache(cache_dir: Path, ttl_days: int) -> int:
    """清除过期的缓存文件，返回清除的文件数"""
    if not cache_dir.exists():
        return 0
    cleared = 0
    for cache_file in cache_dir.glob("*.pdf"):
        if _is_cache_expired(cache_file, ttl_days):
            cache_file.unlink()
            cleared += 1
    return cleared


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError)),
    reraise=True
)
async def _download_pdf_with_retry(
    client: httpx.AsyncClient, pdf_url: str, dest: Path, timeout: float
) -> bool:
    """带重试机制的 PDF 下载"""
    dest.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        resp = await client.get(
            pdf_url,
            headers={"User-Agent": "opportunity-detector/0.1"},
            timeout=timeout
        )
        resp.raise_for_status()
        if "application/pdf" not in (resp.headers.get("content-type") or "").lower():
            return False
        dest.write_bytes(resp.content)
        return dest.stat().st_size > 0
    except Exception:
        raise


async def _download_pdf(
    client: httpx.AsyncClient,
    pdf_url: str,
    dest: Path,
    timeout: float,
    enable_cache: bool,
    cache_ttl_days: int,
    stats: Optional[PaperSummaryStats] = None
) -> tuple[bool, bool]:
    """
    下载 PDF 文件
    
    Returns:
        tuple: (下载成功/缓存命中, 是否是缓存命中)
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    
    # 检查缓存
    if enable_cache and dest.exists():
        if _is_cache_expired(dest, cache_ttl_days):
            # 缓存过期，删除旧文件
            dest.unlink()
        elif dest.stat().st_size > 0:
            if stats:
                stats.pdf_cache_hit += 1
            return True, True  # 缓存命中
    
    # 下载 PDF
    try:
        start_time = time.time()
        resp = await client.get(
            pdf_url,
            headers={"User-Agent": "opportunity-detector/0.1"},
            timeout=timeout
        )
        resp.raise_for_status()
        if "application/pdf" not in (resp.headers.get("content-type") or "").lower():
            if stats:
                stats.pdf_download_failed += 1
            return False, False
        dest.write_bytes(resp.content)
        if stats:
            stats.pdf_downloaded += 1
            stats.avg_download_time_seconds += (time.time() - start_time)
        return dest.stat().st_size > 0, False
    except Exception:
        if stats:
            stats.pdf_download_failed += 1
        return False, False


def _extract_pdf_text(path: Path, max_pages: int, max_chars: int = 40_000) -> str:
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception:
        return ""
    try:
        reader = PdfReader(str(path))
    except Exception:
        return ""
    chunks: list[str] = []
    pages = reader.pages[: max(1, max_pages)]
    for page in pages:
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        if text:
            chunks.append(text)
        if sum(len(c) for c in chunks) >= max_chars:
            break
    out = "\n".join(chunks)
    out = " ".join(out.split())
    return out[:max_chars].strip()


def _fallback_abstract_summary(abstract: str, limit: int = 450) -> str:
    cleaned = " ".join((abstract or "").split())
    if not cleaned:
        return ""
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: max(0, limit - 1)].rstrip() + "…"


def _fallback_keyword_summary(text: str, max_sentences: int = 3) -> str:
    """
    基于关键词的 fallback 摘要
    使用简单的启发式方法：选择包含关键术语的句子
    """
    if not text:
        return ""
    
    # 关键词列表（研究论文中常见的关键术语）
    keywords = [
        "我们提出", "我们的方法", "我们提出了一种", "实验结果", "结果表明",
        "本文提出", "本文提出了一种", "本研究", "研究表明", "结果展示",
        "创新点", "贡献", "主要贡献", "关键创新", "方法论"
    ]
    
    # 分句
    sentences = re.split(r'[。！？!?]+', text)
    scored_sentences = []
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence or len(sentence) < 10:
            continue
        
        # 计算分数：包含关键词越多，分数越高
        score = sum(1 for kw in keywords if kw in sentence)
        # 优先选择较长的句子（通常包含更多信息）
        score += len(sentence) / 100
        
        scored_sentences.append((score, sentence))
    
    # 按分数排序
    scored_sentences.sort(key=lambda x: x[0], reverse=True)
    
    # 选择前 N 个句子
    selected = [s for _, s in scored_sentences[:max_sentences]]
    
    if not selected:
        # 如果没有找到关键词，返回前几个句子
        selected = [s for s in sentences[:max_sentences] if s and len(s) >= 10]
    
    return "。".join(selected) + "。" if selected else ""


def _paper_system_prompt() -> str:
    return (
        "你是一个研究论文速读助手（偏工程落地）。"
        "请用中文输出，尽量短但信息密度高。"
        "输出格式固定为 5 条 bullet："
        "1) 问题/背景 2) 方法要点 3) 关键结果 4) 局限/风险 5) 可产品化/工程落地。"
        "每条不超过 2 句。"
    )


def _summarize_with_llm(
    text: str,
    stats: Optional[PaperSummaryStats] = None
) -> tuple[str, bool]:
    """
    使用 LLM 总结文本
    
    Returns:
        tuple: (总结文本, 是否使用了 fallback)
    """
    cfg = load_ollama_from_env()
    if cfg is None:
        return "", True  # LLM 不可用，使用 fallback
    
    user = f"请总结以下论文内容（可能是摘要或论文前几页提取文本）：\n\n{text}".strip()
    try:
        summary = ollama_best_effort(cfg=cfg, system=_paper_system_prompt(), user=user)
        if summary:
            if stats:
                stats.llm_summarized += 1
            return summary, False
        return "", True  # LLM 返回空，使用 fallback
    except Exception:
        return "", True  # LLM 出错，使用 fallback


async def build_paper_summaries(
    *,
    events: list[EventItem],
    config: DetectorConfig,
    as_of: datetime,
) -> tuple[list[EventItem], list[PaperSummary], PaperSummaryStats]:
    """构建论文摘要，包含增强功能
    
    Returns:
        tuple: (更新后的事件列表, 论文摘要列表, 统计信息)
    """
    if not config.daily_enable_paper_summaries:
        return events, [], PaperSummaryStats()
    
    paper_events: list[EventItem] = []
    for item in events:
        if item.source == "arxiv" or "arxiv.org/" in (item.url or ""):
            paper_events.append(item)
    
    if not paper_events:
        return events, [], PaperSummaryStats()
    
    # 初始化统计信息
    stats = PaperSummaryStats()
    start_time = time.time()
    
    # 获取 paper_config
    paper_config = config.paper_config
    
    # 清除过期缓存
    cache_dir = Path(paper_config.cache_dir)
    if paper_config.enable_cache:
        cleared = _clear_expired_cache(cache_dir, paper_config.cache_ttl_days)
        # 可以在这里记录清除的文件数
    
    timeout = httpx.Timeout(float(paper_config.download_timeout))
    summaries: list[PaperSummary] = []
    updated: list[EventItem] = []
    
    pdf_budget = max(0, int(paper_config.max_pdfs)) if paper_config.enable_pdf_download else 0
    
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        for item in events:
            if item not in paper_events:
                updated.append(item)
                continue
            
            meta = dict(item.meta or {})
            abstract = str(meta.get("summary") or "").strip()
            pdf_url = arxiv_pdf_url(item.url, meta.get("pdf_url"))
            
            # 摘要总结
            abstract_summary, abstract_fallback = _summarize_with_llm(abstract, stats)
            if not abstract_summary:
                abstract_summary = _fallback_abstract_summary(abstract)
                if abstract_fallback:
                    stats.llm_fallback_used += 1
            
            pdf_path = ""
            pdf_summary = ""
            if pdf_budget > 0 and pdf_url:
                dest = _cache_path(cache_dir, pdf_url)
                ok, is_cached = await _download_pdf(
                    client, pdf_url, dest,
                    timeout=float(paper_config.download_timeout),
                    enable_cache=paper_config.enable_cache,
                    cache_ttl_days=paper_config.cache_ttl_days,
                    stats=stats
                )
                if ok:
                    pdf_path = str(dest)
                    extracted = _extract_pdf_text(dest, max_pages=int(paper_config.max_pages))
                    if extracted:
                        pdf_summary, pdf_summary_fallback = _summarize_with_llm(extracted, stats)
                        if pdf_summary_fallback:
                            stats.llm_fallback_used += 1
                            # 如果 LLM 不可用，使用 fallback 摘要
                            if not pdf_summary:
                                pdf_summary = _fallback_keyword_summary(extracted)
                pdf_budget -= 1
            
            meta["abstract_summary"] = abstract_summary
            if pdf_url:
                meta["pdf_url"] = pdf_url
            if pdf_path:
                meta["pdf_path"] = pdf_path
            if pdf_summary:
                meta["pdf_summary"] = pdf_summary
            
            updated_item = EventItem(
                source=item.source,
                topic=item.topic,
                title=item.title,
                url=item.url,
                published_at=item.published_at,
                meta=meta,
            )
            updated.append(updated_item)
            
            summaries.append(
                PaperSummary(
                    topic=item.topic,
                    title=item.title,
                    url=item.url,
                    pdf_url=pdf_url,
                    published_at=(
                        item.published_at.astimezone(timezone.utc).isoformat()
                        if item.published_at
                        else as_of.astimezone(timezone.utc).isoformat()
                    ),
                    abstract=abstract,
                    abstract_summary=abstract_summary,
                    pdf_path=pdf_path,
                    pdf_summary=pdf_summary,
                )
            )
            
            await asyncio.sleep(0)
    
    # 计算统计信息
    stats.total_time_seconds = time.time() - start_time
    if stats.pdf_downloaded > 0:
        stats.avg_download_time_seconds /= stats.pdf_downloaded
    if stats.llm_summarized > 0:
        stats.avg_summarize_time_seconds /= stats.llm_summarized
    
    # 将统计信息添加到 meta 中（可选）
    # 可以通过 config 传递 stats 引用，或者返回额外的统计信息
    
    return updated, summaries, stats


def render_paper_summaries_markdown(rows: list[PaperSummary], as_of: datetime) -> str:
    date_label = as_of.astimezone(timezone.utc).strftime("%Y-%m-%d")
    lines: list[str] = []
    lines.append(f"# 论文总结（{date_label}）")
    lines.append("")
    if not rows:
        lines.append("- 无")
        return "\n".join(lines)
    
    lines.append("| Topic | 论文 | Abstract 总结 | PDF 总结 |")
    lines.append("|---|---|---|---|")
    for item in rows:
        title = f"[{item.title}]({item.url})"
        abstract_sum = (item.abstract_summary or "").replace("\n", "<br>") or "-"
        pdf_sum = (item.pdf_summary or "").replace("\n", "<br>") or "-"
        lines.append(f"| {item.topic} | {title} | {abstract_sum} | {pdf_sum} |")
    lines.append("")
    return "\n".join(lines)
