"""Tests d'extraction des Nitzotzot — Tiferet du sentier Lamed.

"Même dans les Qliphoth les plus denses, des Nitzotzot attendent."
"""

import pytest


def test_extract_manual_insights(fti_bare):
    """Extraction manuelle de nitzotzot avec données fournies."""
    analysis = fti_bare.analyze_failure(
        description="Filter rejected all valid results due to strict threshold",
        domain="search",
    )
    insights = fti_bare.extract_nitzotzot(analysis.id, insights_data=[
        {
            "content": "Le seuil de filtrage doit être adaptatif, pas fixe",
            "insight_type": "constraint",
            "confidence": 0.7,
        },
        {
            "content": "Envisager un mode quarantaine au lieu du rejet binaire",
            "insight_type": "opportunity",
            "confidence": 0.5,
        },
    ])
    assert len(insights) == 2
    assert insights[0].insight_type == "constraint"
    assert insights[0].confidence == 0.7
    assert insights[1].insight_type == "opportunity"


def test_auto_extract_insights(fti_bare):
    """Extraction automatique basée sur la classification."""
    analysis = fti_bare.analyze_failure(
        description="Retry loop stuck because timeout too short",
        domain="networking",
    )
    insights = fti_bare.extract_nitzotzot(analysis.id)
    assert len(insights) >= 1
    # Au minimum un anti-pattern est toujours extrait
    types = [i.insight_type for i in insights]
    assert "anti_pattern" in types


def test_auto_extract_with_root_cause(fti_bare):
    """Si root cause identifiée, une contrainte est extraite."""
    analysis = fti_bare.analyze_failure(
        description="Memory corruption because embedding dimensions changed",
    )
    insights = fti_bare.extract_nitzotzot(analysis.id)
    types = [i.insight_type for i in insights]
    assert "anti_pattern" in types
    assert "constraint" in types  # root cause → constraint


def test_golachab_specific_extraction(fti_bare):
    """Extraction spécifique pour Golachab (sur-filtrage)."""
    analysis = fti_bare.analyze_failure(
        description="Filter too strict, empty result set returned",
    )
    insights = fti_bare.extract_nitzotzot(analysis.id)
    # Golachab devrait produire un insight "opportunity"
    types = [i.insight_type for i in insights]
    assert "opportunity" in types


def test_insights_stored_in_db(fti_bare):
    """Les insights sont persistés en base."""
    analysis = fti_bare.analyze_failure(
        description="Silent failure, seems ok but data is corrupted",
    )
    fti_bare.extract_nitzotzot(analysis.id)

    # Retrieve analysis with insights
    retrieved = fti_bare.db.get_analysis(analysis.id)
    assert len(retrieved.insights) >= 1
