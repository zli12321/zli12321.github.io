"""Source registry.

Adding a source means writing a `fetch(spec, ctx) -> List[RadarItem]` callable and
registering it here under the key it uses in config.yml. Nothing else in the
codebase needs to change.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Callable

from ..models import RadarItem
from . import arxiv, github, huggingface, scholar, survey
from .base import FetchContext

Fetcher = Callable[[Mapping, FetchContext], list[RadarItem]]

SOURCE_FETCHERS: dict[str, Fetcher] = {
    "arxiv": arxiv.fetch,
    "huggingface_models": huggingface.fetch_models,
    "huggingface_datasets": huggingface.fetch_datasets,
    "huggingface_papers": huggingface.fetch_papers,
    "github": github.fetch_repositories,
    "github_releases": github.fetch_releases,
    "semantic_scholar": scholar.fetch_semantic_scholar,
    "openalex": scholar.fetch_openalex,
    "survey": survey.fetch,
}

# Human-readable names used in health reporting and the digest.
SOURCE_LABELS: dict[str, str] = {
    "arxiv": arxiv.SOURCE_NAME,
    "huggingface_models": huggingface.MODELS_SOURCE,
    "huggingface_datasets": huggingface.DATASETS_SOURCE,
    "huggingface_papers": huggingface.PAPERS_SOURCE,
    "github": github.SEARCH_SOURCE,
    "github_releases": github.RELEASES_SOURCE,
    "semantic_scholar": scholar.S2_SOURCE,
    "openalex": scholar.OPENALEX_SOURCE,
    "survey": survey.REPORT_SOURCE,
}

__all__ = ["SOURCE_FETCHERS", "SOURCE_LABELS", "FetchContext", "Fetcher", "survey"]
