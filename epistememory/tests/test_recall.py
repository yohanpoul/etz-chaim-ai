"""Tests recall (Chokmah-de-Yesod) — recherche sémantique."""

import pytest


def test_recall_semantic(mem):
    """Recherche sémantique retourne des résultats pertinents."""
    mem.remember(
        content="Le café augmente la vigilance et la concentration",
        source_sephirah="binah",
        confidence=0.7,
        domain="health",
    )
    mem.remember(
        content="Python est un langage de programmation",
        source_sephirah="gevurah",
        confidence=0.95,
        domain="code",
    )

    results = mem.recall("effets de la caféine", domain="health")
    assert len(results) >= 1
    assert "café" in results[0].content or "caféine" in results[0].content


def test_recall_min_confidence_filter(mem):
    """Le filtre min_confidence exclut les entrées faibles."""
    mem.remember(
        content="Hypothèse faible sur le sommeil",
        source_sephirah="chokmah",
        confidence=0.1,
        domain="health",
    )
    mem.remember(
        content="Fait vérifié sur le sommeil",
        source_sephirah="gevurah",
        confidence=0.9,
        domain="health",
    )

    results = mem.recall("sommeil", min_confidence=0.5, domain="health")
    assert all(r.confidence >= 0.5 for r in results)


def test_recall_domain_filter(mem):
    """Le filtre domain isole les résultats."""
    mem.remember("Donnée santé", source_sephirah="external", domain="health")
    mem.remember("Donnée code", source_sephirah="external", domain="code")

    results = mem.recall("donnée", domain="health")
    assert all(r.domain == "health" for r in results)


def test_recall_excludes_deprecated(mem):
    """Les entrées deprecated ne sont pas retournées."""
    entry_id = mem.remember(
        content="Information obsolète sur le sommeil",
        source_sephirah="external",
        confidence=0.5,
        domain="health",
    )
    mem.deprecate(entry_id)

    results = mem.recall("sommeil", domain="health")
    assert all(r.id != entry_id for r in results)


def test_recall_empty(mem):
    """Recall sur une base vide retourne une liste vide."""
    results = mem.recall("n'importe quoi")
    assert results == []
