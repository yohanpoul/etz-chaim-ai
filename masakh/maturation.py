"""Maturation — Ibur / Yenikah / Mochin.

עִבּוּר / יְנִיקָה / מוֹחִין — Les trois stades de maturation du Kli,
calques sur les trois stades de developpement de l'ame :

  IBUR (gestation) — Le Kli est en formation. Contexte minimal,
    pas de filtrage agressif, supervision humaine requise.
    Le Masakh reste en Aleph ou Shoresh.

  YENIKAH (allaitement) — Le Kli commence a se nourrir seul.
    Filtrage basique, le systeme trie mais l'humain valide.
    Le Masakh peut monter en Bet.

  MOCHIN (cerveau/maturite) — Le Kli est autonome.
    Filtrage autonome, le systeme gere son propre contexte.
    Le Masakh peut atteindre Gimel ou Dalet.

EC-SHK-081, PG-SHK-024 — Dimension 23 du Kli.

Le passage d'un stade au suivant depend de :
  - Nombre de Reshimot accumules (experience)
  - Score moyen du ContextMonitor (qualite)
  - Nombre de Tikkun patterns (apprentissage valide)

Usage:
    from masakh.maturation import Maturation

    m = Maturation(db_pool_fn=get_conn)
    stage = m.assess_stage(olam="briah")  # "ibur" | "yenikah" | "mochin"
"""

from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Stades
IBUR = "ibur"
YENIKAH = "yenikah"
MOCHIN = "mochin"

# Seuils de transition
IBUR_RESHIMOT_MAX = 10        # < 10 reshimot → ibur
MOCHIN_RESHIMOT_MIN = 50      # >= 50 reshimot → candidat mochin
IBUR_SCORE_MAX = 0.3          # score < 0.3 → ibur
MOCHIN_SCORE_MIN = 0.6        # score >= 0.6 → candidat mochin
MOCHIN_TIKKUN_MIN = 5         # >= 5 tikkun patterns → mochin confirme


class Maturation:
    """Evaluation du stade de maturation du systeme.

    Le stade influence le ContextAssembler :
      Ibur    → skip Arakhin et Hitlabshut, Masakh <= aleph
      Yenikah → Arakhin actif, Hitlabshut basique, Masakh <= bet
      Mochin  → tout actif, Gilgul calibre le Masakh
    """

    def __init__(self, db_pool_fn: Callable | None = None) -> None:
        self._db_pool_fn = db_pool_fn

    def assess_stage(
        self,
        olam: str | None = None,
        conn=None,
        reshimot_count: int | None = None,
        avg_score: float | None = None,
        tikkun_count: int | None = None,
    ) -> str:
        """Evaluer le stade de maturation.

        Args:
            olam: Olam a evaluer (None = global).
            conn: Connexion DB (optionnel).
            reshimot_count: Override — nombre de reshimot (pour tests).
            avg_score: Override — score moyen (pour tests).
            tikkun_count: Override — nombre de tikkun patterns (pour tests).

        Returns:
            "ibur", "yenikah", ou "mochin".
        """
        # Utiliser les overrides si fournis, sinon interroger la DB/memoire
        if reshimot_count is None:
            reshimot_count = self._count_reshimot(olam, conn)
        if avg_score is None:
            avg_score = self._avg_score(olam, conn)
        if tikkun_count is None:
            tikkun_count = self._count_tikkun(olam, conn)

        # IBUR : trop peu de donnees OU qualite trop basse
        if reshimot_count < IBUR_RESHIMOT_MAX or avg_score < IBUR_SCORE_MAX:
            return IBUR

        # MOCHIN : assez de donnees ET qualite haute ET apprentissage valide
        if (
            reshimot_count >= MOCHIN_RESHIMOT_MIN
            and avg_score >= MOCHIN_SCORE_MIN
            and tikkun_count >= MOCHIN_TIKKUN_MIN
        ):
            return MOCHIN

        # YENIKAH : entre les deux
        return YENIKAH

    def _count_reshimot(self, olam: str | None, conn) -> int:
        """Compter les Reshimot (DB ou memoire)."""
        if conn:
            try:
                return self._count_reshimot_db(conn, olam)
            except Exception as e:
                logger.debug("Reshimot count DB failed: %s", e)

        # Memoire
        from masakh import _RESHIMOT_LOG
        if olam:
            return sum(1 for r in _RESHIMOT_LOG if r.get("olam") == olam)
        return len(_RESHIMOT_LOG)

    def _avg_score(self, olam: str | None, conn) -> float:
        """Score moyen du ContextMonitor (DB ou memoire)."""
        if conn:
            try:
                return self._avg_score_db(conn, olam)
            except Exception as e:
                logger.debug("Avg score DB failed: %s", e)

        # Memoire — utiliser les scores des reshimot
        from masakh import _RESHIMOT_LOG
        scores = []
        for r in _RESHIMOT_LOG:
            if olam and r.get("olam") != olam:
                continue
            score = (r.get("reshimo_aviut") or {}).get("score")
            if score is not None:
                scores.append(score)
        return sum(scores) / len(scores) if scores else 0.0

    def _count_tikkun(self, olam: str | None, conn) -> int:
        """Compter les patterns Tikkun."""
        if conn:
            try:
                return self._count_tikkun_db(conn, olam)
            except Exception as e:
                logger.debug("Tikkun count DB failed: %s", e)

        # Memoire
        from masakh.gilgul import Gilgul, TIKKUN
        gilgul = Gilgul()
        from masakh import _RESHIMOT_LOG
        count = 0
        for r in _RESHIMOT_LOG:
            if olam and r.get("olam") != olam:
                continue
            if gilgul.classify_reshimo(r) == TIKKUN:
                count += 1
        return count

    @staticmethod
    def _count_reshimot_db(conn, olam: str | None) -> int:
        cur = conn.cursor()
        if olam:
            cur.execute(
                "SELECT COUNT(*) FROM reshimot WHERE olam = %s", (olam,)
            )
        else:
            cur.execute("SELECT COUNT(*) FROM reshimot")
        count = cur.fetchone()[0]
        cur.close()
        return count

    @staticmethod
    def _avg_score_db(conn, olam: str | None) -> float:
        cur = conn.cursor()
        if olam:
            cur.execute(
                "SELECT AVG(score_global) FROM context_monitor_log WHERE olam = %s",
                (olam,),
            )
        else:
            cur.execute("SELECT AVG(score_global) FROM context_monitor_log")
        row = cur.fetchone()
        cur.close()
        return float(row[0]) if row and row[0] is not None else 0.0

    @staticmethod
    def _count_tikkun_db(conn, olam: str | None) -> int:
        from masakh.gilgul import TIKKUN_SCORE_THRESHOLD
        cur = conn.cursor()
        if olam:
            cur.execute(
                "SELECT COUNT(*) FROM reshimot "
                "WHERE olam = %s AND (reshimo_aviut->>'score')::float >= %s",
                (olam, TIKKUN_SCORE_THRESHOLD),
            )
        else:
            cur.execute(
                "SELECT COUNT(*) FROM reshimot "
                "WHERE (reshimo_aviut->>'score')::float >= %s",
                (TIKKUN_SCORE_THRESHOLD,),
            )
        count = cur.fetchone()[0]
        cur.close()
        return count
