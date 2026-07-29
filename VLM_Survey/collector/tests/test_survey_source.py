from __future__ import annotations

from vlm_radar.sources import survey

FIXTURE = """
# Awesome Vision-Language Models

Intro prose that should never become an entry.

## 1. SoTA VLMs

| Model | Year | Architecture | Parameters | Vision Encoder |
|-------|------|--------------|------------|----------------|
| [Qwen3-VL (Alibaba)](https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct) | 10/11/2025 | Decoder-only | 8B | ViT |
| [Molmo2 (Allen AI)](https://arxiv.org/abs/2601.10611) | 01/15/2026 | Decoder-only | 7B | Bi-directional ViT |
| Undocumented row without a link | 2024 | - | - | - |

## 4. Applications

### 4.3 Robotics and Embodied AI

#### 4.3.1 Manipulation

| Title | Year | Paper | Code |
|-------|------|-------|------|
| RT-2: Vision-Language-Action Models | 2023 | [Paper](https://arxiv.org/abs/2307.15818) | [Code](https://github.com/example/rt2) |

```
| Fenced | table | that | must | be | ignored |
|---|---|---|---|---|---|
| no | no | no | no | no | no |
```
"""


def parse(default_date=None):
    return survey.parse_markdown_entries(
        FIXTURE,
        source="VLM Survey",
        origin="fixture",
        heading_categories={
            "sota vlm": ["vlm_model"],
            "manipulation": ["embodied_vla"],
        },
        default_date=default_date,
    )


def test_rows_become_entries_and_prose_does_not():
    entries = parse()
    titles = [entry.title for entry in entries]
    assert titles == ["Qwen3-VL", "Molmo2", "RT-2: Vision-Language-Action Models"]


def test_rows_without_a_link_are_skipped():
    assert all("Undocumented" not in entry.title for entry in parse())


def test_fenced_code_blocks_are_not_parsed_as_tables():
    assert all("Fenced" not in entry.title for entry in parse())


def test_trailing_parenthetical_becomes_the_organization():
    entries = {entry.title: entry for entry in parse()}
    assert entries["Qwen3-VL"].organizations == ["Alibaba"]
    assert entries["Molmo2"].organizations == ["Allen AI"]


def test_heading_trail_supplies_section_and_hint_categories():
    entries = {entry.title: entry for entry in parse()}
    qwen = entries["Qwen3-VL"]
    assert qwen.section == "1. SoTA VLMs"
    assert qwen.hint_categories == ["vlm_model"]

    rt2 = entries["RT-2: Vision-Language-Action Models"]
    assert "4.3.1 Manipulation" in rt2.section
    assert "embodied_vla" in rt2.hint_categories


def test_level_one_heading_is_excluded_from_the_trail():
    for entry in parse():
        assert "Awesome Vision-Language Models" not in entry.section


def test_date_column_is_parsed_into_published_at():
    entries = {entry.title: entry for entry in parse()}
    assert entries["Qwen3-VL"].published_at.startswith("2025-10-11")
    assert entries["Molmo2"].published_at.startswith("2026-01-15")


def test_summary_uses_column_headers_and_skips_generic_link_labels():
    entries = {entry.title: entry for entry in parse()}
    assert "Architecture: Decoder-only" in entries["Qwen3-VL"].summary
    rt2 = entries["RT-2: Vision-Language-Action Models"]
    assert "Paper: Paper" not in rt2.summary
    assert "Code: Code" not in rt2.summary


def test_secondary_links_land_in_artifact_urls():
    rt2 = next(e for e in parse() if e.title.startswith("RT-2"))
    assert rt2.url == "https://arxiv.org/abs/2307.15818"
    assert "https://github.com/example/rt2" in rt2.artifact_urls


def test_default_date_backfills_undated_rows():
    entries = {entry.title: entry for entry in parse(default_date="2026-07-22")}
    rt2 = entries["RT-2: Vision-Language-Action Models"]
    assert rt2.discovered_at.startswith("2026-07-22")


def test_entries_are_marked_curated():
    assert all(entry.provenance == "curated" for entry in parse())
    assert all(entry.event_kind == "curated" for entry in parse())


def test_real_repository_parses_when_present(settings):
    root = settings.survey_root()
    if root is None:
        return  # the sibling survey checkout is optional
    spec = settings.source("survey")
    readme_entries = survey.parse_readme(root, spec)
    assert len(readme_entries) > 100
    assert all(entry.url.startswith("http") for entry in readme_entries)

    reports = survey.parse_reports(root, spec)
    assert reports
    for date, entries in reports.items():
        assert len(date) == 10
        assert entries
