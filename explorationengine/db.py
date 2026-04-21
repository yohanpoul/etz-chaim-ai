"""Accès base de données — Yesod de Chesed."""

from __future__ import annotations

from contextlib import contextmanager

from uuid import UUID

import psycopg2
import psycopg2.extras

from pool import get_conn, init_pool

from explorationengine.models import Connection, Exploration

psycopg2.extras.register_uuid()


def _row_to_exploration(row: dict) -> Exploration:
    return Exploration(
        id=row["id"],
        seed_query=row["seed_query"],
        seed_domain=row["seed_domain"],
        target_domains=row.get("target_domains") or [],
        connections_found=row.get("connections_found", 0),
        novel_connections=row.get("novel_connections", 0),
        max_connections=row.get("max_connections", 50),
        max_duration_seconds=row.get("max_duration_seconds", 600),
        novelty_threshold=row.get("novelty_threshold", 0.3),
        status=row.get("status", "running"),
        created_at=row.get("created_at"),
        completed_at=row.get("completed_at"),
    )


def _row_to_connection(row: dict) -> Connection:
    return Connection(
        id=row["id"],
        exploration_id=row.get("exploration_id"),
        concept_a=row["concept_a"],
        domain_a=row["domain_a"],
        concept_b=row["concept_b"],
        domain_b=row["domain_b"],
        connection_type=row.get("connection_type"),
        description=row["description"],
        novelty_score=row.get("novelty_score"),
        relevance_score=row.get("relevance_score"),
        confidence=row.get("confidence"),
        epistememory_id=row.get("epistememory_id"),
        created_at=row.get("created_at"),
    )


class ExplorationEngineDB:
    """CRUD pour ExplorationEngine — Chesed persiste ses découvertes."""

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

    # --- Explorations ---

    def create_exploration(
        self,
        seed_query: str,
        seed_domain: str,
        target_domains: list[str] | None = None,
        max_connections: int = 50,
        max_duration_seconds: int = 600,
        novelty_threshold: float = 0.3,
    ) -> Exploration:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """INSERT INTO explorationengine_explorations
                   (seed_query, seed_domain, target_domains,
                    max_connections, max_duration_seconds, novelty_threshold)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   RETURNING *""",
                (seed_query, seed_domain, target_domains or [],
                 max_connections, max_duration_seconds, novelty_threshold),
            )
            return _row_to_exploration(cur.fetchone())

    def get_exploration(self, exploration_id: UUID) -> Exploration | None:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM explorationengine_explorations WHERE id = %s",
                (exploration_id,),
            )
            row = cur.fetchone()
            return _row_to_exploration(row) if row else None

    def complete_exploration(
        self,
        exploration_id: UUID,
        status: str,
        connections_found: int,
        novel_connections: int,
    ) -> Exploration | None:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """UPDATE explorationengine_explorations
                   SET status = %s,
                       connections_found = %s,
                       novel_connections = %s,
                       completed_at = NOW()
                   WHERE id = %s RETURNING *""",
                (status, connections_found, novel_connections, exploration_id),
            )
            row = cur.fetchone()
            return _row_to_exploration(row) if row else None

    def get_explorations(
        self,
        seed_domain: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[Exploration]:
        clauses = []
        params: list = []
        if seed_domain:
            clauses.append("seed_domain = %s")
            params.append(seed_domain)
        if status:
            clauses.append("status = %s")
            params.append(status)

        where = "WHERE " + " AND ".join(clauses) if clauses else ""
        params.append(limit)

        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"SELECT * FROM explorationengine_explorations {where} "
                f"ORDER BY created_at DESC LIMIT %s",
                params,
            )
            return [_row_to_exploration(r) for r in cur.fetchall()]

    # --- Connections ---

    def create_connection(
        self,
        exploration_id: UUID,
        concept_a: str,
        domain_a: str,
        concept_b: str,
        domain_b: str,
        connection_type: str,
        description: str,
        novelty_score: float | None = None,
        relevance_score: float | None = None,
        confidence: float | None = None,
        epistememory_id: UUID | None = None,
    ) -> Connection:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """INSERT INTO explorationengine_connections
                   (exploration_id, concept_a, domain_a, concept_b, domain_b,
                    connection_type, description,
                    novelty_score, relevance_score, confidence, epistememory_id)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING *""",
                (exploration_id, concept_a, domain_a, concept_b, domain_b,
                 connection_type, description,
                 novelty_score, relevance_score, confidence, epistememory_id),
            )
            return _row_to_connection(cur.fetchone())

    def get_connections(
        self,
        exploration_id: UUID | None = None,
        domain_a: str | None = None,
        domain_b: str | None = None,
        connection_type: str | None = None,
        min_novelty: float | None = None,
        limit: int = 100,
    ) -> list[Connection]:
        clauses = []
        params: list = []
        if exploration_id:
            clauses.append("exploration_id = %s")
            params.append(exploration_id)
        if domain_a:
            clauses.append("(domain_a = %s OR domain_b = %s)")
            params.extend([domain_a, domain_a])
        if domain_b:
            clauses.append("(domain_a = %s OR domain_b = %s)")
            params.extend([domain_b, domain_b])
        if connection_type:
            clauses.append("connection_type = %s")
            params.append(connection_type)
        if min_novelty is not None:
            clauses.append("novelty_score >= %s")
            params.append(min_novelty)

        where = "WHERE " + " AND ".join(clauses) if clauses else ""
        params.append(limit)

        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"SELECT * FROM explorationengine_connections {where} "
                f"ORDER BY novelty_score DESC NULLS LAST LIMIT %s",
                params,
            )
            return [_row_to_connection(r) for r in cur.fetchall()]

    def count_connections_by_type(
        self, exploration_id: UUID | None = None
    ) -> dict[str, int]:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if exploration_id:
                cur.execute(
                    """SELECT connection_type, COUNT(*) as cnt
                       FROM explorationengine_connections
                       WHERE exploration_id = %s
                       GROUP BY connection_type""",
                    (exploration_id,),
                )
            else:
                cur.execute(
                    """SELECT connection_type, COUNT(*) as cnt
                       FROM explorationengine_connections
                       GROUP BY connection_type"""
                )
            return {r["connection_type"]: r["cnt"] for r in cur.fetchall()}

    # --- Analogies ---

    def create_analogy(
        self,
        domain_a: str,
        domain_b: str,
        pattern: str,
        explanation: str,
        strength: float = 0.5,
        source_connection_ids: list[UUID] | None = None,
        generated_by: str = "heuristic",
    ) -> dict:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """INSERT INTO explorationengine_analogies
                   (domain_a, domain_b, pattern, explanation, strength,
                    source_connection_ids, generated_by)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)
                   RETURNING *""",
                (domain_a, domain_b, pattern, explanation, strength,
                 source_connection_ids or [], generated_by),
            )
            return dict(cur.fetchone())

    def get_analogies(
        self,
        domain_a: str | None = None,
        domain_b: str | None = None,
        min_strength: float | None = None,
        limit: int = 50,
    ) -> list[dict]:
        clauses = []
        params: list = []
        if domain_a:
            clauses.append("(domain_a = %s OR domain_b = %s)")
            params.extend([domain_a, domain_a])
        if domain_b:
            clauses.append("(domain_a = %s OR domain_b = %s)")
            params.extend([domain_b, domain_b])
        if min_strength is not None:
            clauses.append("strength >= %s")
            params.append(min_strength)

        where = "WHERE " + " AND ".join(clauses) if clauses else ""
        params.append(limit)

        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"SELECT * FROM explorationengine_analogies {where} "
                f"ORDER BY strength DESC LIMIT %s",
                params,
            )
            return [dict(r) for r in cur.fetchall()]

    def count_analogies(self) -> int:
        with self._cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM explorationengine_analogies")
            return cur.fetchone()[0]

    def analogy_exists(self, domain_a: str, domain_b: str, pattern: str) -> bool:
        """Vérifie si une analogie similaire existe déjà (anti-doublon)."""
        with self._cursor() as cur:
            cur.execute(
                """SELECT 1 FROM explorationengine_analogies
                   WHERE ((domain_a = %s AND domain_b = %s)
                       OR (domain_a = %s AND domain_b = %s))
                     AND pattern = %s
                   LIMIT 1""",
                (domain_a, domain_b, domain_b, domain_a, pattern),
            )
            return cur.fetchone() is not None

    def get_novelty_stats(self, exploration_id: UUID) -> dict:
        """Stats de nouveauté pour une exploration (anti-Gamchicoth)."""
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT COUNT(*) as total,
                          AVG(novelty_score) as avg_novelty,
                          MIN(novelty_score) as min_novelty,
                          MAX(novelty_score) as max_novelty,
                          COUNT(*) FILTER (WHERE novelty_score >= 0.3) as novel_count
                   FROM explorationengine_connections
                   WHERE exploration_id = %s AND novelty_score IS NOT NULL""",
                (exploration_id,),
            )
            row = cur.fetchone()
            return {
                "total": row["total"] or 0,
                "avg_novelty": float(row["avg_novelty"] or 0),
                "min_novelty": float(row["min_novelty"] or 0),
                "max_novelty": float(row["max_novelty"] or 0),
                "novel_count": row["novel_count"] or 0,
            }
