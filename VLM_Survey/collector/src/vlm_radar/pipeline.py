"""Collect, deduplicate, score, and select.

The funnel is published with every snapshot, so a quiet day is always
distinguishable from a broken day:

    fetched -> deduplicated -> in domain -> not suppressed -> above threshold

Nothing here knows the vision-language vocabulary; that all lives in config.yml
and is compiled by `taxonomy.Taxonomy`.
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from datetime import timedelta

from . import http, rubric
from .config import Settings
from .models import (
    PROVENANCE_CURATED,
    RadarItem,
    RadarRun,
    Selection,
    SourceHealth,
)
from .sources import SOURCE_FETCHERS, SOURCE_LABELS, FetchContext
from .textutil import (
    canonical_url,
    digest,
    hours_between,
    isoformat,
    normalize,
    parse_datetime,
    utcnow,
)

# A title shorter than this is too generic to identify a record on its own, so
# deduplication falls back to the canonical URL.
_MIN_TITLE_KEY_LENGTH = 24


def collect(
    settings: Settings,
    *,
    now=None,
    only: Sequence[str] | None = None,
) -> tuple[list[RadarItem], list[SourceHealth]]:
    """Run every enabled fetcher, recording health for each one."""
    moment = now or utcnow()
    ctx = FetchContext(
        settings=settings,
        now=moment,
        since=moment - timedelta(hours=settings.lookback_hours),
    )

    items: list[RadarItem] = []
    health: list[SourceHealth] = []
    selected_keys = set(only) if only else None

    for key, fetcher in SOURCE_FETCHERS.items():
        spec = settings.source(key)
        label = SOURCE_LABELS.get(key, key)
        if selected_keys is not None and key not in selected_keys:
            continue
        if not spec.get("enabled", False):
            continue

        required = bool(spec.get("required", False))
        started = time.monotonic()
        try:
            fetched = fetcher(spec, ctx)
        except http.HttpError as error:
            health.append(
                SourceHealth(
                    source=label,
                    ok=False,
                    detail=str(error),
                    required=required,
                    duration_seconds=time.monotonic() - started,
                )
            )
            continue
        except Exception as error:  # a broken parser must not lose the whole scan
            health.append(
                SourceHealth(
                    source=label,
                    ok=False,
                    detail=f"{type(error).__name__}: {error}",
                    required=required,
                    duration_seconds=time.monotonic() - started,
                )
            )
            continue

        items.extend(fetched)
        health.append(
            SourceHealth(
                source=label,
                ok=True,
                item_count=len(fetched),
                required=required,
                duration_seconds=time.monotonic() - started,
            )
        )

    return items, health


def _sort_key(item: RadarItem) -> str:
    return max(
        [value for value in (item.updated_at, item.published_at, item.discovered_at) if value]
        or [""]
    )


def dedupe_key(item: RadarItem) -> str:
    normalized_title = normalize(item.title)
    compact = normalized_title.replace(" ", "")
    if len(compact) >= _MIN_TITLE_KEY_LENGTH:
        return digest("title", normalized_title)
    return digest("url", canonical_url(item.url) or item.identity)


def deduplicate(items: Sequence[RadarItem]) -> list[RadarItem]:
    """Merge records that several sources found, keeping the freshest as primary.

    Corroboration is evidence: when arXiv and Semantic Scholar both return a
    paper, the surviving record carries both source names and gains an evidence
    credit for it.
    """
    ordered = sorted(items, key=_sort_key, reverse=True)
    merged: dict[str, RadarItem] = {}

    for item in ordered:
        key = dedupe_key(item)
        primary = merged.get(key)
        if primary is None:
            merged[key] = item
            continue

        if item.source != primary.source and item.source not in primary.corroborating_sources:
            primary.corroborating_sources.append(item.source)
            primary.add_rationale(f"Also found via {item.source}")
        primary.add_artifact_url(item.url)
        for url in item.artifact_urls:
            primary.add_artifact_url(url)
        for name, value in item.metrics.items():
            primary.metrics[name] = max(primary.metrics.get(name, 0.0), value)
        for org in item.organizations:
            if org and org not in primary.organizations:
                primary.organizations.append(org)
        for author in item.authors:
            if author not in primary.authors:
                primary.authors.append(author)
        for category in item.hint_categories:
            if category not in primary.hint_categories:
                primary.hint_categories.append(category)
        if not primary.summary and item.summary:
            primary.summary = item.summary
        if not primary.venue and item.venue:
            primary.venue = item.venue
        if not primary.section and item.section:
            primary.section = item.section

    return list(merged.values())


def _match_text(item: RadarItem) -> str:
    """Only upstream text is matched, never text the radar generated."""
    parts = [item.title, item.summary, item.section, item.venue]
    facets = item.facets or {}
    for key in ("tags", "topics", "pipeline_tag", "task_categories", "arxiv_categories"):
        value = facets.get(key)
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, (list, tuple)):
            parts.extend(str(entry) for entry in value)
    return normalize(" ".join(part for part in parts if part))


def _raw_text(item: RadarItem) -> str:
    return " ".join(part for part in (item.title, item.summary) if part)


def score_item(item: RadarItem, settings: Settings, now) -> RadarItem:
    """Attach categories, watchlist hits, and the four rubric components."""
    taxonomy = settings.taxonomy
    text = _match_text(item)

    anchors = taxonomy.anchor_hits(text)
    categories, terms = taxonomy.categorize(text)
    for hint in item.hint_categories:
        if hint not in categories:
            categories.append(hint)

    item.categories = categories
    item.matched_terms = terms
    item.model_families = taxonomy.match_families(text)
    for org in taxonomy.family_orgs(item.model_families):
        if org not in item.organizations:
            item.organizations.append(org)

    watch_hits = taxonomy.match_watchlist(text)
    item.watchlist = [name for name, _ in watch_hits]
    item.watchlist_notes = [note for _, note in watch_hits if note]

    demotions = 0
    raw_text = _raw_text(item)
    for rule in taxonomy.low_value_hits(raw_text):
        if rule.action == "suppress":
            if rule.reason not in item.suppression_reasons:
                item.suppression_reasons.append(rule.reason)
        else:
            demotions += 1
            item.add_rationale(f"Demoted: {rule.reason}")

    if not anchors:
        item.suppression_reasons.append("No vision-language domain anchor in upstream text.")

    window = (
        settings.curated_lookback_hours
        if item.provenance == PROVENANCE_CURATED
        else settings.lookback_hours
    )
    moment = parse_datetime(item.published_at) or parse_datetime(item.updated_at)
    age = hours_between(now, moment) if moment else window / 2.0

    components = {
        "relevance": rubric.relevance(
            category_count=len(item.categories),
            term_count=len(item.matched_terms),
            anchor_count=len(anchors),
            demotions=demotions,
        ),
        "evidence": rubric.evidence(
            source=item.source,
            summary_length=len(item.summary or ""),
            author_count=len(item.authors),
            artifact_count=len(item.artifact_urls),
            corroborating_sources=len(item.corroborating_sources),
            venue=item.venue,
        ),
        "recency": rubric.recency(age_hours=age, window_hours=window),
        "adoption": rubric.adoption(item.metrics),
    }

    item.relevance_score = components["relevance"]
    item.evidence_score = components["evidence"]
    item.recency_score = components["recency"]
    item.adoption_score = components["adoption"]
    item.total_score = rubric.total(components)
    item.score_version = rubric.SCORING_VERSION

    if item.categories:
        labels = ", ".join(taxonomy.label(key) for key in item.categories[:4])
        item.add_rationale(f"Topics: {labels}")
    if item.matched_terms:
        item.add_rationale(f"Matched: {', '.join(item.matched_terms[:6])}")
    if item.model_families:
        item.add_rationale(f"Tracked family: {', '.join(item.model_families)}")
    for note in item.watchlist_notes:
        item.add_rationale(note)
    item.add_rationale(f"Primary record: {item.source}")
    return item


def _cap_per_source(items: Sequence[RadarItem], limit: int) -> list[RadarItem]:
    """Keep the strongest `limit` records per source so no source can crowd out others."""
    if limit <= 0:
        return list(items)
    counts: dict[str, int] = {}
    kept: list[RadarItem] = []
    for item in sorted(items, key=lambda entry: (entry.pinned, entry.total_score), reverse=True):
        used = counts.get(item.source, 0)
        if used >= limit:
            continue
        counts[item.source] = used + 1
        kept.append(item)
    return kept


def select(items: Sequence[RadarItem], settings: Settings) -> tuple[list[RadarItem], Selection]:
    minimum = settings.minimum_score
    funnel = Selection(minimum_score=minimum)
    qualified: list[RadarItem] = []

    for item in items:
        if any("domain anchor" in reason for reason in item.suppression_reasons):
            funnel.out_of_domain += 1
            continue
        if item.suppression_reasons:
            funnel.suppressed += 1
            continue
        if not item.categories:
            funnel.out_of_domain += 1
            continue
        if not item.pinned and item.total_score < minimum:
            funnel.below_threshold += 1
            continue
        qualified.append(item)

    capped = _cap_per_source(qualified, settings.max_items_per_source)
    ranked = sorted(
        capped,
        key=lambda entry: (
            entry.pinned,
            entry.total_score,
            _sort_key(entry),
        ),
        reverse=True,
    )[: settings.report_limit]

    funnel.published = len(ranked)
    funnel.pinned = sum(1 for item in ranked if item.pinned)
    return ranked, funnel


def guard_boilerplate(items: Sequence[RadarItem], *, threshold: int = 4) -> None:
    """Fail loudly if many records share one summary: that means a parser broke."""
    counts: dict[str, int] = {}
    for item in items:
        summary = (item.summary or "").strip()
        if len(summary) < 60:
            continue
        counts[summary] = counts.get(summary, 0) + 1
    for summary, count in counts.items():
        if count >= threshold:
            raise RuntimeError(
                f"{count} records share an identical summary, which indicates a broken "
                f"parser rather than real duplication: {summary[:120]!r}"
            )


def run_pipeline(
    settings: Settings,
    *,
    now=None,
    only: Sequence[str] | None = None,
) -> RadarRun:
    moment = now or utcnow()
    fetched, health = collect(settings, now=moment, only=only)

    deduped = deduplicate(fetched)
    scored = [score_item(item, settings, moment) for item in deduped]
    guard_boilerplate(scored)
    ranked, funnel = select(scored, settings)

    funnel.fetched = len(fetched)
    funnel.deduplicated = len(deduped)

    missing_required = [entry.source for entry in health if entry.required and not entry.ok]
    if missing_required and not ranked:
        raise RuntimeError(
            "Required sources failed and nothing was collected: " + ", ".join(missing_required)
        )

    return RadarRun(
        items=ranked,
        health=health,
        selection=funnel,
        since=isoformat(moment - timedelta(hours=settings.lookback_hours)),
        generated_at=isoformat(moment),
    )
