from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import os
import re
from typing import Iterable

import httpx

from .config import DetectorConfig
from .connectors.arxiv import fetch_arxiv_papers
from .connectors.gdelt import fetch_gdelt_articles
from .connectors.gdelt import fetch_gdelt_articles_for_query
from .connectors.github import fetch_github_repositories
from .connectors.hackernews import fetch_hn_stories
from .connectors.reddit import fetch_reddit_posts
from .daily_insights import select_daily_insights
from .insights import TopicInsight
from .models import EventItem


_STOPWORDS = {
    "and",
    "or",
    "the",
    "a",
    "an",
    "of",
    "to",
    "in",
    "on",
    "for",
    "with",
    "from",
}

_GENERIC_KEYWORDS = {
    "ai",
    "agent",
    "agents",
    "automation",
    "platform",
    "workflow",
    "support",
    "copilot",
    "saas",
    "b2b",
    "smb",
    "ops",
    "vertical",
}


def _normalize_topic(topic: str) -> str:
    return " ".join(part for part in (topic or "").lower().split() if part)


def _base_keywords(topic_normalized: str) -> list[str]:
    out: list[str] = []
    for part in topic_normalized.split():
        if len(part) < 3:
            continue
        if part in _STOPWORDS:
            continue
        if part in _GENERIC_KEYWORDS:
            continue
        out.append(part)
    return out


def _keyword_expansions(topic_normalized: str) -> set[str]:
    expansions: set[str] = set()
    if any(k in topic_normalized for k in ["finance", "accounting", "finops", "对账", "财务"]):
        expansions |= {
            "accounting",
            "reconciliation",
            "month end",
            "month-end",
            "month end close",
            "invoice",
            "billing",
            "payables",
            "receivables",
        }
    if any(k in topic_normalized for k in ["clinic", "health", "医疗", "诊所"]):
        expansions |= {"healthcare", "hospital", "ehr", "emr", "patient"}
    if any(k in topic_normalized for k in ["logistics", "supply", "仓储", "物流"]):
        expansions |= {"supply", "shipment", "warehouse", "freight", "dispatch", "routing"}
    if any(k in topic_normalized for k in ["support", "helpdesk", "客服"]):
        expansions |= {"helpdesk", "ticket", "sla", "contact", "callcenter", "chat"}
    if any(k in topic_normalized for k in ["coding", "developer", "devops", "代码", "研发"]):
        expansions |= {"developer", "code", "devtools", "ide", "copilot"}
    return {item for item in expansions if len(item) >= 3}


def _custom_keywords(config: DetectorConfig, topic: str) -> list[str]:
    topic_key = (topic or "").strip()
    if not topic_key:
        return []
    items = config.topic_keywords.get(topic_key, [])
    out: list[str] = []
    for item in items:
        cleaned = str(item or "").strip()
        if not cleaned:
            continue
        out.append(cleaned)
    return out


def _arxiv_query(config: DetectorConfig, topic: str) -> str:
    phrases: list[str] = []

    base = " ".join([part for part in _normalize_topic(topic).split() if len(part) >= 3])
    if base:
        phrases.append(base)

    for item in _custom_keywords(config, topic):
        cleaned = " ".join([part for part in _normalize_topic(item).split() if len(part) >= 3])
        if cleaned and cleaned not in phrases:
            phrases.append(cleaned)

    normalized_topic = _normalize_topic(topic)
    if "coding" in normalized_topic or "agent" in normalized_topic:
        for extra in ["code generation", "program synthesis", "software agent"]:
            if extra not in phrases:
                phrases.append(extra)
    if "support" in normalized_topic or "helpdesk" in normalized_topic:
        for extra in ["customer support", "helpdesk"]:
            if extra not in phrases:
                phrases.append(extra)

    phrases = phrases[:3]
    if not phrases:
        return ""

    parts = []
    for phrase in phrases:
        escaped = phrase.replace('"', "")
        parts.append(f'all:"{escaped}"')
    if len(parts) == 1:
        return parts[0]
    return "(" + " OR ".join(parts) + ")"


def _topic_reason(text: str, config: DetectorConfig, topic: str) -> str:
    normalized = _normalize_topic(topic)
    keywords = _base_keywords(normalized)
    keywords.extend(sorted(_keyword_expansions(normalized)))
    keywords.extend(_custom_keywords(config, topic))
    matched = _matched_keywords(text, keywords)
    if not matched:
        return ""
    compact = ", ".join(matched[:2])
    return f"相关词: {compact}"


def _source_reason(item: EventItem) -> str:
    meta = item.meta or {}
    if item.source == "github":
        stars = int(meta.get("stargazers_count", 0) or 0)
        return f"stars={stars}" if stars else ""
    if item.source == "hackernews":
        points = int(meta.get("points", 0) or 0)
        comments = int(meta.get("num_comments", 0) or 0)
        if points or comments:
            return f"points={points}, comments={comments}"
        return ""
    if item.source == "reddit":
        score = int(meta.get("score", 0) or 0)
        comments = int(meta.get("num_comments", 0) or 0)
        if score or comments:
            return f"score={score}, comments={comments}"
        return ""
    return ""


def _event_reason(item: EventItem, config: DetectorConfig) -> str:
    meta = item.meta or {}
    description = ""
    if isinstance(meta.get("description"), str):
        description = meta.get("description") or ""
    text = f"{item.title} {description}".strip()

    category_key = str(meta.get("category") or "").strip()
    category_reason = ""
    if category_key:
        # Best-effort reason from current classifier; keeps explanation stable even if meta only had category.
        category_key, category_reason = _event_category_explain(item)
    else:
        category_key, category_reason = _event_category_explain(item)
    parts: list[str] = []

    if category_key != "other":
        parts.append(category_reason)
    topic_reason = _topic_reason(text, config, item.topic)
    if topic_reason:
        parts.append(topic_reason)
    source_reason = _source_reason(item)
    if source_reason:
        parts.append(source_reason)

    if not parts:
        return "信息来源入选"
    return "；".join(parts)


def _topic_keywords(topic: str) -> list[str]:
    normalized = _normalize_topic(topic)
    out: list[str] = _base_keywords(normalized)
    out.extend(sorted(_keyword_expansions(normalized)))
    return out


_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)


def _normalize_phrase(text: str) -> str:
    tokens = _TOKEN_RE.findall((text or "").lower())
    return " ".join(tokens)


def _token_set(text: str) -> set[str]:
    return set(_TOKEN_RE.findall((text or "").lower()))


_CATEGORY_ORDER: list[tuple[str, str]] = [
    ("product_release", "产品发布"),
    ("funding_ma", "融资并购"),
    ("policy_reg", "政策监管"),
    ("open_source", "开源发布"),
    ("research_paper", "研究论文"),
    ("pricing_biz", "价格与商业模式"),
    ("security_incident", "安全事件"),
    ("other", "其他"),
]


def _contains_keyword(tokens: set[str], phrase: str, keyword: str) -> bool:
    kw = _normalize_phrase(keyword)
    if not kw:
        return False
    if " " in kw:
        return kw in phrase
    return kw in tokens


def _category_score(text: str, keywords: list[str]) -> tuple[int, int]:
    tokens = _token_set(text)
    phrase = _normalize_phrase(text)
    hits = 0
    hit_length = 0
    for kw in keywords:
        if _contains_keyword(tokens, phrase, kw):
            hits += 1
            hit_length += len(_normalize_phrase(kw))
    return hits, hit_length


def _matched_keywords(text: str, keywords: list[str]) -> list[str]:
    tokens = _token_set(text)
    phrase = _normalize_phrase(text)
    matched: list[str] = []
    for kw in keywords:
        if _contains_keyword(tokens, phrase, kw):
            matched.append(kw)
    return matched


def _event_category_explain(item: EventItem) -> tuple[str, str]:
    meta = item.meta or {}
    domain = str(meta.get("domain", "") or "")
    text = f"{item.title} {item.url} {domain}".strip()

    if item.source == "github" or "github.com/" in (item.url or ""):
        return "open_source", "包含 GitHub 仓库/开源链接"
    if item.source == "arxiv" or "arxiv.org/" in (item.url or ""):
        return "research_paper", "来自 arXiv 当天新论文"

    title_lower = (item.title or "").lower()
    if title_lower.startswith("show hn:"):
        # Default show HN items to product unless clearly open-source
        if "github.com/" in (item.url or ""):
            return "open_source", "Show HN + GitHub 链接"
        return "product_release", "Show HN 产品发布"

    product_keywords = [
        "launch",
        "launches",
        "launched",
        "unveil",
        "unveils",
        "introduce",
        "introduces",
        "release",
        "released",
        "beta",
        "rollout",
        "推出",
        "发布",
        "上线",
        "开通",
    ]
    funding_keywords = [
        "raises",
        "raise",
        "funding",
        "series a",
        "series b",
        "seed",
        "round",
        "acquire",
        "acquires",
        "acquired",
        "acquisition",
        "merger",
        "ipo",
        "融资",
        "并购",
        "收购",
        "投资",
        "上市",
    ]
    policy_keywords = [
        "regulation",
        "regulatory",
        "law",
        "bill",
        "ban",
        "government",
        "antitrust",
        "sec",
        "ftc",
        "eu",
        "compliance",
        "gdpr",
        "policy",
        "guidance",
        "监管",
        "政策",
        "法案",
        "条例",
        "合规",
    ]
    open_source_keywords = [
        "open source",
        "oss",
        "github",
        "apache",
        "mit license",
        "released on github",
        "开源",
    ]
    paper_keywords = [
        "arxiv",
        "paper",
        "preprint",
        "dataset",
        "benchmark",
        "论文",
        "预印本",
        "基准",
        "数据集",
    ]
    pricing_keywords = [
        "pricing",
        "price",
        "subscription",
        "plan",
        "freemium",
        "billing",
        "monetization",
        "revenue",
        "business model",
        "paying",
        "customers",
        "涨价",
        "降价",
        "定价",
        "收费",
        "套餐",
        "订阅",
    ]
    security_keywords = [
        "breach",
        "vulnerability",
        "cve",
        "exploit",
        "hacked",
        "hack",
        "ransomware",
        "security incident",
        "漏洞",
        "攻击",
        "泄露",
        "入侵",
    ]

    keyword_map: dict[str, list[str]] = {
        "product_release": product_keywords,
        "funding_ma": funding_keywords,
        "policy_reg": policy_keywords,
        "open_source": open_source_keywords,
        "research_paper": paper_keywords,
        "pricing_biz": pricing_keywords,
        "security_incident": security_keywords,
    }

    best = "other"
    best_score = (0, 0)
    best_matched: list[str] = []
    for key, keywords in keyword_map.items():
        score = _category_score(text, keywords)
        if score > best_score:
            best = key
            best_score = score
            best_matched = _matched_keywords(text, keywords)

    if best_score == (0, 0):
        return "other", "未命中分类关键词"

    # If it matches security and something else, put security later unless it's the strongest signal.
    security_score = _category_score(text, security_keywords)
    if best != "security_incident" and security_score[0] > 0:
        if best_score[0] < security_score[0] and best_score[1] < security_score[1]:
            matched = _matched_keywords(text, security_keywords)[:2]
            if matched:
                return "security_incident", f"命中安全关键词: {', '.join(matched)}"
            return "security_incident", "命中安全关键词"

    matched = best_matched[:2]
    if matched:
        return best, f"命中关键词: {', '.join(matched)}"
    return best, "命中分类关键词"


def _topic_match_score(text: str, topic: str, extra_keywords: list[str]) -> tuple[int, int, int]:
    normalized = _normalize_topic(topic)
    base = _base_keywords(normalized)
    expansions = sorted(_keyword_expansions(normalized))
    expansions.extend(extra_keywords or [])

    tokens = _token_set(text)
    phrase = _normalize_phrase(text)

    def hit(kw: str) -> bool:
        kw_norm = _normalize_phrase(kw)
        if not kw_norm:
            return False
        if " " in kw_norm:
            return kw_norm in phrase
        return kw_norm in tokens

    base_hits = sum(1 for kw in base if hit(kw))
    expansion_hits = sum(1 for kw in expansions if hit(kw))

    hit_length = 0
    for kw in base:
        if hit(kw):
            hit_length += len(_normalize_phrase(kw))
    for kw in expansions:
        if hit(kw):
            hit_length += len(_normalize_phrase(kw))

    return base_hits, base_hits + expansion_hits, hit_length


def _assign_topic(title: str, topics: Iterable[str], config: DetectorConfig) -> str:
    best_topic = "综合"
    best_score = (0, 0, 0)
    for topic in topics:
        score = _topic_match_score(title, topic, _custom_keywords(config, topic))
        if score > best_score:
            best_score = score
            best_topic = topic
    return best_topic


def _looks_like_spam(title: str, url: str) -> bool:
    text = f"{title} {url}".lower()
    spam_markers = [
        "coupon",
        "promo",
        "referral",
        "discount",
        "giveaway",
        "temu",
        "code €",
        "code $",
        "100 off",
    ]
    return any(marker in text for marker in spam_markers)


def _low_signal_for_social(item: EventItem) -> bool:
    if item.source == "reddit":
        meta = item.meta or {}
        score = int(meta.get("score", 0) or 0)
        comments = int(meta.get("num_comments", 0) or 0)
        return score <= 1 and comments <= 0
    if item.source == "hackernews":
        meta = item.meta or {}
        points = int(meta.get("points", 0) or 0)
        comments = int(meta.get("num_comments", 0) or 0)
        return points <= 0 and comments <= 0
    return False


def _github_token() -> str | None:
    token = os.getenv("GITHUB_TOKEN", "").strip()
    return token or None


def _http_timeout() -> float:
    try:
        return float(os.getenv("HTTP_TIMEOUT", "20"))
    except ValueError:
        return 20.0


def _combine_gdelt_query(topics: list[str]) -> str:
    cleaned: list[str] = []
    for item in topics:
        sanitized = " ".join(part for part in (item or "").split() if len(part) >= 3).strip()
        if sanitized:
            cleaned.append(sanitized)
    if not cleaned:
        return ""
    if len(cleaned) == 1:
        return cleaned[0]
    return "(" + " OR ".join(cleaned) + ")"


def _combine_gdelt_or_terms(terms: list[str]) -> str:
    cleaned: list[str] = []
    for term in terms:
        t = " ".join(part for part in (term or "").split() if len(part) >= 3).strip()
        if not t:
            continue
        # Avoid multi-word phrases for GDELT query safety; keep the first token.
        cleaned.append(t.split()[0])
    cleaned = list(dict.fromkeys(cleaned))
    if not cleaned:
        return ""
    if len(cleaned) == 1:
        return cleaned[0]
    return "(" + " OR ".join(cleaned) + ")"


async def collect_events(config: DetectorConfig) -> list[EventItem]:
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=config.daily_days)
    max_per_topic = config.daily_max_items_per_topic
    github_token = _github_token()

    timeout = httpx.Timeout(_http_timeout())
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        gdelt_task = fetch_gdelt_articles(
            client=client,
            topics=config.topics,
            since=since,
            until=now,
            max_records=config.daily_max_gdelt_items,
        )

        biz_tasks = []
        if config.daily_enable_biz_event_queries and config.daily_gdelt_biz_query_max_records > 0:
            topics_query = _combine_gdelt_query(config.topics)
            if topics_query:
                biz_tasks = [
                    fetch_gdelt_articles_for_query(
                        client=client,
                        query=f"{topics_query} {_combine_gdelt_or_terms(terms)}",
                        since=since,
                        until=now,
                        max_records=config.daily_gdelt_biz_query_max_records,
                    )
                    for terms in [
                        [
                            "funding",
                            "raises",
                            "acquire",
                            "acquisition",
                            "merger",
                            "ipo",
                            "融资",
                            "并购",
                            "收购",
                            "上市",
                        ],
                        [
                            "regulation",
                            "law",
                            "bill",
                            "ban",
                            "compliance",
                            "antitrust",
                            "policy",
                            "监管",
                            "政策",
                            "法案",
                            "合规",
                        ],
                        [
                            "pricing",
                            "price",
                            "subscription",
                            "plan",
                            "billing",
                            "revenue",
                            "定价",
                            "订阅",
                            "套餐",
                            "收费",
                            "涨价",
                            "降价",
                        ],
                    ]
                ]

        paper_tasks = []
        if config.daily_max_papers_per_topic > 0:
            for topic in config.topics:
                query = _arxiv_query(config, topic)
                if not query:
                    continue
                paper_tasks.append(
                    fetch_arxiv_papers(
                        client=client,
                        topic=topic,
                        search_query=query,
                        since=since,
                        max_items=config.daily_max_papers_per_topic,
                    )
                )

        hn_tasks = [
            fetch_hn_stories(client=client, topic=topic, since=since, max_items=max_per_topic)
            for topic in config.topics
        ]
        reddit_tasks = [
            fetch_reddit_posts(client=client, topic=topic, since=since, max_items=max_per_topic)
            for topic in config.topics
        ]
        github_tasks = [
            fetch_github_repositories(
                client=client,
                topic=topic,
                since=since,
                max_items=max_per_topic,
                token=github_token,
            )
            for topic in config.topics
        ]

        gathered = await asyncio.gather(
            gdelt_task,
            asyncio.gather(*hn_tasks),
            asyncio.gather(*reddit_tasks),
            asyncio.gather(*github_tasks),
            *(biz_tasks or []),
        )
        gdelt_items = gathered[0]
        hn_items = gathered[1]
        reddit_items = gathered[2]
        github_items = gathered[3]
        biz_items = gathered[4:] if biz_tasks else []
        paper_items: list[list[EventItem]] = []
        if paper_tasks:
            paper_items = await asyncio.gather(*paper_tasks)

    items: list[EventItem] = []
    items.extend(gdelt_items)
    for group in biz_items:
        items.extend(group)
    for group in hn_items:
        items.extend(group)
    for group in reddit_items:
        items.extend(group)
    for group in github_items:
        items.extend(group)
    for group in paper_items:
        items.extend(group)

    # De-duplicate by URL and re-assign topic by title/description relevance.
    dedup: dict[str, EventItem] = {}
    for item in items:
        if _looks_like_spam(item.title, item.url):
            continue

        description = ""
        if item.meta and isinstance(item.meta.get("description"), str):
            description = item.meta.get("description") or ""
        text = f"{item.title} {description}".strip()

        best_topic = _assign_topic(text, config.topics, config)
        score = (
            _topic_match_score(text, best_topic, _custom_keywords(config, best_topic))
            if best_topic != "综合"
            else (0, 0, 0)
        )
        hits = score[1]

        # For sources that tend to be noisy with generic terms, drop if not clearly relevant.
        if item.source in {"reddit", "hackernews"} and hits <= 0:
            continue
        if item.source in {"reddit", "hackernews"} and _low_signal_for_social(item):
            continue

        assigned_topic = best_topic if hits > 0 else (item.topic or "综合")
        key, _ = _event_category_explain(item)
        normalized_meta = dict(item.meta or {})
        normalized_meta["category"] = key
        normalized = EventItem(
            source=item.source,
            topic=assigned_topic,
            title=item.title,
            url=item.url,
            published_at=item.published_at,
            meta=normalized_meta,
        )

        existing = dedup.get(item.url)
        if existing is None:
            dedup[item.url] = normalized
            continue

        existing_description = ""
        if existing.meta and isinstance(existing.meta.get("description"), str):
            existing_description = existing.meta.get("description") or ""
        existing_text = f"{existing.title} {existing_description}".strip()

        existing_best_topic = _assign_topic(existing_text, config.topics, config)
        existing_score = (
            _topic_match_score(
                existing_text,
                existing_best_topic,
                _custom_keywords(config, existing_best_topic),
            )
            if existing_best_topic != "综合"
            else (0, 0, 0)
        )
        existing_hits = existing_score[1]
        if hits > existing_hits:
            dedup[item.url] = normalized

    out = list(dedup.values())

    def sort_key(row: EventItem) -> tuple[int, float]:
        priority = {"gdelt": 0, "hackernews": 1, "reddit": 2, "github": 3}.get(row.source, 9)
        ts = row.published_at.timestamp() if row.published_at else 0.0
        return priority, -ts

    out.sort(key=sort_key)

    # Enforce a global per-topic cap (across all sources) to keep the report readable.
    limited: list[EventItem] = []
    topic_counts: dict[str, int] = {}
    topic_paper_counts: dict[str, int] = {}
    for item in out:
        cap = config.daily_max_items_per_topic
        if item.topic == "综合":
            cap = min(cap, 4)
        count = topic_counts.get(item.topic, 0)
        is_paper = item.source == "arxiv" or (item.meta or {}).get("category") == "research_paper"
        if is_paper:
            paper_cap = max(0, int(config.daily_max_papers_per_topic))
            paper_count = topic_paper_counts.get(item.topic, 0)
            if paper_cap <= 0 or paper_count >= paper_cap:
                continue
            # Keep up to `daily_max_papers_per_topic` papers per topic even if the topic hit its global cap.
            topic_paper_counts[item.topic] = paper_count + 1
        else:
            if count >= cap:
                continue
        topic_counts[item.topic] = count + 1
        limited.append(item)

    return limited


def _band_cn(band: str) -> str:
    return {"high": "高", "medium": "中", "low": "低"}.get(band, band)


def _confidence_cn(confidence: float) -> str:
    if confidence >= 0.75:
        return "高"
    if confidence >= 0.5:
        return "中"
    return "低"


def render_daily_event_report_markdown(
    *,
    events: list[EventItem],
    insights: list[TopicInsight],
    config: DetectorConfig,
    as_of: datetime | None = None,
) -> str:
    as_of = as_of or datetime.now()
    date_label = as_of.strftime("%Y-%m-%d")

    lines: list[str] = []
    lines.append(f"# 每日行业事件与机会洞察（{date_label}）")
    lines.append("")
    lines.append(
        f"本报告覆盖近 {config.daily_days} 天内，与 topic 列表相关的新闻/讨论/开源动态，"
        "并给出可执行的洞察与机会建议。"
    )
    lines.append("")

    insight_map = {item.topic: item for item in insights}

    def event_score(row: EventItem) -> int:
        meta = row.meta or {}
        if row.source == "github":
            return int(meta.get("stargazers_count", 0) or 0)
        if row.source == "hackernews":
            return int(meta.get("points", 0) or 0) + 2 * int(meta.get("num_comments", 0) or 0)
        if row.source == "reddit":
            return int(meta.get("score", 0) or 0) + 2 * int(meta.get("num_comments", 0) or 0)
        return 0

    def event_sort_key(row: EventItem) -> tuple[int, float]:
        ts = row.published_at.timestamp() if row.published_at else 0.0
        return event_score(row), ts

    by_topic: dict[str, list[EventItem]] = {}
    for item in events:
        by_topic.setdefault(item.topic or "综合", []).append(item)

    lines.append("## 机会洞察（重点）")
    lines.append("")
    lines.append("### 机会建议（可执行）")
    lines.append("")

    def insight_rank(item: TopicInsight) -> tuple[float, float, float]:
        band_score = {"high": 3.0, "medium": 2.0, "low": 1.0}.get(item.opportunity_band, 1.0)
        return band_score + float(item.confidence), float(item.opportunity_score), float(item.confidence)

    top_insights = sorted(insights, key=insight_rank, reverse=True)[:3]
    if not top_insights:
        lines.append("- 无（insights 为空）")
        lines.append("")
    else:
        for idx, insight in enumerate(top_insights, start=1):
            evidence_rows = by_topic.get(insight.topic, [])[:2]
            evidence_titles = "；".join(row.title for row in evidence_rows) if evidence_rows else ""
            lines.append(f"#### {idx}. {insight.topic}")
            lines.append(f"{insight.one_line_thesis}")
            lines.append("")
            lines.append(f"- 机会判断: {_band_cn(insight.opportunity_band)} | 类型: {insight.insight_type} | 置信度: {_confidence_cn(insight.confidence)}")
            lines.append(f"- 目标客群: {insight.target_customer}")
            lines.append(f"- 首个可卖功能: {insight.first_sellable_feature}")
            if evidence_titles:
                lines.append(f"- 今日触发事件: {evidence_titles}")
            lines.append("- 24h 验证动作: 找 10 个目标用户，约 3 个访谈；用 1 页 landing page + 1 个 demo 截图验证是否愿意付费试用。")
            lines.append("- 7 天里程碑: 做出可跑通的单流程（含人工兜底），拿到 1 个付费或明确的采购流程。")
            lines.append("")

    lines.append("### 洞察入选逻辑")
    lines.append("")
    lines.append("- 技术向：优先“论文(arXiv)/开源(GitHub)/开发者社区(HN)”等技术落地信号，且尽量跨来源。")
    lines.append("- 商业向：优先“产品发布/融资并购/政策监管/定价与商业模式”这类会改变采购与竞争的信号。")
    lines.append("")

    daily_insights = select_daily_insights(events=events, topic_insights=insights, max_per_angle=2)
    tech_insights = [item for item in daily_insights if item.angle == "tech"]
    biz_insights = [item for item in daily_insights if item.angle == "business"]

    def render_insight_table(title: str, rows: list) -> None:
        lines.append(f"### {title}")
        lines.append("")
        if not rows:
            lines.append("- 无")
            lines.append("")
            return
        lines.append("| Topic | 结论 | 机会 | 入选原因 | 证据 |")
        lines.append("|---|---|---|---|---|")
        for item in rows:
            evidence = []
            for idx, url in enumerate(item.evidence_urls[:3], start=1):
                evidence.append(f"[证据{idx}]({url})")
            evidence_cell = "<br>".join(evidence) if evidence else "-"
            lines.append(
                f"| {item.topic} | {item.thesis} | {item.opportunity} | {item.why_selected} | {evidence_cell} |"
            )
        lines.append("")

    render_insight_table("洞察（技术向）", tech_insights)
    render_insight_table("洞察（商业向）", biz_insights)

    paper_events = [
        row
        for row in events
        if row.source == "arxiv"
        or ("arxiv.org/" in (row.url or ""))
        or (row.meta and row.meta.get("category") == "research_paper")
    ]
    if paper_events:
        lines.append("### 论文快读")
        lines.append("")
        lines.append("| Topic | 论文 | Abstract 总结 | PDF 总结 |")
        lines.append("|---|---|---|---|")
        for item in paper_events[:5]:
            meta = item.meta or {}
            abstract_sum = str(meta.get("abstract_summary") or meta.get("summary") or "").strip()
            pdf_sum = str(meta.get("pdf_summary") or "").strip()
            if not abstract_sum:
                abstract_sum = "-"
            if not pdf_sum:
                pdf_sum = "-"
            abstract_sum = abstract_sum.replace("\n", "<br>")
            pdf_sum = pdf_sum.replace("\n", "<br>")
            lines.append(f"| {item.topic} | [{item.title}]({item.url}) | {abstract_sum} | {pdf_sum} |")
        lines.append("")

    lines.append("### 关键洞察（补充）")
    lines.append("")

    def topic_rank_key(kv: tuple[str, list[EventItem]]) -> tuple[int, int]:
        _, rows = kv
        sources = {row.source for row in rows}
        return len(sources), len(rows)

    ranked_topics = [topic for topic, _ in sorted(by_topic.items(), key=topic_rank_key, reverse=True)]
    top_topics = ranked_topics[:3] if ranked_topics else []

    if not top_topics:
        lines.append("- 今日事件较少或较分散，建议扩大 topic 或拆分为更具体的子方向。")
    else:
        for topic in top_topics:
            rows = by_topic.get(topic, [])[:3]
            sources = {row.source for row in rows}
            insight = insight_map.get(topic)
            headline = "；".join(row.title for row in rows[:2]) if rows else "（暂无）"
            lines.append(
                f"- **{topic}**：今天的讨论主要集中在「{headline}」。"
                f"（覆盖来源: {', '.join(sorted(sources)) or 'n/a'}）"
            )
            if insight:
                lines.append(
                    f"  - 机会判断: {_band_cn(insight.opportunity_band)} | 类型: {insight.insight_type} | 置信度: {_confidence_cn(insight.confidence)}"
                )
                lines.append(f"  - 提示: {insight.one_line_thesis}")

    lines.append("")
    lines.append("## 行业事件（证据）")
    lines.append("")

    if not events:
        lines.append("暂无可用事件数据（可能是 API 限流或关键词过窄）。")
        lines.append("")
        lines.append("（不影响机会评分与洞察生成，但会影响“证据链接”和“商业事件栏目”的丰富度。）")
        lines.append("")
    else:
        lines.append("### 今日大事一览")
        lines.append("")

    by_category: dict[str, list[EventItem]] = {key: [] for key, _ in _CATEGORY_ORDER}
    category_reason: dict[str, str] = {}
    for item in events:
        key, reason = _event_category_explain(item)
        by_category.setdefault(key, []).append(item)
        category_reason[item.url] = reason

    def short(text: str, limit: int = 72) -> str:
        text = (text or "").strip()
        if len(text) <= limit:
            return text
        return text[: max(0, limit - 1)].rstrip() + "…"

    def render_category(key: str, title: str, limit: int) -> None:
        rows = sorted(by_category.get(key, []), key=event_sort_key, reverse=True)[:limit]
        lines.append(f"#### {title}")
        lines.append("")
        if not rows:
            lines.append("- 无")
            lines.append("")
            return

        lines.append("| 时间(UTC) | Topic | 来源 | 事件 | 原因 |")
        lines.append("|---|---|---|---|---|")
        for item in rows:
            time_hint = ""
            if item.published_at:
                time_hint = item.published_at.astimezone(timezone.utc).strftime("%m-%d %H:%MZ")

            source_cn = {"gdelt": "新闻", "hackernews": "HN", "reddit": "Reddit", "github": "GitHub"}.get(
                item.source, item.source
            )
            reason = _event_reason(item, config)
            title_link = f"[{item.title}]({item.url})"
            lines.append(f"| {time_hint} | {item.topic} | {source_cn} | {title_link} | {reason} |")
        lines.append("")

    if events:
        lines.append("| 栏目 | 条数 | Top事件 | Top原因 |")
        lines.append("|---|---:|---|---|")
        for key, label in _CATEGORY_ORDER:
            rows = by_category.get(key, [])
            top = "无"
            top_reason = "无"
            if rows:
                best = sorted(rows, key=event_sort_key, reverse=True)[0]
                top = f"[{short(best.title)}]({best.url})"
                top_reason = short(_event_reason(best, config), limit=60)
            lines.append(f"| {label} | {len(rows)} | {top} | {top_reason} |")

        lines.append("")
        lines.append("### 今日大事件（按栏目）")
        lines.append("")

        render_category("product_release", "产品发布", limit=5)
        render_category("funding_ma", "融资并购", limit=5)
        render_category("policy_reg", "政策监管", limit=5)
        render_category("open_source", "开源发布", limit=5)
        render_category("research_paper", "研究论文", limit=5)
        render_category("pricing_biz", "价格与商业模式", limit=5)
        # Put security later as requested.
        render_category("security_incident", "安全事件（靠后）", limit=3)
        render_category("other", "其他", limit=3)

    lines.append("## 配置与口径")
    lines.append("")
    lines.append(f"- topics: {len(config.topics)} 个")
    lines.append(f"- daily_days: {config.daily_days}")
    lines.append(f"- 每 topic 抓取上限: {config.daily_max_items_per_topic}")
    lines.append(f"- GDELT 抓取上限: {config.daily_max_gdelt_items}")
    lines.append(f"- GDELT 商业补齐查询: {'开启' if config.daily_enable_biz_event_queries else '关闭'}")

    return "\n".join(lines)
