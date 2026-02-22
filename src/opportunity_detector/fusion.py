from __future__ import annotations

from typing import Iterable, List

from .config import Weights
from .models import TopicRawSignals, TopicScored


def _min_max_normalize(values: Iterable[float]) -> List[float]:
    sequence = list(values)
    if not sequence:
        return []
    minimum = min(sequence)
    maximum = max(sequence)
    if maximum == minimum:
        return [0.5 for _ in sequence]
    return [(item - minimum) / (maximum - minimum) for item in sequence]


def score_topics(raw_topics: list[TopicRawSignals], weights: Weights) -> list[TopicScored]:
    if not raw_topics:
        return []

    demand_norms = _min_max_normalize(item.demand_raw for item in raw_topics)
    momentum_norms = _min_max_normalize(item.momentum_raw for item in raw_topics)
    competition_norms = _min_max_normalize(item.competition_raw for item in raw_topics)

    scored: list[TopicScored] = []
    for index, row in enumerate(raw_topics):
        opportunity_score = (
            weights.demand * demand_norms[index]
            + weights.momentum * momentum_norms[index]
            + weights.competition * (1.0 - competition_norms[index])
        )
        scored.append(
            TopicScored(
                topic=row.topic,
                demand_raw=row.demand_raw,
                momentum_raw=row.momentum_raw,
                competition_raw=row.competition_raw,
                demand_norm=demand_norms[index],
                momentum_norm=momentum_norms[index],
                competition_norm=competition_norms[index],
                opportunity_score=opportunity_score,
            )
        )

    scored.sort(key=lambda item: item.opportunity_score, reverse=True)
    return scored
