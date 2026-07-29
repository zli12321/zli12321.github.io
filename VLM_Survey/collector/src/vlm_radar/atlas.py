"""The atlas: a browsable catalogue built from the curated survey README.

Snapshots answer "what is new". The atlas answers "what exists" -- the standing
list of models, benchmarks, datasets, and methods the survey maintainers have
already vetted. It is rebuilt from markdown on every run, so it never drifts from
the upstream repository.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .config import Settings
from .models import RadarItem
from .sources import survey
from .textutil import isoformat, normalize, slug, utcnow

SCHEMA_VERSION = 1


def _entry_payload(item: RadarItem, settings: Settings) -> dict[str, Any]:
    taxonomy = settings.taxonomy
    text = normalize(" ".join([item.title, item.summary, item.section]))
    categories = list(item.hint_categories)
    inferred, _ = taxonomy.categorize(text)
    for category in inferred:
        if category not in categories:
            categories.append(category)

    payload: dict[str, Any] = {
        "title": item.title,
        "url": item.url,
        "categories": categories,
        "section": item.section,
    }
    if item.published_at:
        payload["published_at"] = item.published_at
    if item.summary:
        payload["summary"] = item.summary
    if item.organizations:
        payload["organizations"] = item.organizations
    families = taxonomy.match_families(text)
    if families:
        payload["model_families"] = families
    watch = [name for name, _ in taxonomy.match_watchlist(text)]
    if watch:
        payload["watchlist"] = watch
    columns = (item.facets or {}).get("columns") or {}
    if columns:
        payload["columns"] = columns
    if item.artifact_urls:
        payload["artifact_urls"] = item.artifact_urls[:6]
    return payload


def build_atlas(settings: Settings) -> dict[str, Any]:
    """Parse the survey README into sections of catalogued entries."""
    root = settings.survey_root()
    spec = settings.source("survey")
    generated_at = isoformat(utcnow())

    if root is None:
        return {
            "schema_version": SCHEMA_VERSION,
            "generated_at": generated_at,
            "available": False,
            "detail": (
                "No survey repository found. Set sources.survey.path in config.yml to a "
                "local checkout of Vision-Language-Models-Overview."
            ),
            "sections": [],
            "counts": {"entries": 0, "sections": 0},
        }

    entries = survey.parse_readme(root, spec)
    reports = survey.parse_reports(root, spec)

    sections: dict[str, dict[str, Any]] = {}
    for item in entries:
        trail = item.section.split(" > ") if item.section else []
        top = trail[0] if trail else "Uncategorized"
        bucket = sections.setdefault(
            slug(top) or "uncategorized",
            {"key": slug(top) or "uncategorized", "title": top, "entries": []},
        )
        payload = _entry_payload(item, settings)
        payload["subsection"] = " > ".join(trail[1:]) if len(trail) > 1 else ""
        bucket["entries"].append(payload)

    ordered = sorted(sections.values(), key=lambda bucket: -len(bucket["entries"]))
    for bucket in ordered:
        bucket["count"] = len(bucket["entries"])
        bucket["entries"].sort(key=lambda entry: entry.get("published_at") or "", reverse=True)

    category_counts: dict[str, int] = {}
    family_counts: dict[str, int] = {}
    for bucket in ordered:
        for entry in bucket["entries"]:
            for category in entry.get("categories") or []:
                category_counts[category] = category_counts.get(category, 0) + 1
            for family in entry.get("model_families") or []:
                family_counts[family] = family_counts.get(family, 0) + 1

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "available": True,
        "origin": {
            "repository": root.name,
            "path": str(root),
            "reports": sorted(reports.keys()),
        },
        "sections": ordered,
        "counts": {
            "entries": sum(bucket["count"] for bucket in ordered),
            "sections": len(ordered),
            "report_entries": sum(len(items) for items in reports.values()),
            "reports": len(reports),
        },
        "category_counts": [
            {"category": key, "label": settings.taxonomy.label(key), "count": value}
            for key, value in sorted(category_counts.items(), key=lambda pair: -pair[1])
        ],
        "model_families": [
            {"name": key, "count": value}
            for key, value in sorted(family_counts.items(), key=lambda pair: -pair[1])
        ],
    }


def write_atlas(settings: Settings) -> dict[str, Any]:
    payload = build_atlas(settings)
    settings.atlas_path.parent.mkdir(parents=True, exist_ok=True)
    settings.atlas_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return payload


def load_atlas(settings: Settings) -> Mapping[str, Any] | None:
    path = settings.atlas_path
    if not path.is_file():
        return None
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None


def atlas_or_build(settings: Settings) -> dict[str, Any]:
    """Prefer a cached atlas, but rebuild when it is missing or stale-empty."""
    cached = load_atlas(settings)
    if cached and cached.get("counts", {}).get("entries"):
        return dict(cached)
    return write_atlas(settings)


def readme_sections(settings: Settings) -> list[str]:
    payload = atlas_or_build(settings)
    return [str(bucket.get("title")) for bucket in payload.get("sections") or []]


def atlas_path(settings: Settings) -> Path:
    return settings.atlas_path
