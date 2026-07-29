from __future__ import annotations

from vlm_radar.taxonomy import Taxonomy
from vlm_radar.textutil import normalize


def match(taxonomy: Taxonomy, text: str):
    return taxonomy.categorize(normalize(text))


def test_short_acronyms_do_not_match_inside_longer_words(settings):
    taxonomy = settings.taxonomy
    assert taxonomy.anchor_hits(normalize("a VLM survey"))
    # "vit" must not fire on "invite", and "vqa" must not fire on "vqaish".
    assert not taxonomy.anchor_hits(normalize("please invite the committee"))


def test_acronyms_survive_pluralization(settings):
    taxonomy = settings.taxonomy
    assert taxonomy.anchor_hits(normalize("Recent VLMs outperform prior work"))
    assert taxonomy.anchor_hits(normalize("evaluating MLLMs at scale"))


def test_terms_match_across_hyphenation(settings):
    keys_hyphen, _ = match(settings.taxonomy, "A vision-language model for charts")
    keys_space, _ = match(settings.taxonomy, "A vision language model for charts")
    assert keys_hyphen == keys_space
    assert "vlm_model" in keys_hyphen


def test_domain_gate_rejects_text_only_language_model_work(settings):
    taxonomy = settings.taxonomy
    text_only = normalize(
        "We release a benchmark for evaluating large language models on legal reasoning "
        "with 3,000 statute questions."
    )
    assert not taxonomy.in_domain(text_only)

    multimodal = normalize(
        "We release a benchmark for evaluating multimodal large language models on chart "
        "question answering."
    )
    assert taxonomy.in_domain(multimodal)


def test_categorize_returns_config_order_and_matched_terms(settings):
    keys, terms = match(
        settings.taxonomy,
        "Efficient token pruning for long video understanding in vision-language models",
    )
    assert "vlm_model" in keys
    assert "video" in keys
    assert "efficiency" in keys
    assert keys.index("vlm_model") < keys.index("video") < keys.index("efficiency")
    assert "token pruning" in terms


def test_model_families_and_watchlist_are_detected(settings):
    taxonomy = settings.taxonomy
    text = normalize("Qwen2.5-VL sets a new state of the art on MMMU and MathVista")
    assert "Qwen-VL" in taxonomy.match_families(text)
    names = [name for name, _ in taxonomy.match_watchlist(text)]
    assert "MMMU" in names
    assert "MathVista / MathVision" in names


def test_family_orgs_resolve_from_config(settings):
    assert settings.taxonomy.family_orgs(["Qwen-VL"]) == ["Alibaba"]


def test_low_value_rules_split_into_demote_and_suppress(settings):
    taxonomy = settings.taxonomy
    demoted = taxonomy.low_value_hits("Qwen2.5-VL-7B-Instruct GGUF quantized weights")
    assert demoted and all(rule.action == "demote" for rule in demoted)

    suppressed = taxonomy.low_value_hits("test upload")
    assert any(rule.action == "suppress" for rule in suppressed)


def test_label_falls_back_to_a_readable_string(settings):
    assert settings.taxonomy.label("vlm_model") == "VLM releases"
    assert settings.taxonomy.label("not_a_category") == "Not A Category"


def test_public_dict_publishes_labels_for_the_frontend(settings):
    payload = settings.taxonomy.to_public_dict()
    keys = {entry["key"] for entry in payload["categories"]}
    assert {"vlm_model", "benchmark", "embodied_vla", "hallucination"} <= keys
    assert all(entry["label"] for entry in payload["categories"])
