"""Hugging Face Hub: models, datasets, and the daily papers feed.

The Hub is where new VLM weights actually land, so it is the source that answers
"what shipped today". Search results are dominated by quantized re-uploads; the
`low_value` rules in config.yml demote those rather than hiding them, so the
funnel stays auditable.

Model cards are prose written by the publisher, but each one costs an extra
request, so only the freshest `card_limit` records get enriched.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .. import http
from ..models import PROVENANCE_LIVE, RadarItem
from ..textutil import day_key, days_ago, payload_hash, strip_markdown
from .base import FetchContext, clean_metrics, newest, owner_of

MODELS_SOURCE = "Hugging Face Models"
DATASETS_SOURCE = "Hugging Face Datasets"
PAPERS_SOURCE = "Hugging Face Papers"

API = "https://huggingface.co/api"
CARD_URL = "https://huggingface.co/{prefix}{repo_id}/raw/main/README.md"


def _card_text(repo_id: str, *, dataset: bool) -> str:
    prefix = "datasets/" if dataset else ""
    try:
        body = http.get_text(CARD_URL.format(prefix=prefix, repo_id=repo_id), retries=1, timeout=20)
    except http.HttpError:
        return ""
    return strip_markdown(body, limit=900)


def _search_repos(
    endpoint: str,
    *,
    search: str | None = None,
    pipeline_tag: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {
        "sort": "lastModified",
        "direction": -1,
        "limit": limit,
        "full": "true",
    }
    if search:
        params["search"] = search
    if pipeline_tag:
        params["pipeline_tag"] = pipeline_tag
    payload = http.get_json(f"{API}/{endpoint}", params=params)
    return payload if isinstance(payload, list) else []


def _repo_item(
    record: Mapping[str, Any],
    *,
    source: str,
    ctx: FetchContext,
    dataset: bool,
    query: str,
) -> RadarItem | None:
    repo_id = str(record.get("id") or record.get("modelId") or "").strip()
    if not repo_id:
        return None

    created = record.get("createdAt")
    modified = record.get("lastModified") or record.get("last_modified")
    card_data = record.get("cardData") or {}
    tags = [str(tag) for tag in (record.get("tags") or []) if isinstance(tag, (str, int))]

    kind = "datasets" if dataset else "models"
    url = f"https://huggingface.co/{'datasets/' if dataset else ''}{repo_id}"

    # A repository created inside the window is new; otherwise this is an update.
    event_kind = "published" if ctx.within_window(created) else "updated"

    facets: dict[str, Any] = {"tags": tags[:24], "query": query, "hub_kind": kind}
    for key in ("pipeline_tag", "library_name", "sha"):
        if record.get(key):
            facets[key] = record[key]
    if isinstance(card_data, Mapping):
        for key in ("license", "language", "task_categories", "base_model", "size_categories"):
            if card_data.get(key):
                facets[key] = card_data[key]

    return RadarItem(
        source=source,
        source_id=repo_id,
        title=repo_id,
        url=url,
        published_at=created or modified,
        updated_at=modified,
        summary="",  # filled in later for the freshest records only
        organizations=[owner_of(repo_id)] if owner_of(repo_id) else [],
        artifact_urls=[url],
        metrics=clean_metrics(
            {
                "downloads": record.get("downloads"),
                "likes": record.get("likes"),
            }
        ),
        facets=facets,
        event_kind=event_kind,
        provenance=PROVENANCE_LIVE,
        discovered_at=ctx.now_iso,
        retrieved_at=ctx.now_iso,
        raw_payload_hash=payload_hash(
            {"id": repo_id, "lastModified": modified, "downloads": record.get("downloads")}
        ),
    )


def _collect_repos(
    spec: Mapping[str, Any],
    ctx: FetchContext,
    *,
    endpoint: str,
    source: str,
    dataset: bool,
) -> list[RadarItem]:
    limit = int(spec.get("page_size", 100))
    by_id: dict[str, RadarItem] = {}
    failures: list[str] = []
    queries: list[Sequence[str]] = [("search", str(q)) for q in (spec.get("searches") or [])]
    queries += [("pipeline_tag", str(t)) for t in (spec.get("pipeline_tags") or [])]

    for key, value in queries:
        try:
            records = _search_repos(
                endpoint,
                search=value if key == "search" else None,
                pipeline_tag=value if key == "pipeline_tag" else None,
                limit=limit,
            )
        except http.HttpError as error:
            failures.append(f"{value}: {error}")
            continue
        for record in records:
            item = _repo_item(record, source=source, ctx=ctx, dataset=dataset, query=value)
            if item and item.source_id not in by_id:
                by_id[item.source_id] = item

    if not by_id and failures:
        raise http.HttpError("; ".join(failures[:3]))

    items = sorted(
        by_id.values(),
        key=lambda item: newest(item.updated_at, item.published_at) or "",
        reverse=True,
    )

    card_limit = int(spec.get("card_limit", 0))
    for item in items[:card_limit]:
        summary = _card_text(item.source_id, dataset=dataset)
        if summary:
            item.summary = summary
    return items


def fetch_models(spec: Mapping[str, Any], ctx: FetchContext) -> list[RadarItem]:
    return _collect_repos(spec, ctx, endpoint="models", source=MODELS_SOURCE, dataset=False)


def fetch_datasets(spec: Mapping[str, Any], ctx: FetchContext) -> list[RadarItem]:
    return _collect_repos(spec, ctx, endpoint="datasets", source=DATASETS_SOURCE, dataset=True)


def fetch_papers(spec: Mapping[str, Any], ctx: FetchContext) -> list[RadarItem]:
    """The community-voted daily papers feed: attention, with an abstract attached."""
    days = max(1, int(spec.get("days", 3)))
    by_id: dict[str, RadarItem] = {}
    failures: list[str] = []

    for offset in range(days):
        date = day_key(days_ago(ctx.now, offset))
        try:
            payload = http.get_json(f"{API}/daily_papers", params={"date": date})
        except http.HttpError as error:
            failures.append(f"{date}: {error}")
            continue
        if not isinstance(payload, list):
            continue
        for record in payload:
            item = _paper_item(record, ctx=ctx, listed_on=date)
            if item and item.source_id not in by_id:
                by_id[item.source_id] = item

    if not by_id and failures:
        raise http.HttpError("; ".join(failures[:3]))
    return list(by_id.values())


def _paper_item(
    record: Mapping[str, Any], *, ctx: FetchContext, listed_on: str
) -> RadarItem | None:
    paper = record.get("paper") if isinstance(record.get("paper"), Mapping) else record
    identifier = str(paper.get("id") or "").strip()
    title = " ".join(str(paper.get("title") or "").split())
    if not identifier or not title:
        return None

    authors = []
    for author in paper.get("authors") or []:
        if isinstance(author, Mapping):
            name = author.get("name") or author.get("fullname")
        else:
            name = author
        if name:
            authors.append(str(name))

    return RadarItem(
        source=PAPERS_SOURCE,
        source_id=identifier,
        title=title,
        url=f"https://huggingface.co/papers/{identifier}",
        published_at=paper.get("publishedAt") or record.get("publishedAt"),
        summary=" ".join(str(paper.get("summary") or "").split())[:1400],
        authors=authors[:24],
        artifact_urls=[f"https://arxiv.org/abs/{identifier}"],
        metrics=clean_metrics(
            {
                "upvotes": paper.get("upvotes"),
                "comments": record.get("numComments"),
            }
        ),
        facets={"listed_on": listed_on},
        event_kind="featured",
        provenance=PROVENANCE_LIVE,
        discovered_at=ctx.now_iso,
        retrieved_at=ctx.now_iso,
        raw_payload_hash=payload_hash({"id": identifier, "upvotes": paper.get("upvotes")}),
    )
