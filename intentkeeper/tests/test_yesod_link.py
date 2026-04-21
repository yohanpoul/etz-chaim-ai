"""Tests du lien Netzach↔Yesod (sentier Tsadi) — checkpoints en EpisteMemory.

Tsadi צ = pensée fixée : les états de l'intention sont persistés en mémoire.
"""

import pytest


def test_intention_created_in_epistememory(ik):
    """La création d'une intention persiste dans EpisteMemory avec source='netzach'."""
    ik.set_intention("Build IntentKeeper", max_duration_days=30)

    results = ik.memory.recall("IntentKeeper intention", domain="intentkeeper")
    assert len(results) >= 1
    assert results[0].source_sephirah.value == "netzach"
    assert "intention" in results[0].tags


def test_abandon_persisted_in_epistememory(ik):
    """L'abandon d'une intention est persisté — la leçon est mémorisée."""
    intention = ik.set_intention("Impossible goal", max_duration_days=7)
    ik.abandon(intention.id, "Intractable problem")

    results = ik.memory.recall("intention abandonnée", domain="intentkeeper")
    assert len(results) >= 1
    assert "abandoned" in results[0].tags
    assert "Intractable" in results[0].content
