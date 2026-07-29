from __future__ import annotations

from datetime import datetime

import pytest
from helpers import NOW

from vlm_radar.config import Settings


@pytest.fixture(scope="session")
def settings() -> Settings:
    """The real config.yml, so tests fail when the shipped taxonomy regresses."""
    return Settings.load()


@pytest.fixture()
def now() -> datetime:
    return NOW
