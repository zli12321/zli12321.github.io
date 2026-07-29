"""The sibling survey repository as a first-class source.

`Vision-Language-Models-Overview` is a hand-curated awesome-list: one large
README of markdown tables plus dated "progressive reports" that record what the
maintainers added in each cycle. Those reports are genuine dated discovery
events, so the radar ingests them the same way it ingests an API.

This module owns all markdown-table parsing. `atlas.py` reuses it to build the
browsable catalogue, and `fetch` uses it to emit records inside the scan window.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from ..models import PROVENANCE_CURATED, RadarItem
from ..textutil import (
    isoformat,
    normalize,
    parse_datetime,
    payload_hash,
    slug,
    truncate,
    utcnow,
)
from .base import FetchContext

README_SOURCE = "VLM Survey"
REPORT_SOURCE = "VLM Survey Report"

_HEADING = re.compile(r"^(?P<hashes>#{1,6})\s+(?P<text>.+?)\s*#*$")
_TABLE_DIVIDER = re.compile(r"^\s*\|?[\s:|-]*-[\s:|-]*\|?\s*$")
_MD_LINK = re.compile(r"\[(?P<label>[^\]]*)\]\((?P<href>[^)\s]+)[^)]*\)")
_ANCHOR = re.compile(r"<a\s+name=['\"]?[^'\">]*['\"]?\s*>\s*</a>", re.IGNORECASE)
_HTML_TAG = re.compile(r"<[^>]+>")
_LEADING_NUMBER = re.compile(r"^\s*\d+(\.\d+)*\.?\s*")
_EMOJI = re.compile(
    "[\U0001f000-\U0001faff\u2190-\u21ff\u2300-\u27bf\ufe0f\u2b00-\u2bff\u2600-\u26ff]"
)
_REPORT_DATE = re.compile(r"(?P<date>\d{4}-\d{2}-\d{2})")
_PLACEHOLDER = frozenset({"", "-", "--", "---", "–", "—", "n/a", "na", "tbd", "?"})
_DATE_HEADERS = ("date", "year", "released", "release")
# Cells whose entire text is a link label carry no information once the URL has
# been pulled out into artifact_urls.
_GENERIC_LABELS = frozenset(
    {
        "paper",
        "papers",
        "code",
        "link",
        "links",
        "website",
        "site",
        "project",
        "project page",
        "github",
        "repo",
        "arxiv",
        "pdf",
        "demo",
        "blog",
        "hf",
        "huggingface",
        "hugging face",
        "model",
        "models",
        "dataset",
        "openreview",
        "yes",
        "no",
        "x",
        "check",
    }
)


def clean_cell(text: str) -> str:
    """Strip markdown decoration from a table cell, keeping link labels."""
    without_anchor = _ANCHOR.sub("", text or "")
    delinked = _MD_LINK.sub(r"\1", without_anchor)
    plain = _HTML_TAG.sub(" ", delinked)
    plain = plain.replace("**", "").replace("`", "").replace("*", "")
    return " ".join(plain.split()).strip()


def clean_heading(text: str) -> str:
    stripped = _ANCHOR.sub("", text or "")
    stripped = _MD_LINK.sub(r"\1", stripped)
    stripped = _HTML_TAG.sub(" ", stripped)
    stripped = _EMOJI.sub("", stripped)
    stripped = stripped.replace("**", "").replace("`", "").replace("#", "")
    return " ".join(stripped.split()).strip(" .:-")


def links_in(text: str) -> list[str]:
    return [match.group("href") for match in _MD_LINK.finditer(text or "")]


def _split_row(line: str) -> list[str]:
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|"):
        body = body[:-1]
    return [cell.strip() for cell in body.split("|")]


def _is_row(line: str) -> bool:
    return line.count("|") >= 2


def iter_tables(text: str) -> Iterable[tuple[list[str], list[str], list[list[str]]]]:
    """Yield (heading trail, headers, rows) for every markdown table in `text`.

    The heading trail is the stack of enclosing markdown headings, which is how a
    row like "Manipulation > RT-2" inherits its topic. Level-1 headings are
    excluded: in an awesome-list README the single `#` is the repository title,
    which would otherwise become the parent of every row.
    """
    lines = text.splitlines()
    trail: dict[int, str] = {}
    index = 0
    in_code_fence = False

    while index < len(lines):
        line = lines[index]
        if line.strip().startswith("```"):
            in_code_fence = not in_code_fence
            index += 1
            continue
        if in_code_fence:
            index += 1
            continue

        heading = _HEADING.match(line)
        if heading:
            level = len(heading.group("hashes"))
            label = clean_heading(heading.group("text"))
            trail = {depth: value for depth, value in trail.items() if depth < level}
            if label and level > 1:
                trail[level] = label
            index += 1
            continue

        if _is_row(line) and index + 1 < len(lines) and _TABLE_DIVIDER.match(lines[index + 1]):
            headers = [clean_cell(cell) for cell in _split_row(line)]
            rows: list[list[str]] = []
            cursor = index + 2
            while cursor < len(lines):
                candidate = lines[cursor]
                if not candidate.strip() or _HEADING.match(candidate):
                    break
                if not _is_row(candidate):
                    break
                rows.append(_split_row(candidate))
                cursor += 1
            if rows:
                yield ([trail[depth] for depth in sorted(trail)], headers, rows)
            index = cursor
            continue

        index += 1

    return


def _date_column(headers: Sequence[str]) -> int | None:
    for position, header in enumerate(headers):
        lowered = normalize(header)
        if any(marker in lowered for marker in _DATE_HEADERS):
            return position
    return None


def _informative(value: str) -> bool:
    folded = normalize(value)
    return bool(folded) and folded not in _PLACEHOLDER and folded not in _GENERIC_LABELS


def _row_summary(headers: Sequence[str], cells: Sequence[str], skip: Sequence[int]) -> str:
    parts: list[str] = []
    for position, cell in enumerate(cells):
        if position in skip:
            continue
        value = clean_cell(cell)
        if not _informative(value) or len(value) < 2:
            continue
        header = clean_heading(headers[position]) if position < len(headers) else ""
        parts.append(f"{header}: {value}" if header else value)
    return truncate(". ".join(parts), 800)


def _organization(title: str) -> tuple[str, str]:
    """Split a trailing parenthetical, which the survey uses for the publisher."""
    match = re.search(r"\(([^()]{2,48})\)\s*$", title)
    if not match:
        return title, ""
    annotation = match.group(1).strip()
    trimmed = title[: match.start()].strip()
    words = annotation.split()
    looks_like_org = (
        len(words) <= 5
        and annotation[0].isupper()
        and not annotation.lower().startswith(("gated", "preview", "note", "see", "visual", "text"))
    )
    return (trimmed or title), (annotation if looks_like_org else "")


def _heading_categories(trail: Sequence[str], mapping: Mapping[str, Any]) -> list[str]:
    haystack = normalize(" > ".join(trail))
    found: list[str] = []
    for needle, categories in mapping.items():
        if normalize(str(needle)) and normalize(str(needle)) in haystack:
            for category in categories or []:
                if category not in found:
                    found.append(category)
    return found


def parse_markdown_entries(
    text: str,
    *,
    source: str,
    origin: str,
    heading_categories: Mapping[str, Any],
    default_date: str | None = None,
) -> list[RadarItem]:
    """Turn every table row in a survey markdown file into a RadarItem."""
    entries: list[RadarItem] = []
    seen: set = set()

    for trail, headers, rows in iter_tables(text):
        if len(headers) < 2:
            continue
        date_index = _date_column(headers)
        categories = _heading_categories(trail, heading_categories)
        section = " > ".join(trail[-3:]) if trail else ""

        for cells in rows:
            if not cells:
                continue
            name_cell = cells[0]
            title = clean_cell(name_cell)
            if not title or normalize(title) in _PLACEHOLDER:
                continue

            row_links: list[str] = []
            for cell in cells:
                for href in links_in(cell):
                    if href.startswith("http") and href not in row_links:
                        row_links.append(href)
            primary = next((href for href in links_in(name_cell) if href.startswith("http")), "")
            url = primary or (row_links[0] if row_links else "")
            if not url:
                continue

            raw_date = (
                cells[date_index] if date_index is not None and date_index < len(cells) else ""
            )
            moment = parse_datetime(clean_cell(raw_date)) or parse_datetime(default_date)
            title, organization = _organization(title)

            identifier = f"{origin}:{slug(title)}:{slug(url)[:60]}"
            if identifier in seen:
                continue
            seen.add(identifier)

            skip = {0} | ({date_index} if date_index is not None else set())
            entries.append(
                RadarItem(
                    source=source,
                    source_id=identifier,
                    title=title,
                    url=url,
                    published_at=isoformat(moment) if moment else None,
                    summary=_row_summary(headers, cells, sorted(skip)),
                    organizations=[organization] if organization else [],
                    artifact_urls=[href for href in row_links if href != url][:6],
                    facets={
                        "survey_section": section,
                        "survey_origin": origin,
                        "columns": {
                            clean_heading(headers[i]) or f"column_{i}": clean_cell(cells[i])
                            for i in range(min(len(headers), len(cells)))
                            if _informative(clean_cell(cells[i]))
                        },
                    },
                    hint_categories=categories,
                    section=section,
                    event_kind="curated",
                    provenance=PROVENANCE_CURATED,
                    discovered_at=isoformat(parse_datetime(default_date) or utcnow()),
                    raw_payload_hash=payload_hash({"origin": origin, "title": title, "url": url}),
                )
            )
    return entries


def readme_path(root: Path, spec: Mapping[str, Any]) -> Path:
    return root / str(spec.get("readme") or "README.md")


def reports_dir(root: Path, spec: Mapping[str, Any]) -> Path:
    return root / str(spec.get("reports_dir") or "progressive reports")


def parse_readme(root: Path, spec: Mapping[str, Any]) -> list[RadarItem]:
    path = readme_path(root, spec)
    if not path.is_file():
        return []
    return parse_markdown_entries(
        path.read_text(encoding="utf-8", errors="replace"),
        source=README_SOURCE,
        origin="readme",
        heading_categories=spec.get("heading_categories") or {},
    )


def parse_reports(root: Path, spec: Mapping[str, Any]) -> dict[str, list[RadarItem]]:
    """Map report date -> entries, using the filename as the discovery date."""
    directory = reports_dir(root, spec)
    if not directory.is_dir():
        return {}
    grouped: dict[str, list[RadarItem]] = {}
    for path in sorted(directory.glob("*.md")):
        match = _REPORT_DATE.search(path.stem)
        if not match:
            continue
        date = match.group("date")
        entries = parse_markdown_entries(
            path.read_text(encoding="utf-8", errors="replace"),
            source=REPORT_SOURCE,
            origin=f"report/{date}",
            heading_categories=spec.get("heading_categories") or {},
            default_date=date,
        )
        for entry in entries:
            entry.facets["report_date"] = date
        if entries:
            grouped[date] = entries
    return grouped


def fetch(spec: Mapping[str, Any], ctx: FetchContext) -> list[RadarItem]:
    """Emit curated entries whose own date falls inside the curated window."""
    root = ctx.settings.survey_root()
    if root is None:
        return []

    floor = ctx.now - _timedelta_hours(ctx.settings.curated_lookback_hours)
    collected: list[RadarItem] = []

    for entries in parse_reports(root, spec).values():
        for entry in entries:
            moment = parse_datetime(entry.published_at) or parse_datetime(
                entry.facets.get("report_date")
            )
            if moment and moment >= floor:
                collected.append(entry)

    for entry in parse_readme(root, spec):
        moment = parse_datetime(entry.published_at)
        if moment and moment >= floor:
            entry.discovered_at = ctx.now_iso
            collected.append(entry)

    deduped: dict[str, RadarItem] = {}
    for entry in collected:
        key = f"{slug(entry.title)}:{entry.url}"
        if key not in deduped:
            deduped[key] = entry
    return list(deduped.values())


def _timedelta_hours(hours: float):
    from datetime import timedelta

    return timedelta(hours=float(hours))
