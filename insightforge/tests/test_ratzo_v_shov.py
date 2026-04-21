"""Tests — Ratzo v'Shov (InsightForge).

Vérifie que les rejets nourrissent la génération suivante :
  - analyze_rejections catégorise correctement
  - build_shov_context produit un contexte utile
  - track_improvement détecte la baisse du taux de rejet
  - Le pipeline intègre le contexte Shov
"""

import subprocess
from pathlib import Path
from uuid import uuid4

import psycopg2
import pytest

from insightforge.ratzo_v_shov import (
    REJECTION_DUPLICATE,
    REJECTION_MAX_REACHED,
    REJECTION_NOT_CAUSAL,
    REJECTION_NOT_NOVEL,
    REJECTION_OTHER,
    REJECTION_TRIVIAL,
    REJECTION_VALIDATION_FAILED,
    RatzoVShov,
    RejectionPattern,
    _categorize_rejection,
)
from tests._psql import require_psql

TEST_DB_URL = "postgresql://localhost/etz_chaim_test"
PROJECT_ROOT = str(Path(__file__).resolve().parents[2])


@pytest.fixture(scope="session", autouse=True)
def apply_schemas():
    """Apply schemas once."""
    conn = psycopg2.connect("postgresql://localhost/postgres")
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = 'etz_chaim_test'")
    if not cur.fetchone():
        cur.execute("CREATE DATABASE etz_chaim_test")
    cur.close()
    conn.close()

    conn = psycopg2.connect(TEST_DB_URL)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
    cur.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")
    cur.close()
    conn.close()

    for schema in [
        "insightforge/schema.sql",
    ]:
        subprocess.run(
            [require_psql(), "-d", "etz_chaim_test",
             "-f", schema],
            cwd=PROJECT_ROOT, check=True, capture_output=True,
        )


@pytest.fixture
def db_conn():
    """Fresh DB connection, truncated after test."""
    conn = psycopg2.connect(TEST_DB_URL)
    conn.autocommit = True
    yield conn
    with conn.cursor() as cur:
        cur.execute("TRUNCATE novelty_assessments CASCADE")
        cur.execute("TRUNCATE candidate_insights CASCADE")
        cur.execute("TRUNCATE insight_sessions CASCADE")
    conn.close()


@pytest.fixture
def ratzo():
    """RatzoVShov instance."""
    return RatzoVShov(db_url=TEST_DB_URL)


def _insert_session(cur, question="test?", total=10, rejected=7, insights=3):
    """Helper: insert a session and return its ID."""
    cur.execute(
        """INSERT INTO insight_sessions
           (question, domain, status, total_candidates, insights_found,
            rejected_count, pearl_level)
           VALUES (%s, 'test', 'completed', %s, %s, %s, 'association')
           RETURNING id""",
        (question, total, insights, rejected),
    )
    return cur.fetchone()[0]


def _insert_candidate(cur, session_id, status="rejected", source="hitbonenut",
                       reason="Not novel: Duplicate of earlier candidate in this batch",
                       domain="test", connects=None):
    """Helper: insert a candidate."""
    connects = connects or ["domain_a", "domain_b"]
    cur.execute(
        """INSERT INTO candidate_insights
           (session_id, description, source_module, domain, status,
            rejection_reason, connects_domains)
           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
        (session_id, f"Candidate from {source}", source, domain,
         status, reason, connects),
    )


# --- Tests de _categorize_rejection ---

class TestCategorizeRejection:

    def test_duplicate(self):
        assert _categorize_rejection(
            "Not novel: Duplicate of earlier candidate in this batch"
        ) == REJECTION_DUPLICATE

    def test_reformulation(self):
        assert _categorize_rejection(
            "Not novel: Reformulation of a previously generated insight"
        ) == REJECTION_DUPLICATE

    def test_max_reached(self):
        assert _categorize_rejection("Max insights reached (5)") == REJECTION_MAX_REACHED

    def test_triple_validation_failed(self):
        assert _categorize_rejection(
            "Triple validation failed: Binah: no causal link"
        ) == REJECTION_VALIDATION_FAILED

    def test_trivial(self):
        assert _categorize_rejection(
            "Not novel: Trivial — too short, low confidence"
        ) == REJECTION_TRIVIAL

    def test_not_novel(self):
        assert _categorize_rejection(
            "Not novel: Already present in existing knowledge base"
        ) == REJECTION_NOT_NOVEL

    def test_other(self):
        assert _categorize_rejection("Something else entirely") == REJECTION_OTHER


# --- Tests de analyze_rejections ---

class TestAnalyzeRejections:

    def test_empty_db(self, ratzo, db_conn):
        """Pas de sessions → pattern vide."""
        pattern = ratzo.analyze_rejections()
        assert pattern.total_rejected == 0
        assert pattern.rejection_rate == 0.0

    def test_basic_analysis(self, ratzo, db_conn):
        """Analyse basique avec des candidats rejetés."""
        with db_conn.cursor() as cur:
            sid = _insert_session(cur, total=5, rejected=3, insights=2)

            # 3 rejetés : 2 doublons, 1 trivial
            _insert_candidate(cur, sid, status="rejected", source="hitbonenut",
                              reason="Not novel: Duplicate of earlier candidate")
            _insert_candidate(cur, sid, status="rejected", source="hitbonenut",
                              reason="Not novel: Duplicate of earlier candidate")
            _insert_candidate(cur, sid, status="rejected", source="data_mine",
                              reason="Not novel: Trivial — too short")
            # 2 insights
            _insert_candidate(cur, sid, status="insight", source="chesed")
            _insert_candidate(cur, sid, status="insight", source="hitbonenut")

        pattern = ratzo.analyze_rejections(session_ids=[sid])
        assert pattern.total_candidates == 5
        assert pattern.total_rejected == 3
        assert pattern.rejection_rate == 0.6
        assert pattern.by_category[REJECTION_DUPLICATE] == 2
        assert pattern.by_category[REJECTION_TRIVIAL] == 1
        assert pattern.by_source["hitbonenut"] == 2
        assert pattern.by_source["data_mine"] == 1

    def test_domain_pairs_tracked(self, ratzo, db_conn):
        """Les paires de domaines rejetées sont trackées."""
        with db_conn.cursor() as cur:
            sid = _insert_session(cur, total=3, rejected=3)
            _insert_candidate(cur, sid, connects=["physics", "biology"],
                              reason="Not novel: Duplicate")
            _insert_candidate(cur, sid, connects=["physics", "biology"],
                              reason="Not novel: Duplicate")
            _insert_candidate(cur, sid, connects=["math", "music"],
                              reason="Not novel: Duplicate")

        pattern = ratzo.analyze_rejections(session_ids=[sid])
        assert "physics↔biology" in pattern.by_domain_pair
        assert pattern.by_domain_pair["physics↔biology"] == 2


# --- Tests de build_shov_context ---

class TestBuildShovContext:

    def test_empty_pattern(self, ratzo):
        """Pattern vide → contexte vide."""
        pattern = RejectionPattern()
        assert ratzo.build_shov_context(pattern) == ""

    def test_duplicate_heavy(self, ratzo):
        """Pattern dominé par les doublons → conseil de diversification."""
        pattern = RejectionPattern(
            total_rejected=10,
            total_candidates=15,
            by_category={REJECTION_DUPLICATE: 8, REJECTION_TRIVIAL: 2},
            by_source={"hitbonenut": 7, "data_mine": 3},
            by_domain_pair={"a↔b": 5, "c↔d": 3},
        )
        context = ratzo.build_shov_context(pattern)
        assert "DIVERSIFIER" in context
        assert "doublons" in context
        assert "hitbonenut" in context
        assert "ÉVITER ces paires" in context

    def test_trivial_advice(self, ratzo):
        """Beaucoup de triviaux → conseil d'approfondissement."""
        pattern = RejectionPattern(
            total_rejected=5,
            total_candidates=10,
            by_category={REJECTION_TRIVIAL: 5},
            by_source={"chesed": 5},
        )
        context = ratzo.build_shov_context(pattern)
        assert "APPROFONDIR" in context

    def test_not_causal_advice(self, ratzo):
        """Non-causaux → conseil de causalité."""
        pattern = RejectionPattern(
            total_rejected=3,
            total_candidates=5,
            by_category={REJECTION_NOT_CAUSAL: 3},
            by_source={"chesed": 3},
        )
        context = ratzo.build_shov_context(pattern)
        assert "causales" in context

    def test_validation_failed_advice(self, ratzo):
        """Échecs de validation → conseil de rigueur."""
        pattern = RejectionPattern(
            total_rejected=4,
            total_candidates=8,
            by_category={REJECTION_VALIDATION_FAILED: 4},
            by_source={"hitbonenut": 4},
        )
        context = ratzo.build_shov_context(pattern)
        assert "rigueur" in context

    def test_worst_source_identified(self, ratzo):
        """La pire source est identifiée."""
        pattern = RejectionPattern(
            total_rejected=6,
            total_candidates=10,
            by_category={REJECTION_DUPLICATE: 6},
            by_source={"hitbonenut": 5, "chesed": 1},
        )
        context = ratzo.build_shov_context(pattern)
        assert "hitbonenut" in context
        assert "5 rejets" in context

    def test_failing_pairs_threshold(self, ratzo):
        """Seules les paires avec >= 3 rejets sont signalées."""
        pattern = RejectionPattern(
            total_rejected=5,
            total_candidates=10,
            by_category={REJECTION_DUPLICATE: 5},
            by_source={"chesed": 5},
            by_domain_pair={"a↔b": 3, "c↔d": 1},
        )
        context = ratzo.build_shov_context(pattern)
        assert "a↔b" in context
        # c↔d n'a que 1 rejet, sous le seuil
        assert "c↔d" not in context


# --- Tests de track_improvement ---

class TestTrackImprovement:

    def test_insufficient_data(self, ratzo, db_conn):
        """Moins de 2 sessions → insufficient_data."""
        result = ratzo.track_improvement()
        assert result["trend"] == "insufficient_data"

    def test_improving_trend(self, ratzo, db_conn):
        """Taux de rejet qui baisse → improving."""
        with db_conn.cursor() as cur:
            # Sessions anciennes : taux élevé
            _insert_session(cur, "old1", total=10, rejected=8, insights=2)
            _insert_session(cur, "old2", total=10, rejected=9, insights=1)
            # Sessions récentes : taux bas
            _insert_session(cur, "new1", total=10, rejected=2, insights=8)
            _insert_session(cur, "new2", total=10, rejected=1, insights=9)

        result = ratzo.track_improvement(n_sessions=4)
        assert result["trend"] == "improving"
        assert result["delta"] < 0

    def test_degrading_trend(self, ratzo, db_conn):
        """Taux de rejet qui monte → degrading."""
        with db_conn.cursor() as cur:
            _insert_session(cur, "old1", total=10, rejected=1, insights=9)
            _insert_session(cur, "old2", total=10, rejected=2, insights=8)
            _insert_session(cur, "new1", total=10, rejected=8, insights=2)
            _insert_session(cur, "new2", total=10, rejected=9, insights=1)

        result = ratzo.track_improvement(n_sessions=4)
        assert result["trend"] == "degrading"
        assert result["delta"] > 0

    def test_stable_trend(self, ratzo, db_conn):
        """Taux stable → stable."""
        with db_conn.cursor() as cur:
            _insert_session(cur, "s1", total=10, rejected=5, insights=5)
            _insert_session(cur, "s2", total=10, rejected=5, insights=5)
            _insert_session(cur, "s3", total=10, rejected=5, insights=5)
            _insert_session(cur, "s4", total=10, rejected=5, insights=5)

        result = ratzo.track_improvement(n_sessions=4)
        assert result["trend"] == "stable"
        assert abs(result["delta"]) <= 0.05


# --- Tests de ratzo_cycle ---

class TestRatzoCycle:

    def test_ratzo_cycle_with_session(self, ratzo, db_conn):
        """ratzo_cycle analyse une session et produit un contexte."""
        with db_conn.cursor() as cur:
            sid = _insert_session(cur, total=6, rejected=4, insights=2)
            _insert_candidate(cur, sid, status="rejected", source="hitbonenut",
                              reason="Not novel: Duplicate of earlier candidate")
            _insert_candidate(cur, sid, status="rejected", source="hitbonenut",
                              reason="Not novel: Duplicate of earlier candidate")
            _insert_candidate(cur, sid, status="rejected", source="data_mine",
                              reason="Not novel: Trivial — too short")
            _insert_candidate(cur, sid, status="rejected", source="chesed",
                              reason="Max insights reached (5)")
            _insert_candidate(cur, sid, status="insight", source="chesed")
            _insert_candidate(cur, sid, status="insight", source="hitbonenut")

        result = ratzo.ratzo_cycle(sid)
        assert result["total_rejected"] == 4
        assert result["total_candidates"] == 6
        assert result["rejection_rate"] > 0.5
        assert result["shov_context"] != ""
        assert "doublons" in result["shov_context"]


# --- Tests d'intégration pipeline ---

class TestPipelineIntegration:

    def test_shov_context_injected_in_session(self):
        """Le contexte Shov est propagé à la session."""
        from insightforge.models import InsightSession
        session = InsightSession(question="test", shov_context="[Shov] guidance")
        assert session.shov_context == "[Shov] guidance"

    def test_orchestrator_accepts_shov(self):
        """L'orchestrator accepte et propage le shov_context."""
        from insightforge.models import InsightSession
        from insightforge.orchestrator import Orchestrator

        orch = Orchestrator()
        session = InsightSession(question="test")
        session = orch.orchestrate(session, shov_context="[Shov] test guidance")
        assert session.shov_context == "[Shov] test guidance"
        assert "shov" in session.modules_consulted

    def test_orchestrator_no_shov_no_module(self):
        """Sans shov_context, le module 'shov' n'est pas ajouté."""
        from insightforge.models import InsightSession
        from insightforge.orchestrator import Orchestrator

        orch = Orchestrator()
        session = InsightSession(question="test")
        session = orch.orchestrate(session, shov_context="")
        assert "shov" not in session.modules_consulted
