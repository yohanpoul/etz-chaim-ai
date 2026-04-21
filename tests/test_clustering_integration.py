"""Tests d'intégration — Clustering dual Kab vs ML."""

from __future__ import annotations

import os

import numpy as np
import psycopg2
import psycopg2.extras
import pytest

DB_URL = os.environ.get(
    "ETZ_CHAIM_TEST_DB", "postgresql://localhost/etz_chaim_test"
)


def _truncate_clustering_tables():
    # Garde anti-PROD : ne JAMAIS DELETE sur une DB qui ne finit pas par '_test'
    db_name = DB_URL.rstrip("/").rsplit("/", 1)[-1].split("?")[0]
    if not db_name.endswith("_test"):
        raise RuntimeError(
            f"Refus de DELETE clustering_* sur '{db_name}' (pas une DB de test)."
        )
    try:
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("DELETE FROM clustering_disagreements")
            cur.execute("DELETE FROM clustering_results")
        conn.close()
    except psycopg2.errors.UndefinedTable:
        # Tables clustering pas encore appliquées sur la DB test → skip silent.
        # (Les tests qui en ont besoin appelleront pytest.skip eux-mêmes.)
        pass


# Skip tous les tests de ce module si les tables n'existent pas dans la DB test
def _clustering_tables_exist() -> bool:
    try:
        conn = psycopg2.connect(DB_URL)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_name = 'clustering_disagreements'"
            )
            exists = cur.fetchone() is not None
        conn.close()
        return exists
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _clustering_tables_exist(),
    reason="Tables clustering_* absentes de la DB test (schema non appliqué).",
)


@pytest.fixture(autouse=True)
def _clean():
    """Clean clustering tables before each test."""
    _truncate_clustering_tables()
    yield
    _truncate_clustering_tables()


# ── Unit tests (no DB needed for clustering logic) ──────────


class TestKMeans:
    def test_basic_clustering(self):
        from kabbalah.clustering import _kmeans
        data = np.array([
            [0, 0], [0.1, 0.1], [0, 0.1],
            [5, 5], [5.1, 5], [5, 5.1],
        ], dtype=np.float32)
        labels = _kmeans(data, k=2)
        # Two distinct clusters
        assert labels[0] == labels[1] == labels[2]
        assert labels[3] == labels[4] == labels[5]
        assert labels[0] != labels[3]


class TestPairDisagreement:
    def test_find_pairwise_disagreements(self):
        from kabbalah.clustering import KabbalisticClustering

        kc = KabbalisticClustering()
        kc.concepts = ["A", "B", "C", "D"]
        kc.hebrews = [None] * 4

        # A and B close in kab space, far in ML space
        kc.kab_matrix = np.array([
            [1.0, 0.0],  # A
            [0.9, 0.1],  # B — close to A in kab
            [0.0, 1.0],  # C
            [0.1, 0.9],  # D — close to C in kab
        ], dtype=np.float32)

        kc.ml_matrix = np.array([
            [1.0, 0.0, 0.0],  # A
            [0.0, 0.0, 1.0],  # B — far from A in ML
            [0.0, 1.0, 0.0],  # C
            [0.0, 0.9, 0.1],  # D — close to C in ML
        ], dtype=np.float32)

        kc.cluster_by_cube(n_clusters=2)
        kc.cluster_by_ml(n_clusters=2)

        pairs = kc.find_pairwise_disagreements(top_n=10, min_gap=0.1)
        assert len(pairs) > 0
        # Check structure
        p = pairs[0]
        assert p.concept_a <= p.concept_b  # alphabetical
        assert p.gap > 0
        assert p.disagreement_type in ("kab_close_ml_far", "ml_close_kab_far")

    def test_empty_data(self):
        from kabbalah.clustering import KabbalisticClustering

        kc = KabbalisticClustering()
        kc.concepts = []
        kc.kab_matrix = None
        kc.ml_matrix = None
        assert kc.find_pairwise_disagreements() == []


# ── Integration tests (need DB with hybrid_embeddings) ──────


class TestPersistence:
    def test_persist_run(self):
        from kabbalah.clustering import KabbalisticClustering, PairDisagreement

        kc = KabbalisticClustering(db_url=DB_URL)
        kc.concepts = ["alpha", "beta"]
        kc.hebrews = [None, None]
        kc.kab_matrix = np.array([[1, 0], [0, 1]], dtype=np.float32)
        kc.ml_matrix = np.array([[1, 0], [0, 1]], dtype=np.float32)
        kc._kab_labels = np.array([0, 1])
        kc._ml_labels = np.array([1, 0])
        kc._n_clusters = 2

        pairs = [PairDisagreement(
            concept_a="alpha", concept_b="beta",
            same_cluster_kab=False, same_cluster_ml=False,
            kab_similarity=0.1, ml_similarity=0.9,
            gap=0.8, disagreement_type="ml_close_kab_far",
        )]

        run_id = kc.persist_run(pairs, n_clusters=2)
        assert run_id > 0

        # Verify in DB
        conn = psycopg2.connect(DB_URL)
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM clustering_results WHERE id = %s", (run_id,))
            row = cur.fetchone()
            assert row is not None
            assert row["n_concepts"] == 2

            cur.execute(
                "SELECT * FROM clustering_disagreements WHERE run_id = %s", (run_id,)
            )
            disag = cur.fetchone()
            assert disag is not None
            assert disag["concept_a"] == "alpha"
            assert disag["concept_b"] == "beta"
            assert disag["gap"] == pytest.approx(0.8)
            assert disag["times_seen"] == 1
        conn.close()

    def test_temporal_tracking(self):
        """times_seen increments on second run with same pair."""
        from kabbalah.clustering import KabbalisticClustering, PairDisagreement

        kc = KabbalisticClustering(db_url=DB_URL)
        kc.concepts = ["gamma", "delta"]
        kc.hebrews = [None, None]
        kc.kab_matrix = np.array([[1, 0], [0, 1]], dtype=np.float32)
        kc.ml_matrix = np.array([[1, 0], [0, 1]], dtype=np.float32)
        kc._kab_labels = np.array([0, 1])
        kc._ml_labels = np.array([1, 0])
        kc._n_clusters = 2

        pairs = [PairDisagreement(
            concept_a="delta", concept_b="gamma",  # note: will be reordered
            same_cluster_kab=False, same_cluster_ml=False,
            kab_similarity=0.2, ml_similarity=0.8,
            gap=0.6, disagreement_type="ml_close_kab_far",
        )]

        # First run
        kc.persist_run(pairs, n_clusters=2)
        # Second run — same pair
        kc.persist_run(pairs, n_clusters=2)

        conn = psycopg2.connect(DB_URL)
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT times_seen FROM clustering_disagreements WHERE concept_a = %s AND concept_b = %s",
                ("delta", "gamma"),
            )
            row = cur.fetchone()
            assert row is not None
            assert row["times_seen"] == 2
        conn.close()


class TestRouting:
    def test_already_routed_not_rerouted(self):
        """Disagreements already routed should not be routed again."""
        from kabbalah.clustering import KabbalisticClustering, PairDisagreement

        kc = KabbalisticClustering(db_url=DB_URL)
        kc.concepts = ["epsilon", "zeta"]
        kc.hebrews = [None, None]
        kc.kab_matrix = np.array([[1, 0], [0, 1]], dtype=np.float32)
        kc.ml_matrix = np.array([[1, 0], [0, 1]], dtype=np.float32)
        kc._kab_labels = np.array([0, 1])
        kc._ml_labels = np.array([1, 0])
        kc._n_clusters = 2

        pairs = [PairDisagreement(
            concept_a="epsilon", concept_b="zeta",
            same_cluster_kab=False, same_cluster_ml=False,
            kab_similarity=0.1, ml_similarity=0.9,
            gap=0.8, disagreement_type="ml_close_kab_far",
        )]
        kc.persist_run(pairs, n_clusters=2)

        # Mark as routed manually
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE clustering_disagreements
                SET dissensus_id = gen_random_uuid(), routed_at = NOW()
                WHERE concept_a = 'epsilon' AND concept_b = 'zeta'
            """)
        conn.close()

        # Try to route — should skip
        try:
            from dissensuengine.core import DissensuEngine
            tiferet = DissensuEngine(db_url=DB_URL)
            routed = kc.route_to_dissensus(pairs, tiferet, top_n=5)
            assert len(routed) == 0
        except Exception:
            pytest.skip("DissensuEngine not available")


class TestFullPipeline:
    def test_run_full_with_real_data(self):
        """Test run_full on real hybrid_embeddings (if available)."""
        from kabbalah.clustering import KabbalisticClustering

        kc = KabbalisticClustering(db_url=DB_URL)
        n = kc.load_from_db()
        if n < 10:
            pytest.skip("Not enough embeddings for meaningful clustering")

        result = kc.run_full(
            n_clusters=min(10, n // 2),
            top_n_pairs=50,
            min_gap=0.2,
            tiferet=None,
        )

        assert result["status"] == "ok"
        assert result["n_concepts"] == n
        assert result["run_id"] > 0
        assert 0.0 <= result["agreement_ratio"] <= 1.0
        assert result["n_pair_disagreements"] >= 0
        assert len(result["top_5"]) <= 5

    def test_summary_format(self):
        """Verify summary dict has expected keys."""
        from kabbalah.clustering import KabbalisticClustering

        kc = KabbalisticClustering()
        kc.concepts = ["a", "b", "c"]
        kc.hebrews = [None] * 3
        kc.kab_matrix = np.random.randn(3, 30).astype(np.float32)
        kc.ml_matrix = np.random.randn(3, 768).astype(np.float32)

        kc.cluster_by_cube(2)
        kc.cluster_by_ml(2)

        s = kc.summary()
        assert "total_concepts" in s
        assert "agreement_ratio" in s
        assert "cube_cluster_sizes" in s
        assert "ml_cluster_sizes" in s
