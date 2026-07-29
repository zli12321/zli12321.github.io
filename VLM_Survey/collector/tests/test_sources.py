"""Fetcher tests against recorded upstream payloads.

Each source is exercised with a realistic response shape rather than a live call,
so field mapping stays covered without network access or rate limits. The fixtures
are trimmed copies of real responses.
"""

from __future__ import annotations

import json
from datetime import timedelta

import pytest

from vlm_radar import http
from vlm_radar.sources import arxiv, github, huggingface, scholar
from vlm_radar.sources.base import FetchContext

ARXIV_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/">
  <channel>
    <title>cs.CV updates on arXiv.org</title>
    <lastBuildDate>Tue, 28 Jul 2026 04:00:00 -0400</lastBuildDate>
    <item>
      <title>ChartLens: A Benchmark for Chart Understanding in Vision-Language Models</title>
      <link>https://arxiv.org/abs/2607.12345</link>
      <description>arXiv:2607.12345v1 Announce Type: new
Abstract: We present ChartLens, a benchmark of 4,000 chart question answering pairs for
evaluating multimodal large language models on scientific figures.</description>
      <dc:creator>Ada Lovelace, Grace Hopper</dc:creator>
      <category>cs.CV</category>
      <category>cs.CL</category>
      <pubDate>Tue, 28 Jul 2026 04:00:00 -0400</pubDate>
    </item>
    <item>
      <title>Revisiting Token Pruning for Long Video Understanding</title>
      <link>https://arxiv.org/abs/2607.12346v2</link>
      <description>arXiv:2607.12346v2 Announce Type: replace
Abstract: We revisit visual token pruning for hour-long video understanding.</description>
      <dc:creator>Alan Turing</dc:creator>
      <category>cs.CV</category>
      <pubDate>Tue, 28 Jul 2026 04:00:00 -0400</pubDate>
    </item>
  </channel>
</rss>
"""

HF_MODELS = [
    {
        "id": "Qwen/Qwen3-VL-8B-Instruct",
        "author": "Qwen",
        "createdAt": "2026-07-27T10:00:00.000Z",
        "lastModified": "2026-07-28T08:15:00.000Z",
        "downloads": 48213,
        "likes": 412,
        "pipeline_tag": "image-text-to-text",
        "library_name": "transformers",
        "tags": ["multimodal", "vision-language", "image-text-to-text"],
        "cardData": {"license": "apache-2.0", "base_model": "Qwen/Qwen3-8B"},
    },
    {
        "id": "someone/Qwen3-VL-8B-GGUF",
        "createdAt": "2024-01-01T00:00:00.000Z",
        "lastModified": "2026-07-28T09:00:00.000Z",
        "downloads": 120,
        "likes": 3,
        "tags": ["gguf"],
    },
]

GITHUB_SEARCH = {
    "items": [
        {
            "full_name": "open-compass/VLMEvalKit",
            "html_url": "https://github.com/open-compass/VLMEvalKit",
            "description": "Open-source evaluation toolkit of large vision-language models",
            "stargazers_count": 3120,
            "forks_count": 440,
            "created_at": "2024-01-15T00:00:00Z",
            "pushed_at": "2026-07-28T06:00:00Z",
            "owner": {"login": "open-compass"},
            "topics": ["benchmark", "vlm"],
            "language": "Python",
            "license": {"spdx_id": "Apache-2.0"},
            "homepage": "https://open-compass.github.io/VLMEvalKit/",
        }
    ]
}

GITHUB_RELEASES = [
    {
        "tag_name": "v2.4.0",
        "name": "InternVL 2.4",
        "html_url": "https://github.com/OpenGVLab/InternVL/releases/tag/v2.4.0",
        "published_at": "2026-07-28T05:00:00Z",
        "body": "## Highlights\n\nAdds a new vision encoder and improves video understanding.",
        "draft": False,
        "prerelease": False,
    },
    {
        "tag_name": "v0.0.1-old",
        "name": "ancient",
        "html_url": "https://github.com/OpenGVLab/InternVL/releases/tag/v0.0.1-old",
        "published_at": "2024-01-01T00:00:00Z",
        "body": "old",
        "draft": False,
    },
]

S2_RESPONSE = {
    "data": [
        {
            "paperId": "abc123",
            "title": "Hallucination in Vision-Language Models: A Survey",
            "abstract": "We survey object hallucination in multimodal large language models.",
            "venue": "CVPR",
            "year": 2026,
            "publicationDate": "2026-07-20",
            "externalIds": {"ArXiv": "2607.09999", "DOI": "10.1109/CVPR.2026.1"},
            "url": "https://www.semanticscholar.org/paper/abc123",
            "openAccessPdf": {"url": "https://example.org/paper.pdf"},
            "citationCount": 12,
            "influentialCitationCount": 2,
            "authors": [{"name": "Ada Lovelace"}, {"name": "Alan Turing"}],
        }
    ]
}


@pytest.fixture()
def ctx(settings, now):
    return FetchContext(
        settings=settings, now=now, since=now - timedelta(hours=settings.lookback_hours)
    )


def test_arxiv_rss_maps_ids_abstracts_authors_and_event_kind(ctx, monkeypatch):
    monkeypatch.setattr(http, "get_text", lambda *a, **k: ARXIV_RSS)
    monkeypatch.setattr(arxiv.time, "sleep", lambda seconds: None)

    items = arxiv.fetch({"rss_categories": ["cs.CV"]}, ctx)
    assert len(items) == 2

    first, second = items
    assert first.source == "arXiv"
    assert first.source_id == "2607.12345"
    assert first.url == "https://arxiv.org/abs/2607.12345"
    assert first.event_kind == "published"
    assert first.summary.startswith("We present ChartLens")
    assert "arXiv:2607.12345v1" not in first.summary
    assert "Announce Type" not in first.summary
    assert first.authors == ["Ada Lovelace", "Grace Hopper"]
    assert first.facets["arxiv_categories"] == ["cs.CV", "cs.CL"]
    assert first.artifact_urls == ["https://arxiv.org/pdf/2607.12345"]
    assert first.published_at.startswith("2026-07-28")

    # A version bump is an update, and the version suffix is stripped from the id.
    assert second.source_id == "2607.12346"
    assert second.event_kind == "updated"


def test_arxiv_raises_when_every_category_fails(ctx, monkeypatch):
    def explode(*args, **kwargs):
        raise http.HttpError("HTTP 503")

    monkeypatch.setattr(http, "get_text", explode)
    monkeypatch.setattr(arxiv.time, "sleep", lambda seconds: None)
    with pytest.raises(http.HttpError):
        arxiv.fetch({"rss_categories": ["cs.CV", "cs.CL"]}, ctx)


def test_arxiv_survives_one_bad_category(ctx, monkeypatch):
    calls = {"n": 0}

    def flaky(url, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise http.HttpError("HTTP 503")
        return ARXIV_RSS

    monkeypatch.setattr(http, "get_text", flaky)
    monkeypatch.setattr(arxiv.time, "sleep", lambda seconds: None)
    assert len(arxiv.fetch({"rss_categories": ["cs.CV", "cs.CL"]}, ctx)) == 2


def test_hugging_face_models_map_metrics_facets_and_event_kind(ctx, monkeypatch):
    monkeypatch.setattr(http, "get_json", lambda *a, **k: HF_MODELS)
    monkeypatch.setattr(huggingface, "_card_text", lambda repo_id, dataset: "")

    items = huggingface.fetch_models({"searches": ["vision-language"], "card_limit": 0}, ctx)
    by_id = {item.source_id: item for item in items}
    assert set(by_id) == {"Qwen/Qwen3-VL-8B-Instruct", "someone/Qwen3-VL-8B-GGUF"}

    qwen = by_id["Qwen/Qwen3-VL-8B-Instruct"]
    assert qwen.source == "Hugging Face Models"
    assert qwen.url == "https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct"
    assert qwen.organizations == ["Qwen"]
    assert qwen.metrics == {"downloads": 48213.0, "likes": 412.0}
    assert qwen.facets["pipeline_tag"] == "image-text-to-text"
    assert qwen.facets["license"] == "apache-2.0"
    assert qwen.event_kind == "published"  # created inside the window

    # Created long ago, touched today: an update, not a release.
    assert by_id["someone/Qwen3-VL-8B-GGUF"].event_kind == "updated"


def test_hugging_face_summary_stays_empty_when_no_card_exists(ctx, monkeypatch):
    def missing_card(*args, **kwargs):
        raise http.HttpError("HTTP 404")

    monkeypatch.setattr(http, "get_json", lambda *a, **k: HF_MODELS)
    monkeypatch.setattr(http, "get_text", missing_card)

    items = huggingface.fetch_models({"searches": ["vlm"], "card_limit": 5}, ctx)
    assert all(item.summary == "" for item in items)


def test_hugging_face_card_enrichment_is_capped(ctx, monkeypatch):
    monkeypatch.setattr(http, "get_json", lambda *a, **k: HF_MODELS)
    fetched = []

    def card(repo_id, *, dataset):
        fetched.append(repo_id)
        return "A vision-language model card with enough prose to survive stripping, twice over."

    monkeypatch.setattr(huggingface, "_card_text", card)
    huggingface.fetch_models({"searches": ["vlm"], "card_limit": 1}, ctx)
    assert len(fetched) == 1


def test_hugging_face_daily_papers_map_upvotes(ctx, monkeypatch):
    payload = [
        {
            "paper": {
                "id": "2607.11111",
                "title": "Unified Multimodal Generation and Understanding",
                "summary": "We unify understanding and generation in one model.",
                "upvotes": 87,
                "authors": [{"name": "Grace Hopper"}],
                "publishedAt": "2026-07-27T00:00:00.000Z",
            },
            "numComments": 5,
        }
    ]
    monkeypatch.setattr(http, "get_json", lambda *a, **k: payload)
    items = huggingface.fetch_papers({"days": 1}, ctx)
    assert len(items) == 1
    item = items[0]
    assert item.source == "Hugging Face Papers"
    assert item.url == "https://huggingface.co/papers/2607.11111"
    assert item.artifact_urls == ["https://arxiv.org/abs/2607.11111"]
    assert item.metrics == {"upvotes": 87.0, "comments": 5.0}
    assert item.event_kind == "featured"


def test_github_search_maps_stars_topics_and_homepage(ctx, monkeypatch):
    monkeypatch.setattr(http, "get_json", lambda *a, **k: GITHUB_SEARCH)
    items = github.fetch_repositories({"queries": ['"vlm" in:name'], "per_page": 10}, ctx)
    assert len(items) == 1
    item = items[0]
    assert item.source == "GitHub"
    assert item.source_id == "open-compass/VLMEvalKit"
    assert item.organizations == ["open-compass"]
    assert item.metrics == {"stars": 3120.0, "forks": 440.0}
    assert item.facets["topics"] == ["benchmark", "vlm"]
    assert item.facets["license"] == "Apache-2.0"
    assert "https://open-compass.github.io/VLMEvalKit/" in item.artifact_urls
    assert item.event_kind == "updated"


def test_github_releases_are_filtered_to_the_scan_window(ctx, monkeypatch):
    monkeypatch.setattr(http, "get_json", lambda *a, **k: GITHUB_RELEASES)
    items = github.fetch_releases({"repositories": ["OpenGVLab/InternVL"], "per_page": 10}, ctx)
    assert len(items) == 1
    item = items[0]
    assert item.source_id == "OpenGVLab/InternVL@v2.4.0"
    assert item.event_kind == "released"
    assert item.facets["tag"] == "v2.4.0"
    assert "Adds a new vision encoder" in item.summary
    assert "## Highlights" not in item.summary


def test_github_releases_skip_drafts(ctx, monkeypatch):
    drafts = [dict(GITHUB_RELEASES[0], draft=True)]
    monkeypatch.setattr(http, "get_json", lambda *a, **k: drafts)
    assert github.fetch_releases({"repositories": ["a/b"]}, ctx) == []


def test_semantic_scholar_maps_ids_venue_and_citations(ctx, monkeypatch):
    monkeypatch.setattr(http, "get_json", lambda *a, **k: S2_RESPONSE)
    items = scholar.fetch_semantic_scholar({"searches": ["vlm hallucination"]}, ctx)
    assert len(items) == 1
    item = items[0]
    assert item.venue == "CVPR"
    assert item.metrics == {"citations": 12.0, "influential_citations": 2.0}
    assert "https://arxiv.org/abs/2607.09999" in item.artifact_urls
    assert "https://doi.org/10.1109/CVPR.2026.1" in item.artifact_urls
    assert item.facets["doi"] == "10.1109/CVPR.2026.1"
    assert item.authors == ["Ada Lovelace", "Alan Turing"]


def test_openalex_reconstructs_inverted_abstracts(ctx, monkeypatch):
    payload = {
        "results": [
            {
                "id": "https://openalex.org/W123",
                "display_name": "Spatial Reasoning in Vision-Language Models",
                "publication_date": "2026-07-25",
                "cited_by_count": 3,
                "abstract_inverted_index": {"Vision": [0], "language": [1], "models": [2]},
                "authorships": [
                    {
                        "author": {"display_name": "Ada Lovelace"},
                        "institutions": [{"display_name": "MIT"}],
                    }
                ],
                "primary_location": {"source": {"display_name": "NeurIPS"}},
                "doi": "https://doi.org/10.1/xyz",
            }
        ]
    }
    monkeypatch.setattr(http, "get_json", lambda *a, **k: payload)
    items = scholar.fetch_openalex({"searches": ["vlm"]}, ctx)
    assert len(items) == 1
    item = items[0]
    assert item.summary == "Vision language models"
    assert item.organizations == ["MIT"]
    assert item.venue == "NeurIPS"
    assert item.source_id == "W123"


def test_every_fetcher_produces_records_the_pipeline_can_score(ctx, settings, monkeypatch):
    """A fetcher must emit records that survive the domain gate end to end."""
    from vlm_radar import pipeline

    monkeypatch.setattr(http, "get_text", lambda *a, **k: ARXIV_RSS)
    monkeypatch.setattr(arxiv.time, "sleep", lambda seconds: None)
    items = arxiv.fetch({"rss_categories": ["cs.CV"]}, ctx)

    scored = [pipeline.score_item(item, settings, ctx.now) for item in items]
    kept, funnel = pipeline.select(scored, settings)
    assert funnel.out_of_domain == 0
    assert len(kept) == 2
    assert all(item.categories for item in kept)
    assert json.dumps([item.to_public_dict() for item in kept])
