"""Tests CrossDomainConnector — connexions inter-domaines."""

from explorationengine.cross_domain import CrossDomainConnector


class TestCrossDomainConnector:
    """Trouver des ponts entre domaines."""

    def test_shared_vocabulary_detected(self):
        """Vocabulaire partagé → pattern_shared."""
        connector = CrossDomainConnector()
        conns = connector.find_connections(
            query="attention mechanism in neural networks",
            domain_a="machine_learning",
            domain_b="neuroscience",
            context_a="transformer attention heads",
            context_b="neural attention in cortex",
        )
        types = [c.connection_type for c in conns]
        assert "pattern_shared" in types

    def test_structural_analogy_detected(self):
        """Patterns structurels communs → analogy."""
        connector = CrossDomainConnector(domain_knowledge={
            "ml": "hierarchy of layers in deep learning pipeline",
            "kabbalah": "hierarchy of sefirot levels in emanation",
        })
        conns = connector.find_connections(
            query="hierarchy of processing",
            domain_a="ml",
            domain_b="kabbalah",
        )
        types = [c.connection_type for c in conns]
        assert "analogy" in types

    def test_causal_markers_detected(self):
        """Marqueurs causaux → causal."""
        connector = CrossDomainConnector()
        conns = connector.find_connections(
            query="sleep deprivation causes cognitive decline",
            domain_a="neuroscience",
            domain_b="biology",
            context_b="metabolism influences brain function",
        )
        types = [c.connection_type for c in conns]
        assert "causal" in types

    def test_contradiction_detected(self):
        """Marqueurs de contradiction → contradicts."""
        connector = CrossDomainConnector()
        conns = connector.find_connections(
            query="however the opposite approach works",
            domain_a="physics",
            domain_b="biology",
            context_b="contrary to expectations",
        )
        types = [c.connection_type for c in conns]
        assert "contradicts" in types

    def test_complement_detected(self):
        """Marqueurs de complémentarité → complements."""
        connector = CrossDomainConnector()
        conns = connector.find_connections(
            query="this approach also extends naturally",
            domain_a="writing",
            domain_b="code",
            context_b="additionally supports modular design",
        )
        types = [c.connection_type for c in conns]
        assert "complements" in types

    def test_empty_text_returns_nothing(self):
        connector = CrossDomainConnector()
        conns = connector.find_connections("", "a", "b")
        assert conns == []

    def test_find_connections_multi(self):
        connector = CrossDomainConnector(domain_knowledge={
            "ml": "layers hierarchy flow pipeline",
            "neuro": "layers hierarchy network",
            "bio": "cycle feedback flow",
        })
        conns = connector.find_connections_multi(
            query="layers hierarchy",
            seed_domain="ml",
            target_domains=["neuro", "bio"],
        )
        assert len(conns) >= 2
        domains = {c.domain_b for c in conns}
        assert "neuro" in domains

    def test_confidence_between_0_and_1(self):
        connector = CrossDomainConnector()
        conns = connector.find_connections(
            query="attention mechanism causes learning",
            domain_a="ml",
            domain_b="neuro",
            context_a="hierarchy layers flow",
            context_b="hierarchy network flow",
        )
        for c in conns:
            assert 0 <= c.confidence <= 1
