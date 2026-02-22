from __future__ import annotations

import asyncio
import hashlib
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx

from .config import DetectorConfig
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


async def _download_pdf(client: httpx.AsyncClient, pdf_url: str, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return True
    try:
        resp = await client.get(pdf_url, headers={"User-Agent": "opportunity-detector/0.1"})
        resp.raise_for_status()
        if "application/pdf" not in (resp.headers.get("content-type") or "").lower():
            return False
        dest.write_bytes(resp.content)
        return dest.stat().st_size > 0
    except Exception:
        return False


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


def _paper_system_prompt() -> str:
    return (
        "你是一个研究论文速读助手（偏工程落地）。"
        "请用中文输出，尽量短但信息密度高。"
        "输出格式固定为 5 条 bullet："
        "1) 问题/背景 2) 方法要点 3) 关键结果 4) 局限/风险 5) 可产品化/工程落地。"
        "每条不超过 2 句。"
    )


def _summarize_with_llm(text: str) -> str:
    cfg = load_ollama_from_env()
    if cfg is None:
        return ""
    user = f"请总结以下论文内容（可能是摘要或论文前几页提取文本）：\n\n{text}".strip()
    try:
        return ollama_best_effort(cfg=cfg, system=_paper_system_prompt(), user=user)
    except Exception:
        return ""


async def build_paper_summaries(
    *,
    events: list[EventItem],
    config: DetectorConfig,
    as_of: datetime,
) -> tuple[list[EventItem], list[PaperSummary]]:
    if not config.daily_enable_paper_summaries:
        return events, []

    paper_events: list[EventItem] = []
    for item in events:
        if item.source == "arxiv" or "arxiv.org/" in (item.url or ""):
            paper_events.append(item)

    if not paper_events:
        return events, []

    cache_dir = Path(config.papers_cache_dir)
    timeout = httpx.Timeout(60.0)
    summaries: list[PaperSummary] = []
    updated: list[EventItem] = []

    pdf_budget = max(0, int(config.daily_max_paper_pdfs)) if config.daily_enable_pdf_summaries else 0

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        for item in events:
            if item not in paper_events:
                updated.append(item)
                continue

            meta = dict(item.meta or {})
            abstract = str(meta.get("summary") or "").strip()
            pdf_url = arxiv_pdf_url(item.url, meta.get("pdf_url"))

            abstract_summary = _summarize_with_llm(abstract) if abstract else ""
            if not abstract_summary:
                abstract_summary = _fallback_abstract_summary(abstract)

            pdf_path = ""
            pdf_summary = ""
            if pdf_budget > 0 and pdf_url:
                dest = _cache_path(cache_dir, pdf_url)
                ok = await _download_pdf(client, pdf_url, dest)
                if ok:
                    pdf_path = str(dest)
                    extracted = _extract_pdf_text(dest, max_pages=int(config.daily_pdf_max_pages))
                    if extracted:
                        pdf_summary = _summarize_with_llm(extracted)
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

    return updated, summaries


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
