"""Tests de guidance — Lamed pointe vers Tiferet."""

import pytest


def test_guide_empty(fti_bare):
    """Guidance sur un graphe vide."""
    guidance = fti_bare.guide_next_hypothesis()
    assert guidance.total_failures_analyzed == 0
    assert guidance.confidence == 0.3  # basse confiance sans données


def test_guide_identifies_recurring_patterns(fti_bare):
    """Les qliphoth récurrentes sont signalées."""
    # Créer 3+ analyses avec la même qliphah
    for i in range(4):
        fti_bare.analyze_failure(
            f"Retry failure #{i}", domain="api",
            qliphah_override="aarab_zaraq", severity_override="ruach",
        )

    guidance = fti_bare.guide_next_hypothesis()
    assert "aarab_zaraq" in guidance.avoid_patterns


def test_guide_identifies_recurring_root_causes(fti_bare):
    """Les root causes récurrentes sont signalées."""
    fti_bare.analyze_failure(
        "Failed because insufficient validation",
    )
    fti_bare.analyze_failure(
        "Crashed because insufficient validation",
    )

    guidance = fti_bare.guide_next_hypothesis()
    assert len(guidance.recurring_root_causes) >= 1


def test_guide_confidence_increases(fti_bare):
    """La confiance de la guidance augmente avec plus de données."""
    for i in range(7):
        a = fti_bare.analyze_failure(f"Failure {i}", domain=f"domain_{i}")
        fti_bare.extract_nitzotzot(a.id)

    guidance = fti_bare.guide_next_hypothesis()
    assert guidance.confidence >= 0.5
