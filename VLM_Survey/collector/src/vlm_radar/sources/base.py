"""Shared context and helpers for source fetchers.

A fetcher's only job is faithful transcription: query upstream, map fields onto
`RadarItem`, and stop. Gating, scoring, and capping all happen later in the
pipeline, so a fetcher never has to know the taxonomy.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ..config import Settings
from ..models import RadarItem
from ..textutil import isoformat, parse_datetime


@dataclass
class FetchContext:
    settings: Settings
    now: datetime
    since: datetime

    @property
    def since_iso(self) -> str:
        return isoformat(self.since)

    @property
    def now_iso(self) -> str:
        return isoformat(self.now)

    def within_window(self, *candidates: Any) -> bool:
        """True when any candidate timestamp is at or after the scan floor."""
        for candidate in candidates:
            moment = parse_datetime(candidate)
            if moment and moment >= self.since:
                return True
        return False


def newest(*candidates: Any) -> str | None:
    moments = [parse_datetime(candidate) for candidate in candidates]
    valid = [moment for moment in moments if moment]
    return isoformat(max(valid)) if valid else None


def owner_of(repo_id: str) -> str:
    """Organization portion of an `owner/name` identifier."""
    if "/" in repo_id:
        owner = repo_id.split("/", 1)[0].strip()
        return owner if owner else ""
    return ""


def clean_metrics(raw: Mapping[str, Any]) -> dict[str, float]:
    metrics: dict[str, float] = {}
    for key, value in raw.items():
        if value is None:
            continue
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        if numeric > 0:
            metrics[key] = numeric
    return metrics


def limit_items(items: list[RadarItem], limit: int) -> list[RadarItem]:
    if limit <= 0:
        return items
    return items[:limit]
