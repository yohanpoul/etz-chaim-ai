"""Tests introspect (Hod-de-Yesod) — la mémoire se décrit elle-même."""

import pytest


def test_introspect_empty(mem):
    """Introspection sur une base vide."""
    stats = mem.introspect()
    assert stats.total_entries == 0
    assert stats.active_entries == 0
    assert stats.avg_confidence == 0.0


def test_introspect_counts(mem):
    """Introspection compte correctement par statut et domaine."""
    mem.remember("A", source_sephirah="chokmah", confidence=0.3, domain="health",
                 generate_embedding=False)
    mem.remember("B", source_sephirah="binah", confidence=0.6, domain="health",
                 generate_embedding=False)
    mem.remember("C", source_sephirah="external", confidence=0.95, domain="code",
                 generate_embedding=False)

    stats = mem.introspect()
    assert stats.total_entries == 3
    assert stats.active_entries == 3
    assert stats.by_domain.get("health", 0) == 2
    assert stats.by_domain.get("code", 0) == 1
    assert stats.by_source.get("chokmah", 0) == 1
    assert stats.avg_confidence > 0


def test_introspect_with_deprecated(mem):
    """Introspection distingue actif et deprecated."""
    id1 = mem.remember("Active", source_sephirah="external", generate_embedding=False)
    id2 = mem.remember("Deprecated", source_sephirah="external", generate_embedding=False)
    mem.deprecate(id2)

    stats = mem.introspect()
    assert stats.total_entries == 2
    assert stats.active_entries == 1
    assert stats.deprecated_entries == 1
