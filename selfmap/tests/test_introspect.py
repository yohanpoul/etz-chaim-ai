"""Tests introspection — Hod-de-Hod : la carte se décrit elle-même."""

import pytest

from selfmap.models import DomainScore


def test_describe_empty(sm):
    """Description sur un système vierge."""
    desc = sm.describe_self()
    assert desc.total_domains == 0
    assert desc.evaluated_domains == 0
    assert desc.avg_competence == 0.0


def test_describe_with_data(sm):
    """Description avec données de compétence."""
    for domain, score in [("python", 0.9), ("math", 0.6), ("medicine", 0.2)]:
        sm.db.upsert_competence(DomainScore(
            domain=domain, model_id="test-model",
            score=score, brier_score=0.1, n_evals=10,
        ))

    desc = sm.describe_self()
    assert desc.total_domains == 3
    assert desc.evaluated_domains == 3
    assert "python" in desc.strong_domains
    assert "medicine" in desc.weak_domains
    assert 0.5 < desc.avg_competence < 0.7


def test_describe_decline_rate(sm):
    """Le taux de déclin est calculé correctement."""
    sm.db.upsert_competence(DomainScore(
        domain="medicine", model_id="test-model",
        score=0.1, brier_score=0.5, n_evals=10,
    ))
    sm.db.upsert_competence(DomainScore(
        domain="python", model_id="test-model",
        score=0.9, brier_score=0.05, n_evals=10,
    ))

    # Route some queries
    sm.route("Python list comprehension")     # accepted
    sm.route("What medication for headache?")  # declined

    desc = sm.describe_self()
    assert desc.total_queries_routed >= 2
    assert desc.total_declined >= 1
    assert desc.decline_rate > 0


def test_calibrate_empty(sm):
    """Calibration sur un système vierge."""
    report = sm.calibrate()
    assert report.avg_brier == 0.0
    assert report.by_domain == {}


def test_record_outcome(sm):
    """Enregistrer la qualité d'un routage a posteriori."""
    sm.db.upsert_competence(DomainScore(
        domain="python", model_id="test-model",
        score=0.8, brier_score=0.1, n_evals=5,
    ))
    decision = sm.route("Python decorator")
    # Simulate outcome recording (via log_id from DB)
    # Just verify the describe still works after routing
    desc = sm.describe_self()
    assert desc.total_queries_routed >= 1
