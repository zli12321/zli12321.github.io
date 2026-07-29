from __future__ import annotations

from datetime import timedelta

import pytest
from helpers import make_item

from vlm_radar import pipeline
from vlm_radar.models import PROVENANCE_CURATED


def score(item, settings, now):
    return pipeline.score_item(item, settings, now)


def test_scoring_assigns_categories_terms_and_a_total(settings, now):
    item = score(make_item(), settings, now)
    assert "benchmark" in item.categories
    assert "document_ocr" in item.categories
    assert item.matched_terms
    assert 0 < item.total_score <= 100
    assert item.score_version == 1


def test_out_of_domain_records_are_flagged_not_silently_dropped(settings, now):
    item = score(
        make_item(
            title="A Benchmark for Legal Statute Retrieval",
            summary="We evaluate large language models on 3,000 statute retrieval questions.",
        ),
        settings,
        now,
    )
    assert any("domain anchor" in reason for reason in item.suppression_reasons)

    kept, funnel = pipeline.select([item], settings)
    assert kept == []
    assert funnel.out_of_domain == 1
    assert funnel.suppressed == 0


def test_placeholder_uploads_are_suppressed(settings, now):
    item = score(
        make_item(
            source="Hugging Face Models",
            source_id="someone/test",
            title="test upload of a vision language model",
            summary="",
        ),
        settings,
        now,
    )
    assert item.suppression_reasons
    _, funnel = pipeline.select([item], settings)
    assert funnel.suppressed == 1


def test_quantized_reuploads_are_demoted_but_still_selectable(settings, now):
    plain = score(make_item(title="MiniVLM: a compact vision-language model"), settings, now)
    quantized = score(
        make_item(
            source_id="q",
            title="MiniVLM: a compact vision-language model GGUF",
        ),
        settings,
        now,
    )
    assert quantized.total_score < plain.total_score
    assert any("Demoted" in line for line in quantized.rationale)
    assert not quantized.suppression_reasons


def test_deduplicate_merges_on_title_and_records_corroboration(settings, now):
    primary = make_item(source="arXiv", source_id="2607.00001")
    duplicate = make_item(
        source="Semantic Scholar",
        source_id="s2-1",
        url="https://www.semanticscholar.org/paper/abc",
        metrics={"citations": 4.0},
        organizations=["University of Somewhere"],
    )
    merged = pipeline.deduplicate([primary, duplicate])
    assert len(merged) == 1
    survivor = merged[0]
    assert survivor.corroborating_sources == ["Semantic Scholar"]
    assert survivor.metrics["citations"] == 4.0
    assert "University of Somewhere" in survivor.organizations
    assert any("Also found via" in line for line in survivor.rationale)


def test_deduplicate_keeps_distinct_records_apart(settings):
    first = make_item(title="MMBench: a multimodal capability benchmark", source_id="a")
    second = make_item(title="MMStar: a vision-indispensable benchmark", source_id="b")
    assert len(pipeline.deduplicate([first, second])) == 2


def test_short_titles_fall_back_to_url_identity(settings):
    a = make_item(title="Molmo2", url="https://arxiv.org/abs/2601.10611", source_id="a")
    b = make_item(title="Molmo2", url="https://huggingface.co/allenai/molmo2", source_id="b")
    assert len(pipeline.deduplicate([a, b])) == 2


def weak_pinned_item(now):
    """A tracked family with almost no supporting evidence: pinned but low scoring."""
    return make_item(
        source_id="pinned",
        title="Qwen-VL visual instruction tuning note",
        summary="",
        authors=[],
        artifact_urls=[],
        published_at=(now - timedelta(hours=47)).isoformat(),
    )


def test_pinned_records_bypass_the_score_floor(settings, now):
    scored = score(weak_pinned_item(now), settings, now)
    assert scored.model_families == ["Qwen-VL"]
    assert scored.total_score < settings.minimum_score

    kept, funnel = pipeline.select([scored], settings)
    assert kept and funnel.pinned == 1
    assert funnel.below_threshold == 0


def test_the_category_gate_applies_even_to_pinned_records(settings, now):
    """A pin lifts a record over the score floor, never over the category gate."""
    scored = score(
        make_item(title="Qwen-VL release note", summary="", authors=[], artifact_urls=[]),
        settings,
        now,
    )
    assert scored.model_families == ["Qwen-VL"]
    assert scored.categories == []

    kept, funnel = pipeline.select([scored], settings)
    assert kept == []
    assert funnel.out_of_domain == 1


def test_pinned_records_sort_above_higher_scoring_generic_records(settings, now):
    pinned = score(weak_pinned_item(now), settings, now)
    generic = score(make_item(source_id="generic"), settings, now)
    assert generic.total_score > pinned.total_score

    kept, _ = pipeline.select([generic, pinned], settings)
    assert kept[0] is pinned
    assert kept[1] is generic


def test_per_source_cap_prevents_one_source_from_crowding_out_others(settings, now):
    settings.raw["radar"]["max_items_per_source"] = 2
    try:
        items = [score(make_item(source_id=f"a{i}"), settings, now) for i in range(5)]
        items.append(score(make_item(source="GitHub", source_id="repo/one"), settings, now))
        kept, _ = pipeline.select(items, settings)
        sources = [item.source for item in kept]
        assert sources.count("arXiv") == 2
        assert "GitHub" in sources
    finally:
        settings.raw["radar"]["max_items_per_source"] = 300


def test_curated_records_decay_on_the_longer_window(settings, now):
    age = timedelta(hours=200)
    live = score(
        make_item(published_at=(now - age).isoformat()),
        settings,
        now,
    )
    curated = score(
        make_item(
            source="VLM Survey Report",
            provenance=PROVENANCE_CURATED,
            published_at=(now - age).isoformat(),
        ),
        settings,
        now,
    )
    assert live.recency_score == 0.0
    assert curated.recency_score > 0.0


def test_hint_categories_from_a_source_survive_scoring(settings, now):
    item = score(
        make_item(
            title="RoboWorld",
            summary="Fast autoregressive video world model for policy evaluation.",
            hint_categories=["embodied_vla"],
        ),
        settings,
        now,
    )
    assert "embodied_vla" in item.categories
    assert "world_model" in item.categories


def test_boilerplate_guard_fires_when_a_parser_breaks(settings, now):
    identical = "Dataset Summary This is the generic card text shared by every broken record."
    items = [score(make_item(source_id=str(i), summary=identical), settings, now) for i in range(4)]
    with pytest.raises(RuntimeError, match="identical summary"):
        pipeline.guard_boilerplate(items)


def test_funnel_counts_every_stage(settings, now):
    items = [
        score(make_item(source_id="keep"), settings, now),
        score(
            make_item(source_id="off", title="Legal statute retrieval benchmark", summary=""),
            settings,
            now,
        ),
        score(make_item(source_id="bad", title="test upload vision language"), settings, now),
    ]
    kept, funnel = pipeline.select(items, settings)
    assert funnel.published == len(kept) == 1
    assert funnel.out_of_domain == 1
    assert funnel.suppressed == 1
    assert funnel.minimum_score == settings.minimum_score
