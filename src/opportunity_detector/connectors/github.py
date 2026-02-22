from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus

import httpx
from tenacity import retry, stop_after_attempt, wait_fixed

from ..models import EventItem


def _build_headers(token: str | None) -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "opportunity-detector/0.1",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


@retry(stop=stop_after_attempt(2), wait=wait_fixed(1.0), reraise=True)
async def _search_repo_count(
    client: httpx.AsyncClient,
    topic: str,
    since_date: str,
    token: str | None,
) -> int:
    query = quote_plus(f"{topic} created:>{since_date}")
    url = f"https://api.github.com/search/repositories?q={query}&per_page=1"
    response = await client.get(url, headers=_build_headers(token))
    response.raise_for_status()
    payload = response.json()
    return int(payload.get("total_count", 0))


async def fetch_github_counts(
    client: httpx.AsyncClient,
    topic: str,
    window_days: int,
    recent_days: int,
    token: str | None = None,
) -> tuple[int, int]:
    now = datetime.now(timezone.utc)
    since_window = (now - timedelta(days=window_days)).strftime("%Y-%m-%d")
    since_recent = (now - timedelta(days=recent_days)).strftime("%Y-%m-%d")

    try:
        window_total = await _search_repo_count(client, topic, since_window, token)
        recent_total = await _search_repo_count(client, topic, since_recent, token)
    except Exception:
        return 0, 0

    return max(window_total, 0), max(recent_total, 0)


@retry(stop=stop_after_attempt(2), wait=wait_fixed(1.0), reraise=True)
async def _search_repositories(
    client: httpx.AsyncClient,
    topic: str,
    since_date: str,
    token: str | None,
    max_items: int,
) -> list[dict]:
    query = quote_plus(f"{topic} created:>{since_date}")
    url = f"https://api.github.com/search/repositories?q={query}&sort=stars&order=desc&per_page={max_items}"
    response = await client.get(url, headers=_build_headers(token))
    response.raise_for_status()
    payload = response.json()
    items = payload.get("items", [])
    if isinstance(items, list):
        return items
    return []


async def fetch_github_repositories(
    client: httpx.AsyncClient,
    topic: str,
    since: datetime,
    max_items: int = 3,
    token: str | None = None,
) -> list[EventItem]:
    since_date = since.astimezone(timezone.utc).strftime("%Y-%m-%d")
    try:
        items = await _search_repositories(
            client=client,
            topic=topic,
            since_date=since_date,
            token=token,
            max_items=max_items,
        )
    except Exception:
        return []

    out: list[EventItem] = []
    for item in items:
        title = (item.get("full_name") or "").strip()
        url = (item.get("html_url") or "").strip()
        if not title or not url:
            continue
        created_at = item.get("created_at")
        published_at = None
        if isinstance(created_at, str) and created_at:
            try:
                published_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except ValueError:
                published_at = None
        out.append(
            EventItem(
                source="github",
                topic=topic,
                title=title,
                url=url,
                published_at=published_at,
                meta={
                    "description": item.get("description", "") or "",
                    "stargazers_count": item.get("stargazers_count", 0),
                    "language": item.get("language", "") or "",
                },
            )
        )
        if len(out) >= max_items:
            break

    return out
