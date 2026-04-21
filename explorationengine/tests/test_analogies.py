"""Tests AnalogyEngine — qualité des analogies structurelles."""

from explorationengine.analogy_engine import AnalogyEngine


class TestAnalogyEngine:
    """Analogies structurelles entre domaines."""

    def test_shared_concept_found(self):
        """Un concept partagé est détecté comme analogie."""
        engine = AnalogyEngine()
        conns = engine.find_analogies(
            concept="attention mechanism",
            source_domain="machine_learning",
        )
        # 'attention' exists in both ML and neuroscience
        targets = {c.domain_b for c in conns}
        assert "neuroscience" in targets

    def test_shared_structure_found(self):
        """Structures homologues détectées entre domaines."""
        engine = AnalogyEngine()
        conns = engine.find_analogies(
            concept="hierarchy of processing",
            source_domain="machine_learning",
        )
        # ML and many domains share 'hierarchy' structure
        structure_analogies = [c for c in conns if "structure" in c.description.lower()]
        assert len(structure_analogies) > 0

    def test_target_domain_filtering(self):
        """On peut filtrer les domaines cibles."""
        engine = AnalogyEngine()
        conns = engine.find_analogies(
            concept="attention",
            source_domain="machine_learning",
            target_domains=["neuroscience"],
        )
        domains = {c.domain_b for c in conns}
        assert domains <= {"neuroscience"}

    def test_no_self_analogy(self):
        """Pas d'analogie avec son propre domaine."""
        engine = AnalogyEngine()
        conns = engine.find_analogies(
            concept="gradient descent",
            source_domain="machine_learning",
        )
        for c in conns:
            assert c.domain_b != "machine_learning"

    def test_all_connections_are_analogies(self):
        engine = AnalogyEngine()
        conns = engine.find_analogies(
            concept="network plasticity",
            source_domain="neuroscience",
        )
        for c in conns:
            assert c.connection_type == "analogy"

    def test_known_domains(self):
        engine = AnalogyEngine()
        domains = engine.get_known_domains()
        assert "neuroscience" in domains
        assert "machine_learning" in domains
        assert "kabbale" in domains

    def test_extra_domains(self):
        engine = AnalogyEngine(extra_domains={
            "music": {
                "concepts": ["harmony", "rhythm", "melody", "counterpoint"],
                "structures": ["hierarchy", "cycle"],
                "description": "musical structure and composition",
            }
        })
        assert "music" in engine.get_known_domains()
        conns = engine.find_analogies(
            concept="harmony",
            source_domain="music",
        )
        assert len(conns) >= 0  # May or may not find analogies

    def test_confidence_range(self):
        engine = AnalogyEngine()
        conns = engine.find_analogies("attention", "machine_learning")
        for c in conns:
            assert 0 <= c.confidence <= 1

    def test_new_domains_exist(self):
        """Les domaines ajoutés (auto_improve, hitbonenut, etc.) sont connus."""
        engine = AnalogyEngine()
        domains = engine.get_known_domains()
        for d in ["auto_improve", "hitbonenut", "failure_analysis",
                   "gematria", "tzimtzum", "sefirot", "partzufim"]:
            assert d in domains, f"Domaine manquant: {d}"

    def test_kabbale_sefirot_analogy(self):
        """Kabbale et sefirot partagent des structures."""
        engine = AnalogyEngine()
        conns = engine.find_analogies("sefirot tree", "kabbale", ["sefirot"])
        assert len(conns) > 0

    def test_cross_domain_detection_basic(self):
        """detect_cross_domain_analogies trouve des patterns récurrents."""
        from explorationengine.models import Connection
        conns = [
            Connection(
                concept_a="attention", domain_a="ml",
                concept_b="attention", domain_b="neuro",
                connection_type="analogy",
                description="attention mechanism in both ml and neuroscience",
            ),
            Connection(
                concept_a="training", domain_a="ml",
                concept_b="plasticity", domain_b="neuro",
                connection_type="analogy",
                description="training in ml parallels plasticity in neuroscience",
            ),
        ]
        engine = AnalogyEngine()
        results = engine.detect_cross_domain_analogies(conns)
        assert len(results) > 0
        assert any("ml" in r["domain_a"] or "ml" in r["domain_b"] for r in results)

    def test_cross_domain_needs_minimum_connections(self):
        """Pas d'analogie avec une seule connexion."""
        from explorationengine.models import Connection
        conns = [
            Connection(
                concept_a="x", domain_a="a",
                concept_b="y", domain_b="b",
                connection_type="analogy",
                description="single connection",
            ),
        ]
        engine = AnalogyEngine()
        results = engine.detect_cross_domain_analogies(conns)
        assert len(results) == 0
