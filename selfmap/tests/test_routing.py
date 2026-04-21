"""Tests routage — Tiferet-de-Hod : router avec harmonie."""

import pytest

from selfmap.models import DomainScore


def test_route_known_domain(sm):
    """Routage sur un domaine avec score connu."""
    sm.db.upsert_competence(DomainScore(
        domain="python", model_id="test-model",
        score=0.8, brier_score=0.1, n_evals=10,
    ))

    decision = sm.route("How do I use list comprehension in Python?")
    assert not decision.did_decline
    assert decision.detected_domain == "python"
    assert decision.competence_score == 0.8
    assert decision.routed_to == "test-model"


def test_route_unknown_domain_no_decline(sm):
    """Domaine inconnu : tente quand même (compétence = 0)."""
    decision = sm.route("What is the airspeed of an unladen swallow?")
    # Unknown domain, competence = 0.0, but we still attempt
    assert not decision.did_decline


def test_route_weak_domain_declines(sm):
    """Domaine faible (< seuil) : décline. Anti-Samael."""
    sm.db.upsert_competence(DomainScore(
        domain="medicine", model_id="test-model",
        score=0.15, brier_score=0.4, n_evals=10,
    ))

    decision = sm.route("What medication should I take for chest pain?")
    assert decision.did_decline
    assert "medicine" in decision.decline_reason
    assert "0.15" in decision.decline_reason


def test_routing_logged(sm):
    """Chaque routage est enregistré dans le log."""
    sm.db.upsert_competence(DomainScore(
        domain="python", model_id="test-model",
        score=0.8, brier_score=0.1, n_evals=5,
    ))
    sm.route("Python list slicing")

    desc = sm.describe_self()
    assert desc.total_queries_routed >= 1


def test_route_picks_best_model(sm):
    """Le routage choisit le meilleur modèle disponible."""
    sm.db.upsert_competence(DomainScore(
        domain="math", model_id="test-model",
        score=0.5, brier_score=0.2, n_evals=5,
    ))
    sm.db.upsert_competence(DomainScore(
        domain="math", model_id="better-model",
        score=0.9, brier_score=0.05, n_evals=10,
    ))

    decision = sm.route("What is the derivative of sin(x)?")
    assert decision.routed_to == "better-model"
