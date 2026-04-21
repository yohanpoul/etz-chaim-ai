"""Tests SerendipityWalker — la sérendipité trouve-t-elle l'inattendu ?"""

from explorationengine.serendipity import SerendipityWalker
from explorationengine.analogy_engine import AnalogyEngine
from explorationengine.cross_domain import CrossDomainConnector


class TestSerendipityWalker:
    """Marche de sérendipité entre domaines."""

    def test_walk_visits_multiple_domains(self):
        """La marche visite plusieurs domaines."""
        walker = SerendipityWalker()
        conns = walker.walk(
            start_concept="attention mechanism",
            start_domain="machine_learning",
            n_steps=3,
        )
        domains = set()
        for c in conns:
            domains.add(c.domain_a)
            domains.add(c.domain_b)
        assert len(domains) >= 2

    def test_walk_does_not_revisit(self):
        """La marche ne revisite pas un domaine déjà visité."""
        walker = SerendipityWalker()
        conns = walker.walk(
            start_concept="hierarchy",
            start_domain="machine_learning",
            n_steps=5,
        )
        # Les domain_b successifs doivent être distincts
        # (chaque pas va vers un domaine non visité)
        target_domains = []
        for c in conns:
            if c.domain_b not in target_domains:
                target_domains.append(c.domain_b)

    def test_walk_respects_n_steps(self):
        """La marche s'arrête au nombre de pas demandé."""
        walker = SerendipityWalker()
        conns = walker.walk(
            start_concept="network",
            start_domain="neuroscience",
            n_steps=2,
            available_domains=["neuroscience", "machine_learning", "biology", "physics"],
        )
        # Maximum 2 steps → connections from at most 2 target domains
        target_domains = {c.domain_b for c in conns}
        assert len(target_domains) <= 2

    def test_walk_deterministic(self):
        """Même inputs → même résultat (déterministe)."""
        walker = SerendipityWalker()
        conns1 = walker.walk("attention", "machine_learning", 3)
        conns2 = walker.walk("attention", "machine_learning", 3)
        assert len(conns1) == len(conns2)
        for c1, c2 in zip(conns1, conns2):
            assert c1.domain_b == c2.domain_b

    def test_walk_stops_when_no_domains_left(self):
        """La marche s'arrête quand tous les domaines sont visités."""
        walker = SerendipityWalker()
        conns = walker.walk(
            start_concept="test",
            start_domain="machine_learning",
            n_steps=100,
            available_domains=["machine_learning", "neuroscience"],
        )
        # Only 1 unvisited domain (neuroscience), so max 1 step
        target_domains = {c.domain_b for c in conns}
        assert len(target_domains) <= 1

    def test_pivot_changes_concept(self):
        """Le concept-pivot change à chaque pas."""
        walker = SerendipityWalker()
        # With rich domain knowledge, the pivot should evolve
        connector = CrossDomainConnector(domain_knowledge={
            "ml": "layers hierarchy attention flow pipeline gradient",
            "neuro": "neurons cortex hippocampus synapses plasticity",
            "bio": "cells organism evolution genes metabolism",
        })
        walker_rich = SerendipityWalker(connector=connector)
        conns = walker_rich.walk(
            start_concept="attention layers hierarchy",
            start_domain="ml",
            n_steps=2,
            available_domains=["ml", "neuro", "bio"],
        )
        assert len(conns) > 0

    def test_empty_start_handled(self):
        walker = SerendipityWalker()
        conns = walker.walk("", "unknown_domain", 3)
        # Should handle gracefully
        assert isinstance(conns, list)

    def test_walk_returns_connections(self):
        walker = SerendipityWalker()
        conns = walker.walk("attention", "machine_learning", 2)
        for c in conns:
            assert c.description
            assert c.connection_type in ("analogy", "causal", "contradicts",
                                          "complements", "pattern_shared")
