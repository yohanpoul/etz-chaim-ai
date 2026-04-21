"""Tests CausalTreeBuilder — Hashgachah Pratit.

Le graphe causal global : composantes, causes racines, chaînes.
"""

import pytest

from causalengine.tree_builder import (
    CausalTreeBuilder,
    Chain,
    Community,
)


@pytest.fixture
def builder(db):
    return CausalTreeBuilder(db)


def _insert_claims(db, claims):
    """Insert raw claims for testing."""
    with db._cursor() as cur:
        for cause, effect, confidence in claims:
            cur.execute(
                "INSERT INTO causal_claims (cause, effect, evidence_level, confidence) "
                "VALUES (%s, %s, 'correlation_only', %s)",
                (cause, effect, confidence),
            )


# ── build_graph ──────────────────────────────────────

class TestBuildGraph:
    def test_build_empty(self, builder):
        """No claims above threshold -> empty graph."""
        graph = builder.build_graph(min_confidence=0.9)
        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0

    def test_build_simple_chain(self, db, builder):
        _insert_claims(db, [
            ("A", "B", 0.5),
            ("B", "C", 0.6),
        ])
        graph = builder.build_graph(min_confidence=0.3)
        assert len(graph.nodes) == 3
        assert len(graph.edges) == 2
        assert graph.id is not None  # Persisted

    def test_build_deduplicates_edges(self, db, builder):
        """Duplicate cause->effect keeps max confidence."""
        _insert_claims(db, [
            ("A", "B", 0.4),
            ("A", "B", 0.7),
            ("A", "B", 0.5),
        ])
        graph = builder.build_graph(min_confidence=0.3)
        assert len(graph.edges) == 1
        assert graph.edges[0].confidence == 0.7

    def test_build_filters_by_confidence(self, db, builder):
        _insert_claims(db, [
            ("A", "B", 0.1),  # Below threshold
            ("C", "D", 0.5),
        ])
        graph = builder.build_graph(min_confidence=0.3)
        assert len(graph.nodes) == 2  # Only C, D
        assert len(graph.edges) == 1

    def test_build_skips_self_loops(self, db, builder):
        _insert_claims(db, [
            ("A", "A", 0.9),
            ("A", "B", 0.5),
        ])
        graph = builder.build_graph(min_confidence=0.3)
        assert len(graph.edges) == 1

    def test_build_source_data(self, db, builder):
        _insert_claims(db, [("X", "Y", 0.8)])
        graph = builder.build_graph(min_confidence=0.5)
        assert graph.source_data["min_confidence"] == 0.5
        assert graph.source_data["total_claims_fetched"] == 1


# ── detect_communities ───────────────────────────────

class TestCommunities:
    def test_single_component(self, db, builder):
        _insert_claims(db, [
            ("A", "B", 0.5),
            ("B", "C", 0.5),
        ])
        builder.build_graph(min_confidence=0.3)
        communities = builder.detect_communities()
        assert len(communities) == 1
        assert communities[0].size == 3

    def test_two_components(self, db, builder):
        _insert_claims(db, [
            ("A", "B", 0.5),
            ("C", "D", 0.5),
        ])
        builder.build_graph(min_confidence=0.3)
        communities = builder.detect_communities()
        assert len(communities) == 2
        assert all(c.size == 2 for c in communities)

    def test_empty_graph(self, builder):
        communities = builder.detect_communities()
        assert communities == []

    def test_community_edges(self, db, builder):
        _insert_claims(db, [
            ("A", "B", 0.5),
            ("B", "C", 0.6),
        ])
        builder.build_graph(min_confidence=0.3)
        communities = builder.detect_communities()
        assert len(communities[0].edges) == 2


# ── find_root_causes ─────────────────────────────────

class TestRootCauses:
    def test_linear_chain(self, db, builder):
        _insert_claims(db, [
            ("A", "B", 0.5),
            ("B", "C", 0.5),
            ("C", "D", 0.5),
        ])
        builder.build_graph(min_confidence=0.3)
        roots = builder.find_root_causes()
        assert len(roots) == 1
        assert roots[0][0] == "A"

    def test_multiple_roots(self, db, builder):
        _insert_claims(db, [
            ("A", "C", 0.5),
            ("B", "C", 0.5),
        ])
        builder.build_graph(min_confidence=0.3)
        roots = builder.find_root_causes()
        assert len(roots) == 2
        root_names = {r[0] for r in roots}
        assert root_names == {"A", "B"}

    def test_trace_roots_for_effect(self, db, builder):
        _insert_claims(db, [
            ("A", "B", 0.5),
            ("B", "C", 0.5),
            ("X", "Y", 0.5),  # Separate component
        ])
        builder.build_graph(min_confidence=0.3)
        roots = builder.find_root_causes(effect="C")
        assert len(roots) == 1
        assert roots[0][0] == "A"

    def test_trace_roots_unknown_effect(self, db, builder):
        _insert_claims(db, [("A", "B", 0.5)])
        builder.build_graph(min_confidence=0.3)
        roots = builder.find_root_causes(effect="UNKNOWN")
        assert roots == []

    def test_no_roots_all_have_parents(self, db, builder):
        """Cycle-like structure: A->B->C->A — no real roots."""
        # But we skip self-loops; this is a true cycle in the data.
        # In practice this can happen with unverified direction.
        _insert_claims(db, [
            ("A", "B", 0.5),
            ("B", "A", 0.5),
        ])
        builder.build_graph(min_confidence=0.3)
        roots = builder.find_root_causes()
        assert roots == []  # Both have parents


# ── find_causal_chains ───────────────────────────────

class TestCausalChains:
    def test_finds_chain(self, db, builder):
        _insert_claims(db, [
            ("A", "B", 0.5),
            ("B", "C", 0.6),
            ("C", "D", 0.7),
        ])
        builder.build_graph(min_confidence=0.3)
        chains = builder.find_causal_chains(min_length=3)
        assert len(chains) >= 1
        longest = chains[0]
        assert longest.length >= 3
        assert longest.path[0] == "A"

    def test_chain_with_min_length_4(self, db, builder):
        _insert_claims(db, [
            ("A", "B", 0.5),
            ("B", "C", 0.5),
            ("C", "D", 0.5),
            ("D", "E", 0.5),
        ])
        builder.build_graph(min_confidence=0.3)
        chains_3 = builder.find_causal_chains(min_length=3)
        chains_4 = builder.find_causal_chains(min_length=4)
        assert len(chains_4) <= len(chains_3)
        assert all(c.length >= 4 for c in chains_4)

    def test_no_chains_short_graph(self, db, builder):
        _insert_claims(db, [("A", "B", 0.5)])
        builder.build_graph(min_confidence=0.3)
        chains = builder.find_causal_chains(min_length=3)
        assert chains == []

    def test_chain_product_confidence(self, db, builder):
        _insert_claims(db, [
            ("A", "B", 0.5),
            ("B", "C", 0.8),
            ("C", "D", 0.4),
        ])
        builder.build_graph(min_confidence=0.3)
        chains = builder.find_causal_chains(min_length=3)
        assert len(chains) >= 1
        chain = chains[0]
        expected = 0.5 * 0.8 * 0.4
        assert abs(chain.product_confidence - expected) < 0.001


# ── get_strongest_paths ──────────────────────────────

class TestStrongestPaths:
    def test_strongest_sorted(self, db, builder):
        _insert_claims(db, [
            ("A", "B", 0.9),
            ("B", "C", 0.9),
            ("X", "Y", 0.3),
            ("Y", "Z", 0.3),
        ])
        builder.build_graph(min_confidence=0.3)
        paths = builder.get_strongest_paths(top_n=5)
        if len(paths) >= 2:
            assert paths[0].product_confidence >= paths[1].product_confidence

    def test_strongest_limited(self, db, builder):
        _insert_claims(db, [
            ("A", "B", 0.5),
            ("B", "C", 0.5),
        ])
        builder.build_graph(min_confidence=0.3)
        paths = builder.get_strongest_paths(top_n=1)
        assert len(paths) <= 1


# ── summary ──────────────────────────────────────────

class TestSummary:
    def test_summary_populated(self, db, builder):
        _insert_claims(db, [
            ("A", "B", 0.5),
            ("B", "C", 0.6),
            ("C", "D", 0.7),
            ("X", "Y", 0.8),
        ])
        builder.build_graph(min_confidence=0.3)
        s = builder.summary()
        assert s.total_nodes == 6
        assert s.total_edges == 4
        assert s.connected_components == 2
        assert len(s.top_root_causes) >= 1
        assert len(s.top_terminal_effects) >= 1

    def test_summary_empty(self, builder):
        s = builder.summary()
        assert s.total_nodes == 0
        assert s.total_edges == 0
        assert s.connected_components == 0
