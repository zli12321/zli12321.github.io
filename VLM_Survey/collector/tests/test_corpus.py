from __future__ import annotations

from vlm_radar import corpus


def key(**payload):
    return corpus.exact_artifact_key(payload)


def test_arxiv_identity_survives_abs_pdf_and_html_urls():
    expected = "arxiv:2607.00712"
    assert key(url="https://arxiv.org/abs/2607.00712") == expected
    assert key(url="https://arxiv.org/pdf/2607.00712") == expected
    assert key(url="https://arxiv.org/html/2607.00712v2") == expected
    assert key(url="https://huggingface.co/papers/2607.00712") == expected


def test_doi_outranks_other_identifiers():
    assert (
        key(
            url="https://arxiv.org/abs/2607.00712",
            facets={"doi": "10.1109/CVPR.2026.12345"},
        )
        == "doi:10.1109/cvpr.2026.12345"
    )


def test_hugging_face_repo_identity_is_case_insensitive():
    assert key(source="Hugging Face Models", source_id="Qwen/Qwen3-VL-8B-Instruct") == (
        "hf:qwen/qwen3-vl-8b-instruct"
    )
    assert key(url="https://huggingface.co/datasets/lmms-lab/VQAv2") == "hf:lmms-lab/vqav2"


def test_hugging_face_reserved_paths_are_not_treated_as_repositories():
    assert key(url="https://huggingface.co/collections/qwen/qwen3-vl").startswith("url:")


def test_github_repo_identity_ignores_git_suffix():
    assert key(url="https://github.com/QwenLM/Qwen3-VL.git") == "gh:qwenlm/qwen3-vl"


def test_unknown_urls_fall_back_to_a_canonical_url_key():
    assert key(url="https://example.com/model/?utm_source=x") == "url:https://example.com/model"


def test_similar_titles_never_merge():
    days = [
        {
            "date": "2026-07-28",
            "items": [
                {
                    "title": "MMBench: a multimodal benchmark",
                    "url": "https://arxiv.org/abs/2607.00001",
                    "source": "arXiv",
                    "categories": ["benchmark"],
                    "total_score": 60,
                },
                {
                    "title": "MMBench: a multimodal benchmark",
                    "url": "https://arxiv.org/abs/2607.00002",
                    "source": "arXiv",
                    "categories": ["benchmark"],
                    "total_score": 55,
                },
            ],
        }
    ]

    class Taxonomy:
        def label(self, key):
            return key

    graph = corpus.build_corpus(days, Taxonomy())
    assert graph["artifact_count"] == 2


def test_graph_links_artifacts_to_topics_sources_families_and_orgs(settings):
    days = [
        {
            "date": "2026-07-28",
            "items": [
                {
                    "title": "Qwen3-VL",
                    "url": "https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct",
                    "source": "Hugging Face Models",
                    "corroborating_sources": ["GitHub"],
                    "categories": ["vlm_model", "benchmark"],
                    "organizations": ["Alibaba"],
                    "model_families": ["Qwen-VL"],
                    "total_score": 72.5,
                }
            ],
        }
    ]
    graph = corpus.build_corpus(days, settings.taxonomy)
    kinds = {entity["kind"] for entity in graph["entities"]}
    assert kinds == {"artifact", "topic", "source", "organization", "model_family"}

    relations = {edge["relation"] for edge in graph["edges"]}
    assert relations == {"FOUND_VIA", "HAS_TOPIC", "RELEASED_BY", "TRACKS_FAMILY"}
    assert sum(1 for edge in graph["edges"] if edge["relation"] == "FOUND_VIA") == 2

    labels = {entity["label"] for entity in graph["entities"] if entity["kind"] == "topic"}
    assert "VLM releases" in labels


def test_velocity_marks_the_first_window_as_not_comparable(settings):
    days = [
        {
            "date": f"2026-07-{day:02d}",
            "items": [
                {
                    "title": f"paper {day}",
                    "url": f"https://arxiv.org/abs/2607.0000{day}",
                    "source": "arXiv",
                    "categories": ["benchmark"],
                    "total_score": 50,
                }
            ],
        }
        for day in range(1, 4)
    ]
    velocity = corpus.build_corpus(days, settings.taxonomy)["aggregates"]["topic_velocity"]
    row = next(entry for entry in velocity if entry["category"] == "benchmark")
    assert row["recent"] == 3
    assert row["comparable"] is False


def test_artifact_cap_keeps_context_nodes(settings):
    days = [
        {
            "date": "2026-07-28",
            "items": [
                {
                    "title": f"paper {index}",
                    "url": f"https://arxiv.org/abs/2607.{index:05d}",
                    "source": "arXiv",
                    "categories": ["benchmark"],
                    "total_score": index,
                }
                for index in range(30)
            ],
        }
    ]
    graph = corpus.build_corpus(days, settings.taxonomy, max_artifacts=5)
    artifacts = [entity for entity in graph["entities"] if entity["kind"] == "artifact"]
    assert len(artifacts) == 5
    assert graph["artifact_count"] == 30
    assert any(entity["kind"] == "topic" for entity in graph["entities"])
    assert all(
        edge["source"] in {entity["id"] for entity in graph["entities"]} for edge in graph["edges"]
    )
