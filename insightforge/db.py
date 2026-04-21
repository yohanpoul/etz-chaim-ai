"""Accès base de données — Yesod de Chokmah."""

from __future__ import annotations

from contextlib import contextmanager
from uuid import UUID

import psycopg2
import psycopg2.extras

from pool import get_conn, init_pool

from insightforge.models import (
    CandidateInsight,
    InsightSession,
    NoveltyAssessment,
)

psycopg2.extras.register_uuid()


def _row_to_session(row: dict) -> InsightSession:
    return InsightSession(
        id=row["id"],
        question=row["question"],
        domain=row.get("domain", ""),
        status=row.get("status", "active"),
        modules_consulted=row.get("modules_consulted") or [],
        total_candidates=row.get("total_candidates", 0),
        insights_found=row.get("insights_found", 0),
        rejected_count=row.get("rejected_count", 0),
        pearl_level=row.get("pearl_level", "association"),
        created_at=row.get("created_at"),
        completed_at=row.get("completed_at"),
    )


def _row_to_candidate(row: dict) -> CandidateInsight:
    return CandidateInsight(
        id=row["id"],
        session_id=row.get("session_id"),
        description=row["description"],
        source_module=row.get("source_module", ""),
        domain=row.get("domain", ""),
        novelty_score=row.get("novelty_score", 0.0),
        confidence=row.get("confidence", 0.5),
        status=row.get("status", "candidate"),
        rejection_reason=row.get("rejection_reason") or "",
        binah_validated=row.get("binah_validated", False),
        gevurah_validated=row.get("gevurah_validated", False),
        daat_validated=row.get("daat_validated", False),
        connects_domains=row.get("connects_domains") or [],
        source_connections=row.get("source_connections") or [],
        created_at=row.get("created_at"),
    )


def _row_to_novelty(row: dict) -> NoveltyAssessment:
    return NoveltyAssessment(
        id=row["id"],
        candidate_id=row.get("candidate_id"),
        is_genuinely_new=row.get("is_genuinely_new", False),
        already_known=row.get("already_known", False),
        is_reformulation=row.get("is_reformulation", False),
        is_trivial=row.get("is_trivial", False),
        is_cross_domain=row.get("is_cross_domain", False),
        novelty_score=row.get("novelty_score", 0.0),
        reasoning=row.get("reasoning", ""),
        created_at=row.get("created_at"),
    )


class InsightDB:
    """CRUD pour InsightForge — Chokmah persiste ses insights.

    Emprunte les connexions au pool centralisé (pool.py).
    """

    def __init__(self, db_url: str):
        self.db_url = db_url
        init_pool(db_url)  # idempotent

    def close(self):
        pass  # Pool gère les connexions

    @contextmanager
    def _cursor(self, cursor_factory=None):
        """Emprunte une conn + cursor au pool, puis rend."""
        with get_conn() as conn:
            if cursor_factory:
                with conn.cursor(cursor_factory=cursor_factory) as cur:
                    yield cur
            else:
                with conn.cursor() as cur:
                    yield cur

    # --- Sessions ---

    def save_session(self, session: InsightSession) -> InsightSession:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """INSERT INTO insight_sessions
                   (question, domain, status, modules_consulted,
                    total_candidates, insights_found, rejected_count,
                    pearl_level)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING *""",
                (
                    session.question, session.domain, session.status,
                    session.modules_consulted,
                    session.total_candidates, session.insights_found,
                    session.rejected_count, session.pearl_level,
                ),
            )
            return _row_to_session(cur.fetchone())

    def get_session(self, session_id: UUID) -> InsightSession | None:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM insight_sessions WHERE id = %s",
                (session_id,),
            )
            row = cur.fetchone()
            return _row_to_session(row) if row else None

    def get_sessions(
        self, status: str | None = None, limit: int = 50,
    ) -> list[InsightSession]:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if status:
                cur.execute(
                    "SELECT * FROM insight_sessions WHERE status = %s "
                    "ORDER BY created_at DESC LIMIT %s",
                    (status, limit),
                )
            else:
                cur.execute(
                    "SELECT * FROM insight_sessions "
                    "ORDER BY created_at DESC LIMIT %s",
                    (limit,),
                )
            return [_row_to_session(r) for r in cur.fetchall()]

    def update_session(self, session: InsightSession) -> InsightSession | None:
        if session.id is None:
            return None
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """UPDATE insight_sessions
                   SET status = %s, modules_consulted = %s,
                       total_candidates = %s, insights_found = %s,
                       rejected_count = %s, pearl_level = %s,
                       completed_at = %s
                   WHERE id = %s RETURNING *""",
                (
                    session.status, session.modules_consulted,
                    session.total_candidates, session.insights_found,
                    session.rejected_count, session.pearl_level,
                    session.completed_at, session.id,
                ),
            )
            row = cur.fetchone()
            return _row_to_session(row) if row else None

    # --- Candidates ---

    def save_candidate(self, candidate: CandidateInsight) -> CandidateInsight:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """INSERT INTO candidate_insights
                   (session_id, description, source_module, domain,
                    novelty_score, confidence, status, rejection_reason,
                    binah_validated, gevurah_validated, daat_validated,
                    connects_domains, source_connections)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING *""",
                (
                    candidate.session_id, candidate.description,
                    candidate.source_module, candidate.domain,
                    candidate.novelty_score, candidate.confidence,
                    candidate.status, candidate.rejection_reason or None,
                    candidate.binah_validated, candidate.gevurah_validated,
                    candidate.daat_validated,
                    candidate.connects_domains,
                    candidate.source_connections,
                ),
            )
            return _row_to_candidate(cur.fetchone())

    def get_candidates(
        self, session_id: UUID, status: str | None = None,
    ) -> list[CandidateInsight]:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if status:
                cur.execute(
                    "SELECT * FROM candidate_insights "
                    "WHERE session_id = %s AND status = %s "
                    "ORDER BY novelty_score DESC",
                    (session_id, status),
                )
            else:
                cur.execute(
                    "SELECT * FROM candidate_insights "
                    "WHERE session_id = %s ORDER BY novelty_score DESC",
                    (session_id,),
                )
            return [_row_to_candidate(r) for r in cur.fetchall()]

    def update_candidate(self, candidate: CandidateInsight) -> CandidateInsight | None:
        if candidate.id is None:
            return None
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """UPDATE candidate_insights
                   SET status = %s, novelty_score = %s, confidence = %s,
                       rejection_reason = %s,
                       binah_validated = %s, gevurah_validated = %s,
                       daat_validated = %s
                   WHERE id = %s RETURNING *""",
                (
                    candidate.status, candidate.novelty_score,
                    candidate.confidence, candidate.rejection_reason or None,
                    candidate.binah_validated, candidate.gevurah_validated,
                    candidate.daat_validated, candidate.id,
                ),
            )
            row = cur.fetchone()
            return _row_to_candidate(row) if row else None

    # --- Novelty Assessments ---

    def save_novelty(self, novelty: NoveltyAssessment) -> NoveltyAssessment:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """INSERT INTO novelty_assessments
                   (candidate_id, is_genuinely_new, already_known,
                    is_reformulation, is_trivial, is_cross_domain,
                    novelty_score, reasoning)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING *""",
                (
                    novelty.candidate_id, novelty.is_genuinely_new,
                    novelty.already_known, novelty.is_reformulation,
                    novelty.is_trivial, novelty.is_cross_domain,
                    novelty.novelty_score, novelty.reasoning,
                ),
            )
            return _row_to_novelty(cur.fetchone())

    def get_novelties(self, candidate_id: UUID) -> list[NoveltyAssessment]:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM novelty_assessments "
                "WHERE candidate_id = %s ORDER BY created_at DESC",
                (candidate_id,),
            )
            return [_row_to_novelty(r) for r in cur.fetchall()]
