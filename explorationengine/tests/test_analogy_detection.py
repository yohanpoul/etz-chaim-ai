"""Tests détection d'analogies cross-domain (DB + heuristique)."""

import pytest


class TestAnalogyDB:
    """CRUD analogies dans la DB."""

    def test_create_analogy(self, db):
        result = db.create_analogy(
            domain_a="kabbale",
            domain_b="machine_learning",
            pattern="hierarchy_parallel",
            explanation="Both use hierarchical processing layers",
            strength=0.7,
            generated_by="heuristic",
        )
        assert result["domain_a"] == "kabbale"
        assert result["domain_b"] == "machine_learning"
        assert result["strength"] == 0.7
        assert result["id"] is not None

    def test_get_analogies(self, db):
        db.create_analogy("a", "b", "p1", "expl1", 0.8)
        db.create_analogy("a", "c", "p2", "expl2", 0.3)
        db.create_analogy("d", "e", "p3", "expl3", 0.5)

        # Filtrer par domaine
        results = db.get_analogies(domain_a="a")
        assert len(results) == 2

        # Filtrer par force
        results = db.get_analogies(min_strength=0.5)
        assert len(results) == 2

    def test_count_analogies(self, db):
        assert db.count_analogies() == 0
        db.create_analogy("a", "b", "p", "e", 0.5)
        assert db.count_analogies() == 1

    def test_analogy_exists_dedup(self, db):
        assert not db.analogy_exists("a", "b", "pattern")
        db.create_analogy("a", "b", "pattern", "explanation", 0.5)
        assert db.analogy_exists("a", "b", "pattern")
        # Symétrique
        assert db.analogy_exists("b", "a", "pattern")

    def test_analogy_exists_different_pattern(self, db):
        db.create_analogy("a", "b", "pattern1", "explanation", 0.5)
        assert not db.analogy_exists("a", "b", "pattern2")


class TestRunAnalogyDetection:
    """run_analogy_detection sur l'engine complet."""

    def test_no_connections_reports_error(self, engine):
        result = engine.run_analogy_detection()
        assert "errors" in result
        assert len(result["errors"]) > 0

    def test_heuristic_detection_with_connections(self, engine):
        # Créer une exploration avec des connexions
        exp = engine.db.create_exploration(
            seed_query="test query",
            seed_domain="kabbale",
            target_domains=["machine_learning"],
        )
        engine.db.create_connection(
            exploration_id=exp.id,
            concept_a="hierarchy of sefirot",
            domain_a="kabbale",
            concept_b="hierarchy of layers",
            domain_b="machine_learning",
            connection_type="analogy",
            description="hierarchical processing in both kabbale and ml",
            novelty_score=0.8,
            confidence=0.6,
        )
        engine.db.create_connection(
            exploration_id=exp.id,
            concept_a="tikkun repair",
            domain_a="kabbale",
            concept_b="fine-tuning optimization",
            domain_b="machine_learning",
            connection_type="analogy",
            description="repair and optimization in kabbale and ml hierarchy",
            novelty_score=0.7,
            confidence=0.5,
        )

        result = engine.run_analogy_detection(skip_llm=True)
        assert result["heuristic_found"] > 0
        assert result["stored"] > 0
        assert engine.db.count_analogies() > 0

    def test_dedup_on_second_run(self, engine):
        exp = engine.db.create_exploration(
            seed_query="test", seed_domain="a",
            target_domains=["b"],
        )
        engine.db.create_connection(
            exploration_id=exp.id,
            concept_a="x", domain_a="a",
            concept_b="y", domain_b="b",
            connection_type="analogy",
            description="repeated pattern across a and b domains",
            novelty_score=0.9,
        )
        engine.db.create_connection(
            exploration_id=exp.id,
            concept_a="z", domain_a="a",
            concept_b="w", domain_b="b",
            connection_type="analogy",
            description="another pattern across a and b domains",
            novelty_score=0.8,
        )

        r1 = engine.run_analogy_detection(skip_llm=True)
        count_after_first = engine.db.count_analogies()

        r2 = engine.run_analogy_detection(skip_llm=True)
        count_after_second = engine.db.count_analogies()

        assert count_after_second == count_after_first
        assert r2["duplicates_skipped"] > 0


class TestParseLLMAnalogies:
    """Parsing de la réponse LLM."""

    def test_parse_single_analogy(self):
        from explorationengine.core import ExplorationEngine
        response = (
            "Voici l'analyse:\n\n"
            "PATTERN: hierarchical_compression\n"
            "FORCE: 0.75\n"
            "EXPLICATION: Both domains compress information through layers.\n"
        )
        result = ExplorationEngine._parse_llm_analogies(response, "a", "b")
        assert len(result) == 1
        assert result[0]["pattern"] == "hierarchical_compression"
        assert result[0]["strength"] == 0.75
        assert result[0]["domain_a"] == "a"
        assert result[0]["generated_by"] == "llm"

    def test_parse_multiple_analogies(self):
        from explorationengine.core import ExplorationEngine
        response = (
            "PATTERN: feedback_loop\n"
            "FORCE: 0.8\n"
            "EXPLICATION: Iterative refinement in both.\n"
            "PATTERN: bottleneck\n"
            "FORCE: 0.6\n"
            "EXPLICATION: Compression through narrow channels.\n"
        )
        result = ExplorationEngine._parse_llm_analogies(response, "x", "y")
        assert len(result) == 2

    def test_parse_no_match(self):
        from explorationengine.core import ExplorationEngine
        result = ExplorationEngine._parse_llm_analogies("rien ici", "a", "b")
        assert len(result) == 0

    def test_strength_clamped(self):
        from explorationengine.core import ExplorationEngine
        response = "PATTERN: test\nFORCE: 1.5\nEXPLICATION: over\n"
        result = ExplorationEngine._parse_llm_analogies(response, "a", "b")
        assert result[0]["strength"] == 1.0
