"""arXiv: category RSS plus an optional Atom query API.

Category RSS is the default because it is free, unauthenticated, and returns the
full daily announcement for a category. The Atom query API supports keyword
search but rate limits hard, so it stays off unless explicitly enabled.
"""

from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET
from collections.abc import Mapping
from typing import Any

from .. import http
from ..models import PROVENANCE_LIVE, RadarItem
from ..textutil import isoformat, parse_datetime, payload_hash, truncate
from .base import FetchContext

SOURCE_NAME = "arXiv"
RSS_URL = "https://rss.arxiv.org/rss/{category}"
ATOM_URL = "https://export.arxiv.org/api/query"

_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "dc": "http://purl.org/dc/elements/1.1/",
    "arxiv": "http://arxiv.org/schemas/atom",
}
_ANNOUNCE = re.compile(r"^arXiv:(?P<id>\S+)\s+Announce Type:\s*(?P<kind>[\w-]+)\s*", re.IGNORECASE)
_ABSTRACT = re.compile(r"Abstract:\s*(?P<body>.*)", re.IGNORECASE | re.DOTALL)
_ARXIV_ID = re.compile(r"(\d{4}\.\d{4,5})(v\d+)?")

_EVENT_KINDS = {
    "new": "published",
    "cross": "cross-listed",
    "replace": "updated",
    "replace-cross": "updated",
}


def _text(element: ET.Element | None) -> str:
    if element is None or element.text is None:
        return ""
    return " ".join(element.text.split())


def _arxiv_id(value: str) -> str:
    match = _ARXIV_ID.search(value or "")
    return match.group(1) if match else ""


def _split_authors(raw: str) -> list[str]:
    if not raw:
        return []
    parts = re.split(r",| and ", raw)
    return [part.strip() for part in parts if part.strip()][:24]


def _parse_rss(body: str, category: str, ctx: FetchContext) -> list[RadarItem]:
    try:
        root = ET.fromstring(body)
    except ET.ParseError as error:
        raise http.HttpError(f"arXiv RSS for {category} was not valid XML: {error}") from error

    channel = root.find("channel")
    if channel is None:
        return []
    channel_date = _text(channel.find("lastBuildDate")) or _text(channel.find("pubDate"))

    items: list[RadarItem] = []
    for entry in channel.findall("item"):
        title = _text(entry.find("title"))
        link = _text(entry.find("link"))
        if not title or not link:
            continue

        raw_description = entry.findtext("description") or ""
        announce = _ANNOUNCE.search(raw_description.strip())
        event_kind = "published"
        identifier = _arxiv_id(link)
        if announce:
            identifier = _arxiv_id(announce.group("id")) or identifier
            event_kind = _EVENT_KINDS.get(announce.group("kind").lower(), "published")

        abstract_match = _ABSTRACT.search(raw_description)
        summary = ""
        if abstract_match:
            summary = truncate(" ".join(abstract_match.group("body").split()), 1400)

        published_moment = parse_datetime(_text(entry.find("pubDate")) or channel_date)
        categories = [_text(node) for node in entry.findall("category")]
        authors = _split_authors(_text(entry.find("dc:creator", _NS)))

        items.append(
            RadarItem(
                source=SOURCE_NAME,
                source_id=identifier or link,
                title=title,
                url=f"https://arxiv.org/abs/{identifier}" if identifier else link,
                published_at=isoformat(published_moment) if published_moment else None,
                summary=summary,
                authors=authors,
                event_kind=event_kind,
                provenance=PROVENANCE_LIVE,
                facets={"arxiv_categories": [c for c in categories if c], "feed": category},
                artifact_urls=[f"https://arxiv.org/pdf/{identifier}"] if identifier else [],
                discovered_at=ctx.now_iso,
                retrieved_at=ctx.now_iso,
                raw_payload_hash=payload_hash({"title": title, "link": link, "feed": category}),
            )
        )
    return items


def _parse_atom(body: str, ctx: FetchContext) -> list[RadarItem]:
    try:
        root = ET.fromstring(body)
    except ET.ParseError as error:
        raise http.HttpError(f"arXiv Atom response was not valid XML: {error}") from error

    items: list[RadarItem] = []
    for entry in root.findall("atom:entry", _NS):
        title = _text(entry.find("atom:title", _NS))
        raw_id = _text(entry.find("atom:id", _NS))
        identifier = _arxiv_id(raw_id)
        if not title or not identifier:
            continue
        published = _text(entry.find("atom:published", _NS))
        updated = _text(entry.find("atom:updated", _NS))
        summary = truncate(_text(entry.find("atom:summary", _NS)), 1400)
        authors = [_text(node.find("atom:name", _NS)) for node in entry.findall("atom:author", _NS)]
        primary = entry.find("arxiv:primary_category", _NS)
        artifact_urls = []
        for link in entry.findall("atom:link", _NS):
            href = link.get("href") or ""
            if link.get("title") == "pdf" and href:
                artifact_urls.append(href)

        items.append(
            RadarItem(
                source=SOURCE_NAME,
                source_id=identifier,
                title=title,
                url=f"https://arxiv.org/abs/{identifier}",
                published_at=published or None,
                updated_at=updated or None,
                summary=summary,
                authors=[a for a in authors if a][:24],
                event_kind="updated" if updated and updated != published else "published",
                provenance=PROVENANCE_LIVE,
                facets={
                    "arxiv_categories": [
                        node.get("term", "") for node in entry.findall("atom:category", _NS)
                    ],
                    "primary_category": primary.get("term", "") if primary is not None else "",
                    "feed": "atom",
                },
                artifact_urls=artifact_urls,
                discovered_at=ctx.now_iso,
                retrieved_at=ctx.now_iso,
                raw_payload_hash=payload_hash({"id": identifier, "updated": updated}),
            )
        )
    return items


def fetch(spec: Mapping[str, Any], ctx: FetchContext) -> list[RadarItem]:
    delay = float(spec.get("request_delay_seconds", 3))
    collected: list[RadarItem] = []
    failures: list[str] = []

    categories = [str(c).strip() for c in (spec.get("rss_categories") or []) if str(c).strip()]
    for index, category in enumerate(categories):
        if index:
            time.sleep(delay)
        try:
            body = http.get_text(RSS_URL.format(category=category), accept="application/rss+xml")
        except http.HttpError as error:
            failures.append(f"{category}: {error}")
            continue
        collected.extend(_parse_rss(body, category, ctx))

    if spec.get("atom_enabled"):
        max_results = int(spec.get("atom_max_results", 100))
        for query in spec.get("atom_queries") or []:
            time.sleep(delay)
            params: dict[str, Any] = {
                "search_query": query,
                "start": 0,
                "max_results": max_results,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            }
            try:
                body = http.get_text(ATOM_URL, params=params, accept="application/atom+xml")
            except http.HttpError as error:
                failures.append(f"atom query: {error}")
                continue
            collected.extend(_parse_atom(body, ctx))

    if not collected and failures:
        raise http.HttpError("; ".join(failures[:3]))
    return collected
