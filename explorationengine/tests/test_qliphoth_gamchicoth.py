"""Tests Qliphoth de Gamchicoth — les 4 niveaux anti-Gamchicoth.

Gamchicoth (les Dévoreurs) : Chesed qui explore sans jamais converger.
4 niveaux de diagnostic :
- Nogah : exploration dépasse le budget temps de 20%
- Ruach : connexions redondantes (>50% similaires)
- Anan : score de nouveauté en déclin continu
- Mamash : exploration infinie qui dépasse les hard limits
"""

import pytest

from explorationengine.novelty_scorer import NoveltyScorer
from explorationengine.models import Connection


def _make_conn(desc: str, novelty: float = 0.5, domain_a: str = "a",
               domain_b: str = "b", conn_type: str = "analogy") -> Connection:
    return Connection(
        concept_a="x", domain_a=domain_a,
        concept_b="y", domain_b=domain_b,
        connection_type=conn_type,
        description=desc,
        novelty_score=novelty,
    )


class TestGamchicothDiagnosis:
    """Auto-diagnostic anti-Gamchicoth — Chesed surveille Chesed."""

    def test_healthy_when_empty(self):
        scorer = NoveltyScorer()
        diag = scorer.diagnose(connections=[])
        assert diag["level"] == "healthy"
        assert diag["issues"] == []

    def test_healthy_diverse_connections(self):
        scorer = NoveltyScorer()
        conns = [
            _make_conn("alpha beta gamma", novelty=0.8, domain_a="ml", domain_b="neuro"),
            _make_conn("delta epsilon zeta", novelty=0.7, domain_a="bio", domain_b="phys"),
            _make_conn("theta kappa lambda", novelty=0.6, domain_a="kab", domain_b="code"),
        ]
        diag = scorer.diagnose(conns, elapsed_seconds=100, budget_seconds=600)
        assert diag["level"] == "healthy"

    def test_nogah_time_budget_exceeded(self):
        """Nogah : exploration dépasse le budget temps de 20%."""
        scorer = NoveltyScorer()
        # Connexions suffisamment diverses pour ne pas déclencher Ruach
        conns = [
            _make_conn("alpha beta gamma delta epsilon", novelty=0.5, domain_a="ml", domain_b="neuro"),
            _make_conn("zeta theta kappa lambda omega", novelty=0.5, domain_a="bio", domain_b="phys"),
            _make_conn("neuroscience cortex hippocampus synapse", novelty=0.5, domain_a="neuro", domain_b="kab"),
            _make_conn("physics quantum entropy conservation field", novelty=0.5, domain_a="phys", domain_b="code"),
            _make_conn("writing narrative structure metaphor voice", novelty=0.5, domain_a="writing", domain_b="ml"),
        ]
        diag = scorer.diagnose(
            conns,
            elapsed_seconds=800,  # 33% over budget
            budget_seconds=600,
        )
        assert diag["level"] == "nogah"
        assert any("Nogah" in issue for issue in diag["issues"])

    def test_ruach_redundant_connections(self):
        """Ruach : connexions redondantes (>50% similaires)."""
        scorer = NoveltyScorer()
        conns = [
            _make_conn("same connection about attention mechanism", novelty=0.5),
            _make_conn("same connection about attention mechanism", novelty=0.4),
            _make_conn("same connection about attention mechanism", novelty=0.3),
            _make_conn("same connection about attention mechanism", novelty=0.3),
            _make_conn("same connection about attention mechanism", novelty=0.2),
        ]
        diag = scorer.diagnose(conns)
        assert diag["level"] == "ruach"
        assert any("Ruach" in issue for issue in diag["issues"])

    def test_anan_novelty_decay(self):
        """Anan : score de nouveauté en déclin continu."""
        scorer = NoveltyScorer(decay_window=10)
        conns = [
            _make_conn(f"unique topic {i} about distinct subject", novelty=0.1)
            for i in range(12)
        ]
        diag = scorer.diagnose(conns, novelty_threshold=0.3)
        assert diag["level"] == "anan"
        assert any("Anan" in issue for issue in diag["issues"])

    def test_mamash_hard_limit_exceeded(self):
        """Mamash : exploration infinie dépasse les hard limits."""
        scorer = NoveltyScorer()
        conns = [
            _make_conn(f"connection {i}", novelty=0.8, domain_a=f"d{i}", domain_b=f"d{i+1}")
            for i in range(60)
        ]
        diag = scorer.diagnose(conns, max_connections=50)
        assert diag["level"] == "mamash"
        assert any("Mamash" in issue for issue in diag["issues"])

    def test_mamash_overrides_other_levels(self):
        """Mamash est le niveau le plus grave — il override les autres."""
        scorer = NoveltyScorer(decay_window=5)
        conns = [
            _make_conn("same same same connection", novelty=0.1)
            for _ in range(60)
        ]
        diag = scorer.diagnose(
            conns,
            elapsed_seconds=1000,
            budget_seconds=600,
            max_connections=50,
        )
        assert diag["level"] == "mamash"


class TestExplorationIntegration:
    """Tests d'intégration — ExplorationEngine complète."""

    def test_explore_returns_result(self, engine):
        """explore() retourne un ExplorationResult."""
        result = engine.explore(
            query="attention mechanism",
            seed_domain="machine_learning",
            target_domains=["neuroscience", "biology"],
            max_connections=20,
        )
        assert result.status in ("completed", "stopped_novelty", "stopped_budget")
        assert isinstance(result.connections, list)

    def test_explore_finds_connections(self, engine_with_knowledge):
        """explore() trouve des connexions inter-domaines."""
        result = engine_with_knowledge.explore(
            query="hierarchy of layers",
            seed_domain="machine_learning",
            target_domains=["neuroscience", "kabbale"],
            max_connections=20,
        )
        assert result.total_connections > 0

    def test_explore_persists_to_db(self, engine):
        """Les connexions sont persistées en DB."""
        result = engine.explore(
            query="feedback cycle",
            seed_domain="biology",
            target_domains=["physics"],
            max_connections=10,
        )
        assert result.exploration_id is not None
        # Verify in DB
        exp = engine.db.get_exploration(result.exploration_id)
        assert exp is not None
        assert exp.status in ("completed", "stopped_novelty", "stopped_budget")

    def test_explore_stops_on_budget(self, engine):
        """L'exploration s'arrête quand le budget est atteint."""
        engine.max_duration_seconds = 0  # Budget of 0 seconds
        result = engine.explore(
            query="test",
            seed_domain="machine_learning",
            target_domains=["neuroscience", "biology", "physics", "kabbale"],
            max_connections=100,
        )
        # Should stop quickly
        assert result.status in ("stopped_budget", "completed")

    def test_explore_stops_on_max_connections(self, engine):
        """L'exploration s'arrête au max_connections."""
        result = engine.explore(
            query="attention hierarchy layers flow pipeline",
            seed_domain="machine_learning",
            target_domains=["neuroscience", "biology", "physics", "kabbale",
                            "soufisme", "writing", "code"],
            max_connections=3,
        )
        assert result.total_connections <= 3

    def test_serendipity_walk(self, engine):
        """La marche de sérendipité produit des connexions."""
        conns = engine.serendipity_walk(
            start="attention",
            start_domain="machine_learning",
            n_steps=3,
        )
        assert isinstance(conns, list)

    def test_find_analogies(self, engine):
        """find_analogies retourne des analogies."""
        conns = engine.find_analogies(
            concept="attention",
            source_domain="machine_learning",
            target_domains=["neuroscience"],
        )
        for c in conns:
            assert c.connection_type == "analogy"

    def test_report_generates(self, engine):
        """Le rapport est généré sans erreur."""
        report = engine.report()
        assert "ExplorationEngine Report" in report

    def test_self_diagnose_healthy(self, engine):
        diag = engine.self_diagnose()
        assert diag["level"] == "healthy"
