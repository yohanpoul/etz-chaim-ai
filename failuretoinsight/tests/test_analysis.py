"""Tests d'analyse d'échec — le Birur de base."""

import pytest


def test_analyze_failure_basic(fti_bare):
    """Créer une analyse d'échec avec classification automatique."""
    analysis = fti_bare.analyze_failure(
        description="The retry loop on data fetch is stuck in infinite loop",
        source_type="experiment",
        domain="data_pipeline",
    )
    assert analysis.id is not None
    assert analysis.qliphah == "aarab_zaraq"  # retry + infinite loop
    assert analysis.severity in ("nogah", "ruach", "anan", "mamash")
    assert analysis.domain == "data_pipeline"


def test_analyze_with_override(fti_bare):
    """Classification manuelle par override."""
    analysis = fti_bare.analyze_failure(
        description="Something went wrong",
        qliphah_override="golachab",
        severity_override="ruach",
    )
    assert analysis.qliphah == "golachab"
    assert analysis.severity == "ruach"


def test_analyze_extracts_root_cause(fti_bare):
    """Extraction automatique de root cause depuis la description."""
    analysis = fti_bare.analyze_failure(
        description="Memory corruption because the embedding model changed "
                    "dimensions from 768 to 1024",
    )
    assert analysis.root_cause is not None
    assert "embedding model" in analysis.root_cause


def test_analyze_with_context(fti_bare):
    """Le contexte enrichit l'analyse."""
    analysis = fti_bare.analyze_failure(
        description="Test failure",
        context={"retry_count": 15, "error": "timeout after 30s"},
        domain="testing",
    )
    assert analysis.context is not None
    assert analysis.context["retry_count"] == 15


def test_get_analysis(fti_bare):
    """Récupérer une analyse avec ses insights."""
    analysis = fti_bare.analyze_failure(
        description="Filter rejected all results — nothing found",
        domain="search",
    )
    retrieved = fti_bare.db.get_analysis(analysis.id)
    assert retrieved is not None
    assert retrieved.qliphah == "golachab"
    assert retrieved.domain == "search"
