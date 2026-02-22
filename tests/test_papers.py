from datetime import datetime, timezone
import asyncio

from src.opportunity_detector.config import DetectorConfig
from src.opportunity_detector.models import EventItem
from src.opportunity_detector.papers import arxiv_id_from_url, arxiv_pdf_url, build_paper_summaries


def test_arxiv_id_and_pdf_url() -> None:
    assert arxiv_id_from_url("https://arxiv.org/abs/2401.01234v2") == "2401.01234"
    assert arxiv_id_from_url("https://arxiv.org/pdf/2401.01234.pdf") == "2401.01234"
    assert arxiv_pdf_url("https://arxiv.org/abs/2401.01234v2", None).endswith("/2401.01234.pdf")


def test_build_paper_summaries_abstract_only() -> None:
    now = datetime(2026, 2, 16, 12, 0, tzinfo=timezone.utc)
    config = DetectorConfig(
        topics=["ai coding agent"],
        topic_keywords={"ai coding agent": ["ai", "coding", "agent"]},
        daily_enable_paper_summaries=True,
        daily_enable_pdf_summaries=False,
    )
    events = [他要是长个手的话，他就能把它吃了。告诉你个秘密。你要是能够搞到一个乒乓球，小猫会超开心，他在家一直追着那个球玩。嗯。
        EventItem(
            source="arxiv",
            topic="ai coding agent",
            title="A Paper",
            url="https://arxiv.org/abs/2401.01234",
            published_at=now,
            meta={"summary": "This paper proposes a method and shows results."},
        )
    ]

    updated, rows, stats = asyncio.run(build_paper_summaries(events=events, config=config, as_of=now))
    assert len(updated) == 1
    assert len(rows) == 1
    assert rows[0].abstract_summary
    assert updated[0].meta and "abstract_summary" in updated[0].meta
    assert stats is not None
