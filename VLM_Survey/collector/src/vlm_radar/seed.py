"""Backfill snapshots from the survey's dated progressive reports.

Each progressive report is a dated record of what the survey maintainers added in
that cycle, which is exactly the shape of a radar scan. Replaying them gives the
dashboard real history on a fresh checkout, before any live scan has run, and
keeps the trend view meaningful from day one.

Seeded snapshots are marked `provenance: "curated"` on every record so they are
never mistaken for live API observations.
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Any

from . import pipeline
from .config import Settings
from .models import RadarRun, SourceHealth
from .snapshots import snapshot_path, write_snapshot
from .sources import survey
from .textutil import isoformat, parse_datetime


def available_reports(settings: Settings) -> dict[str, int]:
    root = settings.survey_root()
    if root is None:
        return {}
    reports = survey.parse_reports(root, settings.source("survey"))
    return {date: len(entries) for date, entries in sorted(reports.items())}


def seed_from_survey(settings: Settings, *, overwrite: bool = False) -> list[dict[str, Any]]:
    """Write one snapshot per progressive report. Returns a summary per report."""
    root = settings.survey_root()
    if root is None:
        raise SystemExit(
            "No survey repository found. Point sources.survey.path in config.yml at a "
            "local checkout of Vision-Language-Models-Overview."
        )

    spec = settings.source("survey")
    reports = survey.parse_reports(root, spec)
    if not reports:
        raise SystemExit(
            f"No dated progressive reports found under {survey.reports_dir(root, spec)}"
        )

    written: list[dict[str, Any]] = []
    for date, entries in sorted(reports.items()):
        path = snapshot_path(settings, date)
        if path.exists() and not overwrite:
            written.append({"date": date, "path": path, "skipped": True, "published": 0})
            continue

        # Score as of the report date so recency measures how fresh each entry was
        # when the maintainers recorded it.
        as_of = parse_datetime(date)
        deduped = pipeline.deduplicate(entries)
        scored = [pipeline.score_item(item, settings, as_of) for item in deduped]
        ranked, funnel = pipeline.select(scored, settings)
        funnel.fetched = len(entries)
        funnel.deduplicated = len(deduped)

        run = RadarRun(
            items=ranked,
            health=[
                SourceHealth(
                    source=survey.REPORT_SOURCE,
                    ok=True,
                    item_count=len(entries),
                    detail=f"Replayed from progressive reports/{date}.md",
                )
            ],
            selection=funnel,
            since=isoformat(as_of - timedelta(hours=settings.curated_lookback_hours)),
            generated_at=isoformat(as_of),
        )
        written.append(
            {
                "date": date,
                "path": write_snapshot(settings, run, date=date),
                "skipped": False,
                "published": len(ranked),
                "fetched": len(entries),
            }
        )
    return written


def latest_report_date(settings: Settings) -> str | None:
    reports = available_reports(settings)
    return max(reports) if reports else None


def seeded_snapshot_paths(settings: Settings) -> list[Path]:
    return [
        snapshot_path(settings, date)
        for date in available_reports(settings)
        if snapshot_path(settings, date).exists()
    ]
