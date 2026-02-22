from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx
from tenacity import retry, stop_after_attempt, wait_fixed

from ..models import EventItem


@retry(stop=stop_after_attempt(2), wait=wait_fixed(0.8), reraise=True)
async def _search_posts(client: httpx.AsyncClient, topic: str, after: str | None) -> dict:
    url = "https://www.reddit.com/search.json"
    params = {
        "q": topic,
        "sort": "new",
        "t": "all",
        "limit": 100,
        "raw_json": 1,
        "include_over_18": "on",
    }
    if after:
        params["after"] = after
    headers = {"User-Agent": "opportunity-detector/0.1"}
    response = await client.get(url, params=params, headers=headers)
    response.raise_for_status()
    return response.json()


async def fetch_reddit_counts(
    client: httpx.AsyncClient,
    topic: str,
    window_days: int,
    recent_days: int,
) -> tuple[int, int]:
    now = datetime.now(timezone.utc)
    since_window = now - timedelta(days=window_days)
    since_recent = now - timedelta(days=recent_days)

    window_total = 0
    recent_total = 0
    after: str | None = None

    max_pages = 5
    for _ in range(max_pages):
        try:
            payload = await _search_posts(client, topic, after)
        except Exception:
            break

        data = payload.get("data", {}) or {}
        items = data.get("children", []) or []
        after = data.get("after")
        if not items:
            break

        oldest_created_at: datetime | None = None
        for item in items:
            created_utc = item.get("data", {}).get("created_utc")
            if created_utc is None:
                continue
            try:
                created_at = datetime.fromtimestamp(float(created_utc), tz=timezone.utc)
            except (TypeError, ValueError, OSError):
                continue

            if oldest_created_at is None or created_at < oldest_created_at:
                oldest_created_at = created_at

            if created_at >= since_window:
                window_total += 1
                if created_at >= since_recent:
                    recent_total += 1

        if oldest_created_at is not None and oldest_created_at < since_window:
            break
        if not after:
            break

    return max(window_total, 0), max(recent_total, 0)


async def fetch_reddit_posts(
    client: httpx.AsyncClient,
    topic: str,
    since: datetime,
    max_items: int = 3,
) -> list[EventItem]:
    since = since.astimezone(timezone.utc)
    after: str | None = None
    out: list[EventItem] = []

    max_pages = 5
    for _ in range(max_pages):
        try:
            payload = await _search_posts(client, topic, after)
        except Exception:
            break

        data = payload.get("data", {}) or {}
        items = data.get("children", []) or []
        after = data.get("after")
        if not items:
            break

        oldest_created_at: datetime | None = None
        for item in items:
            row = item.get("data", {}) or {}
            created_utc = row.get("created_utc")
            try:
                created_at = datetime.fromtimestamp(float(created_utc), tz=timezone.utc)
            except (TypeError, ValueError, OSError):
                continue

            if oldest_created_at is None or created_at < oldest_created_at:
                oldest_created_at = created_at

            if created_at < since:
                continue

            title = (row.get("title") or "").strip()
            url = (row.get("url") or "").strip()
            if not title or not url:
                continue
            out.append(
                EventItem(
                    source="reddit",
                    topic=topic,
                    title=title,
                    url=url,
                    published_at=created_at,
                    meta={
                        "subreddit": row.get("subreddit", ""),
                        "score": row.get("score", 0),
                        "num_comments": row.get("num_comments", 0),
                    },
                )
            )
            if len(out) >= max_items:
                return out

        if oldest_created_at is not None and oldest_created_at < since:
            break
        if not after:
            break

    return out
