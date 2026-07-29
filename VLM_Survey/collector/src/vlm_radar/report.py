"""Markdown digest for a GitHub Issue or the terminal.

The digest is the human-readable face of a scan. It leads with the funnel so a
reader can tell a quiet day from a broken one before reading a single record.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from .config import Settings
from .models import RadarItem, RadarRun
from .textutil import truncate

MARKER_START = "<!-- vlm-radar:start -->"
MARKER_END = "<!-- vlm-radar:end -->"


def _score_bar(score: float, width: int = 10) -> str:
    filled = int(round((max(0.0, min(100.0, score)) / 100.0) * width))
    return "█" * filled + "·" * (width - filled)


def _item_block(item: RadarItem, settings: Settings) -> str:
    topics = ", ".join(settings.taxonomy.label(key) for key in item.categories[:4])
    lines = [f"### [{item.title}]({item.url})"]

    badges = [f"`{item.total_score:.0f}/100` {_score_bar(item.total_score)}", item.source]
    if item.event_kind and item.event_kind != "published":
        badges.append(item.event_kind)
    if item.model_families:
        badges.append("family: " + ", ".join(item.model_families))
    if item.watchlist:
        badges.append("watchlist: " + ", ".join(item.watchlist))
    lines.append(" · ".join(badges))

    if topics:
        lines.append(f"*{topics}*")
    if item.summary:
        lines.append("")
        lines.append(truncate(item.summary, 420))
    details = []
    if item.published_at:
        details.append(f"published {item.published_at[:10]}")
    if item.organizations:
        details.append(", ".join(item.organizations[:3]))
    if item.metrics:
        details.append(
            " · ".join(f"{name} {value:,.0f}" for name, value in sorted(item.metrics.items()))
        )
    for url in item.artifact_urls[:3]:
        details.append(f"[link]({url})")
    if details:
        lines.append("")
        lines.append(" — ".join(details))
    return "\n".join(lines)


def _funnel_table(funnel: Mapping[str, object]) -> str:
    rows = [
        ("Fetched", funnel.get("fetched")),
        ("After dedupe", funnel.get("deduplicated")),
        ("Out of domain", funnel.get("out_of_domain")),
        ("Suppressed", funnel.get("suppressed")),
        ("Below threshold", funnel.get("below_threshold")),
        ("Published", funnel.get("published")),
        ("Pinned", funnel.get("pinned")),
    ]
    lines = ["| Stage | Records |", "| --- | --- |"]
    lines += [f"| {label} | {value if value is not None else 0} |" for label, value in rows]
    return "\n".join(lines)


def _health_table(health: Sequence[Mapping[str, object]]) -> str:
    lines = ["| Source | Status | Records | Detail |", "| --- | --- | --- | --- |"]
    for entry in health:
        status = "ok" if entry.get("ok") else "failed"
        if entry.get("required") and not entry.get("ok"):
            status = "**failed (required)**"
        detail = str(entry.get("detail") or "")
        lines.append(
            f"| {entry.get('source')} | {status} | {entry.get('item_count', 0)} | "
            f"{truncate(detail, 120) or '—'} |"
        )
    return "\n".join(lines)


def render_markdown(run: RadarRun, settings: Settings, *, date: str) -> str:
    taxonomy = settings.taxonomy
    counts: dict[str, int] = {}
    for item in run.items:
        for category in item.categories:
            counts[category] = counts.get(category, 0) + 1

    top_topics = ", ".join(
        f"{taxonomy.label(key)} ({value})"
        for key, value in sorted(counts.items(), key=lambda pair: -pair[1])[:6]
    )
    pinned = [item for item in run.items if item.pinned]

    parts: list[str] = [
        MARKER_START,
        f"# {settings.publish.get('issue_title_prefix', 'VLM Radar')} — {date}",
        "",
        f"{len(run.items)} records published from {run.selection.fetched} fetched. "
        f"Window: {run.since} → {run.generated_at}.",
        "",
        f"**Topics today:** {top_topics or 'none'}",
        "",
        "## Selection funnel",
        "",
        _funnel_table(run.selection.to_dict()),
        "",
    ]

    if pinned:
        parts += ["## Pinned", ""]
        for item in pinned[: settings.issue_item_limit]:
            parts += [_item_block(item, settings), ""]

    generic = [item for item in run.items if not item.pinned]
    if generic:
        parts += ["## Today's signals", ""]
        for item in generic[: settings.issue_item_limit]:
            parts += [_item_block(item, settings), ""]
        remaining = len(generic) - settings.issue_item_limit
        if remaining > 0:
            parts += [f"_{remaining} more records in the dashboard and snapshot._", ""]

    parts += [
        "## Source health",
        "",
        _health_table([entry.to_dict() for entry in run.health]),
        "",
        "---",
        "",
        "Scores rank discovery confidence, not research quality. "
        f"Minimum published score: {settings.minimum_score:g}/100.",
        MARKER_END,
    ]
    return "\n".join(parts) + "\n"


def render_terminal(run: RadarRun, settings: Settings, *, limit: int = 15) -> str:
    """Compact console summary for local runs."""
    lines = [
        f"published {len(run.items)} of {run.selection.fetched} fetched "
        f"({run.selection.out_of_domain} out of domain, "
        f"{run.selection.below_threshold} below {settings.minimum_score:g})",
        "",
    ]
    for item in run.items[:limit]:
        pin = "*" if item.pinned else " "
        topics = ",".join(item.categories[:3])
        lines.append(
            f" {pin} {item.total_score:5.1f}  {item.source:<24} {truncate(item.title, 68)}"
            + (f"  [{topics}]" if topics else "")
        )
    if len(run.items) > limit:
        lines.append(f"   ... {len(run.items) - limit} more")
    lines.append("")
    for entry in run.health:
        status = "ok " if entry.ok else "ERR"
        detail = f"  {truncate(entry.detail, 90)}" if entry.detail and not entry.ok else ""
        lines.append(f" {status} {entry.source:<24} {entry.item_count:>4}{detail}")
    return "\n".join(lines)
