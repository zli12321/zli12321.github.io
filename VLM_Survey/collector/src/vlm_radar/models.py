"""Record types that travel through the pipeline.

`RadarItem` is the single currency of the collector: every source produces them,
the pipeline scores them, and snapshots persist their public projection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Provenance tells a reader how a record entered the corpus.
PROVENANCE_LIVE = "live"  # fetched from an upstream API this scan
PROVENANCE_CURATED = "curated"  # transcribed from the human-maintained survey


@dataclass
class RadarItem:
    """One discovered artifact: a paper, model, dataset, repository, or release."""

    source: str
    source_id: str
    title: str
    url: str
    published_at: str | None = None
    updated_at: str | None = None
    summary: str = ""
    authors: list[str] = field(default_factory=list)
    organizations: list[str] = field(default_factory=list)
    artifact_urls: list[str] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)
    facets: dict[str, Any] = field(default_factory=dict)
    event_kind: str = "published"
    provenance: str = PROVENANCE_LIVE
    venue: str = ""
    section: str = ""

    # Categories a source already knows from context, such as the heading a
    # curated survey row sits under. The pipeline merges these with what it
    # infers from the text.
    hint_categories: list[str] = field(default_factory=list)

    # Assigned by the pipeline.
    categories: list[str] = field(default_factory=list)
    matched_terms: list[str] = field(default_factory=list)
    model_families: list[str] = field(default_factory=list)
    watchlist: list[str] = field(default_factory=list)
    watchlist_notes: list[str] = field(default_factory=list)
    relevance_score: float = 0.0
    evidence_score: float = 0.0
    recency_score: float = 0.0
    adoption_score: float = 0.0
    total_score: float = 0.0
    score_version: int = 1
    rationale: list[str] = field(default_factory=list)
    suppression_reasons: list[str] = field(default_factory=list)
    corroborating_sources: list[str] = field(default_factory=list)
    discovered_at: str | None = None
    retrieved_at: str | None = None
    raw_payload_hash: str = ""

    @property
    def pinned(self) -> bool:
        """Watchlist or model-family hits sort above generic scoring."""
        return bool(self.watchlist or self.model_families)

    @property
    def identity(self) -> str:
        return f"{self.source}:{self.source_id}"

    def add_rationale(self, line: str) -> None:
        if line and line not in self.rationale:
            self.rationale.append(line)

    def add_artifact_url(self, url: str) -> None:
        if url and url != self.url and url not in self.artifact_urls:
            self.artifact_urls.append(url)

    def to_public_dict(self) -> dict[str, Any]:
        """Projection published in snapshots. Empty fields are omitted."""
        payload: dict[str, Any] = {
            "source": self.source,
            "source_id": self.source_id,
            "title": self.title,
            "url": self.url,
            "event_kind": self.event_kind,
            "provenance": self.provenance,
            "categories": list(self.categories),
            "relevance_score": round(self.relevance_score, 2),
            "evidence_score": round(self.evidence_score, 2),
            "recency_score": round(self.recency_score, 2),
            "adoption_score": round(self.adoption_score, 2),
            "total_score": round(self.total_score, 2),
            "score_version": self.score_version,
        }
        optional = {
            "published_at": self.published_at,
            "updated_at": self.updated_at,
            "summary": self.summary,
            "authors": self.authors[:12],
            "organizations": self.organizations,
            "artifact_urls": self.artifact_urls[:8],
            "metrics": {k: round(v, 2) for k, v in self.metrics.items()},
            "facets": self.facets,
            "venue": self.venue,
            "section": self.section,
            "matched_terms": self.matched_terms[:16],
            "model_families": self.model_families,
            "watchlist": self.watchlist,
            "watchlist_notes": self.watchlist_notes,
            "rationale": self.rationale,
            "suppression_reasons": self.suppression_reasons,
            "corroborating_sources": self.corroborating_sources,
            "discovered_at": self.discovered_at,
            "raw_payload_hash": self.raw_payload_hash,
        }
        for key, value in optional.items():
            if value:
                payload[key] = value
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> RadarItem:
        known = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in payload.items() if k in known})


@dataclass
class SourceHealth:
    """Per-source fetch outcome, published so an empty day is explainable."""

    source: str
    ok: bool
    item_count: int = 0
    detail: str = ""
    required: bool = False
    duration_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "source": self.source,
            "ok": self.ok,
            "item_count": self.item_count,
            "required": self.required,
            "duration_seconds": round(self.duration_seconds, 2),
        }
        if self.detail:
            payload["detail"] = self.detail
        return payload


@dataclass
class Selection:
    """The funnel from raw rows to published records."""

    fetched: int = 0
    deduplicated: int = 0
    out_of_domain: int = 0
    suppressed: int = 0
    below_threshold: int = 0
    published: int = 0
    pinned: int = 0
    minimum_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "fetched": self.fetched,
            "deduplicated": self.deduplicated,
            "out_of_domain": self.out_of_domain,
            "suppressed": self.suppressed,
            "below_threshold": self.below_threshold,
            "published": self.published,
            "pinned": self.pinned,
            "minimum_score": self.minimum_score,
        }


@dataclass
class RadarRun:
    """One pipeline execution."""

    items: list[RadarItem] = field(default_factory=list)
    health: list[SourceHealth] = field(default_factory=list)
    selection: Selection = field(default_factory=Selection)
    since: str | None = None
    generated_at: str | None = None
