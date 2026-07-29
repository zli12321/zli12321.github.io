from __future__ import annotations

import math

from vlm_radar import rubric


def test_weights_are_normalized():
    assert math.isclose(sum(rubric.WEIGHTS.values()), 1.0, rel_tol=1e-9)


def test_every_component_stays_inside_zero_to_one_hundred():
    extremes = [
        rubric.relevance(category_count=18, term_count=99, anchor_count=40, demotions=0),
        rubric.relevance(category_count=0, term_count=0, anchor_count=0, demotions=9),
        rubric.evidence(
            source="arXiv",
            summary_length=5000,
            author_count=40,
            artifact_count=20,
            corroborating_sources=5,
            venue="CVPR",
        ),
        rubric.recency(age_hours=0.0, window_hours=48.0),
        rubric.recency(age_hours=9999.0, window_hours=48.0),
        rubric.adoption({"downloads": 10**9}),
    ]
    assert all(0.0 <= value <= rubric.SCORE_MAX for value in extremes)


def test_relevance_rewards_breadth_then_penalizes_low_value_patterns():
    narrow = rubric.relevance(category_count=1, term_count=1, anchor_count=1, demotions=0)
    broad = rubric.relevance(category_count=3, term_count=6, anchor_count=4, demotions=0)
    demoted = rubric.relevance(category_count=3, term_count=6, anchor_count=4, demotions=1)
    assert narrow < broad
    assert demoted < broad


def test_mentions_earn_less_evidence_than_primary_sources():
    shared = dict(
        summary_length=400, author_count=3, artifact_count=1, corroborating_sources=0, venue=""
    )
    assert rubric.evidence(source="arXiv", **shared) > rubric.evidence(source="Blog", **shared)


def test_corroboration_increases_evidence():
    shared = dict(source="arXiv", summary_length=400, author_count=3, artifact_count=1, venue="")
    alone = rubric.evidence(corroborating_sources=0, **shared)
    confirmed = rubric.evidence(corroborating_sources=2, **shared)
    assert confirmed > alone


def test_recency_decays_linearly_to_zero_at_the_window_edge():
    assert rubric.recency(age_hours=0.0, window_hours=48.0) == 100.0
    assert math.isclose(rubric.recency(age_hours=24.0, window_hours=48.0), 50.0)
    assert rubric.recency(age_hours=48.0, window_hours=48.0) == 0.0


def test_adoption_is_log_scaled_and_takes_the_strongest_signal():
    modest = rubric.adoption({"stars": 40})
    strong = rubric.adoption({"stars": 4000})
    assert modest < strong
    assert rubric.adoption({"stars": 40, "downloads": 60000}) == rubric.adoption(
        {"downloads": 60000}
    )
    assert rubric.adoption({}) == 0.0


def test_adoption_ignores_metrics_without_a_published_ceiling():
    assert rubric.adoption({"mystery_metric": 10**6}) == 0.0


def test_total_matches_the_published_component_contributions():
    components = {"relevance": 80.0, "evidence": 60.0, "recency": 40.0, "adoption": 20.0}
    described = rubric.describe_components(components)
    assert math.isclose(
        rubric.total(components), sum(row["contribution"] for row in described), abs_tol=0.02
    )


def test_reference_publishes_everything_the_dashboard_renders():
    reference = rubric.reference(minimum_score=30, lookback_hours=48)
    assert reference["version"] == rubric.SCORING_VERSION
    assert reference["minimum_score"] == 30
    assert set(reference["weights"]) == set(rubric.WEIGHTS)
    assert len(reference["components"]) == len(rubric.WEIGHTS)
    assert reference["gates"]
    assert reference["worked_example"]["total"] > 0


def test_worked_example_arithmetic_is_self_consistent():
    example = rubric.reference(minimum_score=30, lookback_hours=48)["worked_example"]
    contributions = sum(row["contribution"] for row in example["components"])
    assert math.isclose(example["total"], contributions, abs_tol=0.05)
