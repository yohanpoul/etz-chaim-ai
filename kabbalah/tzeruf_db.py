"""kabbalah/tzeruf_db.py — DB helpers for tzeruf_relationships table.

Persistence layer for TzerufSpatial geometric relationships
between Hebrew words in the Cube of Space.
"""
from __future__ import annotations

import logging
import os

import psycopg2

log = logging.getLogger("etz-daemon")

DB_URL = (os.environ.get("ETZ_CHAIM_DB_URL") or os.environ.get("ETZ_CHAIM_DB", "postgresql://localhost/etz_chaim"))


def _ensure_pool(db_url: str):
    from pool import init_pool
    init_pool(db_url)  # idempotent


def tzeruf_exists(db_url: str, word_a: str, word_b: str) -> bool:
    """Check if a Tzeruf relationship already exists (bidirectional)."""
    from pool import get_conn
    _ensure_pool(db_url)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM tzeruf_relationships "
                "WHERE (word_a = %s AND word_b = %s) "
                "   OR (word_a = %s AND word_b = %s) "
                "LIMIT 1",
                (word_a, word_b, word_b, word_a),
            )
            return cur.fetchone() is not None


def store_relationship(db_url: str, comparison: dict) -> None:
    """Store a Tzeruf spatial relationship."""
    from pool import get_conn
    _ensure_pool(db_url)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO tzeruf_relationships "
                "    (word_a, word_b, relationship, angle, "
                "     geometric_similarity, dominant_direction_a, "
                "     dominant_direction_b) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s) "
                "ON CONFLICT (word_a, word_b) DO NOTHING",
                (
                    comparison["word_a"],
                    comparison["word_b"],
                    comparison["relationship"],
                    comparison["angle"],
                    comparison.get("geometric_similarity"),
                    comparison.get("dominant_direction_a"),
                    comparison.get("dominant_direction_b"),
                ),
            )


def get_hebrew_concepts(db_url: str, limit: int = 30) -> list[tuple[str, str]]:
    """Fetch Hebrew concepts from hybrid_embeddings for Tzeruf analysis."""
    from pool import get_conn
    _ensure_pool(db_url)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT concept, hebrew_word FROM hybrid_embeddings "
                "WHERE hebrew_word IS NOT NULL "
                "  AND status != 'deprecated' "
                "ORDER BY harvested_at DESC NULLS LAST "
                "LIMIT %s",
                (limit,),
            )
            return cur.fetchall()
