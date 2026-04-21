"""Tests NoveltyScorer — le score de nouveauté fonctionne-t-il ?"""

from explorationengine.novelty_scorer import NoveltyScorer
from explorationengine.models import Connection


def _make_conn(desc: str, domain_a: str = "a", domain_b: str = "b",
               conn_type: str = "analogy", novelty: float = 0.5) -> Connection:
    return Connection(
        concept_a="concept_a",
        domain_a=domain_a,
        concept_b="concept_b",
        domain_b=domain_b,
        connection_type=conn_type,
        description=desc,
        novelty_score=novelty,
    )


class TestNoveltyScorer:
    """Anti-Gamchicoth : score de nouveauté."""

    def test_first_connection_is_novel(self):
        """La première connexion a une nouveauté de 1.0."""
        scorer = NoveltyScorer()
        conn = _make_conn("a brand new connection between domains")
        score = scorer.score(conn, [])
        assert score == 1.0

    def test_identical_connection_not_novel(self):
        """Une connexion identique a une nouveauté basse."""
        scorer = NoveltyScorer()
        existing = _make_conn("attention mechanism bridges neuroscience and machine learning")
        new = _make_conn("attention mechanism bridges neuroscience and machine learning")
        score = scorer.score(new, [existing])
        assert score < 0.3

    def test_different_connection_is_novel(self):
        """Une connexion très différente a une nouveauté haute."""
        scorer = NoveltyScorer()
        existing = _make_conn("attention mechanism bridges neuroscience and learning")
        new = _make_conn(
            "evolutionary biology shares feedback cycles with thermodynamics",
            domain_a="biology", domain_b="physics", conn_type="pattern_shared",
        )
        score = scorer.score(new, [existing])
        assert score > 0.5

    def test_novelty_between_0_and_1(self):
        scorer = NoveltyScorer()
        existing = [_make_conn(f"connection about topic {i}") for i in range(5)]
        new = _make_conn("semi-related connection about topic 3 and 7")
        score = scorer.score(new, existing)
        assert 0 <= score <= 1

    def test_domain_overlap_reduces_novelty(self):
        """Mêmes domaines → novelty réduite."""
        scorer = NoveltyScorer()
        existing = _make_conn("connection between A and B", "ml", "neuro")
        new_same = _make_conn("different insight between same fields", "ml", "neuro")
        new_diff = _make_conn("different insight between other fields", "bio", "physics")
        score_same = scorer.score(new_same, [existing])
        score_diff = scorer.score(new_diff, [existing])
        assert score_diff > score_same

    def test_detect_decay_false_when_few(self):
        """Pas de détection de déclin avec peu de connexions."""
        scorer = NoveltyScorer(decay_window=10)
        conns = [_make_conn(f"conn {i}", novelty=0.1) for i in range(5)]
        assert not scorer.detect_decay(conns, threshold=0.3)

    def test_detect_decay_true_when_all_low(self):
        """Déclin détecté quand toutes les récentes sont basses."""
        scorer = NoveltyScorer(decay_window=5)
        conns = [_make_conn(f"conn {i}", novelty=0.1) for i in range(10)]
        assert scorer.detect_decay(conns, threshold=0.3)

    def test_detect_decay_false_when_mixed(self):
        """Pas de déclin quand les scores sont variés."""
        scorer = NoveltyScorer(decay_window=5)
        conns = [_make_conn(f"conn {i}", novelty=0.1 if i % 2 == 0 else 0.8)
                 for i in range(10)]
        assert not scorer.detect_decay(conns, threshold=0.3)

    def test_detect_redundancy_true(self):
        """Redondance détectée quand >50% des paires sont similaires."""
        scorer = NoveltyScorer()
        # All same description → all pairs similar
        conns = [_make_conn("same description same words same content") for _ in range(5)]
        assert scorer.detect_redundancy(conns)

    def test_detect_redundancy_false(self):
        """Pas de redondance quand les connexions sont diverses."""
        scorer = NoveltyScorer()
        conns = [
            _make_conn("alpha beta gamma delta epsilon"),
            _make_conn("zeta theta omega kappa lambda"),
            _make_conn("neuroscience cortex hippocampus synapse"),
            _make_conn("physics quantum entropy conservation field"),
        ]
        assert not scorer.detect_redundancy(conns)
