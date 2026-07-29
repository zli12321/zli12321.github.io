"""Standard-library HTTP client with retries and credential-safe errors.

The collector deliberately avoids `requests` so that a fresh checkout needs only
PyYAML and certifi. Every source goes through `get_json` or `get_text`.
"""

from __future__ import annotations

import gzip
import json
import os
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from collections.abc import Mapping, Sequence
from typing import Any

from . import __version__

USER_AGENT = f"vlm-radar/{__version__} (+https://github.com/topics/vision-language-model)"
RETRY_STATUS = frozenset({408, 425, 429, 500, 502, 503, 504})


def _ssl_context() -> ssl.SSLContext:
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:  # pragma: no cover - certifi is a declared dependency
        return ssl.create_default_context()


_CONTEXT = _ssl_context()


class HttpError(RuntimeError):
    """Raised when a request fails after exhausting retries."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


def _redact(url: str) -> str:
    """Strip query values that look like credentials before logging a URL."""
    try:
        parts = urllib.parse.urlsplit(url)
    except ValueError:
        return "<unparsable url>"
    if not parts.query:
        return f"{parts.scheme}://{parts.netloc}{parts.path}"
    kept = []
    for key, value in urllib.parse.parse_qsl(parts.query, keep_blank_values=True):
        lowered = key.lower()
        if any(marker in lowered for marker in ("key", "token", "secret", "password", "auth")):
            kept.append((key, "REDACTED"))
        else:
            kept.append((key, value))
    return urllib.parse.urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urllib.parse.urlencode(kept), "")
    )


def build_url(url: str, params: Mapping[str, Any] | None = None) -> str:
    if not params:
        return url
    pairs: list[tuple[str, str]] = []
    for key, value in params.items():
        if value is None:
            continue
        if isinstance(value, (list, tuple, set)):
            for entry in value:
                pairs.append((key, str(entry)))
        else:
            pairs.append((key, str(value)))
    if not pairs:
        return url
    separator = "&" if urllib.parse.urlsplit(url).query else "?"
    return url + separator + urllib.parse.urlencode(pairs)


def _decode(raw: bytes, encoding: str) -> str:
    if encoding == "gzip":
        try:
            raw = gzip.decompress(raw)
        except OSError:
            pass
    elif encoding == "deflate":
        try:
            raw = zlib.decompress(raw, -zlib.MAX_WBITS)
        except zlib.error:
            pass
    return raw.decode("utf-8", "replace")


def get_text(
    url: str,
    *,
    params: Mapping[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
    timeout: float = 30.0,
    retries: int = 3,
    backoff: float = 2.0,
    accept: str = "*/*",
) -> str:
    """Fetch a URL as text, retrying transient failures with exponential backoff."""
    target = build_url(url, params)
    request_headers: dict[str, str] = {
        "User-Agent": USER_AGENT,
        "Accept": accept,
        "Accept-Encoding": "gzip, deflate",
    }
    if headers:
        request_headers.update({k: v for k, v in headers.items() if v})

    last_error: str | None = None
    last_status: int | None = None
    for attempt in range(retries):
        request = urllib.request.Request(target, headers=request_headers)
        try:
            with urllib.request.urlopen(request, timeout=timeout, context=_CONTEXT) as response:
                encoding = (response.headers.get("Content-Encoding") or "").lower()
                return _decode(response.read(), encoding)
        except urllib.error.HTTPError as error:
            last_status = error.code
            last_error = f"HTTP {error.code}"
            if error.code not in RETRY_STATUS or attempt == retries - 1:
                break
            wait = _retry_after(error.headers.get("Retry-After")) or backoff * (2**attempt)
            time.sleep(min(wait, 30.0))
        except (urllib.error.URLError, TimeoutError, ssl.SSLError, ConnectionError) as error:
            last_error = f"{type(error).__name__}: {error}"
            if attempt == retries - 1:
                break
            time.sleep(backoff * (2**attempt))
    raise HttpError(f"{_redact(target)} failed ({last_error})", status=last_status)


def _retry_after(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def get_json(
    url: str,
    *,
    params: Mapping[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
    timeout: float = 30.0,
    retries: int = 3,
) -> Any:
    body = get_text(
        url,
        params=params,
        headers=headers,
        timeout=timeout,
        retries=retries,
        accept="application/json",
    )
    try:
        return json.loads(body)
    except json.JSONDecodeError as error:
        raise HttpError(
            f"{_redact(build_url(url, params))} returned malformed JSON: {error}"
        ) from error


def github_headers() -> dict[str, str]:
    """Authorization headers for GitHub, if a token is present in the environment."""
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def first_present(mapping: Mapping[str, Any], keys: Sequence[str]) -> Any:
    for key in keys:
        if key in mapping and mapping[key] not in (None, "", [], {}):
            return mapping[key]
    return None
