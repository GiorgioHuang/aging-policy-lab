"""HAPI weighting sensitivity: the robustness test must use full domain profiles."""
from hapi_pipeline.indicators.weighting import (
    EQUAL, EXPERT, _composite, latest_profile, ordering,
)


def test_latest_profile_takes_each_domains_latest_period():
    periods = {
        "2019-01-01": {"health": 40.0, "social_participation": 60.0},
        "2022-01-01": {"health": 45.0},
        "2026-01-01": {"care_access": 50.0},
    }
    scores, as_of = latest_profile(periods)
    assert scores == {"health": 45.0, "social_participation": 60.0, "care_access": 50.0}
    assert as_of == {"health": "2022-01-01", "social_participation": "2019-01-01",
                     "care_access": "2026-01-01"}


def test_single_domain_composite_ignores_weights():
    # Why the latest period alone is no robustness test: one domain → same value.
    one = {"care_access": 42.0}
    assert _composite(one, EQUAL) == _composite(one, EXPERT) == 42.0


def test_ordering_reports_a_flip():
    rows = [
        {"jurisdiction": "CA", "composite": {"equal": 53.8, "empirical": 51.4}},
        {"jurisdiction": "CA-NS", "composite": {"equal": 51.0, "empirical": 51.6}},
    ]
    order = ordering(rows, ["equal", "empirical"])
    assert order == {"equal": ["CA", "CA-NS"], "empirical": ["CA-NS", "CA"]}
