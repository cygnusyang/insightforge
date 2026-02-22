from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any


@dataclass
class TopicRawSignals:
    topic: str
    gdelt_total: int = 0
    gdelt_recent: int = 0
    hn_total: int = 0
    hn_recent: int = 0
    github_total: int = 0
    github_recent: int = 0
    reddit_total: int = 0
    reddit_recent: int = 0

    @property
    def demand_raw(self) -> float:
        return float(
            self.gdelt_recent
            + self.hn_recent
            + self.reddit_recent
            + (0.5 * self.github_recent)
        )

    @property
    def momentum_raw(self) -> float:
        source_ratios = []
        for recent, total in [
            (self.gdelt_recent, self.gdelt_total),
            (self.hn_recent, self.hn_total),
            (self.reddit_recent, self.reddit_total),
            (self.github_recent, self.github_total),
        ]:
            if total > 0:
                source_ratios.append(recent / total)
        if not source_ratios:
            return 0.0
        return sum(source_ratios) / len(source_ratios)

    @property
    def competition_raw(self) -> float:
        return float(self.github_total)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["demand_raw"] = round(self.demand_raw, 4)
        data["momentum_raw"] = round(self.momentum_raw, 6)
        data["competition_raw"] = round(self.competition_raw, 4)
        return data


@dataclass
class TopicScored:
    topic: str
    demand_raw: float
    momentum_raw: float
    competition_raw: float
    demand_norm: float
    momentum_norm: float
    competition_norm: float
    opportunity_score: float

    def to_dict(self) -> dict:
        return {
            "topic": self.topic,
            "demand_raw": round(self.demand_raw, 6),
            "momentum_raw": round(self.momentum_raw, 6),
            "competition_raw": round(self.competition_raw, 6),
            "demand_norm": round(self.demand_norm, 6),
            "momentum_norm": round(self.momentum_norm, 6),
            "competition_norm": round(self.competition_norm, 6),
            "opportunity_score": round(self.opportunity_score, 6),
        }


@dataclass(frozen=True)
class EventItem:
    source: str
    topic: str
    title: str
    url: str
    published_at: datetime | None = None
    meta: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "topic": self.topic,
            "title": self.title,
            "url": self.url,
            "published_at": self.published_at.isoformat() if self.published_at else "",
            "meta": self.meta or {},
        }
