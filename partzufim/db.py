"""partzufim/db.py — Persistance des Partzufim en DB.

UPSERT après chaque update_from_modules(), chargement au démarrage.
Utilise le pool centralisé (pool.py).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def save_partzuf(name: str, overall: float, mochin_state: str,
                 orientation: str, faculties: dict[str, float]) -> None:
    """UPSERT un Partzuf dans partzufim_state."""
    from pool import get_conn

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO partzufim_state (name, overall_score, mochin_state,
                                             orientation, faculties, updated_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
                ON CONFLICT (name) DO UPDATE SET
                    overall_score = EXCLUDED.overall_score,
                    mochin_state  = EXCLUDED.mochin_state,
                    orientation   = EXCLUDED.orientation,
                    faculties     = EXCLUDED.faculties,
                    updated_at    = NOW()
            """, (name, overall, mochin_state, orientation,
                  json.dumps(faculties)))


def load_all_partzufim() -> dict[str, dict]:
    """Charger tous les Partzufim depuis DB.

    Retourne {name: {overall, mochin_state, orientation, faculties, updated_at}}
    ou {} si la table est vide ou n'existe pas.

    Audit cycle 4, C5 : pool exclusif (CB-protégé). Pas d'auto
    init_pool() — le daemon (ou le test) initialise le pool en amont.
    Si le pool n'est pas prêt, on retourne {} sans bypass : aucun
    fallback `psycopg2.connect` direct, sinon le circuit breaker
    serait court-circuité.
    """
    import psycopg2.extras

    try:
        from pool import get_conn
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT name, overall_score, mochin_state, orientation,
                           faculties, updated_at
                    FROM partzufim_state
                    ORDER BY name
                """)
                rows = cur.fetchall()
                return {
                    row["name"]: {
                        "overall": row["overall_score"],
                        "mochin_state": row["mochin_state"],
                        "orientation": row["orientation"],
                        "faculties": row["faculties"] or {},
                        "updated_at": row["updated_at"],
                    }
                    for row in rows
                }
    except Exception as e:
        logger.debug("load_all_partzufim: %s", e)
        return {}
