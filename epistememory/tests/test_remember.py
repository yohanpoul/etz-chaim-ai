"""Tests remember (Chesed-de-Yesod) — acquisition en mémoire."""

import pytest


def test_remember_basic(mem):
    """Chesed: stocker une entrée et la récupérer."""
    entry_id = mem.remember(
        content="Le jeûne intermittent 16/8 améliore la variabilité cardiaque",
        source_sephirah="chokmah",
        confidence=0.3,
        domain="health",
    )
    assert entry_id is not None

    entry = mem.get(entry_id)
    assert entry is not None
    assert entry.content == "Le jeûne intermittent 16/8 améliore la variabilité cardiaque"
    assert entry.source_sephirah.value == "chokmah"
    assert entry.confidence == 0.3
    assert entry.domain == "health"
    assert entry.epistemic_status.value == "hypothesis"


def test_remember_high_confidence_becomes_fact(mem):
    """Une entrée à confiance >= 0.9 est automatiquement un 'fact'."""
    entry_id = mem.remember(
        content="Ma fréquence cardiaque au repos est de 52 bpm",
        source_sephirah="external",
        confidence=0.95,
        domain="health",
    )
    entry = mem.get(entry_id)
    assert entry.epistemic_status.value == "fact"


def test_remember_with_ttl(mem):
    """Entrée avec TTL a une date d'expiration."""
    entry_id = mem.remember(
        content="Température actuelle : 22°C",
        source_sephirah="external",
        confidence=0.9,
        ttl_days=1,
    )
    entry = mem.get(entry_id)
    assert entry.ttl_days == 1
    assert entry.expires_at is not None


def test_remember_with_tags(mem):
    """Entrée avec tags."""
    entry_id = mem.remember(
        content="Python 3.12 supporte les type aliases natifs",
        source_sephirah="gevurah",
        confidence=0.95,
        domain="code",
        tags=["python", "typing"],
    )
    entry = mem.get(entry_id)
    assert "python" in entry.tags
    assert "typing" in entry.tags


def test_remember_supersedes(mem):
    """Une entrée peut remplacer une précédente."""
    old_id = mem.remember(
        content="Version 1 du fait",
        source_sephirah="external",
        confidence=0.5,
    )
    new_id = mem.remember(
        content="Version 2 du fait (corrigée)",
        source_sephirah="external",
        confidence=0.7,
        supersedes=old_id,
    )
    old_entry = mem.get(old_id)
    new_entry = mem.get(new_id)
    assert new_entry.supersedes == old_id
    assert old_entry.superseded_by == new_id


def test_remember_without_embedding(mem):
    """On peut stocker sans embedding (mode dégradé)."""
    entry_id = mem.remember(
        content="Test sans embedding",
        source_sephirah="unknown",
        generate_embedding=False,
    )
    entry = mem.get(entry_id)
    assert entry is not None
    assert entry.content == "Test sans embedding"
