from __future__ import annotations

from vlm_radar.config import Settings


def test_survey_root_resolves_the_configured_relative_path(settings):
    root = settings.survey_root()
    if root is None:
        return  # the sibling survey checkout is optional
    assert root.is_absolute()
    assert root.is_dir()


def test_environment_variable_overrides_the_configured_path(settings, tmp_path, monkeypatch):
    """CI checks the survey out to a scratch directory config.yml cannot predict."""
    scratch = tmp_path / "checked-out-survey"
    scratch.mkdir()
    monkeypatch.setenv("VLM_RADAR_SURVEY_PATH", str(scratch))
    assert settings.survey_root() == scratch


def test_a_missing_override_path_reads_as_absent_rather_than_crashing(
    settings, tmp_path, monkeypatch
):
    monkeypatch.setenv("VLM_RADAR_SURVEY_PATH", str(tmp_path / "does-not-exist"))
    assert settings.survey_root() is None


def test_blank_override_falls_back_to_the_configured_path(settings, monkeypatch):
    monkeypatch.setenv("VLM_RADAR_SURVEY_PATH", "   ")
    assert settings.survey_root() == Settings.load(settings.root).survey_root()
