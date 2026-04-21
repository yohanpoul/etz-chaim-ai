"""Tests de l'auto-diagnostic — Hod du sentier Lamed.

Le sentier s'examine lui-même : est-ce que le Birur fonctionne ?
"""

import pytest


def test_healthy_when_empty(fti_bare):
    """Pas de problème quand aucune analyse."""
    diag = fti_bare.self_diagnose()
    assert diag["level"] == "healthy"
    assert len(diag["issues"]) == 0


def test_healthy_with_good_analyses(fti_bare):
    """Analyses bien classifiées et avec insights → healthy."""
    a = fti_bare.analyze_failure(
        "Filter rejected all results because threshold was too strict",
        domain="search",
    )
    fti_bare.extract_nitzotzot(a.id)

    diag = fti_bare.self_diagnose()
    # No shallow (long description), no unknown (golachab detected),
    # insights extracted
    assert diag["level"] == "healthy"


def test_report_human_readable(fti_bare):
    """Le rapport est lisible par un humain."""
    fti_bare.analyze_failure(
        "Retry loop stuck in infinite cycle",
        domain="api",
    )
    report = fti_bare.report()
    assert "Sentier Lamed" in report
    assert "Analyses:" in report
    assert "Qliphoth distribution:" in report
