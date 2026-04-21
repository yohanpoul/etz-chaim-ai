"""Accès base de données — Yesod du sentier Lamed."""

from __future__ import annotations

import json
import re
from contextlib import contextmanager
from datetime import datetime
from uuid import UUID

import psycopg2
import psycopg2.extras

from pool import get_conn, init_pool

from failuretoinsight.models import (
    FailureAnalysis,
    FailureGraphEdge,
    Insight,
)


# Regex de normalisation pour dedup (Sprint megaclean T5 / Dette 10) :
# collapse whitespace + strip trailing punctuation.
_WHITESPACE_RUN_RE = re.compile(r"\s+")
_TRAILING_PUNCT_RE = re.compile(r"[.,;:!?—\-\s]+$")


def _normalize_content_for_dedup(content: str) -> str:
    """Normaliser un `content` pour la déduplication.

    Transformations (conservatives, lossy contrôlé) :
    1. strip leading/trailing whitespace
    2. collapse internal whitespace runs à un seul espace
    3. strip trailing punctuation (`. , ; : ! ? — -`)
    4. lowercase

    Rationale T5 — Sprint 8b faisait exact-match `content = %s`. Edge cases :
      - "Boucle ..." vs "Boucle ... " (trailing space) → distincts
      - "Boucle ..." vs "BOUCLE ..." (casse) → distincts
      - "stratégie" vs "stratégie." (ponctuation) → distincts
    Ces variations surface régulièrement dans les extractions qliphah.
    Normalisation évite les faux négatifs de dédup.
    """
    s = content.strip()
    s = _WHITESPACE_RUN_RE.sub(" ", s)
    s = _TRAILING_PUNCT_RE.sub("", s)
    return s.lower()

psycopg2.extras.register_uuid()


def _row_to_analysis(row: dict) -> FailureAnalysis:
    ctx = row.get("context")
    if isinstance(ctx, str):
        ctx = json.loads(ctx)
    return FailureAnalysis(
        id=row["id"],
        source_type=row["source_type"],
        source_id=row.get("source_id"),
        description=row["description"],
        qliphah=row["qliphah"],
        severity=row["severity"],
        root_cause=row.get("root_cause"),
        context=ctx,
        domain=row.get("domain"),
        created_at=row.get("created_at"),
    )


def _row_to_insight(row: dict) -> Insight:
    return Insight(
        id=row["id"],
        analysis_id=row["analysis_id"],
        content=row["content"],
        insight_type=row["insight_type"],
        confidence=row["confidence"],
        domain=row.get("domain"),
        epistememory_id=row.get("epistememory_id"),
        created_at=row.get("created_at"),
    )


def _row_to_edge(row: dict) -> FailureGraphEdge:
    return FailureGraphEdge(
        id=row["id"],
        from_analysis_id=row["from_analysis_id"],
        to_analysis_id=row["to_analysis_id"],
        edge_type=row["edge_type"],
        weight=row["weight"],
        created_at=row.get("created_at"),
    )


class FailureToInsightDB:
    """Couche d'accès aux données pour le sentier Lamed."""

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

    # --- Analyses ---

    def create_analysis(
        self,
        source_type: str,
        description: str,
        qliphah: str,
        severity: str,
        source_id: UUID | None = None,
        root_cause: str | None = None,
        context: dict | None = None,
        domain: str | None = None,
    ) -> FailureAnalysis:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """INSERT INTO failuretoinsight_analyses
                   (source_type, source_id, description, qliphah, severity,
                    root_cause, context, domain)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING *""",
                (
                    source_type, source_id, description, qliphah, severity,
                    root_cause, json.dumps(context) if context else None, domain,
                ),
            )
            return _row_to_analysis(cur.fetchone())

    def get_analysis(self, analysis_id: UUID) -> FailureAnalysis | None:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM failuretoinsight_analyses WHERE id = %s",
                (analysis_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            analysis = _row_to_analysis(row)
            analysis.insights = self.get_insights(analysis_id)
            return analysis

    def get_all_analyses(self, domain: str | None = None) -> list[FailureAnalysis]:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if domain:
                cur.execute(
                    """SELECT * FROM failuretoinsight_analyses
                       WHERE domain = %s ORDER BY created_at""",
                    (domain,),
                )
            else:
                cur.execute(
                    "SELECT * FROM failuretoinsight_analyses ORDER BY created_at"
                )
            return [_row_to_analysis(row) for row in cur.fetchall()]

    def get_analyses_by_qliphah(self, qliphah: str) -> list[FailureAnalysis]:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT * FROM failuretoinsight_analyses
                   WHERE qliphah = %s ORDER BY created_at""",
                (qliphah,),
            )
            return [_row_to_analysis(row) for row in cur.fetchall()]

    def get_unextracted(self) -> list[FailureAnalysis]:
        """Analyses sans nitzotzot extraits — échecs non traités."""
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM unextracted_failures ORDER BY created_at")
            return [_row_to_analysis(row) for row in cur.fetchall()]

    def count_by_qliphah(self) -> dict[str, int]:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT qliphah, COUNT(*) AS count
                   FROM failuretoinsight_analyses
                   GROUP BY qliphah ORDER BY count DESC"""
            )
            return {row["qliphah"]: row["count"] for row in cur.fetchall()}

    # --- Insights (Nitzotzot) ---

    def create_insight(
        self,
        analysis_id: UUID,
        content: str,
        insight_type: str,
        confidence: float = 0.5,
        domain: str | None = None,
        epistememory_id: UUID | None = None,
    ) -> Insight:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """INSERT INTO failuretoinsight_insights
                   (analysis_id, content, insight_type, confidence, domain,
                    epistememory_id)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   RETURNING *""",
                (analysis_id, content, insight_type, confidence, domain,
                 epistememory_id),
            )
            return _row_to_insight(cur.fetchone())

    def recent_insight_exists(
        self, content: str, hours: int = 24,
    ) -> bool:
        """Retourne True si un insight avec ce content (normalisé) a été
        créé récemment.

        Sprint 8b fix 2 introduisait la dédup exact-match. Sprint megaclean
        T5 / Dette 10 étend aux edge cases normalisés : whitespace
        (trailing, multiple internal), casse, ponctuation terminale. Voir
        `_normalize_content_for_dedup`.

        Implémentation : charge les N rows de la fenêtre glissante et
        normalise-compare en Python. Préféré à une expression SQL
        compliquée (REGEXP_REPLACE + LOWER + TRIM en WHERE) qui serait
        illisible, et préféré à un index fonctionnel (migration DB
        interdite dans ce sprint). La fenêtre 24h contient ~100-300 rows
        en régime nominal — chargement négligeable.
        """
        normalized_target = _normalize_content_for_dedup(content)
        if not normalized_target:
            return False

        with self._cursor() as cur:
            cur.execute(
                """SELECT content FROM failuretoinsight_insights
                   WHERE created_at > NOW() - make_interval(hours => %s)""",
                (int(hours),),
            )
            rows = cur.fetchall()

        for row in rows:
            stored = row[0] if row else None
            if stored is None:
                continue
            if _normalize_content_for_dedup(stored) == normalized_target:
                return True
        return False

    def get_insights(self, analysis_id: UUID) -> list[Insight]:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT * FROM failuretoinsight_insights
                   WHERE analysis_id = %s ORDER BY created_at""",
                (analysis_id,),
            )
            return [_row_to_insight(row) for row in cur.fetchall()]

    def get_all_insights(self, domain: str | None = None) -> list[Insight]:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if domain:
                cur.execute(
                    """SELECT * FROM failuretoinsight_insights
                       WHERE domain = %s ORDER BY created_at""",
                    (domain,),
                )
            else:
                cur.execute(
                    "SELECT * FROM failuretoinsight_insights ORDER BY created_at"
                )
            return [_row_to_insight(row) for row in cur.fetchall()]

    # --- Graph edges ---

    def create_edge(
        self,
        from_id: UUID,
        to_id: UUID,
        edge_type: str,
        weight: float = 1.0,
    ) -> FailureGraphEdge:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """INSERT INTO failuretoinsight_graph_edges
                   (from_analysis_id, to_analysis_id, edge_type, weight)
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT (from_analysis_id, to_analysis_id, edge_type) DO UPDATE
                   SET weight = EXCLUDED.weight
                   RETURNING *""",
                (from_id, to_id, edge_type, weight),
            )
            return _row_to_edge(cur.fetchone())

    def get_edges(self, analysis_id: UUID | None = None) -> list[FailureGraphEdge]:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if analysis_id:
                cur.execute(
                    """SELECT * FROM failuretoinsight_graph_edges
                       WHERE from_analysis_id = %s OR to_analysis_id = %s
                       ORDER BY created_at""",
                    (analysis_id, analysis_id),
                )
            else:
                cur.execute(
                    "SELECT * FROM failuretoinsight_graph_edges ORDER BY created_at"
                )
            return [_row_to_edge(row) for row in cur.fetchall()]

    def get_all_edges(self) -> list[FailureGraphEdge]:
        return self.get_edges(analysis_id=None)
