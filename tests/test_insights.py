from src.opportunity_detector.insights import build_topic_insights
from src.opportunity_detector.models import TopicRawSignals, TopicScored


def test_build_topic_insights_outputs_actionable_fields() -> None:
    raw = [
        TopicRawSignals(
            topic="clinic management saas",
            gdelt_total=10,
            gdelt_recent=7,
            hn_total=20,
            hn_recent=12,
            github_total=15,
            github_recent=8,
            reddit_total=30,
            reddit_recent=20,
        )
    ]
    scored = [
        TopicScored(
            topic="clinic management saas",
            demand_raw=100.0,
            momentum_raw=0.8,
            competition_raw=15.0,
            demand_norm=0.9,
            momentum_norm=0.9,
            competition_norm=0.2,
            opportunity_score=0.82,
        )
    ]

    insights = build_topic_insights(raw, scored)

    assert len(insights) == 1
    assert insights[0].opportunity_band == "high"
    assert insights[0].insight_type == "fast_growing_white_space"
    assert insights[0].confidence > 0
    assert len(insights[0].one_line_thesis) > 0
    assert len(insights[0].target_customer) > 0
    assert len(insights[0].first_sellable_feature) > 0
    assert insights[0].industry_guess == "healthcare"
    assert "诊所" in insights[0].target_customer
    assert len(insights[0].suggested_play) > 0


def test_build_topic_insights_general_topic_has_industry_guess() -> None:
    raw = [TopicRawSignals(topic="generic workflow platform")]
    scored = [
        TopicScored(
            topic="generic workflow platform",
            demand_raw=10.0,
            momentum_raw=0.2,
            competition_raw=5.0,
            demand_norm=0.4,
            momentum_norm=0.2,
            competition_norm=0.3,
            opportunity_score=0.38,
        )
    ]

    insights = build_topic_insights(raw, scored)

    assert insights[0].industry_guess == "general_b2b"


def test_early_signal_uses_industry_template() -> None:
    raw = [
        TopicRawSignals(
            topic="clinic intake automation",
            gdelt_total=0,
            gdelt_recent=0,
            hn_total=0,
            hn_recent=0,
            github_total=2,
            github_recent=0,
            reddit_total=20,
            reddit_recent=20,
        )
    ]
    scored = [
        TopicScored(
            topic="clinic intake automation",
            demand_raw=20.0,
            momentum_raw=1.0,
            competition_raw=2.0,
            demand_norm=0.2,
            momentum_norm=0.9,
            competition_norm=0.2,
            opportunity_score=0.56,
        )
    ]

    insights = build_topic_insights(raw, scored)

    assert insights[0].insight_type == "early_signal_niche"
    assert insights[0].industry_guess == "healthcare"
    assert "诊所" in insights[0].target_customer
    assert "MVP" in insights[0].first_sellable_feature
