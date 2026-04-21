"""Tests du lien Tiferet↔Yesod — les synthèses persistent en EpisteMemory.

Les synthèses sont stockées dans la mémoire épistémique
avec source_sephirah='tiferet'.
"""

import pytest


def test_synthesis_persisted_in_epistememory(engine):
    """Une synthèse réussie est persistée dans EpisteMemory."""
    engine.submit_conclusion(
        "Feature extraction benefits from hierarchical processing layers",
        source_label="LeCun", source_type="paper", domain="vision",
    )
    engine.submit_conclusion(
        "Layered feature extraction improves deep learning model accuracy",
        source_label="He", source_type="paper", domain="vision",
    )
    syn = engine.synthesize_or_dissent(domain="vision")

    if syn.mode == "synthesis":
        results = engine.memory.recall("synthèse Tiferet", domain="vision")
        assert len(results) >= 1
        assert results[0].source_sephirah.value == "tiferet"
        assert "synthesis" in results[0].tags
