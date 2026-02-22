from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .insights import TopicInsight
from .models import EventItem


@dataclass(frozen=True)
class DailyInsight:
    angle: str  # "tech" | "business"
    topic: str
    thesis: str
    opportunity: str
    why_selected: str
    evidence_urls: list[str]


def _unique_urls(items: Iterable[EventItem], limit: int = 3) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        url = (item.url or "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        out.append(url)
        if len(out) >= limit:
            break
    return out


def _topic_stats(items: list[EventItem]) -> dict[str, int]:
    sources = {item.source for item in items}
    categories = {item.meta.get("category") for item in items if item.meta and item.meta.get("category")}
    stats: dict[str, int] = {
        "count": len(items),
        "sources": len(sources),
        "categories": len(categories),
        "open_source": sum(1 for item in items if item.source in {"github"} or "github.com/" in (item.url or "")),
        "papers": sum(1 for item in items if item.source == "arxiv" or "arxiv.org/" in (item.url or "")),
        "product": sum(1 for item in items if (item.meta or {}).get("category") == "product_release"),
        "funding": sum(1 for item in items if (item.meta or {}).get("category") == "funding_ma"),
        "policy": sum(1 for item in items if (item.meta or {}).get("category") == "policy_reg"),
        "pricing": sum(1 for item in items if (item.meta or {}).get("category") == "pricing_biz"),
    }
    return stats


def select_daily_insights(
    *,
    events: list[EventItem],
    topic_insights: list[TopicInsight],
    max_per_angle: int = 2,
) -> list[DailyInsight]:
    by_topic: dict[str, list[EventItem]] = {}
    for item in events:
        if not item.topic:
            continue
        by_topic.setdefault(item.topic, []).append(item)

    insight_map = {item.topic: item for item in topic_insights}

    tech_candidates: list[tuple[float, str]] = []
    biz_candidates: list[tuple[float, str]] = []

    for topic, items in by_topic.items():
        stats = _topic_stats(items)
        base_conf = insight_map.get(topic).confidence if topic in insight_map else 0.0
        opp_score = insight_map.get(topic).opportunity_score if topic in insight_map else 0.0

        tech_trigger = (stats["papers"] + stats["open_source"]) > 0
        biz_trigger = (stats["product"] + stats["funding"] + stats["policy"] + stats["pricing"]) > 0

        tech_score = (
            2.0 * stats["papers"]
            + 1.5 * stats["open_source"]
            + 0.6 * stats["sources"]
            + 0.4 * stats["categories"]
            + 0.5 * base_conf
        )
        biz_score = (
            2.0 * stats["product"]
            + 2.0 * stats["funding"]
            + 1.6 * stats["pricing"]
            + 1.6 * stats["policy"]
            + 0.4 * stats["sources"]
            + 0.3 * stats["categories"]
            + 0.3 * opp_score
        )

        if tech_trigger and tech_score > 0.9:
            tech_candidates.append((tech_score, topic))
        if biz_trigger and biz_score > 0.9:
            biz_candidates.append((biz_score, topic))

    tech_candidates.sort(reverse=True)
    biz_candidates.sort(reverse=True)

    out: list[DailyInsight] = []

    def build_tech(topic: str) -> DailyInsight:
        items = by_topic.get(topic, [])
        insight = insight_map.get(topic)
        stats = _topic_stats(items)
        papers = [item for item in items if item.source == "arxiv" or "arxiv.org/" in (item.url or "")]
        repos = [item for item in items if item.source == "github" or "github.com/" in (item.url or "")]
        evidence = papers + repos + items
        urls = _unique_urls(evidence, limit=3)

        thesis = "技术信号增强：出现新的研究/开源产出，说明方案正在工程化落地。"
        if papers and repos:
            thesis = "从论文到开源的链条变短：新论文 + 新仓库同时出现，落地窗口更清晰。"
        elif repos and not papers:
            thesis = "开源活跃：出现新仓库/新项目，生态在加速迭代。"
        elif papers and not repos:
            thesis = "研究升温：当天有新论文/预印本更新，值得跟进方法与评测。"

        opportunity = "做一个可复现 demo/benchmark，对标主流方案；再切一个垂直场景打包成可交付能力。"
        if insight and insight.insight_type == "crowded_hot_market":
            opportunity = "把通用能力收敛成“垂直评测 + 可控交付”的产品形态（数据接入/审计/合规）。"

        why = f"论文={stats['papers']}，开源={stats['open_source']}，跨来源={stats['sources']}"
        return DailyInsight(
            angle="tech",
            topic=topic,
            thesis=thesis,
            opportunity=opportunity,
            why_selected=why,
            evidence_urls=urls,
        )

    def build_biz(topic: str) -> DailyInsight:
        items = by_topic.get(topic, [])
        insight = insight_map.get(topic)
        stats = _topic_stats(items)
        urls = _unique_urls(items, limit=3)

        thesis = "商业信号增强：出现产品/定价/并购/监管等变化，意味着需求与预算正在显性化。"
        if stats["pricing"] > 0:
            thesis = "定价/商业模式信号出现：付费转化与 ROI 叙事成为竞争关键。"
        elif stats["funding"] > 0:
            thesis = "融资/并购信号出现：赛道被资本确认，竞争与并购整合可能加速。"
        elif stats["policy"] > 0:
            thesis = "政策/监管信号出现：合规与风控会成为差异化壁垒。"
        elif stats["product"] > 0:
            thesis = "产品发布信号出现：供给侧推进，用户侧会更快形成可比价的采购框架。"

        opportunity = "把机会拆成可购买的 1 个功能包（明确 ROI/合规边界），先拿 1–2 个付费试点。"
        if insight and insight.opportunity_band in {"high", "medium"}:
            opportunity = "按“最小可卖功能”推进：先用低成本试点验证付费，再扩展到端到端流程。"

        why = (
            f"产品发布={stats['product']}，定价={stats['pricing']}，融资并购={stats['funding']}，政策监管={stats['policy']}"
        )
        return DailyInsight(
            angle="business",
            topic=topic,
            thesis=thesis,
            opportunity=opportunity,
            why_selected=why,
            evidence_urls=urls,
        )

    for _, topic in tech_candidates[:max_per_angle]:
        out.append(build_tech(topic))
    for _, topic in biz_candidates[:max_per_angle]:
        out.append(build_biz(topic))

    return out
