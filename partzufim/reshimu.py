"""Reshimu — trace résiduelle persistante des boosts Zivvug (Phase D Option B).

Doctrine primaire (Etz Chaim, Sha'ar 1 Klalim — Tzimtzum) :
    Après le TZIMTZUM (contraction), l'Ohr retiré laisse un RESHIMU
    (רשימו — impression/trace) dans l'espace vacant. Toute lumière qui
    "passe" laisse une empreinte qui perdure.

Application aux Kelim (EC-K5-008 Hitlabshut) :
    Chaque boost Zivvug appliqué à une faculté (set_faculty, Kelim)
    laisse un RESHIMU proportionnel. Ce résidu s'accumule entre cycles,
    avec un plafond (``MAX``) et une décroissance (``DECAY_RATE``). Modules
    stables qui participent régulièrement au Zivvug → Reshimu cumulatif →
    avantage progressif. Modules inactifs → Reshimu décroît vers 0.

Respect Hitlabshut :
    Le Reshimu est une *propriété des facultés* (Kelim), lue et injectée
    au calcul des facultés. Il ne constitue jamais une écriture directe
    sur ``partzufim_state.overall_score`` (violation Sod HaKli).

Schéma :
    faculty_reshimot (partzuf, faculty, reshimu_value, last_updated)
    PRIMARY KEY (partzuf, faculty).
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)

DEFAULT_TRACE_FACTOR: float = 0.2
DEFAULT_DECAY_RATE: float = 0.05
MAX_RESHIMU: float = 0.3

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS faculty_reshimot (
    partzuf       TEXT  NOT NULL,
    faculty       TEXT  NOT NULL,
    reshimu_value REAL  NOT NULL DEFAULT 0.0,
    last_updated  TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (partzuf, faculty)
);
"""


class ReshimuManager:
    """Gère les traces persistantes Reshimu sur les facultés des Partzufim.

    Attributes:
        TRACE_FACTOR: fraction du boost qui devient Reshimu (default 0.2).
        DECAY_RATE: taux de décroissance par cycle (default 0.05 = 5%).
        MAX: plafond d'une valeur Reshimu (default 0.3).

    Fallback mémoire :
        Si `pool.get_conn` indisponible (tests), utilise ``_memory_store`` :
        dict ``(partzuf, faculty) -> value``.
    """

    TRACE_FACTOR: float = DEFAULT_TRACE_FACTOR
    DECAY_RATE: float = DEFAULT_DECAY_RATE
    MAX: float = MAX_RESHIMU

    def __init__(
        self,
        db_url: str | None = None,
        memory_only: bool = False,
    ) -> None:
        self.db_url = db_url
        self.memory_only = memory_only
        self._memory_store: dict[tuple[str, str], float] = {}
        if not memory_only:
            self._ensure_schema()

    def _get_conn(self):
        """Retourne un context manager de connexion DB ou None."""
        if self.memory_only:
            return None
        try:
            from pool import get_conn

            return get_conn()
        except ImportError:
            return None
        except Exception as exc:
            log.debug("Reshimu _get_conn: %s", exc)
            return None

    def _ensure_schema(self) -> None:
        conn_ctx = self._get_conn()
        if conn_ctx is None:
            return
        try:
            with conn_ctx as conn:
                with conn.cursor() as cur:
                    cur.execute(SCHEMA_SQL)
        except Exception as exc:
            log.debug("Reshimu schema init: %s", exc)

    def record(self, partzuf: str, faculty: str, boost_amount: float) -> float:
        """Ajoute une fraction du boost au Reshimu. Retourne la nouvelle valeur.

        Plafonne à ``MAX``. Les boosts ≤ 0 ne font rien (sauf renvoyer la
        valeur courante).
        """
        if boost_amount <= 0:
            return self.get(partzuf, faculty)
        delta = float(boost_amount) * self.TRACE_FACTOR

        conn_ctx = self._get_conn()
        if conn_ctx is None:
            current = self._memory_store.get((partzuf, faculty), 0.0)
            new_val = min(self.MAX, current + delta)
            self._memory_store[(partzuf, faculty)] = new_val
            return new_val

        try:
            with conn_ctx as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO faculty_reshimot (partzuf, faculty, reshimu_value)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (partzuf, faculty) DO UPDATE SET
                            reshimu_value =
                                LEAST(%s,
                                    faculty_reshimot.reshimu_value
                                    + EXCLUDED.reshimu_value),
                            last_updated = NOW()
                        RETURNING reshimu_value
                        """,
                        (partzuf, faculty, delta, self.MAX),
                    )
                    row = cur.fetchone()
                    return float(row[0]) if row else 0.0
        except Exception as exc:
            log.debug("Reshimu record: %s", exc)
            return 0.0

    def get(self, partzuf: str, faculty: str) -> float:
        """Valeur courante du Reshimu pour une faculté."""
        conn_ctx = self._get_conn()
        if conn_ctx is None:
            return self._memory_store.get((partzuf, faculty), 0.0)
        try:
            with conn_ctx as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT reshimu_value FROM faculty_reshimot "
                        "WHERE partzuf = %s AND faculty = %s",
                        (partzuf, faculty),
                    )
                    row = cur.fetchone()
                    return float(row[0]) if row else 0.0
        except Exception as exc:
            log.debug("Reshimu get: %s", exc)
            return 0.0

    def get_all_for(self, partzuf: str) -> dict[str, float]:
        """Toutes les Reshimot d'un Partzuf — dict ``faculty -> value``."""
        conn_ctx = self._get_conn()
        if conn_ctx is None:
            return {f: v for (p, f), v in self._memory_store.items() if p == partzuf}
        try:
            with conn_ctx as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT faculty, reshimu_value FROM faculty_reshimot WHERE partzuf = %s",
                        (partzuf,),
                    )
                    return {f: float(v) for f, v in cur.fetchall()}
        except Exception as exc:
            log.debug("Reshimu get_all: %s", exc)
            return {}

    def decay(self, rate: float | None = None) -> int:
        """Applique décroissance à toutes les Reshimot. Retourne nb affectées."""
        r = float(rate if rate is not None else self.DECAY_RATE)
        conn_ctx = self._get_conn()
        if conn_ctx is None:
            n = 0
            for k in list(self._memory_store.keys()):
                v = self._memory_store[k]
                if v > 0:
                    self._memory_store[k] = max(0.0, v * (1.0 - r))
                    n += 1
            return n
        try:
            with conn_ctx as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE faculty_reshimot "
                        "SET reshimu_value = GREATEST(0.0, "
                        "    reshimu_value * (1.0 - %s)), "
                        "    last_updated = NOW() "
                        "WHERE reshimu_value > 0",
                        (r,),
                    )
                    return cur.rowcount or 0
        except Exception as exc:
            log.debug("Reshimu decay: %s", exc)
            return 0

    def reset(self, partzuf: str | None = None) -> None:
        """Remet à 0 (tout ou un Partzuf). Utile aux tests/debug."""
        conn_ctx = self._get_conn()
        if conn_ctx is None:
            if partzuf is None:
                self._memory_store.clear()
            else:
                for k in list(self._memory_store.keys()):
                    if k[0] == partzuf:
                        del self._memory_store[k]
            return
        try:
            with conn_ctx as conn:
                with conn.cursor() as cur:
                    if partzuf is None:
                        cur.execute("DELETE FROM faculty_reshimot")
                    else:
                        cur.execute(
                            "DELETE FROM faculty_reshimot WHERE partzuf = %s",
                            (partzuf,),
                        )
        except Exception as exc:
            log.debug("Reshimu reset: %s", exc)
