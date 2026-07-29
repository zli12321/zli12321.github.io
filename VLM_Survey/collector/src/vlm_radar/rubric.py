"""The published scoring rubric.

Four components, each on 0-100, combined by fixed weights into a 0-100 priority.
The same definition is embedded in the dashboard JSON so the site can explain any
score without reimplementing the maths.

A score answers "how strong is the evidence that this is a notable new
vision-language artifact today", never "is this good research".
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

SCORING_VERSION = 1
SCORE_MAX = 100.0

WEIGHTS: dict[str, float] = {
    "relevance": 0.38,
    "evidence": 0.22,
    "recency": 0.25,
    "adoption": 0.15,
}

# Relevance
POINTS_PER_CATEGORY = 22.0
POINTS_PER_TERM = 5.0
POINTS_PER_ANCHOR = 4.0
MAX_ANCHOR_POINTS = 12.0
DEMOTION_PENALTY = 26.0

# Evidence
EVIDENCE_PRIMARY = 34.0
EVIDENCE_ABSTRACT = 18.0
EVIDENCE_LONG_ABSTRACT = 8.0
EVIDENCE_AUTHORS = 10.0
EVIDENCE_PER_ARTIFACT = 8.0
EVIDENCE_MAX_ARTIFACT = 24.0
EVIDENCE_CORROBORATION = 16.0
EVIDENCE_VENUE = 10.0

# Adoption. Ceilings are the value at which a metric saturates the component;
# they are log-scaled so a 40k-download dataset does not erase a 400-star repo.
ADOPTION_CEILINGS: dict[str, float] = {
    "stars": 4000.0,
    "forks": 800.0,
    "downloads": 60000.0,
    "likes": 800.0,
    "citations": 400.0,
    "upvotes": 250.0,
    "influential_citations": 80.0,
}

# Sources that publish the artifact itself rather than a mention of it.
PRIMARY_SOURCES = frozenset(
    {
        "arXiv",
        "Hugging Face Models",
        "Hugging Face Datasets",
        "Hugging Face Papers",
        "GitHub",
        "GitHub Releases",
        "VLM Survey",
        "VLM Survey Report",
    }
)


def clamp(value: float, low: float = 0.0, high: float = SCORE_MAX) -> float:
    return max(low, min(high, value))


def relevance(
    *,
    category_count: int,
    term_count: int,
    anchor_count: int,
    demotions: int,
) -> float:
    """Topic fit: how many buckets and how many distinct terms the text hits."""
    raw = (
        POINTS_PER_CATEGORY * category_count
        + POINTS_PER_TERM * term_count
        + min(MAX_ANCHOR_POINTS, POINTS_PER_ANCHOR * anchor_count)
    )
    return clamp(raw - DEMOTION_PENALTY * demotions)


def evidence(
    *,
    source: str,
    summary_length: int,
    author_count: int,
    artifact_count: int,
    corroborating_sources: int,
    venue: str,
) -> float:
    """How much verifiable substance travels with the record."""
    score = EVIDENCE_PRIMARY if source in PRIMARY_SOURCES else EVIDENCE_PRIMARY / 2
    if summary_length >= 120:
        score += EVIDENCE_ABSTRACT
    if summary_length >= 600:
        score += EVIDENCE_LONG_ABSTRACT
    if author_count:
        score += EVIDENCE_AUTHORS
    score += min(EVIDENCE_MAX_ARTIFACT, EVIDENCE_PER_ARTIFACT * artifact_count)
    if corroborating_sources:
        score += EVIDENCE_CORROBORATION
    if venue:
        score += EVIDENCE_VENUE
    return clamp(score)


def recency(*, age_hours: float, window_hours: float) -> float:
    """Linear decay across the scan window. Undated records land mid-window."""
    if window_hours <= 0:
        return 0.0
    return clamp(SCORE_MAX * (1.0 - (age_hours / window_hours)))


def adoption(metrics: Mapping[str, float]) -> float:
    """Log-scaled community traction, taking the strongest available signal."""
    best = 0.0
    for name, value in metrics.items():
        ceiling = ADOPTION_CEILINGS.get(name)
        if not ceiling or value is None or value <= 0:
            continue
        scaled = math.log10(1.0 + float(value)) / math.log10(1.0 + ceiling)
        best = max(best, scaled)
    return clamp(SCORE_MAX * best)


def total(components: Mapping[str, float]) -> float:
    return round(
        clamp(sum(WEIGHTS[name] * components.get(name, 0.0) for name in WEIGHTS)),
        2,
    )


def describe_components(components: Mapping[str, float]) -> list[dict[str, float]]:
    return [
        {
            "component": name,
            "weight": WEIGHTS[name],
            "score": round(components.get(name, 0.0), 2),
            "contribution": round(WEIGHTS[name] * components.get(name, 0.0), 2),
        }
        for name in WEIGHTS
    ]


def reference(*, minimum_score: float, lookback_hours: float) -> dict[str, object]:
    """Machine-readable rubric published with every dashboard build."""
    return {
        "version": SCORING_VERSION,
        "score_max": SCORE_MAX,
        "minimum_score": minimum_score,
        "lookback_hours": lookback_hours,
        "weights": dict(WEIGHTS),
        "summary": (
            "Priority is a weighted 0-100 blend of topic relevance, evidence "
            "substance, recency, and adoption. It ranks discovery confidence, not "
            "research quality."
        ),
        "components": [
            {
                "name": "relevance",
                "weight": WEIGHTS["relevance"],
                "detail": (
                    f"{POINTS_PER_CATEGORY:g} points per taxonomy category, "
                    f"{POINTS_PER_TERM:g} per distinct matched term, up to "
                    f"{MAX_ANCHOR_POINTS:g} for vision-language anchors, minus "
                    f"{DEMOTION_PENALTY:g} per low-value pattern."
                ),
            },
            {
                "name": "evidence",
                "weight": WEIGHTS["evidence"],
                "detail": (
                    f"{EVIDENCE_PRIMARY:g} for a primary source (half for a mention), "
                    f"+{EVIDENCE_ABSTRACT:g} for an upstream abstract, "
                    f"+{EVIDENCE_AUTHORS:g} for named authors, "
                    f"+{EVIDENCE_PER_ARTIFACT:g} per linked artifact (max "
                    f"{EVIDENCE_MAX_ARTIFACT:g}), +{EVIDENCE_CORROBORATION:g} when a "
                    f"second source found the same record, +{EVIDENCE_VENUE:g} for a venue."
                ),
            },
            {
                "name": "recency",
                "weight": WEIGHTS["recency"],
                "detail": (
                    "Linear decay from 100 at publication to 0 at the end of the scan "
                    "window. Curated survey entries use a longer window because they "
                    "arrive in periodic batches."
                ),
            },
            {
                "name": "adoption",
                "weight": WEIGHTS["adoption"],
                "detail": (
                    "Log-scaled maximum over stars, downloads, likes, citations, and "
                    "upvotes, each saturating at a per-metric ceiling."
                ),
            },
        ],
        "adoption_ceilings": dict(ADOPTION_CEILINGS),
        "gates": [
            "A record must hit at least one vision-language domain anchor.",
            "A record must land in at least one taxonomy category.",
            "Records matching a suppression pattern are dropped entirely.",
            "Watchlist and model-family hits are pinned above generic ranking.",
        ],
        "worked_example": _worked_example(),
    }


def _worked_example() -> dict[str, object]:
    """A concrete score so readers can check the arithmetic themselves."""
    components = {
        "relevance": relevance(category_count=2, term_count=4, anchor_count=3, demotions=0),
        "evidence": evidence(
            source="arXiv",
            summary_length=900,
            author_count=6,
            artifact_count=1,
            corroborating_sources=0,
            venue="",
        ),
        "recency": recency(age_hours=6.0, window_hours=48.0),
        "adoption": adoption({"upvotes": 12.0}),
    }
    return {
        "scenario": (
            "A 6-hour-old arXiv paper with a full abstract, six authors, one code "
            "link, hitting two categories and four terms, with 12 upvotes."
        ),
        "components": describe_components(components),
        "total": total(components),
    }


def bands() -> Sequence[dict[str, object]]:
    return (
        {"label": "Pinned", "min": None, "detail": "Watchlist or tracked model family."},
        {
            "label": "Strong",
            "min": 65,
            "detail": "Multiple categories with fresh primary evidence.",
        },
        {"label": "Notable", "min": 48, "detail": "Clear domain fit, moderate corroboration."},
        {"label": "Watch", "min": 34, "detail": "Meets the floor; skim before acting."},
    )
