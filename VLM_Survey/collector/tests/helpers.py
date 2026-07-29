"""Shared record builder for the test suite."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from vlm_radar.models import RadarItem

NOW = datetime(2026, 7, 28, 12, 0, tzinfo=timezone.utc)


def make_item(**overrides) -> RadarItem:
    """A realistic in-domain arXiv record, overridable field by field."""
    payload = {
        "source": "arXiv",
        "source_id": "2607.00001",
        "title": "A Vision-Language Benchmark for Chart Understanding",
        "url": "https://arxiv.org/abs/2607.00001",
        "summary": (
            "We introduce a benchmark for evaluating vision-language models on chart "
            "understanding, with 4,000 human-verified question answer pairs drawn from "
            "scientific figures across twelve domains."
        ),
        "authors": ["Ada Lovelace", "Grace Hopper"],
        "published_at": (NOW - timedelta(hours=6)).isoformat(),
        "artifact_urls": ["https://arxiv.org/pdf/2607.00001"],
    }
    payload.update(overrides)
    return RadarItem(**payload)
