"""Tests du lien Lamed↔Yesod — les insights persistent en EpisteMemory.

Les Nitzotzot extraits sont stockés dans la mémoire épistémique
avec source_sephirah='gevurah' (le point de départ du sentier).
"""

import pytest


def test_analysis_persisted_in_epistememory(fti):
    """L'analyse d'un échec est persistée dans EpisteMemory."""
    fti.analyze_failure(
        description="Retry loop caused by timeout too short",
        domain="networking",
    )

    results = fti.memory.recall("échec retry timeout", domain="networking")
    assert len(results) >= 1
    assert results[0].source_sephirah.value == "gevurah"
    assert "failure" in results[0].tags


def test_nitzotzot_persisted_in_epistememory(fti):
    """Les nitzotzot extraits sont persistés avec leurs tags."""
    analysis = fti.analyze_failure(
        description="Filter rejected all results, empty result set",
        domain="search",
    )
    insights = fti.extract_nitzotzot(analysis.id)

    # Check that insights have epistememory_ids
    assert any(i.epistememory_id is not None for i in insights)

    # Check in epistememory
    results = fti.memory.recall("Nitzotz golachab", domain="search")
    assert len(results) >= 1
    assert "nitzotz" in results[0].tags
