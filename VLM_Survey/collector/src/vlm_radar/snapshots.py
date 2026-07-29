"""Snapshot persistence and deterministic dashboard rebuilds.

Daily snapshots under `data/snapshots/` are the canonical record and are the only
thing committed. `site/data/radar.json` is derived: given the same snapshots, a
rebuild always produces the same dashboard, which is what makes the published
site auditable.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from . import atlas as atlas_module
from . import corpus as corpus_module
from . import rubric
from .config import Settings
from .models import RadarItem, RadarRun
from .textutil import day_key, isoformat, parse_datetime, utcnow

SNAPSHOT_SCHEMA_VERSION = 1
DASHBOARD_SCHEMA_VERSION = 1


class SnapshotError(RuntimeError):
    """Raised when a snapshot fails validation and must not be written."""


def snapshot_payload(run: RadarRun, *, date: str) -> dict[str, Any]:
    return {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "date": date,
        "generated_at": run.generated_at,
        "since": run.since,
        "selection": run.selection.to_dict(),
        "health": [entry.to_dict() for entry in run.health],
        "items": [item.to_public_dict() for item in run.items],
    }


def validate_snapshot(payload: Mapping[str, Any]) -> None:
    if payload.get("schema_version") != SNAPSHOT_SCHEMA_VERSION:
        raise SnapshotError(
            f"snapshot schema_version must be {SNAPSHOT_SCHEMA_VERSION}, "
            f"got {payload.get('schema_version')!r}"
        )
    if not payload.get("date"):
        raise SnapshotError("snapshot is missing a date")
    items = payload.get("items")
    if not isinstance(items, list):
        raise SnapshotError("snapshot items must be a list")

    seen = set()
    for item in items:
        for field in ("source", "title", "url", "total_score"):
            if field not in item:
                raise SnapshotError(f"snapshot item is missing {field!r}: {item.get('title')!r}")
        if not item.get("categories"):
            raise SnapshotError(f"published item has no category: {item.get('title')!r}")
        identity = (item.get("source"), item.get("source_id"))
        if identity in seen:
            raise SnapshotError(f"duplicate item in snapshot: {identity}")
        seen.add(identity)


def snapshot_path(settings: Settings, date: str) -> Path:
    return settings.snapshots_dir / f"{date}.json"


def write_snapshot(settings: Settings, run: RadarRun, *, date: str | None = None) -> Path:
    resolved = date or day_key(parse_datetime(run.generated_at) or utcnow())
    payload = snapshot_payload(run, date=resolved)
    validate_snapshot(payload)
    settings.snapshots_dir.mkdir(parents=True, exist_ok=True)
    path = snapshot_path(settings, resolved)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def load_snapshots(settings: Settings) -> list[dict[str, Any]]:
    """All snapshots in chronological order, skipping unreadable files loudly."""
    directory = settings.snapshots_dir
    if not directory.is_dir():
        return []
    loaded: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")):
        try:
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError) as error:
            raise SnapshotError(f"{path.name} could not be read: {error}") from error
        payload.setdefault("date", path.stem)
        loaded.append(payload)
    loaded.sort(key=lambda snapshot: str(snapshot.get("date")))
    return loaded


def _counted(values: Sequence[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        if value:
            counts[value] = counts.get(value, 0) + 1
    return counts


def _day_view(snapshot: Mapping[str, Any], previous: Mapping[str, Any] | None) -> dict[str, Any]:
    items = list(snapshot.get("items") or [])
    categories: list[str] = []
    sources: list[str] = []
    events: list[str] = []
    families: list[str] = []
    organizations: list[str] = []

    for item in items:
        categories.extend(str(value) for value in item.get("categories") or [])
        sources.append(str(item.get("source") or ""))
        events.append(str(item.get("event_kind") or ""))
        families.extend(str(value) for value in item.get("model_families") or [])
        organizations.extend(str(value) for value in item.get("organizations") or [])

    category_counts = _counted(categories)
    previous_counts = (previous or {}).get("category_counts") or {}

    trends = []
    for key in sorted(set(category_counts) | set(previous_counts)):
        current = category_counts.get(key, 0)
        baseline = int(previous_counts.get(key, 0))
        trends.append(
            {
                "category": key,
                "count": current,
                "baseline": baseline,
                "delta": current - baseline,
                "comparable": previous is not None,
            }
        )
    trends.sort(key=lambda row: (-row["count"], row["category"]))

    health = list(snapshot.get("health") or [])
    return {
        "date": str(snapshot.get("date")),
        "generated_at": snapshot.get("generated_at"),
        "since": snapshot.get("since"),
        "item_count": len(items),
        "pinned_count": sum(
            1 for item in items if item.get("model_families") or item.get("watchlist")
        ),
        "curated_count": sum(1 for item in items if item.get("provenance") == "curated"),
        "category_counts": category_counts,
        "source_counts": _counted(sources),
        "event_counts": _counted(events),
        "family_counts": _counted(families),
        "organization_counts": _counted(organizations),
        "category_trends": trends,
        "selection": snapshot.get("selection") or {},
        "health": health,
        "sources_ok": sum(1 for entry in health if entry.get("ok")),
        "sources_total": len(health),
        "items": items,
    }


def _facets(days: Sequence[Mapping[str, Any]]) -> dict[str, list[str]]:
    dates: list[str] = []
    categories: set = set()
    sources: set = set()
    organizations: set = set()
    families: set = set()
    events: set = set()
    provenance: set = set()

    for day in days:
        dates.append(str(day.get("date")))
        categories.update(day.get("category_counts") or {})
        sources.update(day.get("source_counts") or {})
        organizations.update(day.get("organization_counts") or {})
        families.update(day.get("family_counts") or {})
        events.update(day.get("event_counts") or {})
        for item in day.get("items") or []:
            provenance.add(str(item.get("provenance") or "live"))

    return {
        "dates": sorted(dates, reverse=True),
        "categories": sorted(categories),
        "sources": sorted(sources),
        "organizations": sorted(organizations),
        "model_families": sorted(families),
        "event_kinds": sorted(value for value in events if value),
        "provenance": sorted(provenance),
    }


def dashboard_data(settings: Settings) -> dict[str, Any]:
    """Assemble the single JSON file the static site consumes."""
    snapshots = load_snapshots(settings)
    for snapshot in snapshots:
        validate_snapshot(snapshot)

    days: list[dict[str, Any]] = []
    previous: dict[str, Any] | None = None
    for snapshot in snapshots:
        view = _day_view(snapshot, previous)
        days.append(view)
        previous = view

    totals = {
        "items": sum(day["item_count"] for day in days),
        "days": len(days),
        "pinned": sum(day["pinned_count"] for day in days),
        "curated": sum(day["curated_count"] for day in days),
    }

    atlas_payload = atlas_module.atlas_or_build(settings)
    graph = corpus_module.build_corpus(days, settings.taxonomy)

    return {
        "schema_version": DASHBOARD_SCHEMA_VERSION,
        "generated_at": isoformat(utcnow()),
        "latest_date": days[-1]["date"] if days else None,
        "snapshot_count": len(days),
        "site": {
            "title": settings.publish.get("site_title") or "VLM Radar",
            "tagline": settings.publish.get("tagline") or "",
            "repository": settings.publish.get("repository") or "",
            "dashboard_url": settings.publish.get("dashboard_url") or "",
        },
        "taxonomy": settings.taxonomy.to_public_dict(),
        "rubric": rubric.reference(
            minimum_score=settings.minimum_score, lookback_hours=settings.lookback_hours
        ),
        "bands": list(rubric.bands()),
        "facets": _facets(days),
        "totals": totals,
        "days": days,
        "corpus": graph,
        "atlas": atlas_payload,
    }


def write_dashboard(settings: Settings) -> Path:
    payload = dashboard_data(settings)
    path = settings.dashboard_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8"
    )
    return path


def items_from_snapshot(snapshot: Mapping[str, Any]) -> list[RadarItem]:
    return [RadarItem.from_dict(item) for item in snapshot.get("items") or []]
