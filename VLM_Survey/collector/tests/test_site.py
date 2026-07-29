"""Contract tests between the published data and the static site.

The dashboard has no build step and no test runner of its own, so these tests
treat `index.html` and `app.js` as text and assert the contract they rely on:
every element the script looks up exists, every data key it reads is published,
and no code path uses innerHTML on upstream data.
"""

from __future__ import annotations

import re

import pytest

from vlm_radar import snapshots


@pytest.fixture(scope="module")
def site(settings):
    root = settings.site_dir
    return {
        "html": (root / "index.html").read_text(encoding="utf-8"),
        "js": (root / "assets" / "app.js").read_text(encoding="utf-8"),
        "css": (root / "assets" / "styles.css").read_text(encoding="utf-8"),
    }


def test_site_files_exist(settings):
    assert (settings.site_dir / "index.html").is_file()
    assert (settings.site_dir / "assets" / "app.js").is_file()
    assert (settings.site_dir / "assets" / "styles.css").is_file()


def test_the_dashboard_is_published_outside_the_collector(settings):
    """The served folder is the collector's parent, so the public URL has no
    /collector/site/ in it. Jekyll copies that folder verbatim."""
    assert settings.site_dir.resolve() == settings.root.parent.resolve()
    assert settings.dashboard_path.parent.name == "data"


def test_every_element_the_script_looks_up_exists_in_the_html(site):
    referenced = set(re.findall(r"""\$\(["']([a-z0-9-]+)["']\)""", site["js"]))
    declared = set(re.findall(r"""id=["']([a-z0-9-]+)["']""", site["html"]))
    missing = sorted(referenced - declared)
    assert not missing, f"app.js reads ids that index.html does not define: {missing}"


def test_every_view_has_a_section_and_a_nav_button(site):
    views = re.findall(r"""const VIEWS = \[([^\]]+)\]""", site["js"])[0]
    names = re.findall(r"""["']([a-z]+)["']""", views)
    assert names, "VIEWS should not be empty"
    for name in names:
        assert f'id="{name}-view"' in site["html"], name
        assert f'data-view="{name}"' in site["html"], name


def test_data_url_and_schema_match_the_builder(site, settings):
    assert f'"{settings.dashboard_path.name}"' in site["js"] or "data/radar.json" in site["js"]
    version = int(re.findall(r"const SUPPORTED_SCHEMA = (\d+)", site["js"])[0])
    assert version == snapshots.DASHBOARD_SCHEMA_VERSION


def test_script_reads_only_keys_the_builder_publishes(site, settings):
    payload = snapshots.dashboard_data(settings)
    top_level = re.findall(r"""(?:state\.data|payload)\.([a-z_]+)""", site["js"])
    allowed = set(payload) | {"length"}
    unknown = sorted({name for name in top_level if name not in allowed})
    assert not unknown, f"app.js reads unpublished top-level keys: {unknown}"


def test_day_keys_used_by_the_script_are_published(settings):
    payload = snapshots.dashboard_data(settings)
    if not payload["days"]:
        pytest.skip("no snapshots on disk")
    day = payload["days"][0]
    for key in (
        "date",
        "item_count",
        "pinned_count",
        "category_counts",
        "source_counts",
        "category_trends",
        "selection",
        "health",
        "items",
        "since",
        "generated_at",
    ):
        assert key in day, key


def test_item_keys_used_by_the_script_are_published(settings):
    payload = snapshots.dashboard_data(settings)
    items = [item for day in payload["days"] for item in day["items"]]
    if not items:
        pytest.skip("no records on disk")
    for key in ("title", "url", "source", "categories", "total_score", "event_kind"):
        assert all(key in item for item in items), key
    # Component scores drive the rubric breakdown panel.
    for key in ("relevance_score", "evidence_score", "recency_score", "adoption_score"):
        assert all(key in item for item in items), key


def test_upstream_text_is_never_written_as_markup(site):
    assert "innerHTML" not in site["js"]
    assert "insertAdjacentHTML" not in site["js"]
    assert "document.write" not in site["js"]


def test_external_links_are_hardened(site):
    targets = re.findall(r"""target:\s*["']_blank["']""", site["js"])
    noopener = re.findall(r"""rel:\s*["']noopener noreferrer["']""", site["js"])
    assert targets and len(noopener) >= len(targets)


def test_accessibility_landmarks_and_skip_link_are_present(site):
    html = site["html"]
    assert 'class="skip-link"' in html
    assert 'id="main-content"' in html
    assert "<main" in html and "<footer" in html
    assert 'aria-label="Dashboard views"' in html
    assert html.count("aria-labelledby") >= 5
    assert 'aria-live="polite"' in html


def test_an_unreadable_data_file_shows_an_explained_error(site):
    assert 'id="error-state"' in site["html"]
    assert "showError(" in site["js"]
    assert "vlm-radar seed" in site["html"]


def test_rubric_dialog_is_reachable_from_nav_and_from_a_record(site):
    assert 'id="rubric-dialog"' in site["html"]
    assert "openRubric(null)" in site["js"]
    assert "Why this score" in site["js"]


def test_reduced_motion_is_respected(site):
    assert "prefers-reduced-motion" in site["css"]
