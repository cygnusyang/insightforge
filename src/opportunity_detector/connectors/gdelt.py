from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import time
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_fixed

from ..error import DataCollectionError, handle_error
from ..models import EventItem

# 配置日志
logger = logging.getLogger(__name__)


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


_GDELT_RATE_LOCK = asyncio.Lock()
_GDELT_LAST_CALL_AT = 0.0
_GDELT_MIN_INTERVAL_SECONDS = 5.6


async def _gdelt_rate_limit() -> None:
    global _GDELT_LAST_CALL_AT
    async with _GDELT_RATE_LOCK:
        now = time.monotonic()
        sleep_for = _GDELT_MIN_INTERVAL_SECONDS - (now - _GDELT_LAST_CALL_AT)
        if sleep_for > 0:
            await asyncio.sleep(sleep_for)
        _GDELT_LAST_CALL_AT = time.monotonic()


def _sanitize_query(query: str) -> str:
    parts = [part for part in (query or "").split() if len(part) >= 3]
    return " ".join(parts).strip()


def _cache_dir() -> Path:
    return Path(".cache") / "gdelt"


def _cache_key(parts: list[str]) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return digest


def _load_cache(key: str) -> dict | None:
    path = _cache_dir() / f"{key}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _save_cache(key: str, payload: dict) -> None:
    try:
        _cache_dir().mkdir(parents=True, exist_ok=True)
        (_cache_dir() / f"{key}.json").write_text(json.dumps(payload), encoding="utf-8")
    except Exception:
        return


@retry(stop=stop_after_attempt(3), wait=wait_fixed(7.0), reraise=True)
async def _fetch_timeline(client: httpx.AsyncClient, query: str) -> dict:
    url = "https://api.gdeltproject.org/api/v2/doc/doc"
    params = {
        "query": query,
        "mode": "timelinevolraw",
        "format": "json",
        "maxrecords": 250,
    }
    cache_key = _cache_key(["timelinevolraw", query, datetime.now(timezone.utc).strftime("%Y-%m-%d")])
    cached = _load_cache(cache_key)
    if cached is not None:
        return cached
    await _gdelt_rate_limit()
    response = await client.get(url, params=params)
    response.raise_for_status()
    content_type = (response.headers.get("content-type") or "").lower()
    if "application/json" not in content_type:
        raise ValueError("GDELT response was not JSON")
    payload = response.json()
    if isinstance(payload, dict):
        _save_cache(cache_key, payload)
    return payload


@retry(stop=stop_after_attempt(3), wait=wait_fixed(7.0), reraise=True)
async def _fetch_articles(client: httpx.AsyncClient, query: str, start: str, end: str, max_records: int) -> dict:
    url = "https://api.gdeltproject.org/api/v2/doc/doc"
    params = {
        "query": query,
        "mode": "artlist",
        "format": "json",
        "maxrecords": max_records,
        "sort": "hybridrel",
        "startdatetime": start,
        "enddatetime": end,
    }
    cache_key = _cache_key(["artlist", query, start, end, str(max_records)])
    cached = _load_cache(cache_key)
    if cached is not None:
        return cached
    await _gdelt_rate_limit()
    response = await client.get(url, params=params)
    response.raise_for_status()
    content_type = (response.headers.get("content-type") or "").lower()
    if "application/json" not in content_type:
        raise ValueError("GDELT response was not JSON")
    payload = response.json()
    if isinstance(payload, dict):
        _save_cache(cache_key, payload)
    return payload


def _combine_topics(topics: list[str]) -> str:
    cleaned: list[str] = []
    for item in topics:
        sanitized = _sanitize_query(item)
        if sanitized:
            cleaned.append(sanitized)
    if not cleaned:
        return ""
    if len(cleaned) == 1:
        return cleaned[0]
    # GDELT requires OR expressions to be wrapped by a single pair of parentheses,
    # and does not allow nesting parentheses around individual terms.
    return "(" + " OR ".join(cleaned) + ")"


async def fetch_gdelt_counts(
    client: httpx.AsyncClient,
    topic: str,
    window_days: int,
    recent_days: int,
) -> tuple[int, int]:
    """获取GDELT数据计数
    
    Returns:
        tuple[int, int]: (历史窗口总数, 近期窗口总数)
    """
    now = datetime.now(timezone.utc)
    since_window = now - timedelta(days=window_days)
    since_recent = now - timedelta(days=recent_days)

    try:
        payload = await _fetch_timeline(client, topic)
    except Exception as e:
        sanitized = _sanitize_query(topic)
        if not sanitized or sanitized == topic:
            logger.warning(f"GDELT: 无法处理主题 '{topic}'，返回0")
            return 0, 0
        try:
            payload = await _fetch_timeline(client, sanitized)
        except Exception as e2:
            logger.warning(f"GDELT: 无法处理主题 '{topic}' (尝试 '{sanitized}')，返回0: {e2}")
            return 0, 0

    timeline = payload.get("timeline", [])
    points: list[dict] = []
    if isinstance(timeline, list) and timeline:
        first = timeline[0]
        if isinstance(first, dict) and isinstance(first.get("data"), list):
            points = first.get("data", [])
        else:
            points = timeline  # best-effort for older payload shapes
    elif isinstance(timeline, dict) and isinstance(timeline.get("data"), list):
        points = timeline.get("data", [])

    window_total = 0
    recent_total = 0

    for point in points:
        raw_date = str(point.get("date", ""))
        if len(raw_date) < 8:
            continue
        try:
            parsed = datetime.strptime(raw_date[:8], "%Y%m%d").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if parsed < since_window:
            continue

        volume = _safe_int(point.get("value", 0))
        window_total += volume
        if parsed >= since_recent:
            recent_total += volume

    return max(window_total, 0), max(recent_total, 0)


async def fetch_gdelt_articles(
    client: httpx.AsyncClient,
    topics: list[str],
    since: datetime,
    until: datetime,
    max_records: int = 12,
) -> list[EventItem]:
    query = _combine_topics(topics)
    if not query:
        return []

    start = since.astimezone(timezone.utc).strftime("%Y%m%d%H%M%S")
    end = until.astimezone(timezone.utc).strftime("%Y%m%d%H%M%S")

    try:
        payload = await _fetch_articles(client, query, start=start, end=end, max_records=max_records)
    except Exception:
        return []

    articles = payload.get("articles", [])
    if not isinstance(articles, list):
        return []

    out: list[EventItem] = []
    for item in articles:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        url = str(item.get("url", "")).strip()
        if not title or not url:
            continue
        published_at = None
        seendate = str(item.get("seendate", "")).strip()
        if seendate:
            try:
                published_at = datetime.strptime(seendate[:15], "%Y%m%dT%H%M%S").replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                published_at = None
        out.append(
            EventItem(
                source="gdelt",
                topic="",
                title=title,
                url=url,
                published_at=published_at,
                meta={
                    "domain": item.get("domain", ""),
                    "language": item.get("language", ""),
                    "sourcecountry": item.get("sourcecountry", ""),
                },
            )
        )
        if len(out) >= max_records:
            break

    return out


async def fetch_gdelt_articles_for_query(
    client: httpx.AsyncClient,
    query: str,
    since: datetime,
    until: datetime,
    max_records: int = 12,
) -> list[EventItem]:
    query = (query or "").strip()
    if not query:
        return []

    start = since.astimezone(timezone.utc).strftime("%Y%m%d%H%M%S")
    end = until.astimezone(timezone.utc).strftime("%Y%m%d%H%M%S")

    try:
        payload = await _fetch_articles(client, query, start=start, end=end, max_records=max_records)
    except Exception:
        return []

    articles = payload.get("articles", [])
    if not isinstance(articles, list):
        return []

    out: list[EventItem] = []
    for item in articles:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        url = str(item.get("url", "")).strip()
        if not title or not url:
            continue
        published_at = None
        seendate = str(item.get("seendate", "")).strip()
        if seendate:
            try:
                published_at = datetime.strptime(seendate[:15], "%Y%m%dT%H%M%S").replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                published_at = None
        out.append(
            EventItem(
                source="gdelt",
                topic="",
                title=title,
                url=url,
                published_at=published_at,
                meta={
                    "domain": item.get("domain", ""),
                    "language": item.get("language", ""),
                    "sourcecountry": item.get("sourcecountry", ""),
                    "gdelt_query": query,
                },
            )
        )
        if len(out) >= max_records:
            break

    return out


async def fetch_gdelt_articles_for_topic(
    client: httpx.AsyncClient,
    topic: str,
    since: datetime,
    until: datetime,
    max_records: int = 3,
) -> list[EventItem]:
    query = _sanitize_query(topic)
    if not query:
        return []

    start = since.astimezone(timezone.utc).strftime("%Y%m%d%H%M%S")
    end = until.astimezone(timezone.utc).strftime("%Y%m%d%H%M%S")

    try:
        payload = await _fetch_articles(client, query, start=start, end=end, max_records=max_records)
    except Exception:
        return []

    articles = payload.get("articles", [])
    if not isinstance(articles, list):
        return []

    out: list[EventItem] = []
    for item in articles:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        url = str(item.get("url", "")).strip()
        if not title or not url:
            continue
        published_at = None
        seendate = str(item.get("seendate", "")).strip()
        if seendate:
            try:
                published_at = datetime.strptime(seendate[:15], "%Y%m%dT%H%M%S").replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                published_at = None
        out.append(
            EventItem(
                source="gdelt",
                topic=topic,
                title=title,
                url=url,
                published_at=published_at,
                meta={
                    "domain": item.get("domain", ""),
                    "language": item.get("language", ""),
                    "sourcecountry": item.get("sourcecountry", ""),
                },
            )
        )
        if len(out) >= max_records:
            break

    return out
