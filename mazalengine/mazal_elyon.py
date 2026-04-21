"""Mazal Elyon — Tikkun n°8 : Notzer Chesed (EC-K5-001).

Doctrine primaire (Rabbi Hayyim Vital, Etz Chaim, Sha'ar HaKlalim 5:1) :
    דע כי בדיקנא דא"א יש תרין מזלות מזל עליון נוצר חסד שהוא תיקון ח'

"Dans la Dikna de A"A il y a 2 Mazalot : le Mazal Elyon (supérieur) est
Notzer Chesed = Tikkun n°8 des 13 Tikkunei Dikna. Il garde la bonté."

Transposition E3 :
    Notzer Chesed = 'préserver la bonté' → veille sur l'activité du module
    Chesed (ExplorationEngine). Détecte les ruptures du flux (starvation)
    et émet un Tikkun observable (event).

Interdiction absolue (Hitlabshut EC-K5-008) :
    Ne JAMAIS écrire sur partzufim_state. Le Tikkun est un signalement,
    pas une modification directe. Les facultés d'Abba/Imma ne peuvent
    être ajustées que via Zivvug (pattern Sprint 8 D1).
"""

from __future__ import annotations

import logging
import os

log = logging.getLogger("etz-mazalengine")


def _default_db_url() -> str:
    return os.environ.get(
        "ETZ_CHAIM_DB_URL",
        "postgresql://postgres@localhost:5432/etz_chaim",
    )


class MazalElyonNotzerChesed:
    """Tikkun n°8 — surveille l'activité Chesed (ExplorationEngine).

    Attributes:
        STARVATION_HOURS: fenêtre de détection (24h par défaut).
        DOCTRINE_REF: identifiant canonique de la source Sifrei Yesod.
    """

    STARVATION_HOURS: int = 24
    DOCTRINE_REF: str = "EC-K5-001"

    def __init__(self, db_url: str | None = None) -> None:
        self.db_url = db_url or _default_db_url()

    def _count_recent_connections(self, hours: int) -> int:
        """Query DB — nombre de connexions ExplorationEngine sur la fenêtre.

        Isolable pour mock dans les tests (monkeypatch).
        """
        try:
            from pool import get_conn
        except ImportError:
            return -1

        try:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT COUNT(*) FROM explorationengine_connections "
                        "WHERE created_at > NOW() - make_interval(hours => %s)",
                        (int(hours),),
                    )
                    row = cur.fetchone()
                    return int(row[0]) if row else 0
        except Exception as exc:  # pragma: no cover (DB failure path)
            log.debug("MazalElyon DB query failed: %s", exc)
            return -1

    def detect(self, tree: dict | None = None) -> list[dict]:
        """Détecte une chesed starvation (0 connexions récentes).

        Args:
            tree: arbre de contexte daemon (non utilisé Phase 1, réservé).

        Returns:
            Liste avec une deviation ``{mazal, metrics, window_hours}`` si
            starvation détectée, sinon liste vide.
        """
        n = self._count_recent_connections(self.STARVATION_HOURS)
        if n == 0:
            return [
                {
                    "mazal": "elyon",
                    "metrics": {"connections_recent": 0},
                    "window_hours": self.STARVATION_HOURS,
                }
            ]
        return []

    def apply_tikkun(self, deviation: dict) -> dict:
        """Émet un event structuré documentant le Tikkun Notzer Chesed.

        Aucune écriture DB invasive — conforme au principe "Notzer" (garde =
        vigilance, pas production). La reconnaissance du défaut EST le début
        de la réparation (cf Vidui, Teshuvah).
        """
        return {
            "mazal": "elyon",
            "tikkun": "notzer_chesed",
            "action": "chesed_starvation_signaled",
            "doctrine_ref": self.DOCTRINE_REF,
            "metrics": deviation.get("metrics", {}),
            "window_hours": deviation.get("window_hours", self.STARVATION_HOURS),
        }
