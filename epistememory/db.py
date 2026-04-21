"""Interface PostgreSQL/pgvector — Yesod-de-Yesod : la fondation de la fondation."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import psycopg2
import psycopg2.extras
from pgvector.psycopg2 import register_vector

from .models import (
    EpistemicStatus,
    GCReport,
    MemoryEntry,
    MemoryStats,
    SourceSephirah,
)

# Register UUID adapter
psycopg2.extras.register_uuid()


def _row_to_entry(row: dict) -> MemoryEntry:
    """Convert a database row to a MemoryEntry."""
    return MemoryEntry(
        id=row["id"],
        content=row["content"],
        source_sephirah=SourceSephirah(row["source_sephirah"]),
        confidence=row["confidence"],
        epistemic_status=EpistemicStatus(row["epistemic_status"]),
        created_at=row["created_at"],
        last_accessed=row.get("last_accessed"),
        access_count=row.get("access_count", 0),
        domain=row.get("domain"),
        tags=row.get("tags") or [],
        contradicts=[UUID(str(u)) for u in (row.get("contradicts") or [])],
        supports=[UUID(str(u)) for u in (row.get("supports") or [])],
        supersedes=row.get("supersedes"),
        superseded_by=row.get("superseded_by"),
        ttl_days=row.get("ttl_days"),
        expires_at=row.get("expires_at"),
        source_detail=row.get("source_detail"),
        similarity=row.get("similarity"),
    )


class Database:
    """Interface directe à PostgreSQL + pgvector.

    Utilise le pool centralisé (pool.py) au lieu de créer des connexions
    ad-hoc. Chaque opération emprunte puis rend une connexion au pool.
    """

    def __init__(self, db_url: str = "postgresql://localhost/etz_chaim") -> None:
        self.db_url = db_url

    def _get_conn(self, autocommit: bool = True):
        """Emprunter une connexion au pool centralisé avec pgvector enregistré."""
        from pool import get_conn
        return get_conn(autocommit=autocommit)

    def _register_vector_on(self, conn):
        """Enregistrer pgvector sur une connexion empruntée au pool."""
        try:
            register_vector(conn)
        except Exception as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)  # Déjà enregistré sur cette connexion

    def close(self) -> None:
        pass  # Le pool gère les connexions

    def insert(
        self,
        content: str,
        embedding: list[float] | None,
        source_sephirah: str,
        confidence: float,
        epistemic_status: str = "hypothesis",
        domain: str | None = None,
        tags: list[str] | None = None,
        ttl_days: int | None = None,
        source_detail: dict[str, Any] | None = None,
        supersedes: UUID | None = None,
    ) -> UUID:
        """Insert a memory entry, return its UUID."""
        import numpy as np

        expires_at = None
        if ttl_days is not None:
            expires_at = datetime.now(timezone.utc) + timedelta(days=ttl_days)

        emb = np.array(embedding, dtype=np.float32) if embedding else None

        with self._get_conn(autocommit=False) as conn:
            self._register_vector_on(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO epistememory
                        (content, embedding, source_sephirah, confidence,
                         epistemic_status, domain, tags, ttl_days, expires_at,
                         source_detail, supersedes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        content,
                        emb,
                        source_sephirah,
                        confidence,
                        epistemic_status,
                        domain,
                        tags,
                        ttl_days,
                        expires_at,
                        json.dumps(source_detail) if source_detail else None,
                        supersedes,
                    ),
                )
                entry_id = cur.fetchone()[0]

                # If supersedes, update the old entry
                if supersedes:
                    cur.execute(
                        "UPDATE epistememory SET superseded_by = %s WHERE id = %s",
                        (entry_id, supersedes),
                    )

            conn.commit()
        return entry_id

    def get(self, entry_id: UUID) -> MemoryEntry | None:
        """Get a single entry by ID."""
        with self._get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT *, NULL::float AS similarity FROM epistememory WHERE id = %s",
                    (entry_id,),
                )
                row = cur.fetchone()
                if row is None:
                    return None

                # Update access tracking
                cur.execute(
                    """UPDATE epistememory
                       SET last_accessed = NOW(), access_count = access_count + 1
                       WHERE id = %s""",
                    (entry_id,),
                )
                return _row_to_entry(row)

    def search_by_embedding(
        self,
        query_embedding: list[float],
        limit: int = 10,
        min_confidence: float = 0.0,
        epistemic_statuses: list[str] | None = None,
        domain: str | None = None,
    ) -> list[MemoryEntry]:
        """Semantic search using pgvector cosine distance."""
        import numpy as np

        emb = np.array(query_embedding, dtype=np.float32)

        conditions = [
            "epistemic_status != 'deprecated'",
            "(expires_at IS NULL OR expires_at > NOW())",
            "confidence >= %s",
        ]
        where_params: list[Any] = [min_confidence]

        if epistemic_statuses:
            conditions.append("epistemic_status = ANY(%s)")
            where_params.append(epistemic_statuses)

        if domain:
            conditions.append("domain = %s")
            where_params.append(domain)

        where_clause = " AND ".join(conditions)

        # Params order: SELECT %s, WHERE %s..., ORDER BY %s, LIMIT %s
        all_params = [emb, *where_params, emb, limit]

        with self._get_conn() as conn:
            self._register_vector_on(conn)
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    f"""
                    SELECT *, 1 - (embedding <=> %s) AS similarity
                    FROM epistememory
                    WHERE embedding IS NOT NULL AND {where_clause}
                    ORDER BY embedding <=> %s
                    LIMIT %s
                    """,
                    all_params,
                )
                rows = cur.fetchall()

                # Update access tracking for returned entries
                if rows:
                    ids = [row["id"] for row in rows]
                    cur.execute(
                        """UPDATE epistememory
                           SET last_accessed = NOW(), access_count = access_count + 1
                           WHERE id = ANY(%s)""",
                        (ids,),
                    )

            entries = [_row_to_entry(row) for row in rows]

            # Nogah warning: near expiration
            for entry in entries:
                if (
                    entry.expires_at
                    and entry.expires_at
                    < datetime.now(timezone.utc) + timedelta(days=7)
                ):
                    entry.warning = "near_expiration"

            return entries

    def add_contradiction(self, entry_id: UUID, contradicts_id: UUID) -> None:
        """Mark two entries as contradicting each other (bidirectional)."""
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE epistememory
                       SET contradicts = array_append(
                           COALESCE(contradicts, ARRAY[]::uuid[]), %s),
                           epistemic_status = 'contested'
                       WHERE id = %s AND NOT (%s = ANY(COALESCE(contradicts, ARRAY[]::uuid[])))""",
                    (contradicts_id, entry_id, contradicts_id),
                )
                cur.execute(
                    """UPDATE epistememory
                       SET contradicts = array_append(
                           COALESCE(contradicts, ARRAY[]::uuid[]), %s),
                           epistemic_status = 'contested'
                       WHERE id = %s AND NOT (%s = ANY(COALESCE(contradicts, ARRAY[]::uuid[])))""",
                    (entry_id, contradicts_id, entry_id),
                )

    def add_support(self, entry_id: UUID, supports_id: UUID) -> None:
        """Mark an entry as supporting another."""
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE epistememory
                       SET supports = array_append(
                           COALESCE(supports, ARRAY[]::uuid[]), %s)
                       WHERE id = %s AND NOT (%s = ANY(COALESCE(supports, ARRAY[]::uuid[])))""",
                    (supports_id, entry_id, supports_id),
                )

    def verify(self, entry_id: UUID, source: str) -> None:
        """Upgrade epistemic status after verification (Gevurah-de-Yesod)."""
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT epistemic_status, confidence, source_detail FROM epistememory WHERE id = %s",
                    (entry_id,),
                )
                row = cur.fetchone()
                if row is None:
                    return

                status, confidence, detail = row
                detail = detail or {}
                verifications = detail.get("verifications", [])
                verifications.append({"source": source, "at": datetime.now(timezone.utc).isoformat()})
                detail["verifications"] = verifications

                # Promote status
                if status in ("hypothesis", "correlation"):
                    new_status = "verified_once"
                    new_confidence = min(confidence + 0.2, 0.95)
                elif status == "verified_once":
                    new_status = "verified_multi"
                    new_confidence = min(confidence + 0.1, 0.95)
                elif status == "verified_multi" and confidence >= 0.9:
                    new_status = "fact"
                    new_confidence = confidence
                else:
                    new_status = status
                    new_confidence = min(confidence + 0.05, 0.95)

                cur.execute(
                    """UPDATE epistememory
                       SET epistemic_status = %s, confidence = %s, source_detail = %s
                       WHERE id = %s""",
                    (new_status, new_confidence, json.dumps(detail), entry_id),
                )

    def mature(self, max_per_level: int = 50) -> dict:
        """Yesod maturation — promotion automatique par lots.

        Critères :
          hypothesis → fact (voie rapide) : confidence >= 0.8 ET non contradictée
          hypothesis → verified_once : confidence >= 0.6 ET access_count >= 1
          verified_once → fact : confidence >= 0.7 ET ancienneté > 24h ET non contradictée
        """
        promoted: dict[str, list[UUID]] = {
            "to_fact_fast": [],
            "to_verified_once": [],
            "to_fact": [],
        }

        with self._get_conn() as conn:
            with conn.cursor() as cur:
                # Voie rapide : hypothesis → fact (haute confiance, pas de contradiction)
                cur.execute(
                    """UPDATE epistememory
                       SET epistemic_status = 'fact'
                       WHERE id IN (
                           SELECT id FROM epistememory
                           WHERE epistemic_status = 'hypothesis'
                             AND confidence >= 0.8
                             AND (contradicts IS NULL OR array_length(contradicts, 1) IS NULL)
                           ORDER BY confidence DESC
                           LIMIT %s
                       )
                       RETURNING id""",
                    (max_per_level,),
                )
                promoted["to_fact_fast"] = [row[0] for row in cur.fetchall()]

                # hypothesis → verified_once
                cur.execute(
                    """UPDATE epistememory
                       SET epistemic_status = 'verified_once'
                       WHERE id IN (
                           SELECT id FROM epistememory
                           WHERE epistemic_status = 'hypothesis'
                             AND confidence >= 0.6
                             AND access_count >= 1
                           ORDER BY confidence DESC
                           LIMIT %s
                       )
                       RETURNING id""",
                    (max_per_level,),
                )
                promoted["to_verified_once"] = [row[0] for row in cur.fetchall()]

                # verified_once → fact (seuil abaissé à 0.7)
                cur.execute(
                    """UPDATE epistememory
                       SET epistemic_status = 'fact'
                       WHERE id IN (
                           SELECT id FROM epistememory
                           WHERE epistemic_status = 'verified_once'
                             AND confidence >= 0.7
                             AND created_at < NOW() - INTERVAL '24 hours'
                             AND (contradicts IS NULL OR array_length(contradicts, 1) IS NULL)
                           ORDER BY confidence DESC
                           LIMIT %s
                       )
                       RETURNING id""",
                    (max_per_level,),
                )
                promoted["to_fact"] = [row[0] for row in cur.fetchall()]

        return promoted

    def deprecate(self, entry_id: UUID, superseded_by: UUID | None = None) -> None:
        """Mark an entry as deprecated."""
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE epistememory
                       SET epistemic_status = 'deprecated', superseded_by = COALESCE(%s, superseded_by)
                       WHERE id = %s""",
                    (superseded_by, entry_id),
                )

    def gc(self, remove_expired: bool = True, remove_deprecated: bool = False) -> GCReport:
        """Gevurah-de-Yesod: garbage collection."""
        expired_ids: list[UUID] = []
        deprecated_ids: list[UUID] = []

        with self._get_conn() as conn:
            with conn.cursor() as cur:
                # Find expired entries
                cur.execute(
                    "SELECT id FROM epistememory WHERE expires_at IS NOT NULL AND expires_at <= NOW()"
                )
                expired_ids = [row[0] for row in cur.fetchall()]

                if remove_expired and expired_ids:
                    cur.execute(
                        "UPDATE epistememory SET epistemic_status = 'deprecated' WHERE id = ANY(%s)",
                        (expired_ids,),
                    )

                # Find already deprecated
                cur.execute(
                    "SELECT id FROM epistememory WHERE epistemic_status = 'deprecated'"
                )
                deprecated_ids = [row[0] for row in cur.fetchall()]

                if remove_deprecated and deprecated_ids:
                    cur.execute(
                        "DELETE FROM epistememory WHERE id = ANY(%s)", (deprecated_ids,)
                    )

        return GCReport(
            expired_count=len(expired_ids),
            expired_ids=expired_ids,
            deprecated_count=len(deprecated_ids),
            deprecated_ids=deprecated_ids,
            low_confidence_count=0,
            low_confidence_ids=[],
            total_removed=len(deprecated_ids) if remove_deprecated else 0,
        )

    # --- Lilit diagnostics (Qliphah de Yesod) ---

    def count_confident_contested(self, min_confidence: float = 0.7) -> int:
        """Lilit-Nogah : entries confiantes mais contested."""
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM epistememory "
                    "WHERE confidence >= %s AND epistemic_status = 'contested'",
                    (min_confidence,),
                )
                return cur.fetchone()[0]

    def count_stagnant_hypotheses(self, min_access: int = 3) -> int:
        """Lilit-Ruach : hypothèses accédées souvent mais jamais vérifiées."""
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM epistememory "
                    "WHERE epistemic_status = 'hypothesis' AND access_count >= %s",
                    (min_access,),
                )
                return cur.fetchone()[0]

    def count_never_accessed(self) -> int:
        """Lilit-Anan : entries actives jamais accédées."""
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM active_memory WHERE access_count = 0"
                )
                return cur.fetchone()[0]

    def count_unverified_facts(self) -> int:
        """Lilit-Mamash : faits sans vérification réelle."""
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM epistememory "
                    "WHERE epistemic_status = 'fact' AND ("
                    "  source_detail IS NULL "
                    "  OR source_detail->'verifications' IS NULL "
                    "  OR jsonb_array_length(source_detail->'verifications') = 0"
                    ")"
                )
                return cur.fetchone()[0]

    def stats(self) -> MemoryStats:
        """Hod-de-Yesod: introspection statistics."""
        with self._get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT COUNT(*) AS total FROM epistememory")
                total = cur.fetchone()["total"]

                cur.execute("SELECT COUNT(*) AS c FROM active_memory")
                active = cur.fetchone()["c"]

                cur.execute(
                    "SELECT COUNT(*) AS c FROM epistememory WHERE epistemic_status = 'deprecated'"
                )
                deprecated = cur.fetchone()["c"]

                cur.execute(
                    "SELECT epistemic_status, COUNT(*) AS c FROM epistememory GROUP BY epistemic_status"
                )
                by_status = {row["epistemic_status"]: row["c"] for row in cur.fetchall()}

                cur.execute(
                    "SELECT COALESCE(domain, 'unset') AS d, COUNT(*) AS c FROM epistememory GROUP BY domain"
                )
                by_domain = {row["d"]: row["c"] for row in cur.fetchall()}

                cur.execute(
                    "SELECT source_sephirah, COUNT(*) AS c FROM epistememory GROUP BY source_sephirah"
                )
                by_source = {row["source_sephirah"]: row["c"] for row in cur.fetchall()}

                cur.execute("SELECT AVG(confidence) AS avg FROM epistememory")
                avg_conf = cur.fetchone()["avg"] or 0.0

                cur.execute("SELECT COUNT(*) AS c FROM open_contradictions")
                contradictions = cur.fetchone()["c"]

                cur.execute("SELECT COUNT(*) AS c FROM near_expiration")
                near_exp = cur.fetchone()["c"]

                cur.execute("SELECT MIN(created_at) AS oldest, MAX(created_at) AS newest FROM epistememory")
                row = cur.fetchone()

        return MemoryStats(
            total_entries=total,
            active_entries=active,
            deprecated_entries=deprecated,
            by_status=by_status,
            by_domain=by_domain,
            by_source=by_source,
            avg_confidence=float(avg_conf),
            contradictions_open=contradictions,
            near_expiration=near_exp,
            oldest_entry=row["oldest"],
            newest_entry=row["newest"],
        )
