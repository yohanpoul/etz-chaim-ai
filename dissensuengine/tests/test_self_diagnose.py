"""Tests de l'auto-diagnostic — Hod de Tiferet.

Tiferet s'examine : est-ce que le système est honnête ?
"""

import pytest


def test_healthy_when_empty(engine_bare):
    """Pas de données → healthy."""
    diag = engine_bare.self_diagnose()
    assert diag["level"] == "healthy"
    assert len(diag["issues"]) == 0


def test_healthy_with_good_synthesis(engine_bare):
    """Synthèse propre → healthy."""
    engine_bare.submit_conclusion(
        "Gradient descent converges on convex loss functions reliably",
        source_label="Boyd", source_type="paper", domain="opt",
    )
    engine_bare.submit_conclusion(
        "Convex optimization with gradients reaches global minimum",
        source_label="Nesterov", source_type="paper", domain="opt",
    )
    engine_bare.synthesize_or_dissent(domain="opt")

    diag = engine_bare.self_diagnose()
    assert diag["level"] == "healthy"


def test_report_human_readable(engine_bare):
    """Le rapport est lisible par un humain."""
    engine_bare.submit_conclusion(
        "Test claim for report", source_label="A", source_type="human",
    )
    report = engine_bare.report()
    assert "DissensuEngine Report" in report
    assert "Tiferet" in report
    assert "Conclusions:" in report
    assert "Tensions:" in report
