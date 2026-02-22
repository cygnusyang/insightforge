from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode
import xml.etree.ElementTree as ET

import httpx
from tenacity import retry, stop_after_attempt, wait_fixed

from ..models import EventItem


_ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


def _safe_text(node: ET.Element | None, path: str) -> str:
    if node is None:
        return ""
    found = node.find(path, _ATOM_NS)
    if found is None or found.text is None:
        return ""
    return found.text.strip()


def _safe_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _compact_summary(text: str, limit: int = 240) -> str:
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: max(0, limit - 1)].rstrip() + "…"


@retry(stop=stop_after_attempt(2), wait=wait_fixed(0.8), reraise=True)
async def _fetch_feed(client: httpx.AsyncClient, search_query: str, max_results: int) -> str:
    base = "http://export.arxiv.org/api/query"
    query = urlencode(
        {
            "search_query": search_query,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "start": 0,
            "max_results": max_results,
        }
    )
    url = f"{base}?{query}"
    response = await client.get(url, headers={"User-Agent": "opportunity-detector/0.1"})
    response.raise_for_status()
    return response.text


async def fetch_arxiv_papers(
    client: httpx.AsyncClient,
    topic: str,
    search_query: str,
    since: datetime,
    max_items: int = 3,
) -> list[EventItem]:
    since = since.astimezone(timezone.utc)
    try:
        xml_text = await _fetch_feed(client, search_query=search_query, max_results=max(10, max_items * 4))
    except Exception:
        return []

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    entries = root.findall("atom:entry", _ATOM_NS)
    out: list[EventItem] = []
    for entry in entries:
        paper_title = _safe_text(entry, "atom:title")
        summary = _safe_text(entry, "atom:summary")
        published = _safe_datetime(_safe_text(entry, "atom:published"))
        if not paper_title or published is None:
            continue
        if published < since:
            continue

        links = entry.findall("atom:link", _ATOM_NS)
        url = ""
        pdf_url = ""
        for link in links:
            href = link.attrib.get("href", "").strip()
            rel = link.attrib.get("rel", "").strip()
            link_type = (link.attrib.get("type", "") or "").strip().lower()
            link_title = (link.attrib.get("title", "") or "").strip().lower()
            if href and link_type == "application/pdf":
                pdf_url = href
            if href and link_title == "pdf":
                pdf_url = href
            if href and (rel == "alternate" or not rel):
                url = href
                break
        if not url:
            url = _safe_text(entry, "atom:id")
        if not url:
            continue

        authors = []
        for author in entry.findall("atom:author", _ATOM_NS):
            name = _safe_text(author, "atom:name")
            if name:
                authors.append(name)

        categories = []
        for cat in entry.findall("atom:category", _ATOM_NS):
            term = (cat.attrib.get("term") or "").strip()
            if term:
                categories.append(term)

        out.append(
            EventItem(
                source="arxiv",
                topic=topic,
                title=paper_title,
                url=url,
                published_at=published,
                meta={
                    "authors": authors[:5],
                    "categories": categories[:3],
                    "summary": _compact_summary(summary),
                    "pdf_url": pdf_url,
                },
            )
        )
        if len(out) >= max_items:
            break

    return out
