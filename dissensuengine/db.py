"""Accès base de données — Yesod de Tiferet."""

from __future__ import annotations

from contextlib import contextmanager

import json
from datetime import datetime
from uuid import UUID

import psycopg2
import psycopg2.extras

from pool import get_conn, init_pool

from dissensuengine.models import (
    Conclusion,
    ConsistencyReport,
    OpenQuestion,
    Synthesis,
    Tension,
)

psycopg2.extras.register_uuid()


def _row_to_conclusion(row: dict) -> Conclusion:
    meta = row.get("metadata")
    if isinstance(meta, str):
        meta = json.loads(meta)
    return Conclusion(
        id=row["id"],
        content=row["content"],
        source_label=row["source_label"],
        source_type=row["source_type"],
        domain=row.get("domain"),
        confidence=row["confidence"],
        metadata=meta,
        created_at=row.get("created_at"),
    )


def _row_to_tension(row: dict) -> Tension:
    return Tension(
        id=row["id"],
        conclusion_a_id=row["conclusion_a_id"],
        conclusion_b_id=row["conclusion_b_id"],
        tension_type=row["tension_type"],
        divergence_score=row["divergence_score"],
        description=row.get("description"),
        resolution_status=row["resolution_status"],
        resolved_by=row.get("resolved_by"),
        created_at=row.get("created_at"),
    )


def _row_to_synthesis(row: dict) -> Synthesis:
    sources = row["sources_used"]
    if isinstance(sources, str):
        sources = json.loads(sources)
    return Synthesis(
        id=row["id"],
        mode=row["mode"],
        content=row["content"],
        sources_used=sources if sources else [],
        source_coverage=row["source_coverage"],
        max_divergence=row["max_divergence"],
        confidence=row["confidence"],
        domain=row.get("domain"),
        epistememory_id=row.get("epistememory_id"),
        created_at=row.get("created_at"),
    )


def _row_to_open_question(row: dict) -> OpenQuestion:
    return OpenQuestion(
        id=row["id"],
        tension_id=row["tension_id"],
        question=row["question"],
        missing_evidence=row.get("missing_evidence"),
        priority=row["priority"],
        domain=row.get("domain"),
        created_at=row.get("created_at"),
        resolved_at=row.get("resolved_at"),
    )


class DissensuEngineDB:
    """Couche d'accès aux données pour Tiferet."""

    def __init__(self, db_url: str):
        self.db_url = db_url
        init_pool(db_url)  # idempotent

    def close(self):
        pass  # pool gère les connexions

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

    # --- Conclusions ---

    def create_conclusion(
        self,
        content: str,
        source_label: str,
        source_type: str,
        domain: str | None = None,
        confidence: float = 0.5,
        metadata: dict | None = None,
    ) -> Conclusion:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """INSERT INTO dissensuengine_conclusions
                   (content, source_label, source_type, domain, confidence, metadata)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   RETURNING *""",
                (content, source_label, source_type, domain, confidence,
                 json.dumps(metadata) if metadata else None),
            )
            return _row_to_conclusion(cur.fetchone())

    def get_conclusion(self, conclusion_id: UUID) -> Conclusion | None:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM dissensuengine_conclusions WHERE id = %s",
                (conclusion_id,),
            )
            row = cur.fetchone()
            return _row_to_conclusion(row) if row else None

    def get_all_conclusions(self, domain: str | None = None) -> list[Conclusion]:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if domain:
                cur.execute(
                    """SELECT * FROM dissensuengine_conclusions
                       WHERE domain = %s ORDER BY created_at""",
                    (domain,),
                )
            else:
                cur.execute(
                    "SELECT * FROM dissensuengine_conclusions ORDER BY created_at"
                )
            return [_row_to_conclusion(row) for row in cur.fetchall()]

    # --- Tensions ---

    def create_tension(
        self,
        conclusion_a_id: UUID,
        conclusion_b_id: UUID,
        tension_type: str,
        divergence_score: float,
        description: str | None = None,
    ) -> Tension:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """INSERT INTO dissensuengine_tensions
                   (conclusion_a_id, conclusion_b_id, tension_type,
                    divergence_score, description)
                   VALUES (%s, %s, %s, %s, %s)
                   ON CONFLICT (conclusion_a_id, conclusion_b_id) DO UPDATE
                   SET tension_type = EXCLUDED.tension_type,
                       divergence_score = EXCLUDED.divergence_score,
                       description = EXCLUDED.description
                   RETURNING *""",
                (conclusion_a_id, conclusion_b_id, tension_type,
                 divergence_score, description),
            )
            return _row_to_tension(cur.fetchone())

    def get_tension(self, tension_id: UUID) -> Tension | None:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM dissensuengine_tensions WHERE id = %s",
                (tension_id,),
            )
            row = cur.fetchone()
            return _row_to_tension(row) if row else None

    def get_tensions_for_conclusion(self, conclusion_id: UUID) -> list[Tension]:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT * FROM dissensuengine_tensions
                   WHERE conclusion_a_id = %s OR conclusion_b_id = %s
                   ORDER BY divergence_score DESC""",
                (conclusion_id, conclusion_id),
            )
            return [_row_to_tension(row) for row in cur.fetchall()]

    def get_all_tensions(
        self, status: str | None = None
    ) -> list[Tension]:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if status:
                cur.execute(
                    """SELECT * FROM dissensuengine_tensions
                       WHERE resolution_status = %s
                       ORDER BY divergence_score DESC""",
                    (status,),
                )
            else:
                cur.execute(
                    """SELECT * FROM dissensuengine_tensions
                       ORDER BY divergence_score DESC"""
                )
            return [_row_to_tension(row) for row in cur.fetchall()]

    def resolve_tension(
        self, tension_id: UUID, synthesis_id: UUID, status: str = "resolved"
    ) -> Tension:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """UPDATE dissensuengine_tensions
                   SET resolution_status = %s, resolved_by = %s
                   WHERE id = %s RETURNING *""",
                (status, synthesis_id, tension_id),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Tension {tension_id} not found")
            return _row_to_tension(row)

    def resolve_tensions_for_sources(
        self, source_ids: list[UUID], synthesis_id: UUID
    ) -> int:
        """Résoudre toutes les tensions ouvertes impliquant ces conclusions."""
        if not source_ids:
            return 0
        with self._cursor() as cur:
            cur.execute(
                """UPDATE dissensuengine_tensions
                   SET resolution_status = 'resolved', resolved_by = %s
                   WHERE resolution_status = 'open'
                     AND (conclusion_a_id = ANY(%s) OR conclusion_b_id = ANY(%s))
                   """,
                (synthesis_id, source_ids, source_ids),
            )
            return cur.rowcount

    # --- Syntheses ---

    def create_synthesis(
        self,
        mode: str,
        content: str,
        sources_used: list[UUID],
        source_coverage: float,
        max_divergence: float,
        confidence: float,
        domain: str | None = None,
        epistememory_id: UUID | None = None,
    ) -> Synthesis:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """INSERT INTO dissensuengine_syntheses
                   (mode, content, sources_used, source_coverage,
                    max_divergence, confidence, domain, epistememory_id)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING *""",
                (mode, content, sources_used, source_coverage,
                 max_divergence, confidence, domain, epistememory_id),
            )
            return _row_to_synthesis(cur.fetchone())

    def get_synthesis(self, synthesis_id: UUID) -> Synthesis | None:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM dissensuengine_syntheses WHERE id = %s",
                (synthesis_id,),
            )
            row = cur.fetchone()
            return _row_to_synthesis(row) if row else None

    def get_all_syntheses(
        self, mode: str | None = None, domain: str | None = None
    ) -> list[Synthesis]:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            conditions = []
            params = []
            if mode:
                conditions.append("mode = %s")
                params.append(mode)
            if domain:
                conditions.append("domain = %s")
                params.append(domain)
            where = " WHERE " + " AND ".join(conditions) if conditions else ""
            cur.execute(
                f"SELECT * FROM dissensuengine_syntheses{where} ORDER BY created_at",
                params,
            )
            return [_row_to_synthesis(row) for row in cur.fetchall()]

    # --- Open Questions ---

    def create_open_question(
        self,
        tension_id: UUID,
        question: str,
        missing_evidence: str | None = None,
        priority: str = "medium",
        domain: str | None = None,
    ) -> OpenQuestion:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """INSERT INTO dissensuengine_open_questions
                   (tension_id, question, missing_evidence, priority, domain)
                   VALUES (%s, %s, %s, %s, %s)
                   RETURNING *""",
                (tension_id, question, missing_evidence, priority, domain),
            )
            return _row_to_open_question(cur.fetchone())

    def get_open_questions(
        self, domain: str | None = None, unresolved_only: bool = True
    ) -> list[OpenQuestion]:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            conditions = []
            params = []
            if unresolved_only:
                conditions.append("resolved_at IS NULL")
            if domain:
                conditions.append("domain = %s")
                params.append(domain)
            where = " WHERE " + " AND ".join(conditions) if conditions else ""
            cur.execute(
                f"""SELECT * FROM dissensuengine_open_questions{where}
                    ORDER BY CASE priority
                        WHEN 'critical' THEN 0 WHEN 'high' THEN 1
                        WHEN 'medium' THEN 2 WHEN 'low' THEN 3
                    END, created_at""",
                params,
            )
            return [_row_to_open_question(row) for row in cur.fetchall()]

    def resolve_question(self, question_id: UUID) -> OpenQuestion:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """UPDATE dissensuengine_open_questions
                   SET resolved_at = NOW()
                   WHERE id = %s RETURNING *""",
                (question_id,),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Question {question_id} not found")
            return _row_to_open_question(row)

    def get_tensions_needing_escalation(
        self,
        min_severity: float = 0.7,
        min_age_days: int = 7,
    ) -> list[Tension]:
        """Retourne les tensions ouvertes qui méritent escalade en open_question.

        Critères (OR) :
          - divergence_score >= min_severity (tensions graves)
          - ouvertes depuis >= min_age_days (tensions stagnantes)

        Exclut les tensions déjà liées à une open_question non résolue.
        """
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT t.*
                   FROM dissensuengine_tensions t
                   WHERE t.resolution_status = 'open'
                     AND (
                         t.divergence_score >= %s
                         OR t.created_at <= NOW() - INTERVAL '%s days'
                     )
                     AND NOT EXISTS (
                         SELECT 1 FROM dissensuengine_open_questions oq
                         WHERE oq.tension_id = t.id
                           AND oq.resolved_at IS NULL
                     )
                   ORDER BY t.divergence_score DESC""",
                (min_severity, min_age_days),
            )
            return [_row_to_tension(row) for row in cur.fetchall()]

    def purge_trivial_tensions(self, max_divergence: float = 0.3) -> int:
        """Marquer les tensions triviales ouvertes comme résolues.

        Soft-delete : les paires restent en base pour empêcher le daemon
        de les recréer au cycle suivant (contrainte UNIQUE).
        """
        with self._cursor() as cur:
            cur.execute(
                """UPDATE dissensuengine_tensions
                   SET resolution_status = 'resolved'
                   WHERE resolution_status = 'open'
                     AND divergence_score < %s""",
                (max_divergence,),
            )
            return cur.rowcount

    def get_existing_tension_pair_ids(
        self, conclusion_ids: list[UUID]
    ) -> set[tuple[UUID, UUID]]:
        """Retourne les paires (a_id, b_id) ayant déjà un enregistrement de tension."""
        if not conclusion_ids:
            return set()
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT conclusion_a_id, conclusion_b_id
                   FROM dissensuengine_tensions
                   WHERE conclusion_a_id = ANY(%s)
                     AND conclusion_b_id = ANY(%s)""",
                (conclusion_ids, conclusion_ids),
            )
            return {
                (row["conclusion_a_id"], row["conclusion_b_id"])
                for row in cur.fetchall()
            }

    def get_domains_with_open_tensions(self) -> list[str]:
        """Domaines ayant des tensions ouvertes, triés par nombre décroissant."""
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT c.domain, COUNT(t.id) as cnt
                   FROM dissensuengine_tensions t
                   JOIN dissensuengine_conclusions c ON c.id = t.conclusion_a_id
                   WHERE t.resolution_status = 'open'
                     AND c.domain IS NOT NULL
                   GROUP BY c.domain
                   ORDER BY cnt DESC"""
            )
            return [row["domain"] for row in cur.fetchall()]

    # --- Aggregates ---

    def count_tensions_by_type(self) -> dict[str, int]:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT tension_type, COUNT(*) AS count
                   FROM dissensuengine_tensions
                   GROUP BY tension_type ORDER BY count DESC"""
            )
            return {row["tension_type"]: row["count"] for row in cur.fetchall()}

    def count_syntheses_by_mode(self) -> dict[str, int]:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT mode, COUNT(*) AS count
                   FROM dissensuengine_syntheses
                   GROUP BY mode ORDER BY count DESC"""
            )
            return {row["mode"]: row["count"] for row in cur.fetchall()}

    def count_open_tensions_by_domain(self) -> dict[str, int]:
        """Count open tensions per domain (via conclusion_a's domain)."""
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT c.domain, COUNT(t.id) AS cnt
                   FROM dissensuengine_tensions t
                   JOIN dissensuengine_conclusions c ON c.id = t.conclusion_a_id
                   WHERE t.resolution_status = 'open'
                     AND c.domain IS NOT NULL
                   GROUP BY c.domain"""
            )
            return {row["domain"]: row["cnt"] for row in cur.fetchall()}

    def count_syntheses_by_domain(self) -> dict[str, int]:
        """Count syntheses per domain."""
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT domain, COUNT(*) AS cnt
                   FROM dissensuengine_syntheses
                   WHERE domain IS NOT NULL
                   GROUP BY domain"""
            )
            return {row["domain"]: row["cnt"] for row in cur.fetchall()}
