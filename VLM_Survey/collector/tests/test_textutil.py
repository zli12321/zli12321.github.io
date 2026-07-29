from __future__ import annotations

from datetime import datetime, timezone

from vlm_radar import textutil


def test_normalize_folds_separators_so_hyphenation_stops_mattering():
    assert textutil.normalize("Vision-Language") == "vision language"
    assert textutil.normalize("Vision_Language") == textutil.normalize("vision language")
    assert textutil.normalize("Text-to-Image") == "text to image"


def test_normalize_strips_accents_and_collapses_whitespace():
    assert textutil.normalize("  Café   Résumé ") == "cafe resume"


def test_canonical_url_drops_tracking_parameters_and_trailing_slash():
    messy = "HTTPS://ArXiv.org/abs/2607.00001/?utm_source=x&ref=y&version=2"
    assert textutil.canonical_url(messy) == "https://arxiv.org/abs/2607.00001?version=2"


def test_canonical_url_makes_equivalent_urls_compare_equal():
    a = textutil.canonical_url("https://example.com/paper?utm_campaign=news")
    b = textutil.canonical_url("https://example.com/paper/")
    assert a == b


def test_strip_markdown_removes_front_matter_code_and_images():
    card = """---
license: apache-2.0
---

# MyVLM

![banner](banner.png)

MyVLM is a vision-language model trained on interleaved image-text data and
evaluated on twelve public benchmarks covering captioning and reasoning.

```python
print("ignored")
```
"""
    summary = textutil.strip_markdown(card)
    assert "license" not in summary
    assert "banner" not in summary
    assert "ignored" not in summary
    assert summary.startswith("MyVLM is a vision-language model")


def test_strip_markdown_returns_empty_rather_than_inventing_prose():
    assert textutil.strip_markdown("") == ""
    assert textutil.strip_markdown("# Title\n\n- a\n- b\n") == ""


def test_parse_datetime_handles_the_shapes_sources_actually_emit():
    cases = {
        "2026-07-28T09:59:05Z": (2026, 7, 28),
        "2026-07-28": (2026, 7, 28),
        "07/21/2026": (2026, 7, 21),
        "04/2026": (2026, 4, 1),
        "2026": (2026, 1, 1),
        "Tue, 21 Jul 2026 00:00:00 -0400": (2026, 7, 21),
    }
    for raw, expected in cases.items():
        parsed = textutil.parse_datetime(raw)
        assert parsed is not None, raw
        assert (parsed.year, parsed.month, parsed.day) == expected or raw.endswith("-0400")
        assert parsed.tzinfo is not None


def test_parse_datetime_returns_none_for_unparsable_values():
    assert textutil.parse_datetime("Undisclosed") is None
    assert textutil.parse_datetime("-") is None
    assert textutil.parse_datetime(None) is None


def test_day_key_is_utc():
    moment = datetime(2026, 7, 28, 23, 30, tzinfo=timezone.utc)
    assert textutil.day_key(moment) == "2026-07-28"


def test_payload_hash_is_stable_and_prefixed():
    first = textutil.payload_hash({"b": 1, "a": 2})
    second = textutil.payload_hash({"a": 2, "b": 1})
    assert first == second
    assert first.startswith("sha256:")
