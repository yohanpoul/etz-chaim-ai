"""Structural graph analysis for Kabbalah-AI isomorphism detection.

Compares the Etz Chaim graph (10 Sephiroth, 22 paths) against
IA architecture graphs using spectral and topological measures.
"""
from __future__ import annotations

from typing import Any

import networkx as nx
import numpy as np
from scipy import linalg


class StructuralAnalyzer:
    """Analyze structural similarity between graphs."""

    def spectral_distance(self, g1: nx.Graph, g2: nx.Graph) -> float:
        """Spectral distance based on normalized Laplacian eigenvalues."""
        spec1 = self._spectrum(g1)
        spec2 = self._spectrum(g2)

        max_len = max(len(spec1), len(spec2))
        s1 = np.zeros(max_len)
        s2 = np.zeros(max_len)
        s1[: len(spec1)] = spec1
        s2[: len(spec2)] = spec2

        return float(np.linalg.norm(s1 - s2))

    def betweenness(self, g: nx.Graph) -> dict[str, float]:
        """Betweenness centrality for all nodes."""
        return nx.betweenness_centrality(g)

    def compare(self, g1: nx.Graph, g2: nx.Graph) -> dict[str, Any]:
        """Full comparison report between two graphs."""
        sd = self.spectral_distance(g1, g2)

        deg1 = sorted(dict(g1.degree()).values(), reverse=True)
        deg2 = sorted(dict(g2.degree()).values(), reverse=True)

        max_len = max(len(deg1), len(deg2))
        d1 = np.zeros(max_len)
        d2 = np.zeros(max_len)
        d1[: len(deg1)] = deg1
        d2[: len(deg2)] = deg2

        if np.std(d1) == 0 or np.std(d2) == 0:
            corr = 0.0
        else:
            corr = float(np.corrcoef(d1, d2)[0, 1])

        matches = sum(1 for a, b in zip(d1, d2) if a == b)
        ratio = matches / max_len if max_len > 0 else 0.0

        return {
            "spectral_distance": sd,
            "degree_correlation": corr,
            "common_degree_sequence_ratio": ratio,
        }

    @staticmethod
    def _spectrum(g: nx.Graph) -> np.ndarray:
        """Sorted eigenvalues of the normalized Laplacian."""
        if g.number_of_nodes() == 0:
            return np.array([])
        lap = nx.normalized_laplacian_matrix(g).toarray()
        eigenvalues = np.sort(linalg.eigvalsh(lap))
        return eigenvalues
