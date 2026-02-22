from src.opportunity_detector.config import Weights
from src.opportunity_detector.fusion import score_topics
from src.opportunity_detector.models import TopicRawSignals


def test_score_topics_sorted_desc() -> None:
    rows = [
        TopicRawSignals(topic="a", gdelt_recent=10, hn_recent=5, github_total=50, github_recent=10),
        TopicRawSignals(topic="b", gdelt_recent=6, hn_recent=3, github_total=10, github_recent=2),
        TopicRawSignals(topic="c", gdelt_recent=1, hn_recent=1, github_total=100, github_recent=1),
    ]

    scored = score_topics(rows, Weights(demand=0.45, momentum=0.35, competition=0.20))

    assert len(scored) == 3
    assert scored[0].opportunity_score >= scored[1].opportunity_score >= scored[2].opportunity_score
