"""Tests GC (Gevurah-de-Yesod) — oubli sélectif et purification."""

import pytest

from pool import get_conn


def test_gc_marks_expired(mem):
    """GC marque les entrées expirées comme deprecated."""
    # Insert with already-expired TTL by manipulating DB directly
    entry_id = mem.remember(
        content="Donnée éphémère",
        source_sephirah="external",
        confidence=0.5,
        generate_embedding=False,
    )
    # Force expire in the past
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE epistememory SET expires_at = NOW() - INTERVAL '1 hour' WHERE id = %s",
            (entry_id,),
        )

    report = mem.gc()
    assert report.expired_count >= 1
    assert entry_id in report.expired_ids

    entry = mem.get(entry_id)
    assert entry.epistemic_status.value == "deprecated"


def test_deprecate_entry(mem):
    """Deprecate marque l'entrée correctement."""
    entry_id = mem.remember(
        content="Info obsolète",
        source_sephirah="external",
        generate_embedding=False,
    )
    mem.deprecate(entry_id)

    entry = mem.get(entry_id)
    assert entry.epistemic_status.value == "deprecated"


def test_deprecate_with_successor(mem):
    """Deprecate avec successeur crée le lien."""
    old_id = mem.remember("v1", source_sephirah="external", generate_embedding=False)
    new_id = mem.remember("v2", source_sephirah="external", generate_embedding=False)
    mem.deprecate(old_id, superseded_by=new_id)

    old = mem.get(old_id)
    assert old.superseded_by == new_id


def test_verify_promotes_status(mem):
    """Verify fait monter le statut épistémique."""
    entry_id = mem.remember(
        content="Hypothèse à vérifier",
        source_sephirah="chokmah",
        confidence=0.3,
        generate_embedding=False,
    )
    entry = mem.get(entry_id)
    assert entry.epistemic_status.value == "hypothesis"

    mem.verify(entry_id, "source A")
    entry = mem.get(entry_id)
    assert entry.epistemic_status.value == "verified_once"
    assert entry.confidence > 0.3

    mem.verify(entry_id, "source B")
    entry = mem.get(entry_id)
    assert entry.epistemic_status.value == "verified_multi"
