"""Tests for structural graph analysis.

Compares the Etz Chaim graph (10 nodes, 22 edges) against
IA architecture graphs using spectral distance and MCS.
"""
from __future__ import annotations

import networkx as nx
import numpy as np

from halom.structural import StructuralAnalyzer


def _etz_chaim_graph() -> nx.Graph:
    """The Tree of Life: 10 Sephiroth, 22 paths."""
    g = nx.Graph()
    sephiroth = [
        "keter", "chokmah", "binah", "chesed", "gevurah",
        "tiferet", "netzach", "hod", "yesod", "malkuth",
    ]
    g.add_nodes_from(sephiroth)
    edges = [
        ("keter", "chokmah"), ("keter", "binah"), ("keter", "tiferet"),
        ("chokmah", "binah"), ("chokmah", "chesed"), ("chokmah", "tiferet"),
        ("binah", "gevurah"), ("binah", "tiferet"),
        ("chesed", "gevurah"), ("chesed", "tiferet"), ("chesed", "netzach"),
        ("gevurah", "tiferet"), ("gevurah", "hod"),
        ("tiferet", "netzach"), ("tiferet", "hod"), ("tiferet", "yesod"),
        ("netzach", "hod"), ("netzach", "yesod"),
        ("hod", "yesod"),
        ("yesod", "malkuth"),
        ("netzach", "malkuth"), ("hod", "malkuth"),
    ]
    g.add_edges_from(edges)
    return g


class TestEtzChaimProperties:
    """Verify known properties of the Tree of Life graph."""

    def test_node_count(self):
        g = _etz_chaim_graph()
        assert g.number_of_nodes() == 10

    def test_edge_count(self):
        g = _etz_chaim_graph()
        assert g.number_of_edges() == 22

    def test_tiferet_degree(self):
        """Tiferet is the hub — degree 8."""
        g = _etz_chaim_graph()
        assert g.degree("tiferet") == 8

    def test_diameter(self):
        g = _etz_chaim_graph()
        assert nx.diameter(g) == 3


class TestSpectralDistance:
    """Spectral distance between graphs."""

    def test_identical_graphs_zero_distance(self):
        """Same graph → distance 0."""
        g = _etz_chaim_graph()
        analyzer = StructuralAnalyzer()
        d = analyzer.spectral_distance(g, g)
        assert d == 0.0

    def test_different_graphs_positive_distance(self):
        """Different graphs → positive distance."""
        g1 = _etz_chaim_graph()
        g2 = nx.path_graph(10)
        analyzer = StructuralAnalyzer()
        d = analyzer.spectral_distance(g1, g2)
        assert d > 0.0

    def test_distance_symmetry(self):
        """d(G1, G2) = d(G2, G1)."""
        g1 = _etz_chaim_graph()
        g2 = nx.complete_graph(10)
        analyzer = StructuralAnalyzer()
        assert analyzer.spectral_distance(g1, g2) == analyzer.spectral_distance(g2, g1)


class TestBetweenness:
    """Betweenness centrality analysis."""

    def test_tiferet_highest_betweenness(self):
        """Tiferet should have the highest betweenness centrality."""
        g = _etz_chaim_graph()
        analyzer = StructuralAnalyzer()
        bc = analyzer.betweenness(g)
        max_node = max(bc, key=bc.get)
        assert max_node == "tiferet"

    def test_tiferet_betweenness_value(self):
        """Tiferet betweenness ≈ 0.38."""
        g = _etz_chaim_graph()
        analyzer = StructuralAnalyzer()
        bc = analyzer.betweenness(g)
        assert abs(bc["tiferet"] - 0.384) < 0.05


class TestSimilarityReport:
    """Full similarity report between two graphs."""

    def test_report_structure(self):
        """Report contains expected keys."""
        g1 = _etz_chaim_graph()
        g2 = nx.path_graph(10)
        analyzer = StructuralAnalyzer()
        report = analyzer.compare(g1, g2)
        assert "spectral_distance" in report
        assert "degree_correlation" in report
        assert "common_degree_sequence_ratio" in report
