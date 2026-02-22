from datetime import datetime, timezone

from src.opportunity_detector.config import DetectorConfig
from src.opportunity_detector.events import render_daily_event_report_markdown
from src.opportunity_detector.insights import TopicInsight
from src.opportunity_detector.models import EventItem


def test_render_daily_event_report_has_sections() -> None:
    config = DetectorConfig(
        topics=["ai coding agent", "smb finance ops"],
        daily_days=1,
        daily_max_items_per_topic=3,
        daily_max_gdelt_items=12,
    )
    now = datetime(2026, 2, 16, 12, 0, tzinfo=timezone.utc)
    events = [
        EventItem(
            source="gdelt",
            topic="ai coding agent",
            title="AI coding agent market update",
            url="https://example.com/news1",
            published_at=now,
        ),
        EventItem(
            source="hackernews",
            topic="ai coding agent",
            title="Which AI coding tools are you using?",
            url="https://example.com/hn1",
            published_at=now,
            meta={"points": 10},
        ),
    ]
    insights = [
        TopicInsight(
            topic="ai coding agent",
            industry_guess="developer_tools",
            opportunity_score=0.5,
            opportunity_band="medium",
            insight_type="crowded_hot_market",
            confidence=0.75,
            one_line_thesis="需求强但供给密集，需要垂直化。",
            target_customer="平台工程负责人",
            first_sellable_feature="发布风险审计助手",
            evidence="sources=gdelt/hn/github/reddit",
            suggested_play="选择细分场景做 MVP",
        )
    ]

    report = render_daily_event_report_markdown(events=events, insights=insights, config=config, as_of=now)

    assert "每日行业事件与机会洞察" in report
    assert "今日大事一览" in report
    assert "| 栏目 | 条数 | Top事件 | Top原因 |" in report
    assert "今日大事件（按栏目）" in report
    assert "产品发布" in report
    assert "融资并购" in report
    assert "政策监管" in report
    assert "开源发布" in report
    assert "价格与商业模式" in report
    assert "| 时间(UTC) | Topic | 来源 | 事件 | 原因 |" in report
    assert "洞察入选逻辑" in report
    assert "洞察（技术向）" in report
    assert "洞察（商业向）" in report
    assert "机会建议" in report
