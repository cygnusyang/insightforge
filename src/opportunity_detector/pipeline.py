from __future__ import annotations

import asyncio
import csv
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Tuple

import httpx

from .config import DetectorConfig
from .connectors import (
    fetch_gdelt_counts,
    fetch_github_counts,
    fetch_hn_counts,
    fetch_reddit_counts,
)
from .error import DataCollectionError, handle_error
from .fusion import score_topics
from .events import collect_events, render_daily_event_report_markdown
from .insights import (
    build_topic_insights,
    render_daily_brief_markdown,
    render_insights_markdown,
)
from .papers import build_paper_summaries, render_paper_summaries_markdown
from .models import TopicRawSignals, TopicScored

# 配置日志
logger = logging.getLogger(__name__)


def _http_timeout() -> float:
    try:
        return float(os.getenv("HTTP_TIMEOUT", "20"))
    except ValueError:
        return 20.0


def _github_token() -> str | None:
    token = os.getenv("GITHUB_TOKEN", "").strip()
    return token or None


async def _collect_topic(
    client: httpx.AsyncClient,
    topic: str,
    window_days: int,
    recent_days: int,
    github_token: str | None,
) -> Tuple[TopicRawSignals, list[str]]:
    """收集单个主题的信号数据
    
    Returns:
        Tuple[TopicRawSignals, list[str]]: 信号数据和警告列表
    """
    gdelt_task = fetch_gdelt_counts(client, topic, window_days, recent_days)
    hn_task = fetch_hn_counts(client, topic, window_days, recent_days)
    github_task = fetch_github_counts(client, topic, window_days, recent_days, github_token)
    reddit_task = fetch_reddit_counts(client, topic, window_days, recent_days)
    
    warnings: list[str] = []

    try:
        gdelt, hn, github, reddit = await asyncio.gather(
            gdelt_task, hn_task, github_task, reddit_task
        )
    except Exception as e:
        error = handle_error(e, context={"topic": topic, "source": "data_collection"})
        logger.error(f"收集主题 {topic} 数据失败: {error.message}")
        warnings.append(f"数据收集警告: {error.message}")
        # 返回默认值
        return (
            TopicRawSignals(topic=topic),
            warnings,
        )

    return (
        TopicRawSignals(
            topic=topic,
            gdelt_total=gdelt[0],
            gdelt_recent=gdelt[1],
            hn_total=hn[0],
            hn_recent=hn[1],
            github_total=github[0],
            github_recent=github[1],
            reddit_total=reddit[0],
            reddit_recent=reddit[1],
        ),
        warnings,
    )


async def collect_signals(config: DetectorConfig) -> list[TopicRawSignals]:
    """收集所有主题的信号数据
    
    Returns:
        list[TopicRawSignals]: 信号数据列表
    """
    timeout = httpx.Timeout(_http_timeout())
    token = _github_token()
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        tasks = [
            _collect_topic(
                client=client,
                topic=topic,
                window_days=config.window_days,
                recent_days=config.recent_days,
                github_token=token,
            )
            for topic in config.topics
        ]
        results = await asyncio.gather(*tasks)
        # 提取信号数据（忽略警告）
        return [result[0] for result in results]


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _write_report(path: Path, scored: list[TopicScored], config: DetectorConfig) -> None:
    lines: list[str] = []
    lines.append("# 机会探测报告")
    lines.append("")
    lines.append(f"- window_days: {config.window_days}")
    lines.append(f"- recent_days: {config.recent_days}")
    lines.append(
        "- weights: "
        f"demand={config.weights.demand}, "
        f"momentum={config.weights.momentum}, "
        f"competition={config.weights.competition}"
    )
    lines.append("")
    lines.append("## Top Opportunities")
    lines.append("")
    for idx, item in enumerate(scored, start=1):
        lines.append(
            f"{idx}. **{item.topic}** | score={item.opportunity_score:.4f} "
            f"(demand={item.demand_norm:.3f}, momentum={item.momentum_norm:.3f}, "
            f"competition={item.competition_norm:.3f})"
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def run_pipeline(config: DetectorConfig, out_dir: str | Path) -> tuple[list[TopicRawSignals], list[TopicScored]]:
    output_dir = Path(out_dir)
    raw_signals = asyncio.run(collect_signals(config))
    scored = score_topics(raw_signals, config.weights)
    insights = build_topic_insights(raw_signals, scored)
    events = asyncio.run(collect_events(config))
    as_of = datetime.now()
    events, paper_summaries = asyncio.run(
        build_paper_summaries(events=events, config=config, as_of=as_of)
    )

    raw_rows = [row.to_dict() for row in raw_signals]
    score_rows = [row.to_dict() for row in scored]
    insight_rows = [item.to_dict() for item in insights]
    event_rows = [item.to_dict() for item in events]
    paper_rows = [item.to_dict() for item in paper_summaries]

    _write_csv(output_dir / "signals.csv", raw_rows)
    _write_csv(output_dir / "opportunities.csv", score_rows)
    _write_csv(output_dir / "insights.csv", insight_rows)
    _write_csv(output_dir / "events.csv", event_rows)
    _write_csv(output_dir / "paper_summaries.csv", paper_rows)
    _write_report(output_dir / "report.md", scored, config)
    (output_dir / "insights.md").write_text(
        render_insights_markdown(insights), encoding="utf-8"
    )
    daily_content = render_daily_brief_markdown(
        insights,
        window_days=config.window_days,
        recent_days=config.recent_days,
        as_of=as_of,
    )
    (output_dir / "daily.md").write_text(daily_content, encoding="utf-8")
    dated_daily = output_dir / "daily" / f"{datetime.now().strftime('%Y-%m-%d')}.md"
    dated_daily.parent.mkdir(parents=True, exist_ok=True)
    dated_daily.write_text(daily_content, encoding="utf-8")

    daily_report = render_daily_event_report_markdown(
        events=events,
        insights=insights,
        config=config,
        as_of=as_of,
    )
    (output_dir / "daily_report.md").write_text(daily_report, encoding="utf-8")
    dated_daily_report = output_dir / "daily" / f"{datetime.now().strftime('%Y-%m-%d')}.report.md"
    dated_daily_report.write_text(daily_report, encoding="utf-8")

    (output_dir / "paper_summaries.md").write_text(
        render_paper_summaries_markdown(paper_summaries, as_of=as_of), encoding="utf-8"
    )

    return raw_signals, scored
