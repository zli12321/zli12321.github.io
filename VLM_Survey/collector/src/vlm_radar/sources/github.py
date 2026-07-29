"""GitHub: repository search and releases from an allowlist of VLM projects.

Search finds new projects. Releases catch the moment an established harness or
model family ships a version, which is often the only public signal for work that
never gets a paper.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .. import http
from ..models import PROVENANCE_LIVE, RadarItem
from ..textutil import payload_hash, strip_markdown, truncate
from .base import FetchContext, clean_metrics, owner_of

SEARCH_SOURCE = "GitHub"
RELEASES_SOURCE = "GitHub Releases"
SEARCH_URL = "https://api.github.com/search/repositories"
RELEASES_URL = "https://api.github.com/repos/{repo}/releases"


def _repo_item(record: Mapping[str, Any], *, ctx: FetchContext, query: str) -> RadarItem | None:
    full_name = str(record.get("full_name") or "").strip()
    url = record.get("html_url")
    if not full_name or not url:
        return None

    owner = record.get("owner") or {}
    description = " ".join(str(record.get("description") or "").split())
    homepage = str(record.get("homepage") or "").strip()
    license_info = record.get("license") or {}

    artifact_urls = [url]
    if homepage.startswith("http"):
        artifact_urls.append(homepage)

    created = record.get("created_at")
    event_kind = "published" if ctx.within_window(created) else "updated"

    facets: dict[str, Any] = {"query": query}
    if record.get("topics"):
        facets["topics"] = list(record["topics"])[:20]
    if record.get("language"):
        facets["language"] = record["language"]
    if isinstance(license_info, Mapping) and license_info.get("spdx_id"):
        facets["license"] = license_info["spdx_id"]

    return RadarItem(
        source=SEARCH_SOURCE,
        source_id=full_name,
        title=full_name,
        url=url,
        published_at=created,
        updated_at=record.get("pushed_at") or record.get("updated_at"),
        summary=truncate(description, 700),
        organizations=[str(owner.get("login"))] if owner.get("login") else [owner_of(full_name)],
        artifact_urls=artifact_urls,
        metrics=clean_metrics(
            {
                "stars": record.get("stargazers_count"),
                "forks": record.get("forks_count"),
            }
        ),
        facets=facets,
        event_kind=event_kind,
        provenance=PROVENANCE_LIVE,
        discovered_at=ctx.now_iso,
        retrieved_at=ctx.now_iso,
        raw_payload_hash=payload_hash({"repo": full_name, "pushed_at": record.get("pushed_at")}),
    )


def fetch_repositories(spec: Mapping[str, Any], ctx: FetchContext) -> list[RadarItem]:
    per_page = min(100, int(spec.get("per_page", 40)))
    by_id: dict[str, RadarItem] = {}
    failures: list[str] = []

    for query in spec.get("queries") or []:
        params = {"q": str(query), "sort": "updated", "order": "desc", "per_page": per_page}
        try:
            payload = http.get_json(SEARCH_URL, params=params, headers=http.github_headers())
        except http.HttpError as error:
            failures.append(f"{query}: {error}")
            continue
        for record in (payload or {}).get("items") or []:
            item = _repo_item(record, ctx=ctx, query=str(query))
            if item and item.source_id not in by_id:
                by_id[item.source_id] = item

    if not by_id and failures:
        raise http.HttpError("; ".join(failures[:3]))
    return list(by_id.values())


def fetch_releases(spec: Mapping[str, Any], ctx: FetchContext) -> list[RadarItem]:
    per_page = min(100, int(spec.get("per_page", 10)))
    items: list[RadarItem] = []
    failures: list[str] = []

    for repo in spec.get("repositories") or []:
        try:
            payload = http.get_json(
                RELEASES_URL.format(repo=repo),
                params={"per_page": per_page},
                headers=http.github_headers(),
            )
        except http.HttpError as error:
            failures.append(f"{repo}: {error}")
            continue
        if not isinstance(payload, list):
            continue
        for record in payload:
            if record.get("draft"):
                continue
            published = record.get("published_at") or record.get("created_at")
            if not ctx.within_window(published):
                continue
            tag = str(record.get("tag_name") or "").strip()
            name = " ".join(str(record.get("name") or "").split()) or tag
            url = record.get("html_url")
            if not url or not tag:
                continue
            items.append(
                RadarItem(
                    source=RELEASES_SOURCE,
                    source_id=f"{repo}@{tag}",
                    title=f"{repo} {name}".strip(),
                    url=url,
                    published_at=published,
                    summary=strip_markdown(str(record.get("body") or ""), limit=800),
                    organizations=[owner_of(str(repo))],
                    artifact_urls=[f"https://github.com/{repo}"],
                    facets={
                        "tag": tag,
                        "prerelease": bool(record.get("prerelease")),
                        "repository": str(repo),
                    },
                    event_kind="released",
                    provenance=PROVENANCE_LIVE,
                    discovered_at=ctx.now_iso,
                    retrieved_at=ctx.now_iso,
                    raw_payload_hash=payload_hash({"repo": repo, "tag": tag}),
                )
            )

    if not items and failures and len(failures) == len(spec.get("repositories") or []):
        raise http.HttpError("; ".join(failures[:3]))
    return items
