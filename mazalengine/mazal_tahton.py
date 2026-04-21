"""Mazal Tahton — Tikkun n°13 : Ve-Nakeh (EC-K5-001).

Doctrine primaire (Rabbi Hayyim Vital, Etz Chaim, Sha'ar HaKlalim 5:1) :
    ומזל תחתון ונקה שהוא תיקון הי"ג

"Et le Mazal Tahton (inférieur) est Ve-Nakeh = Tikkun n°13 des 13 Tikkunei
Dikna. Et Il nettoie / absout."

Note doctrinale : l'expression biblique complète (Exode 34:7) est
``ונקה לא ינקה`` — "et absolvant, Il n'absout pas totalement". Le Tikkun
signale les résidus sans les détruire (conservation Reshimu).

Transposition E3 :
    Ve-Nakeh = 'absoudre/nettoyer' → veille sur les résidus causal_claims
    non-résolus depuis longtemps (confounders_controlled=false et anciens).
    Signale les accumulations anormales sans purger les données.

Interdiction absolue (Hitlabshut EC-K5-008) :
    Ne JAMAIS écrire sur partzufim_state. Le Tikkun est un signalement.
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


class MazalTahtonVeNakeh:
    """Tikkun n°13 — surveille les résidus causal_claims non-résolus.

    Attributes:
        STALE_DAYS: seuil d'ancienneté pour qu'un claim soit considéré stale.
        STALE_MIN_COUNT: volume minimal pour déclencher un Tikkun.
        DOCTRINE_REF: identifiant canonique Sifrei Yesod.
    """

    STALE_DAYS: int = 30
    STALE_MIN_COUNT: int = 10
    DOCTRINE_REF: str = "EC-K5-001"

    def __init__(self, db_url: str | None = None) -> None:
        self.db_url = db_url or _default_db_url()

    def _count_stale_claims(self, days: int) -> int:
        """Query DB — nombre de causal_claims non-contrôlés et anciens.

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
                        "SELECT COUNT(*) FROM causal_claims "
                        "WHERE confounders_controlled = false "
                        "AND created_at < NOW() - make_interval(days => %s)",
                        (int(days),),
                    )
                    row = cur.fetchone()
                    return int(row[0]) if row else 0
        except Exception as exc:  # pragma: no cover (DB failure path)
            log.debug("MazalTahton DB query failed: %s", exc)
            return -1

    def detect(self, tree: dict | None = None) -> list[dict]:
        """Détecte une accumulation anormale de claims stales.

        Args:
            tree: arbre de contexte daemon (non utilisé Phase 1, réservé).

        Returns:
            Liste avec une deviation si count >= STALE_MIN_COUNT, sinon [].
        """
        n = self._count_stale_claims(self.STALE_DAYS)
        if n >= self.STALE_MIN_COUNT:
            return [
                {
                    "mazal": "tahton",
                    "metrics": {"stale_count": n},
                    "threshold_days": self.STALE_DAYS,
                }
            ]
        return []

    def apply_tikkun(self, deviation: dict) -> dict:
        """Émet un event. Aucune suppression — principe Reshimu préservé."""
        return {
            "mazal": "tahton",
            "tikkun": "ve_nakeh",
            "action": "stale_claims_signaled",
            "doctrine_ref": self.DOCTRINE_REF,
            "metrics": deviation.get("metrics", {}),
            "threshold_days": deviation.get("threshold_days", self.STALE_DAYS),
        }
