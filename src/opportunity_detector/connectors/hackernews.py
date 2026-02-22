from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus

import httpx
from tenacity import retry, stop_after_attempt, wait_fixed

from ..models import EventItem


@retry(stop=stop_after_attempt(2), wait=wait_fixed(0.8), reraise=True)
async def _search_count(client: httpx.AsyncClient, topic: str, since_unix: int) -> int:
    encoded = quote_plus(topic)
    url = (
        "https://hn.algolia.com/api/v1/search_by_date"
        f"?query={encoded}&tags=story&hitsPerPage=0&numericFilters=created_at_i>{since_unix}"
    )
    response = await client.get(url)
    response.raise_for_status()
    payload = response.json()
    return int(payload.get("nbHits", 0))


@retry(stop=stop_after_attempt(2), wait=wait_fixed(0.8), reraise=True)
async def _search_stories(
    client: httpx.AsyncClient, topic: str, since_unix: int, max_items: int
) -> list[dict]:
    encoded = quote_plus(topic)
    url = (
        "https://hn.algolia.com/api/v1/search_by_date"
        f"?query={encoded}&tags=story&hitsPerPage={max_items}"
        f"&numericFilters=created_at_i>{since_unix}"
    )
    response = await client.get(url)
    response.raise_for_status()
    payload = response.json()
    hits = payload.get("hits", [])
    if isinstance(hits, list):
        return hits
    return []


async def fetch_hn_counts(
    client: httpx.AsyncClient,
    topic: str,
    window_days: int,
    recent_days: int,
) -> tuple[int, int]:
    now = datetime.now(timezone.utc)
    since_window = int((now - timedelta(days=window_days)).timestamp())
    since_recent = int((now - timedelta(days=recent_days)).timestamp())

    try:
        window_total = await _search_count(client, topic, since_window)
        recent_total = await _search_count(client, topic, since_recent)
    except Exception:
        return 0, 0

    return max(window_total, 0), max(recent_total, 0)


async def fetch_hn_stories(
    client: httpx.AsyncClient,
    topic: str,
    since: datetime,
    max_items: int = 3,
) -> list[EventItem]:
    since_unix = int(since.replace(tzinfo=timezone.utc).timestamp())
    try:
        hits = await _search_stories(client, topic, since_unix, max_items=max_items)
    except Exception:
        return []

    out: list[EventItem] = []
    for hit in hits:
        title = (hit.get("title") or "").strip()
        url = (hit.get("url") or "").strip()
        if not title or not url:
            continue
        created_at_i = hit.get("created_at_i")
        published_at = None
        try:
            published_at = datetime.fromtimestamp(float(created_at_i), tz=timezone.utc)
        except (TypeError, ValueError, OSError):
            published_at = None
        out.append(
            EventItem(
                source="hackernews",
                topic=topic,
                title=title,
                url=url,
                published_at=published_at,
                meta={
                    "points": hit.get("points", 0),
                    "num_comments": hit.get("num_comments", 0),
                    "author": hit.get("author", ""),
                },
            )
        )
        if len(out) >= max_items:
            break
    return out
