"""Domain gate and category matching.

Two independent decisions live here:

1. Is the record about vision-language work at all? (`Taxonomy.anchor_hits`)
2. Which research buckets does it belong to? (`Taxonomy.categorize`)

Both operate on the normalized text form from `textutil.normalize`, and both are
driven entirely by config.yml so that retuning the radar never requires a code
change.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field

from .textutil import normalize

# Terms match on word boundaries so short acronyms like "vlm" or "vqa" cannot
# match inside a longer word, plus a small suffix group so that a single config
# entry covers "caption", "captions", and "captioning".
_INFLECTIONS = r"(?:s|es|ed|ing)?"


def compile_term(term: str) -> tuple[str, re.Pattern[str]]:
    normalized = normalize(term)
    if not normalized:
        raise ValueError(f"term {term!r} normalizes to nothing")
    pattern = re.compile(r"(?<![a-z0-9])" + re.escape(normalized) + _INFLECTIONS + r"(?![a-z0-9])")
    return normalized, pattern


def compile_terms(terms: Iterable[str]) -> list[tuple[str, re.Pattern[str]]]:
    compiled = []
    seen = set()
    for term in terms:
        try:
            normalized, pattern = compile_term(term)
        except ValueError:
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        compiled.append((normalized, pattern))
    return compiled


@dataclass
class Category:
    key: str
    label: str
    blurb: str = ""
    terms: list[tuple[str, re.Pattern[str]]] = field(default_factory=list)

    def matches(self, text: str) -> list[str]:
        return [term for term, pattern in self.terms if pattern.search(text)]

    def to_public_dict(self) -> dict[str, str]:
        return {"key": self.key, "label": self.label, "blurb": self.blurb}


@dataclass
class NamedEntity:
    """A model family or watchlisted benchmark, matched by name plus aliases."""

    name: str
    note: str = ""
    org: str = ""
    patterns: list[tuple[str, re.Pattern[str]]] = field(default_factory=list)

    def matches(self, text: str) -> bool:
        return any(pattern.search(text) for _, pattern in self.patterns)

    def to_public_dict(self) -> dict[str, str]:
        payload = {"name": self.name}
        if self.note:
            payload["note"] = self.note
        if self.org:
            payload["org"] = self.org
        return payload


@dataclass
class LowValueRule:
    pattern: re.Pattern[str]
    reason: str
    action: str  # "demote" or "suppress"


class Taxonomy:
    """Compiled view of the `domain`, `taxonomy`, and watchlist config blocks."""

    def __init__(
        self,
        categories: Sequence[Category],
        anchors: Sequence[tuple[str, re.Pattern[str]]],
        minimum_anchor_hits: int,
        model_families: Sequence[NamedEntity],
        watchlist: Sequence[NamedEntity],
        low_value: Sequence[LowValueRule],
    ) -> None:
        self.categories = list(categories)
        self._by_key = {category.key: category for category in self.categories}
        self.anchors = list(anchors)
        self.minimum_anchor_hits = max(0, int(minimum_anchor_hits))
        self.model_families = list(model_families)
        self.watchlist = list(watchlist)
        self.low_value = list(low_value)

    @classmethod
    def from_config(cls, config: Mapping) -> Taxonomy:
        domain = config.get("domain") or {}
        anchors = compile_terms(domain.get("anchors") or [])

        categories = []
        for key, spec in (config.get("taxonomy") or {}).items():
            spec = spec or {}
            categories.append(
                Category(
                    key=key,
                    label=spec.get("label") or key.replace("_", " ").title(),
                    blurb=spec.get("blurb") or "",
                    terms=compile_terms(spec.get("terms") or []),
                )
            )

        families = [
            NamedEntity(
                name=entry.get("name", ""),
                org=entry.get("org", ""),
                patterns=compile_terms([entry.get("name", "")] + list(entry.get("aliases") or [])),
            )
            for entry in (config.get("model_families") or [])
            if entry.get("name")
        ]
        watchlist = [
            NamedEntity(
                name=entry.get("name", ""),
                note=entry.get("note", ""),
                patterns=compile_terms([entry.get("name", "")] + list(entry.get("aliases") or [])),
            )
            for entry in (config.get("watchlist") or [])
            if entry.get("name")
        ]

        low_value = []
        low_value_config = config.get("low_value") or {}
        for action in ("demote", "suppress"):
            for rule in low_value_config.get(action) or []:
                raw = rule.get("pattern")
                if not raw:
                    continue
                low_value.append(
                    LowValueRule(
                        pattern=re.compile(raw),
                        reason=rule.get("reason") or f"Matched {action} rule",
                        action=action,
                    )
                )

        return cls(
            categories=categories,
            anchors=anchors,
            minimum_anchor_hits=int(domain.get("minimum_hits", 1)),
            model_families=families,
            watchlist=watchlist,
            low_value=low_value,
        )

    def label(self, key: str) -> str:
        category = self._by_key.get(key)
        return category.label if category else key.replace("_", " ").title()

    def anchor_hits(self, text: str) -> list[str]:
        return [term for term, pattern in self.anchors if pattern.search(text)]

    def in_domain(self, text: str) -> bool:
        if self.minimum_anchor_hits <= 0:
            return True
        return len(self.anchor_hits(text)) >= self.minimum_anchor_hits

    def categorize(self, text: str) -> tuple[list[str], list[str]]:
        """Return (category keys, matched terms) preserving config order."""
        keys: list[str] = []
        terms: list[str] = []
        for category in self.categories:
            hits = category.matches(text)
            if not hits:
                continue
            keys.append(category.key)
            for hit in hits:
                if hit not in terms:
                    terms.append(hit)
        return keys, terms

    def match_families(self, text: str) -> list[str]:
        return [family.name for family in self.model_families if family.matches(text)]

    def family_orgs(self, names: Sequence[str]) -> list[str]:
        lookup = {family.name: family.org for family in self.model_families}
        return [lookup[name] for name in names if lookup.get(name)]

    def match_watchlist(self, text: str) -> list[tuple[str, str]]:
        return [(e.name, e.note) for e in self.watchlist if e.matches(text)]

    def low_value_hits(self, raw_text: str) -> list[LowValueRule]:
        return [rule for rule in self.low_value if rule.pattern.search(raw_text)]

    def to_public_dict(self) -> dict[str, object]:
        return {
            "categories": [category.to_public_dict() for category in self.categories],
            "model_families": [family.to_public_dict() for family in self.model_families],
            "watchlist": [entry.to_public_dict() for entry in self.watchlist],
        }
