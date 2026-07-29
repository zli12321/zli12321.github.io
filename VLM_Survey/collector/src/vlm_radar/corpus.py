"""Cumulative entity graph across all snapshots.

Artifacts merge only on exact identifiers -- DOI, arXiv id, Hugging Face repo,
GitHub repo -- never on fuzzy title similarity. Two papers with similar names stay
separate nodes, because a wrong merge silently rewrites history and there is no
way for a reader to notice.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from .taxonomy import Taxonomy
from .textutil import canonical_url, day_key, parse_datetime, slug

ARTIFACT = "artifact"
TOPIC = "topic"
ORGANIZATION = "organization"
SOURCE = "source"
MODEL_FAMILY = "model_family"

FOUND_VIA = "FOUND_VIA"
HAS_TOPIC = "HAS_TOPIC"
RELEASED_BY = "RELEASED_BY"
TRACKS_FAMILY = "TRACKS_FAMILY"

_ARXIV = re.compile(r"arxiv\.org/(?:abs|pdf|html)/(\d{4}\.\d{4,5})", re.IGNORECASE)
_HF_PAPER = re.compile(r"huggingface\.co/papers/(\d{4}\.\d{4,5})", re.IGNORECASE)
_HF_REPO = re.compile(
    r"huggingface\.co/(?:datasets/|models/)?([A-Za-z0-9][\w.\-]*/[\w.\-]+)", re.IGNORECASE
)
_GITHUB = re.compile(r"github\.com/([A-Za-z0-9][\w.\-]*/[\w.\-]+)", re.IGNORECASE)
_DOI = re.compile(r"(10\.\d{4,9}/[^\s\"'<>]+)")
_HF_RESERVED = frozenset({"papers", "collections", "spaces", "blog", "docs", "api"})


def exact_artifact_key(item: Mapping[str, Any]) -> str:
    """Highest-confidence identifier available for a record."""
    candidates: list[str] = [str(item.get("url") or "")]
    candidates.extend(str(url) for url in item.get("artifact_urls") or [])
    facets = item.get("facets") or {}
    if isinstance(facets, Mapping):
        if facets.get("doi"):
            candidates.insert(0, f"https://doi.org/{facets['doi']}")
        if facets.get("arxiv_id"):
            candidates.insert(0, f"https://arxiv.org/abs/{facets['arxiv_id']}")

    joined = " ".join(candidates)

    doi = _DOI.search(joined)
    if doi:
        return "doi:" + doi.group(1).lower().rstrip(".,;")

    arxiv = _ARXIV.search(joined) or _HF_PAPER.search(joined)
    if arxiv:
        return "arxiv:" + arxiv.group(1)

    source = str(item.get("source") or "")
    if source.startswith("Hugging Face") and item.get("source_id"):
        return "hf:" + str(item["source_id"]).lower()

    hf = _HF_REPO.search(joined)
    if hf:
        repo = hf.group(1)
        if repo.split("/")[0].lower() not in _HF_RESERVED:
            return "hf:" + repo.lower()

    github = _GITHUB.search(joined)
    if github:
        return "gh:" + github.group(1).lower().removesuffix(".git")

    canonical = canonical_url(str(item.get("url") or ""))
    if canonical:
        return "url:" + canonical.lower()
    return "id:" + slug(f"{source} {item.get('source_id') or item.get('title') or ''}")


class _Node:
    __slots__ = ("key", "kind", "label", "count", "score", "first_seen", "last_seen", "extra")

    def __init__(self, key: str, kind: str, label: str) -> None:
        self.key = key
        self.kind = kind
        self.label = label
        self.count = 0
        self.score = 0.0
        self.first_seen: str | None = None
        self.last_seen: str | None = None
        self.extra: dict[str, Any] = {}

    def observe(self, date: str, score: float) -> None:
        self.count += 1
        self.score = max(self.score, score)
        if self.first_seen is None or date < self.first_seen:
            self.first_seen = date
        if self.last_seen is None or date > self.last_seen:
            self.last_seen = date

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.key,
            "kind": self.kind,
            "label": self.label,
            "observations": self.count,
            "score": round(self.score, 2),
        }
        if self.first_seen:
            payload["first_seen"] = self.first_seen
        if self.last_seen:
            payload["last_seen"] = self.last_seen
        payload.update(self.extra)
        return payload


def build_corpus(
    days: Sequence[Mapping[str, Any]],
    taxonomy: Taxonomy,
    *,
    max_artifacts: int = 240,
) -> dict[str, Any]:
    """Fold every snapshot into nodes, edges, and rollups for the map view."""
    nodes: dict[str, _Node] = {}
    edges: dict[tuple[str, str, str], int] = {}

    def node(key: str, kind: str, label: str) -> _Node:
        existing = nodes.get(key)
        if existing is None:
            existing = _Node(key, kind, label)
            nodes[key] = existing
        return existing

    def link(source_key: str, target_key: str, relation: str) -> None:
        edge = (source_key, target_key, relation)
        edges[edge] = edges.get(edge, 0) + 1

    topic_history: dict[str, dict[str, int]] = {}
    source_totals: dict[str, int] = {}
    family_totals: dict[str, int] = {}
    org_totals: dict[str, int] = {}

    for day in days:
        date = str(day.get("date") or "")
        for item in day.get("items") or []:
            score = float(item.get("total_score") or 0.0)
            artifact_key = exact_artifact_key(item)
            artifact = node(artifact_key, ARTIFACT, str(item.get("title") or artifact_key))
            artifact.observe(date, score)
            artifact.extra.setdefault("url", item.get("url") or "")
            artifact.extra["provenance"] = item.get("provenance") or "live"

            source_name = str(item.get("source") or "unknown")
            source_totals[source_name] = source_totals.get(source_name, 0) + 1
            source_node = node(f"source:{slug(source_name)}", SOURCE, source_name)
            source_node.observe(date, score)
            link(artifact_key, source_node.key, FOUND_VIA)
            for extra_source in item.get("corroborating_sources") or []:
                extra_node = node(f"source:{slug(str(extra_source))}", SOURCE, str(extra_source))
                extra_node.observe(date, score)
                link(artifact_key, extra_node.key, FOUND_VIA)

            for category in item.get("categories") or []:
                label = taxonomy.label(str(category))
                topic_node = node(f"topic:{category}", TOPIC, label)
                topic_node.observe(date, score)
                link(artifact_key, topic_node.key, HAS_TOPIC)
                bucket = topic_history.setdefault(str(category), {})
                bucket[date] = bucket.get(date, 0) + 1

            for organization in item.get("organizations") or []:
                name = str(organization).strip()
                if not name:
                    continue
                org_totals[name] = org_totals.get(name, 0) + 1
                org_node = node(f"org:{slug(name)}", ORGANIZATION, name)
                org_node.observe(date, score)
                link(artifact_key, org_node.key, RELEASED_BY)

            for family in item.get("model_families") or []:
                name = str(family).strip()
                if not name:
                    continue
                family_totals[name] = family_totals.get(name, 0) + 1
                family_node = node(f"family:{slug(name)}", MODEL_FAMILY, name)
                family_node.observe(date, score)
                link(artifact_key, family_node.key, TRACKS_FAMILY)

    artifacts = sorted(
        (node for node in nodes.values() if node.kind == ARTIFACT),
        key=lambda entry: (entry.score, entry.last_seen or ""),
        reverse=True,
    )
    keep = {entry.key for entry in artifacts[:max_artifacts]}
    keep.update(entry.key for entry in nodes.values() if entry.kind != ARTIFACT)

    published_edges = [
        {"source": source, "target": target, "relation": relation, "weight": weight}
        for (source, target, relation), weight in edges.items()
        if source in keep and target in keep
    ]

    return {
        "generated_from_days": len(days),
        "artifact_count": sum(1 for entry in nodes.values() if entry.kind == ARTIFACT),
        "entities": [nodes[key].to_dict() for key in keep if key in nodes],
        "edges": published_edges,
        "aggregates": {
            "topic_velocity": _velocity(topic_history, taxonomy),
            "source_mix": _ranked(source_totals),
            "organizations": _ranked(org_totals, limit=24),
            "model_families": _ranked(family_totals, limit=24),
        },
    }


def _ranked(totals: Mapping[str, int], *, limit: int = 40) -> list[dict[str, Any]]:
    return [
        {"label": label, "count": count}
        for label, count in sorted(totals.items(), key=lambda pair: (-pair[1], pair[0]))[:limit]
    ]


def _velocity(
    history: Mapping[str, Mapping[str, int]], taxonomy: Taxonomy, *, window: int = 7
) -> list[dict[str, Any]]:
    """Recent versus prior counts per topic, over the last `window` observed days."""
    all_dates = sorted({date for buckets in history.values() for date in buckets})
    recent = set(all_dates[-window:])
    prior = set(all_dates[-2 * window : -window])

    rows = []
    for category, buckets in history.items():
        recent_count = sum(count for date, count in buckets.items() if date in recent)
        prior_count = sum(count for date, count in buckets.items() if date in prior)
        rows.append(
            {
                "category": category,
                "label": taxonomy.label(category),
                "recent": recent_count,
                "prior": prior_count,
                "delta": recent_count - prior_count,
                "total": sum(buckets.values()),
                "comparable": bool(prior),
            }
        )
    rows.sort(key=lambda row: (-row["recent"], row["label"]))
    return rows


def observed_days(days: Iterable[Mapping[str, Any]]) -> list[str]:
    return sorted({str(day.get("date")) for day in days if day.get("date")})


def day_of(item: Mapping[str, Any], fallback: str) -> str:
    moment = parse_datetime(item.get("discovered_at")) or parse_datetime(item.get("published_at"))
    return day_key(moment) if moment else fallback
