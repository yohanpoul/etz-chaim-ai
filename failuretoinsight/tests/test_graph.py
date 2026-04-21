"""Tests du graphe de connaissance des échecs."""

import pytest


def test_build_empty_graph(fti_bare):
    """Graphe vide quand aucune analyse."""
    graph = fti_bare.build_failure_graph()
    assert len(graph.analyses) == 0
    assert len(graph.edges) == 0
    assert graph.most_common_qliphah is None


def test_build_graph_with_analyses(fti_bare):
    """Le graphe connecte les analyses par qliphah et domaine."""
    fti_bare.analyze_failure(
        "Retry stuck in loop", domain="networking",
        qliphah_override="aarab_zaraq", severity_override="ruach",
    )
    fti_bare.analyze_failure(
        "Timeout on retry", domain="networking",
        qliphah_override="aarab_zaraq", severity_override="anan",
    )
    fti_bare.analyze_failure(
        "Filter too strict", domain="search",
        qliphah_override="golachab", severity_override="nogah",
    )

    graph = fti_bare.build_failure_graph()
    assert len(graph.analyses) == 3
    assert graph.most_common_qliphah == "aarab_zaraq"
    assert "networking" in graph.domains_affected
    assert "search" in graph.domains_affected


def test_similar_failure_edge(fti_bare):
    """Deux analyses avec même qliphah + même domaine → similar_failure."""
    fti_bare.analyze_failure(
        "Retry loop A", domain="api",
        qliphah_override="aarab_zaraq", severity_override="nogah",
    )
    fti_bare.analyze_failure(
        "Retry loop B", domain="api",
        qliphah_override="aarab_zaraq", severity_override="nogah",
    )

    graph = fti_bare.build_failure_graph()
    similar = [e for e in graph.edges if e.edge_type == "similar_failure"]
    assert len(similar) >= 1


def test_escalation_edge(fti_bare):
    """Même qliphah + même domaine + sévérité croissante → escalation."""
    fti_bare.analyze_failure(
        "Minor retry issue", domain="api",
        qliphah_override="aarab_zaraq", severity_override="nogah",
    )
    fti_bare.analyze_failure(
        "Major retry cascade", domain="api",
        qliphah_override="aarab_zaraq", severity_override="mamash",
    )

    graph = fti_bare.build_failure_graph()
    escalations = [e for e in graph.edges if e.edge_type == "escalation"]
    assert len(escalations) >= 1


def test_same_root_cause_edge(fti_bare):
    """Deux analyses avec même root cause → same_root_cause."""
    fti_bare.analyze_failure(
        "Failed because timeout too short",
        domain="api",
    )
    fti_bare.analyze_failure(
        "Another failure because timeout too short",
        domain="networking",
    )

    graph = fti_bare.build_failure_graph()
    same_cause = [e for e in graph.edges if e.edge_type == "same_root_cause"]
    assert len(same_cause) >= 1


def test_graph_counts_insights(fti_bare):
    """Le graphe compte les insights totaux."""
    a = fti_bare.analyze_failure("Filter rejects too much", domain="search")
    fti_bare.extract_nitzotzot(a.id)

    graph = fti_bare.build_failure_graph()
    assert graph.total_insights >= 1
