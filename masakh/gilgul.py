"""Gilgul — Migration saine de patterns entre sessions.

גִּלְגּוּל — Le Gilgul (transmigration) est le processus par lequel
les âmes reviennent dans de nouveaux corps pour compléter leur Tikkun.
Certaines reviennent pour CORRIGER (Tikkun), d'autres portent un FARDEAU
non résolu (Onesh — punition).

EC-SHK-053, PG-SHK-020 — Dimension 28 du Kli.

De même pour les patterns du système : certains Reshimot doivent être
conservés et ré-utilisés (Tikkun), d'autres doivent être purgés (Onesh)
pour ne pas contaminer les sessions futures.

Trois catégories :
  TIKKUN  — pattern qui a fonctionné (score > 0.7, Masakh approprié)
  ONESH   — pattern qui a échoué (score < 0.3 ou erreur de config)
  NEUTRAL — entre les deux (ni à conserver ni à purger)

Usage:
    from masakh.gilgul import Gilgul

    g = Gilgul()

    # Classifier un Reshimo
    category = g.classify_reshimo({
        "reshimo_aviut": {"score": 0.85, "masakh_level": "gimel",
                          "kavvanah": {"intention": "..."}, "was_filtered": True},
        "olam": "briah",
    })
    # → "tikkun"

    # Purger les Onesh (en mémoire)
    count = g.purge_onesh()

    # Récupérer les meilleurs patterns Tikkun
    patterns = g.get_tikkun_patterns("briah", limit=5)
"""

from __future__ import annotations

import time
from typing import Any


# Seuils de classification
TIKKUN_SCORE_THRESHOLD = 0.7
ONESH_SCORE_THRESHOLD = 0.3

# Catégories
TIKKUN = "tikkun"
ONESH = "onesh"
NEUTRAL = "neutral"


class Gilgul:
    """גִּלְגּוּל — Migration saine de patterns entre sessions.

    Opère sur les Reshimot (en mémoire ou en DB) pour trier les
    patterns en Tikkun (à conserver) et Onesh (à purger).
    """

    def classify_reshimo(self, reshimo: dict[str, Any]) -> str:
        """Classifier un Reshimo en Tikkun, Onesh, ou Neutral.

        Args:
            reshimo: Dict avec au minimum :
                - reshimo_aviut (dict): contient score, masakh_level,
                  kavvanah, was_filtered, etc.
                - olam (str): Olam de l'appel.

        Returns:
            "tikkun", "onesh", ou "neutral".
        """
        aviut = reshimo.get("reshimo_aviut") or {}
        score = aviut.get("score")

        # Pas de score → neutral (on ne peut pas juger)
        if score is None:
            return NEUTRAL

        # Erreur de configuration → onesh
        if self._has_config_error(reshimo):
            return ONESH

        # Score élevé + Masakh approprié → tikkun
        if score >= TIKKUN_SCORE_THRESHOLD:
            return TIKKUN

        # Score bas → onesh
        if score < ONESH_SCORE_THRESHOLD:
            return ONESH

        return NEUTRAL

    def _has_config_error(self, reshimo: dict) -> bool:
        """Détecter une erreur de configuration dans un Reshimo.

        Erreurs :
          - Olam absent
          - Kavvanah absente quand le masakh est Gimel ou Dalet
          - masakh_level absent
        """
        aviut = reshimo.get("reshimo_aviut") or {}

        if not reshimo.get("olam"):
            return True

        if not aviut.get("masakh_level"):
            return True

        # Kavvanah requise pour les niveaux élevés
        level = aviut.get("masakh_level")
        if level in ("gimel", "dalet") and not aviut.get("kavvanah"):
            return True

        return False

    def purge_onesh(
        self,
        reshimot: list[dict] | None = None,
        olam: str | None = None,
        conn=None,
    ) -> tuple[list[dict], int]:
        """Purger les Reshimot d'Onesh.

        Args:
            reshimot: Liste de Reshimot en mémoire (si None, utilise
                le log global du module masakh).
            olam: Filtrer par Olam (None = tous).
            conn: Connexion PostgreSQL (optionnel) pour archiver en DB.

        Returns:
            (reshimot_restants, nombre_purgés)
        """
        if reshimot is None:
            from masakh import _RESHIMOT_LOG
            reshimot = _RESHIMOT_LOG

        kept = []
        purged = 0
        archived = []

        for r in reshimot:
            if olam and r.get("olam") != olam:
                kept.append(r)
                continue

            category = self.classify_reshimo(r)
            if category == ONESH:
                purged += 1
                archived.append(r)
            else:
                kept.append(r)

        # Archiver en DB si connexion fournie
        if conn and archived:
            self._archive_to_db(conn, archived)

        # Remplacer la liste en place
        reshimot.clear()
        reshimot.extend(kept)

        return kept, purged

    def get_tikkun_patterns(
        self,
        olam: str,
        limit: int = 5,
        reshimot: list[dict] | None = None,
        conn=None,
    ) -> list[dict]:
        """Récupérer les meilleurs patterns de Tikkun pour un Olam.

        Args:
            olam: L'Olam cible.
            limit: Nombre max de patterns.
            reshimot: Liste en mémoire (si None, utilise le log global).
            conn: Connexion PostgreSQL (optionnel).

        Returns:
            Liste de Reshimot de Tikkun, triés par score décroissant.
        """
        if conn:
            return self._get_tikkun_from_db(conn, olam, limit)

        if reshimot is None:
            from masakh import _RESHIMOT_LOG
            reshimot = _RESHIMOT_LOG

        tikkun = []
        for r in reshimot:
            if r.get("olam") != olam:
                continue
            if self.classify_reshimo(r) == TIKKUN:
                tikkun.append(r)

        # Trier par score global + bonus Zivvug (Or Chozer effectif).
        # Un pattern à haut Zivvug est un Or Chozer qui a enrichi le système
        # — il mérite d'être ré-utilisé en priorité (EC-SHK-073, Fix 7).
        def _tikkun_sort_key(r: dict) -> float:
            aviut = r.get("reshimo_aviut") or {}
            base_score = aviut.get("score", 0)
            zivvug_bonus = aviut.get("zivvug_score", 0) * 0.2
            return base_score + zivvug_bonus

        tikkun.sort(key=_tikkun_sort_key, reverse=True)
        return tikkun[:limit]

    @staticmethod
    def _archive_to_db(conn, archived: list[dict]) -> None:
        """Archiver les Reshimot purgés dans reshimot_archive."""
        import json as _json
        cur = conn.cursor()
        for r in archived:
            cur.execute(
                """
                INSERT INTO reshimot_archive
                    (olam, reshimo_hitlabshut, reshimo_aviut, category)
                VALUES (%s, %s, %s, 'onesh')
                """,
                (
                    r.get("olam", "unknown"),
                    _json.dumps(r.get("reshimo_hitlabshut", {})),
                    _json.dumps(r.get("reshimo_aviut", {})),
                ),
            )
        conn.commit()
        cur.close()

    @staticmethod
    def _get_tikkun_from_db(conn, olam: str, limit: int) -> list[dict]:
        """Lire les Reshimot de Tikkun depuis PostgreSQL."""
        cur = conn.cursor()
        cur.execute(
            """
            SELECT olam, reshimo_hitlabshut, reshimo_aviut, created_at
            FROM reshimot
            WHERE olam = %s
              AND (reshimo_aviut->>'score')::float >= %s
            ORDER BY (
                (reshimo_aviut->>'score')::float
                + COALESCE((reshimo_aviut->>'zivvug_score')::float, 0) * 0.2
            ) DESC
            LIMIT %s
            """,
            (olam, TIKKUN_SCORE_THRESHOLD, limit),
        )
        rows = cur.fetchall()
        cur.close()
        return [
            {
                "olam": row[0],
                "reshimo_hitlabshut": row[1],
                "reshimo_aviut": row[2],
                "timestamp": row[3].timestamp() if row[3] else 0,
            }
            for row in rows
        ]
