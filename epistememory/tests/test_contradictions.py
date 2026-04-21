"""Tests contradictions (Tiferet-de-Yesod) — gestion des tensions."""

import pytest


def test_contradict_marks_both_entries(mem):
    """Contradire marque les DEUX entrées comme contested."""
    id1 = mem.remember(
        content="Le café améliore le sommeil",
        source_sephirah="chokmah",
        confidence=0.3,
    )
    id2 = mem.remember(
        content="Le café nuit au sommeil",
        source_sephirah="binah",
        confidence=0.6,
    )
    mem.contradict(id1, id2)

    e1 = mem.get(id1)
    e2 = mem.get(id2)

    assert id2 in e1.contradicts
    assert id1 in e2.contradicts
    assert e1.epistemic_status.value == "contested"
    assert e2.epistemic_status.value == "contested"


def test_contradict_idempotent(mem):
    """Contradire deux fois ne duplique pas."""
    id1 = mem.remember("A", source_sephirah="external", generate_embedding=False)
    id2 = mem.remember("B", source_sephirah="external", generate_embedding=False)
    mem.contradict(id1, id2)
    mem.contradict(id1, id2)  # second call

    e1 = mem.get(id1)
    assert e1.contradicts.count(id2) == 1


def test_support_links(mem):
    """Support ajoute un lien unidirectionnel."""
    id1 = mem.remember("Claim A", source_sephirah="external", generate_embedding=False)
    id2 = mem.remember("Evidence for A", source_sephirah="external", generate_embedding=False)
    mem.support(id2, id1)

    e2 = mem.get(id2)
    assert id1 in e2.supports


def test_recall_shows_contradiction_warning(mem):
    """Le recall signale les contradictions."""
    id1 = mem.remember(
        content="Le thé vert aide la concentration",
        source_sephirah="chokmah",
        confidence=0.4,
    )
    id2 = mem.remember(
        content="Le thé vert n'a aucun effet sur la concentration",
        source_sephirah="binah",
        confidence=0.5,
    )
    mem.contradict(id1, id2)

    results = mem.recall("thé vert concentration")
    contested = [r for r in results if r.warning and "contested" in r.warning]
    assert len(contested) > 0
