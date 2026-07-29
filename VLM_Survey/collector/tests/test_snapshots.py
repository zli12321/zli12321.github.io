from __future__ import annotations

import copy
import json

import pytest
from helpers import make_item

from vlm_radar import pipeline, snapshots
from vlm_radar.config import Settings
from vlm_radar.models import RadarRun, Selection, SourceHealth


@pytest.fixture()
def temp_settings(tmp_path, settings):
    """A settings object rooted in a temp dir but carrying the real taxonomy."""
    (tmp_path / "config.yml").write_text(
        (settings.root / "config.yml").read_text(encoding="utf-8"), encoding="utf-8"
    )
    isolated = Settings.load(tmp_path)
    # The atlas depends on an external checkout; keep these tests self-contained.
    isolated.raw["sources"]["survey"]["path"] = ""
    # The real config publishes to the parent directory. Keep writes inside tmp.
    isolated.raw["publish"]["site_dir"] = "site"
    isolated.ensure_directories()
    return isolated


def build_run(settings, now, *, count=3):
    items = [
        pipeline.score_item(make_item(source_id=f"2607.0000{i}"), settings, now)
        for i in range(count)
    ]
    kept, funnel = pipeline.select(items, settings)
    return RadarRun(
        items=kept,
        health=[SourceHealth(source="arXiv", ok=True, item_count=count, required=True)],
        selection=funnel,
        since="2026-07-26T12:00:00+00:00",
        generated_at="2026-07-28T12:00:00+00:00",
    )


def test_write_snapshot_round_trips(temp_settings, now):
    run = build_run(temp_settings, now)
    path = snapshots.write_snapshot(temp_settings, run, date="2026-07-28")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == snapshots.SNAPSHOT_SCHEMA_VERSION
    assert payload["date"] == "2026-07-28"
    assert len(payload["items"]) == len(run.items)
    snapshots.validate_snapshot(payload)


def test_public_projection_omits_empty_fields(temp_settings, now):
    run = build_run(temp_settings, now, count=1)
    payload = snapshots.snapshot_payload(run, date="2026-07-28")
    item = payload["items"][0]
    assert "watchlist" not in item
    assert "suppression_reasons" not in item
    assert item["categories"]


def test_validation_rejects_an_uncategorized_item(temp_settings, now):
    run = build_run(temp_settings, now, count=1)
    payload = snapshots.snapshot_payload(run, date="2026-07-28")
    payload["items"][0]["categories"] = []
    with pytest.raises(snapshots.SnapshotError, match="no category"):
        snapshots.validate_snapshot(payload)


def test_validation_rejects_duplicates_and_bad_schema(temp_settings, now):
    run = build_run(temp_settings, now, count=1)
    payload = snapshots.snapshot_payload(run, date="2026-07-28")
    duplicated = copy.deepcopy(payload)
    duplicated["items"].append(copy.deepcopy(duplicated["items"][0]))
    with pytest.raises(snapshots.SnapshotError, match="duplicate"):
        snapshots.validate_snapshot(duplicated)

    wrong_version = copy.deepcopy(payload)
    wrong_version["schema_version"] = 99
    with pytest.raises(snapshots.SnapshotError, match="schema_version"):
        snapshots.validate_snapshot(wrong_version)


def test_dashboard_rebuild_is_deterministic(temp_settings, now):
    snapshots.write_snapshot(temp_settings, build_run(temp_settings, now), date="2026-07-27")
    snapshots.write_snapshot(temp_settings, build_run(temp_settings, now), date="2026-07-28")

    first = snapshots.dashboard_data(temp_settings)
    second = snapshots.dashboard_data(temp_settings)
    for payload in (first, second):
        payload.pop("generated_at")
        payload.get("atlas", {}).pop("generated_at", None)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_dashboard_publishes_the_contract_the_site_reads(temp_settings, now):
    snapshots.write_snapshot(temp_settings, build_run(temp_settings, now), date="2026-07-28")
    payload = snapshots.dashboard_data(temp_settings)

    assert payload["schema_version"] == snapshots.DASHBOARD_SCHEMA_VERSION
    published = ("days", "facets", "corpus", "rubric", "taxonomy", "totals", "site", "atlas")
    for key in (*published, "bands"):
        assert key in payload, key
    assert payload["latest_date"] == "2026-07-28"

    day = payload["days"][0]
    for key in ("date", "item_count", "category_counts", "category_trends", "selection", "health"):
        assert key in day, key

    facets = payload["facets"]
    assert facets["dates"] == ["2026-07-28"]
    assert "arXiv" in facets["sources"]
    assert set(facets["categories"]) <= {c["key"] for c in payload["taxonomy"]["categories"]}


def test_trends_are_only_comparable_once_there_is_a_previous_scan(temp_settings, now):
    snapshots.write_snapshot(temp_settings, build_run(temp_settings, now), date="2026-07-27")
    first = snapshots.dashboard_data(temp_settings)["days"][0]
    assert all(row["comparable"] is False for row in first["category_trends"])

    snapshots.write_snapshot(temp_settings, build_run(temp_settings, now), date="2026-07-28")
    days = snapshots.dashboard_data(temp_settings)["days"]
    assert all(row["comparable"] is True for row in days[1]["category_trends"])


def test_days_are_chronological(temp_settings, now):
    for date in ("2026-07-28", "2026-07-26", "2026-07-27"):
        snapshots.write_snapshot(temp_settings, build_run(temp_settings, now), date=date)
    dates = [day["date"] for day in snapshots.dashboard_data(temp_settings)["days"]]
    assert dates == sorted(dates)


def test_unreadable_snapshot_fails_loudly(temp_settings):
    (temp_settings.snapshots_dir / "2026-07-29.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(snapshots.SnapshotError, match="could not be read"):
        snapshots.load_snapshots(temp_settings)


def test_empty_selection_still_produces_a_valid_snapshot(temp_settings):
    run = RadarRun(
        items=[],
        health=[SourceHealth(source="arXiv", ok=False, detail="HTTP 503", required=True)],
        selection=Selection(fetched=120, deduplicated=118, out_of_domain=118),
        since="2026-07-26T12:00:00+00:00",
        generated_at="2026-07-28T12:00:00+00:00",
    )
    path = snapshots.write_snapshot(temp_settings, run, date="2026-07-28")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["items"] == []
    assert payload["health"][0]["ok"] is False
    assert payload["selection"]["fetched"] == 120
