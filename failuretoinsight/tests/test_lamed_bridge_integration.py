"""Tests d'intégration — recycleurs daemon vers FailureToInsight.

Couvre les deux chemins de la chaîne Lamed (Sprint 2) :
  - _recycle_rejections_to_fti : autojudge_experiments → FTI
    (fix Gap 1 : CHECK constraint source_type)
  - _recycle_candidate_rejections_to_fti : candidate_insights → FTI
    (fix Gap 2 : path inexistant pour InsightForge)

Les tests injectent un rejet synthétique, appellent le recycleur
directement (mode sync, pas d'attente du cycle daemon), et vérifient
la création d'une failuretoinsight_analysis + de ses Nitzotzot.
"""
from __future__ import annotations

import uuid

import pytest

from daemon_tasks.chokmah import (
    _recycle_candidate_rejections_to_fti,
    _recycle_rejections_to_fti,
    _resolve_fti,
)


# ── Fixtures ─────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _cleanup_after_test():
    """Garantir que candidate_insights + autojudge_experiments sont propres
    après chaque test de ce module — sinon pollution des autres suites."""
    yield
    from pool import get_conn
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE candidate_insights CASCADE")
            cur.execute("TRUNCATE insight_sessions CASCADE")
            cur.execute("TRUNCATE autojudge_experiments CASCADE")
        conn.commit()


# ── Helpers ──────────────────────────────────────────────────


def _truncate_insightforge(conn):
    with conn.cursor() as cur:
        cur.execute("TRUNCATE candidate_insights CASCADE")
        cur.execute("TRUNCATE insight_sessions CASCADE")
    conn.commit()


def _truncate_autojudge(conn):
    """Nettoyer autojudge_experiments + garantir le domaine FK."""
    with conn.cursor() as cur:
        cur.execute("TRUNCATE autojudge_experiments CASCADE")
        # FK sur autojudge_domains : s'assurer que hitbonenut_eval existe
        cur.execute(
            """
            INSERT INTO autojudge_domains (id, display_name, loss_function)
            VALUES ('hitbonenut_eval', 'Test', 'dummy')
            ON CONFLICT (id) DO NOTHING
            """
        )
    conn.commit()


def _insert_candidate_rejection(
    conn, description="Un candidat douteux", domain="cross_domain",
    reason="Triple validation failed: Binah: Correlation only (confidence=0.35)",
):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO candidate_insights
              (description, domain, source_module, status, rejection_reason,
               novelty_score, confidence)
            VALUES (%s, %s, 'test', 'rejected', %s, 0.8, 0.4)
            RETURNING id
            """,
            (description, domain, reason),
        )
        ci_id = cur.fetchone()[0]
    conn.commit()
    return ci_id


def _insert_autojudge_rejection(
    conn, question="Question faible",
    response="Réponse superficielle", domain_id="hitbonenut_eval",
    hypothesis="Rendre la réponse plus profonde",
):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO autojudge_experiments
              (domain_id, hypothesis, original_content, modified_content,
               decision, score_overall)
            VALUES (%s, %s, %s, %s, 'rejected', 0.25)
            RETURNING id
            """,
            (domain_id, hypothesis, question, response),
        )
        ae_id = cur.fetchone()[0]
    conn.commit()
    return ae_id


# ── _recycle_candidate_rejections_to_fti ────────────────────


class TestCandidateRejectionRecycler:
    """Gap 2 — InsightForge rejets doivent atteindre FTI."""

    def test_no_fti_returns_zero(self):
        """Sans FTI dans l'arbre, le recycleur n'insère rien."""
        assert _recycle_candidate_rejections_to_fti({}) == 0

    def test_single_rejection_produces_analysis_and_insight(self, fti):
        """Un rejet InsightForge → 1 analyse FTI + ≥ 1 Nitzotz."""
        from pool import get_conn

        with get_conn() as conn:
            _truncate_insightforge(conn)
            ci_id = _insert_candidate_rejection(conn)

        tree = {"lamed": fti}
        recycled = _recycle_candidate_rejections_to_fti(tree, batch_limit=5)
        assert recycled == 1

        # L'analyse porte source_type='hypothesis' + source_id=ci.id
        analyses = fti.db.get_all_analyses()
        assert len(analyses) == 1
        analysis = analyses[0]
        assert analysis.source_type == "hypothesis"
        assert analysis.source_id == ci_id
        assert "rejected" in analysis.description.lower() or \
               "rejeté" in analysis.description.lower()

        # Nitzotzot extraits
        insights = fti.db.get_all_insights()
        assert len(insights) >= 1

    def test_idempotence_no_double_insert(self, fti):
        """Rappeler le recycleur ne recrée pas l'analyse."""
        from pool import get_conn

        with get_conn() as conn:
            _truncate_insightforge(conn)
            _insert_candidate_rejection(conn)

        tree = {"lamed": fti}
        first = _recycle_candidate_rejections_to_fti(tree, batch_limit=5)
        second = _recycle_candidate_rejections_to_fti(tree, batch_limit=5)

        assert first == 1
        assert second == 0, "2e passage ne doit rien ré-insérer"

        analyses = fti.db.get_all_analyses()
        assert len(analyses) == 1

    def test_batch_limit_respected(self, fti):
        """batch_limit plafonne le nombre de rejets traités par appel."""
        from pool import get_conn

        with get_conn() as conn:
            _truncate_insightforge(conn)
            for i in range(5):
                _insert_candidate_rejection(
                    conn, description=f"Rejet #{i}", domain=f"dom_{i}",
                )

        tree = {"lamed": fti}
        recycled = _recycle_candidate_rejections_to_fti(tree, batch_limit=2)
        assert recycled == 2

        analyses = fti.db.get_all_analyses()
        assert len(analyses) == 2

    def test_only_rejected_are_picked(self, fti):
        """Les candidats 'candidate'/'validated' ne sont pas touchés."""
        from pool import get_conn

        with get_conn() as conn:
            _truncate_insightforge(conn)
            # 1 rejeté + 2 candidates + 1 validated
            _insert_candidate_rejection(conn, description="rejeté")
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO candidate_insights "
                    "(description, status) VALUES ('cand', 'candidate')"
                )
                cur.execute(
                    "INSERT INTO candidate_insights "
                    "(description, status) VALUES ('cand2', 'candidate')"
                )
                cur.execute(
                    "INSERT INTO candidate_insights "
                    "(description, status) VALUES ('ok', 'validated')"
                )
            conn.commit()

        tree = {"lamed": fti}
        recycled = _recycle_candidate_rejections_to_fti(tree, batch_limit=10)
        assert recycled == 1


# ── _recycle_rejections_to_fti (Gap 1 regression) ──────────


class TestAutoJudgeRecyclerAfterFix:
    """Gap 1 — la CHECK constraint ne doit plus rejeter les INSERTs."""

    def test_rejection_inserts_successfully(self, fti):
        """source_type='experiment' passe la CHECK constraint."""
        from pool import get_conn

        with get_conn() as conn:
            _truncate_autojudge(conn)
            ae_id = _insert_autojudge_rejection(conn)

        tree = {"lamed": fti}
        recycled = _recycle_rejections_to_fti(tree, batch_limit=5)
        assert recycled == 1

        analyses = fti.db.get_all_analyses()
        assert len(analyses) == 1
        assert analyses[0].source_type == "experiment"
        assert analyses[0].source_id == ae_id

    def test_idempotence(self, fti):
        """Rappeler ne réinsère pas."""
        from pool import get_conn

        with get_conn() as conn:
            _truncate_autojudge(conn)
            _insert_autojudge_rejection(conn)

        tree = {"lamed": fti}
        first = _recycle_rejections_to_fti(tree, batch_limit=5)
        second = _recycle_rejections_to_fti(tree, batch_limit=5)
        assert first == 1
        assert second == 0


# ── _resolve_fti (helper) ───────────────────────────────────


class TestResolveFti:
    """Le helper de résolution couvre les 3 emplacements possibles."""

    def test_direct_lamed_key(self, fti):
        assert _resolve_fti({"lamed": fti}) is fti

    def test_alias_failuretoinsight(self, fti):
        assert _resolve_fti({"failuretoinsight": fti}) is fti

    def test_via_gevurah_fti_attr(self, fti):
        class Gev:
            pass
        g = Gev()
        g.fti = fti
        assert _resolve_fti({"gevurah": g}) is fti

    def test_via_gevurah_lamed_bridge(self, fti):
        class Bridge:
            def __init__(self, f):
                self.fti = f
        class Gev:
            pass
        g = Gev()
        g.lamed = Bridge(fti)
        assert _resolve_fti({"gevurah": g}) is fti

    def test_empty_tree_returns_none(self):
        assert _resolve_fti({}) is None
