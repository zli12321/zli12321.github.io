"""Bibliographic sources: Semantic Scholar and OpenAlex.

These add venue and citation context that arXiv alone cannot provide, and they
catch camera-ready versions of papers that were first seen as preprints.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

from .. import http
from ..models import PROVENANCE_LIVE, RadarItem
from ..textutil import day_key, payload_hash, truncate
from .base import FetchContext, clean_metrics

S2_SOURCE = "Semantic Scholar"
OPENALEX_SOURCE = "OpenAlex"
S2_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
S2_FIELDS = (
    "title,abstract,venue,year,publicationDate,externalIds,url,openAccessPdf,"
    "citationCount,influentialCitationCount,authors.name"
)
OPENALEX_URL = "https://api.openalex.org/works"


def _s2_headers() -> dict[str, str]:
    key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "").strip()
    return {"x-api-key": key} if key else {}


def _s2_item(record: Mapping[str, Any], *, ctx: FetchContext, query: str) -> RadarItem | None:
    title = " ".join(str(record.get("title") or "").split())
    if not title:
        return None
    external = record.get("externalIds") or {}
    paper_id = str(record.get("paperId") or external.get("DOI") or title)[:120]

    artifact_urls: list[str] = []
    if external.get("ArXiv"):
        artifact_urls.append(f"https://arxiv.org/abs/{external['ArXiv']}")
    if external.get("DOI"):
        artifact_urls.append(f"https://doi.org/{external['DOI']}")
    open_access = record.get("openAccessPdf") or {}
    if isinstance(open_access, Mapping) and open_access.get("url"):
        artifact_urls.append(str(open_access["url"]))

    authors = [
        str(author.get("name"))
        for author in record.get("authors") or []
        if isinstance(author, Mapping) and author.get("name")
    ]

    facets: dict[str, Any] = {"query": query}
    if external.get("ArXiv"):
        facets["arxiv_id"] = external["ArXiv"]
    if external.get("DOI"):
        facets["doi"] = external["DOI"]
    if record.get("year"):
        facets["year"] = record["year"]

    return RadarItem(
        source=S2_SOURCE,
        source_id=paper_id,
        title=title,
        url=str(record.get("url") or (artifact_urls[0] if artifact_urls else "")),
        published_at=record.get("publicationDate")
        or (f"{record['year']}-01-01" if record.get("year") else None),
        summary=truncate(" ".join(str(record.get("abstract") or "").split()), 1400),
        authors=authors[:24],
        artifact_urls=artifact_urls,
        metrics=clean_metrics(
            {
                "citations": record.get("citationCount"),
                "influential_citations": record.get("influentialCitationCount"),
            }
        ),
        facets=facets,
        venue=" ".join(str(record.get("venue") or "").split()),
        event_kind="published",
        provenance=PROVENANCE_LIVE,
        discovered_at=ctx.now_iso,
        retrieved_at=ctx.now_iso,
        raw_payload_hash=payload_hash(
            {"paperId": paper_id, "citations": record.get("citationCount")}
        ),
    )


def fetch_semantic_scholar(spec: Mapping[str, Any], ctx: FetchContext) -> list[RadarItem]:
    page_size = min(100, int(spec.get("page_size", 100)))
    max_requests = int(spec.get("max_requests", 3))
    by_id: dict[str, RadarItem] = {}
    failures: list[str] = []
    requests = 0

    for query in spec.get("searches") or []:
        if requests >= max_requests:
            break
        requests += 1
        params = {
            "query": str(query),
            "limit": page_size,
            "fields": S2_FIELDS,
            "publicationDateOrYear": f"{day_key(ctx.since)}:",
        }
        try:
            payload = http.get_json(S2_URL, params=params, headers=_s2_headers())
        except http.HttpError as error:
            failures.append(f"{query}: {error}")
            continue
        for record in (payload or {}).get("data") or []:
            item = _s2_item(record, ctx=ctx, query=str(query))
            if item and item.url and item.source_id not in by_id:
                by_id[item.source_id] = item

    if not by_id and failures:
        raise http.HttpError("; ".join(failures[:3]))
    return list(by_id.values())


def _reconstruct_abstract(inverted: Mapping[str, Any] | None) -> str:
    """OpenAlex ships abstracts as a word -> positions index."""
    if not isinstance(inverted, Mapping) or not inverted:
        return ""
    positions: list[tuple] = []
    for word, indexes in inverted.items():
        if not isinstance(indexes, list):
            continue
        for index in indexes:
            try:
                positions.append((int(index), str(word)))
            except (TypeError, ValueError):
                continue
    if not positions:
        return ""
    positions.sort()
    return truncate(" ".join(word for _, word in positions), 1400)


def fetch_openalex(spec: Mapping[str, Any], ctx: FetchContext) -> list[RadarItem]:
    per_page = min(200, int(spec.get("per_page", 50)))
    mailto = os.environ.get("OPENALEX_MAILTO", "").strip()
    by_id: dict[str, RadarItem] = {}
    failures: list[str] = []

    for query in spec.get("searches") or []:
        params: dict[str, Any] = {
            "search": str(query),
            "filter": f"from_publication_date:{day_key(ctx.since)}",
            "per-page": per_page,
            "sort": "publication_date:desc",
        }
        if mailto:
            params["mailto"] = mailto
        try:
            payload = http.get_json(OPENALEX_URL, params=params)
        except http.HttpError as error:
            failures.append(f"{query}: {error}")
            continue
        for record in (payload or {}).get("results") or []:
            item = _openalex_item(record, ctx=ctx, query=str(query))
            if item and item.source_id not in by_id:
                by_id[item.source_id] = item

    if not by_id and failures:
        raise http.HttpError("; ".join(failures[:3]))
    return list(by_id.values())


def _openalex_item(record: Mapping[str, Any], *, ctx: FetchContext, query: str) -> RadarItem | None:
    title = " ".join(str(record.get("display_name") or record.get("title") or "").split())
    identifier = str(record.get("id") or "").strip()
    if not title or not identifier:
        return None

    authors: list[str] = []
    organizations: list[str] = []
    for authorship in record.get("authorships") or []:
        if not isinstance(authorship, Mapping):
            continue
        author = authorship.get("author") or {}
        if isinstance(author, Mapping) and author.get("display_name"):
            authors.append(str(author["display_name"]))
        for institution in authorship.get("institutions") or []:
            if isinstance(institution, Mapping) and institution.get("display_name"):
                name = str(institution["display_name"])
                if name not in organizations:
                    organizations.append(name)

    primary = record.get("primary_location") or {}
    venue = ""
    if isinstance(primary, Mapping):
        source_info = primary.get("source") or {}
        if isinstance(source_info, Mapping):
            venue = str(source_info.get("display_name") or "")

    artifact_urls = []
    if record.get("doi"):
        artifact_urls.append(str(record["doi"]))
    if isinstance(primary, Mapping) and primary.get("pdf_url"):
        artifact_urls.append(str(primary["pdf_url"]))

    return RadarItem(
        source=OPENALEX_SOURCE,
        source_id=identifier.rsplit("/", 1)[-1],
        title=title,
        url=str(record.get("doi") or identifier),
        published_at=record.get("publication_date"),
        summary=_reconstruct_abstract(record.get("abstract_inverted_index")),
        authors=authors[:24],
        organizations=organizations[:8],
        artifact_urls=artifact_urls,
        metrics=clean_metrics({"citations": record.get("cited_by_count")}),
        facets={"query": query, "type": record.get("type") or ""},
        venue=venue,
        event_kind="published",
        provenance=PROVENANCE_LIVE,
        discovered_at=ctx.now_iso,
        retrieved_at=ctx.now_iso,
        raw_payload_hash=payload_hash({"id": identifier}),
    )
