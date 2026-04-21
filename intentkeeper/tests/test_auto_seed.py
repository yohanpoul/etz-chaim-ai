"""Tests auto-seed — Netzach garde automatiquement les objectifs du système."""

import psycopg2
import psycopg2.extras
import pytest

from intentkeeper.core import IntentKeeper, _query_system_metrics

TEST_DB_URL = "postgresql://localhost/etz_chaim_test"


@pytest.fixture
def seeded_db():
    """Prépare une DB de test avec des données système réalistes."""
    conn = psycopg2.connect(TEST_DB_URL)
    conn.autocommit = True
    cur = conn.cursor()

    # Selfmap: domaines faibles
    cur.execute("DELETE FROM selfmap_competence")
    for domain, score in [
        ("qliphoth", 0.65), ("sefer_yetzirah", 0.66),
        ("gematria", 0.85), ("tzeruf", 0.90),
    ]:
        cur.execute(
            "INSERT INTO selfmap_competence (domain, model_id, score, n_evals) "
            "VALUES (%s, 'test', %s, 10)",
            (domain, score),
        )

    # Causal claims: toutes correlation_only
    try:
        cur.execute("DELETE FROM causal_claims")
        for i in range(20):
            cur.execute(
                "INSERT INTO causal_claims (cause, effect, evidence_level) "
                "VALUES (%s, %s, 'correlation_only')",
                (f"cause_{i}", f"effect_{i}"),
            )
    except Exception:
        conn.rollback()
        conn.autocommit = True

    # Epistememory
    try:
        cur.execute("DELETE FROM epistememory")
        for i in range(100):
            conf = 0.7 if i < 30 else 0.4
            status = "active" if i < 30 else "hypothesis"
            cur.execute(
                "INSERT INTO epistememory (content, source_sephirah, confidence, "
                "epistemic_status, domain) VALUES (%s, 'test', %s, %s, 'test')",
                (f"memory_{i}", conf, status),
            )
    except Exception:
        conn.rollback()
        conn.autocommit = True

    # Omer
    try:
        cur.execute("DELETE FROM omer_history")
        for i in range(5):
            cur.execute(
                "INSERT INTO omer_history (param_key, param_name, sephirah, "
                "inner_midah, module, new_value, reason) "
                "VALUES (%s, %s, 'chesed', 'chesed', 'test', '0.5', 'test')",
                (f"param_{i}", f"Param {i}"),
            )
    except Exception:
        conn.rollback()
        conn.autocommit = True

    # Failuretoinsight — need analysis first (FK)
    try:
        cur.execute("DELETE FROM failuretoinsight_insights")
        cur.execute("DELETE FROM failuretoinsight_analyses")
        cur.execute(
            "INSERT INTO failuretoinsight_analyses "
            "(source_type, description, qliphah) "
            "VALUES ('subtask', 'test analysis', 'gamaliel') RETURNING id"
        )
        analysis_id = cur.fetchone()[0]
        for i in range(15):
            cur.execute(
                "INSERT INTO failuretoinsight_insights "
                "(analysis_id, content, insight_type) "
                "VALUES (%s, %s, 'pattern')",
                (analysis_id, f"insight_{i}"),
            )
    except Exception:
        conn.rollback()
        conn.autocommit = True

    cur.close()
    yield conn

    # Cleanup
    conn2 = psycopg2.connect(TEST_DB_URL)
    conn2.autocommit = True
    c2 = conn2.cursor()
    c2.execute("TRUNCATE intentkeeper_heartbeats CASCADE")
    c2.execute("TRUNCATE intentkeeper_subtasks CASCADE")
    c2.execute("TRUNCATE intentkeeper_intentions CASCADE")
    c2.close()
    conn2.close()
    conn.close()


@pytest.fixture
def ik_clean():
    """IntentKeeper propre pour tests."""
    keeper = IntentKeeper(db_url=TEST_DB_URL)
    yield keeper
    with keeper.db._cursor() as cur:
        cur.execute("TRUNCATE intentkeeper_heartbeats CASCADE")
        cur.execute("TRUNCATE intentkeeper_subtasks CASCADE")
        cur.execute("TRUNCATE intentkeeper_intentions CASCADE")
    keeper.db.close()


class TestQuerySystemMetrics:
    """Test _query_system_metrics."""

    def test_returns_all_keys(self, seeded_db):
        metrics = _query_system_metrics(seeded_db)
        assert "weak_domains" in metrics
        assert "causal_claims" in metrics
        assert "nitzotzot" in metrics
        assert "ohr_ratio" in metrics
        assert "omer_count" in metrics

    def test_weak_domains(self, seeded_db):
        metrics = _query_system_metrics(seeded_db)
        weak = metrics["weak_domains"]
        domains = [d for d, _ in weak]
        assert "qliphoth" in domains
        assert "sefer_yetzirah" in domains
        # gematria (0.85) et tzeruf (0.90) ne sont PAS faibles
        assert "gematria" not in domains
        assert "tzeruf" not in domains

    def test_causal_ratio(self, seeded_db):
        metrics = _query_system_metrics(seeded_db)
        assert metrics["causal_claims"]["correlation_ratio"] == 1.0

    def test_omer_count(self, seeded_db):
        metrics = _query_system_metrics(seeded_db)
        assert metrics["omer_count"] == 5


class TestSeedSystemIntentions:
    """Test seed_system_intentions."""

    def test_creates_intentions(self, ik_clean, seeded_db):
        created = ik_clean.seed_system_intentions(TEST_DB_URL)
        assert len(created) >= 3  # Au moins domaines faibles, causal, nitzotzot

    def test_idempotent(self, ik_clean, seeded_db):
        first = ik_clean.seed_system_intentions(TEST_DB_URL)
        second = ik_clean.seed_system_intentions(TEST_DB_URL)
        assert len(second) == 0, "Second seed should create nothing"

    def test_creates_subtasks(self, ik_clean, seeded_db):
        ik_clean.seed_system_intentions(TEST_DB_URL)
        active = ik_clean.db.get_active_intentions()
        for intention in active:
            full = ik_clean.db.get_intention(intention.id)
            assert full.total_subtasks > 0, f"'{intention.goal}' has no subtasks"

    def test_weak_domains_subtasks_match(self, ik_clean, seeded_db):
        ik_clean.seed_system_intentions(TEST_DB_URL)
        metrics = _query_system_metrics(seeded_db)
        weak_count = len(metrics["weak_domains"])

        for intention in ik_clean.db.get_active_intentions():
            if "domaines faibles" in intention.goal:
                assert intention.total_subtasks == weak_count
                break
        else:
            pytest.fail("No 'domaines faibles' intention found")


class TestRefreshProgress:
    """Test refresh_progress_from_state."""

    def test_updates_nitzotzot_progress(self, ik_clean, seeded_db):
        ik_clean.seed_system_intentions(TEST_DB_URL)
        ik_clean.refresh_progress_from_state(TEST_DB_URL)

        for intention in ik_clean.db.get_active_intentions():
            if "Nitzotzot" in intention.goal:
                # 15 nitzotzot / 288 = ~0.052
                assert intention.progress > 0
                assert intention.progress == round(15 / 288, 3)
                break
        else:
            pytest.fail("No Nitzotzot intention found")

    def test_omer_progress(self, ik_clean, seeded_db):
        ik_clean.seed_system_intentions(TEST_DB_URL)
        ik_clean.refresh_progress_from_state(TEST_DB_URL)

        for intention in ik_clean.db.get_active_intentions():
            if "Omer" in intention.goal:
                assert intention.progress == round(5 / 49, 3)
                break
        else:
            pytest.fail("No Omer intention found")
