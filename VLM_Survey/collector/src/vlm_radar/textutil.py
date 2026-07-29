"""Text normalization shared by matching, deduplication, and summarization.

Keyword matching happens on a single normalized form so that "vision-language",
"vision language", and "Vision_Language" are the same string. Every term in
config.yml is normalized the same way at load time.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
import urllib.parse
from datetime import datetime, timedelta, timezone

_SEPARATORS = re.compile(r"[-_/\\.,;:()\[\]{}\u2010-\u2015\u2018\u2019\u201c\u201d\"'`*~|+]")
_WHITESPACE = re.compile(r"\s+")
_MD_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_MD_LINK = re.compile(r"\[([^\]]*)\]\(([^)]*)\)")
_MD_CODE_FENCE = re.compile(r"```.*?```", re.DOTALL)
_MD_INLINE_CODE = re.compile(r"`([^`]*)`")
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_HTML_TAG = re.compile(r"<[^>]+>")
_YAML_FRONT_MATTER = re.compile(r"\A---\s*\n.*?\n---\s*\n", re.DOTALL)
_MD_HEADING = re.compile(r"^\s{0,3}#{1,6}\s*", re.MULTILINE)
_MD_EMPHASIS = re.compile(r"(\*\*|__|\*|_)")
_TRACKING_PARAMS = frozenset(
    {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "ref",
        "referrer",
        "source",
        "fbclid",
        "gclid",
        "spm",
    }
)


def normalize(text: str) -> str:
    """Fold text to a lowercase, separator-free form used for keyword matching."""
    if not text:
        return ""
    folded = unicodedata.normalize("NFKD", text)
    folded = folded.encode("ascii", "ignore").decode("ascii").lower()
    folded = _SEPARATORS.sub(" ", folded)
    return _WHITESPACE.sub(" ", folded).strip()


def slug(text: str) -> str:
    """Stable identifier fragment for entity keys and DOM ids."""
    return re.sub(r"[^a-z0-9]+", "-", normalize(text)).strip("-")


def strip_markdown(text: str, *, limit: int = 900) -> str:
    """Reduce a README or model card to a single plain-text paragraph.

    Returns an empty string when nothing usable survives. Callers must never
    substitute filler prose: an empty summary is honest, and boilerplate would
    let a record score on text the radar itself invented.
    """
    if not text:
        return ""
    body = _YAML_FRONT_MATTER.sub("", text)
    body = _HTML_COMMENT.sub(" ", body)
    body = _MD_CODE_FENCE.sub(" ", body)
    body = _MD_IMAGE.sub(" ", body)
    body = _MD_LINK.sub(r"\1", body)
    body = _HTML_TAG.sub(" ", body)
    body = _MD_INLINE_CODE.sub(r"\1", body)
    body = _MD_HEADING.sub("", body)
    body = _MD_EMPHASIS.sub("", body)

    paragraphs = []
    for chunk in body.split("\n\n"):
        cleaned = _WHITESPACE.sub(" ", chunk).strip(" -*|#>\t")
        if len(cleaned) < 40:
            continue
        if cleaned.count("|") > 3:  # residual markdown table
            continue
        paragraphs.append(cleaned)
        if sum(len(p) for p in paragraphs) > limit:
            break
    if not paragraphs:
        single = _WHITESPACE.sub(" ", body).strip(" -*|#>\t")
        if len(single) < 40:
            return ""
        paragraphs = [single]
    summary = " ".join(paragraphs)
    return truncate(summary, limit)


def truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return cut.rstrip(" ,;:.") + "..."


def canonical_url(url: str) -> str:
    """Drop tracking parameters and casing differences so URLs compare equal."""
    if not url:
        return ""
    try:
        parts = urllib.parse.urlsplit(url.strip())
    except ValueError:
        return url.strip()
    if not parts.scheme and not parts.netloc:
        return url.strip()
    query = [
        (key, value)
        for key, value in urllib.parse.parse_qsl(parts.query, keep_blank_values=False)
        if key.lower() not in _TRACKING_PARAMS
    ]
    path = parts.path.rstrip("/") or "/"
    return urllib.parse.urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            path,
            urllib.parse.urlencode(query),
            "",
        )
    )


def digest(*parts: str) -> str:
    hasher = hashlib.sha256()
    for part in parts:
        hasher.update(part.encode("utf-8", "ignore"))
        hasher.update(b"\x1f")
    return hasher.hexdigest()


def payload_hash(payload: object) -> str:
    """Fingerprint a raw upstream payload without republishing it."""
    import json

    encoded = json.dumps(payload, sort_keys=True, default=str, ensure_ascii=False)
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def isoformat(moment: datetime) -> str:
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).isoformat()


_DATE_FORMATS = (
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S.%f%z",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%a, %d %b %Y %H:%M:%S %z",
    "%a, %d %b %Y %H:%M:%S %Z",
    "%d %b %Y",
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%m/%Y",
    "%Y/%m/%d",
    "%B %d, %Y",
    "%b %d, %Y",
    "%Y",
)


def parse_datetime(value: object) -> datetime | None:
    """Parse the many date shapes upstream sources emit. Returns UTC or None."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    candidate = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(candidate)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        pass
    for fmt in _DATE_FORMATS:
        try:
            parsed = datetime.strptime(text, fmt)
        except ValueError:
            continue
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    return None


def hours_between(later: datetime, earlier: datetime) -> float:
    return max(0.0, (later - earlier).total_seconds() / 3600.0)


def day_key(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%d")


def days_ago(moment: datetime, count: int) -> datetime:
    return moment - timedelta(days=count)
