"""Configuration loading and repository layout.

`Settings` resolves every path the collector reads or writes, so no other module
needs to know where the repository root is.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .taxonomy import Taxonomy

CONFIG_FILENAME = "config.yml"


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ModuleNotFoundError as error:  # pragma: no cover - dependency is declared
        raise SystemExit(
            "PyYAML is required. Install the project with: python -m pip install -e '.[dev]'"
        ) from error
    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    if not isinstance(loaded, dict):
        raise SystemExit(f"{path} must contain a YAML mapping at the top level")
    return loaded


def find_repo_root(start: Path | None = None) -> Path:
    """Walk up from `start` looking for config.yml, defaulting to the package root."""
    candidates = []
    if start:
        candidates.append(Path(start).resolve())
    candidates.append(Path.cwd().resolve())
    candidates.append(Path(__file__).resolve().parents[2])

    for candidate in candidates:
        for directory in [candidate, *candidate.parents]:
            if (directory / CONFIG_FILENAME).is_file():
                return directory
    raise SystemExit(f"Could not locate {CONFIG_FILENAME}. Run vlm-radar from the repository root.")


@dataclass
class Settings:
    root: Path
    raw: dict[str, Any]
    taxonomy: Taxonomy

    @classmethod
    def load(cls, root: Path | None = None) -> Settings:
        resolved = find_repo_root(root)
        raw = _load_yaml(resolved / CONFIG_FILENAME)
        return cls(root=resolved, raw=raw, taxonomy=Taxonomy.from_config(raw))

    # --- config sections -------------------------------------------------

    @property
    def radar(self) -> Mapping[str, Any]:
        return self.raw.get("radar") or {}

    @property
    def sources(self) -> Mapping[str, Any]:
        return self.raw.get("sources") or {}

    @property
    def publish(self) -> Mapping[str, Any]:
        return self.raw.get("publish") or {}

    def source(self, name: str) -> Mapping[str, Any]:
        return self.sources.get(name) or {}

    def source_enabled(self, name: str) -> bool:
        return bool(self.source(name).get("enabled", False))

    # --- tuning knobs ----------------------------------------------------

    @property
    def lookback_hours(self) -> float:
        return float(self.radar.get("lookback_hours", 48))

    @property
    def curated_lookback_hours(self) -> float:
        return float(self.radar.get("curated_lookback_hours", 720))

    @property
    def max_items_per_source(self) -> int:
        return int(self.radar.get("max_items_per_source", 300))

    @property
    def report_limit(self) -> int:
        return int(self.radar.get("report_limit", 400))

    @property
    def issue_item_limit(self) -> int:
        return int(self.radar.get("issue_item_limit", 40))

    @property
    def minimum_score(self) -> float:
        return float(self.radar.get("minimum_score", 34))

    # --- paths -----------------------------------------------------------

    @property
    def data_dir(self) -> Path:
        return self.root / "data"

    @property
    def snapshots_dir(self) -> Path:
        return self.data_dir / "snapshots"

    @property
    def atlas_path(self) -> Path:
        return self.data_dir / "atlas.json"

    @property
    def site_dir(self) -> Path:
        """Directory holding the published dashboard.

        Defaults to `site/` beside the collector. `publish.site_dir` moves it, which
        is how the dashboard can live at the root of a folder served by an outer
        static-site generator while the collector sits in a subdirectory.
        """
        configured = str(self.publish.get("site_dir") or "site")
        candidate = Path(os.path.expanduser(configured))
        if not candidate.is_absolute():
            candidate = (self.root / candidate).resolve()
        return candidate

    @property
    def dashboard_path(self) -> Path:
        return self.site_dir / "data" / "radar.json"

    @property
    def out_dir(self) -> Path:
        return self.root / "out"

    def survey_root(self) -> Path | None:
        """Absolute path to the survey repository, if configured and present.

        `VLM_RADAR_SURVEY_PATH` overrides config.yml. CI needs this: the survey
        lives in a separate repository, so a workflow checks it out to a scratch
        directory whose path the committed config cannot know.
        """
        override = os.environ.get("VLM_RADAR_SURVEY_PATH", "").strip()
        raw_path = override or self.source("survey").get("path")
        if not raw_path:
            return None
        candidate = Path(os.path.expanduser(str(raw_path)))
        if not candidate.is_absolute():
            candidate = (self.root / candidate).resolve()
        return candidate if candidate.is_dir() else None

    def ensure_directories(self) -> None:
        for directory in (self.snapshots_dir, self.out_dir, self.dashboard_path.parent):
            directory.mkdir(parents=True, exist_ok=True)
