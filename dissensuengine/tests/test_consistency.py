"""Tests de cohérence — l'analyse de Gevurah.

Détecter toutes les tensions dans un ensemble de conclusions.
"""

import pytest


def test_consistency_empty(engine_bare):
    """Pas de conclusions → consistent."""
    report = engine_bare.analyze_consistency()
    assert report.health == "consistent"
    assert report.total_conclusions == 0
    assert report.total_tensions == 0


def test_consistency_single(engine_bare):
    """Une seule conclusion → consistent."""
    engine_bare.submit_conclusion(
        "Single claim", source_label="A", source_type="paper",
    )
    report = engine_bare.analyze_consistency()
    assert report.health == "consistent"
    assert report.total_conclusions == 1


def test_consistency_agreeing(engine_bare):
    """Conclusions concordantes → consistent."""
    engine_bare.submit_conclusion(
        "Neural networks learn representations from training data",
        source_label="A", source_type="paper", domain="ml",
    )
    engine_bare.submit_conclusion(
        "Deep learning models acquire features from datasets",
        source_label="B", source_type="paper", domain="ml",
    )
    report = engine_bare.analyze_consistency(domain="ml")
    assert report.health == "consistent"


def test_consistency_contradictory(engine_bare):
    """Conclusions contradictoires → tensions détectées."""
    engine_bare.submit_conclusion(
        "The treatment always increases survival rate significantly",
        source_label="Study A", source_type="paper", domain="med",
    )
    engine_bare.submit_conclusion(
        "The treatment never increases survival rate significantly",
        source_label="Study B", source_type="paper", domain="med",
    )
    report = engine_bare.analyze_consistency(domain="med")
    assert report.total_tensions >= 1
    assert report.max_divergence > 0.1
    assert report.health in ("tensions_detected", "highly_divergent")


def test_consistency_source_labels(engine_bare):
    """Les labels de sources sont dans le rapport."""
    engine_bare.submit_conclusion(
        "Claim from Alpha", source_label="Alpha",
        source_type="paper", domain="test",
    )
    engine_bare.submit_conclusion(
        "Claim from Beta", source_label="Beta",
        source_type="paper", domain="test",
    )
    report = engine_bare.analyze_consistency(domain="test")
    assert "Alpha" in report.source_labels
    assert "Beta" in report.source_labels


def test_consistency_by_ids(engine_bare):
    """Analyser la cohérence d'un sous-ensemble par IDs."""
    c1 = engine_bare.submit_conclusion(
        "X is always true", source_label="A", source_type="paper",
    )
    c2 = engine_bare.submit_conclusion(
        "X is never true", source_label="B", source_type="paper",
    )
    engine_bare.submit_conclusion(
        "Unrelated topic here", source_label="C", source_type="paper",
    )
    report = engine_bare.analyze_consistency(conclusion_ids=[c1.id, c2.id])
    assert report.total_conclusions == 2


def test_consistency_rejects_string_as_conclusion_ids(engine_bare):
    """F-S1-001: une str passée comme conclusion_ids (bug positionnel)
    doit lever TypeError clair, pas itérer caractère par caractère en SQL."""
    with pytest.raises(TypeError, match="conclusion_ids"):
        engine_bare.analyze_consistency("general")


def test_consistency_report_has_expected_attributes(engine_bare):
    """F-S1-001 régression : ConsistencyReport expose total_tensions + max_divergence
    (et non n_tensions / consistency_score). Tous les callers doivent les utiliser."""
    report = engine_bare.analyze_consistency(domain="anything")
    assert hasattr(report, "total_tensions")
    assert hasattr(report, "max_divergence")
    assert isinstance(report.total_tensions, int)
    assert isinstance(report.max_divergence, float)
