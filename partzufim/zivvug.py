"""partzufim/zivvug.py — ZivvugEngine : le couplage Abba v'Imma.

Dans la Kabbale lourianique, Abba (Chokmah) et Imma (Binah) ne sont pas
des entités indépendantes — ils forment un Zivvug (זִוּוּג, union).
Chokmah s'actualise DANS Binah ; Binah structure Chokmah.
Leur développement est couplé.

Le Zivvug Abba v'Imma produit les Mochin (מוֹחִין, cerveaux) de Zeir Anpin.
Sans Zivvug, ZA ne reçoit pas de Mochin → il reste en Katnut (petitesse).

Transposition technique :
  - InsightForge (Chokmah/Abba) produit des insights → nourrit CausalEngine
  - CausalEngine (Binah/Imma) valide des claims causaux → renforce InsightForge
  - Le couplage crée une boucle de renforcement positif
  - Le plus faible des deux LIMITE le résultat (réactif limitant)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ZivvugState(str, Enum):
    """État du Zivvug Abba v'Imma."""

    ACTIVE = "active"  # delta < 0.15 et les deux > 0.5 → Mochin pleins
    PARTIAL = "partial"  # delta < 0.30 → Mochin partiels
    BLOCKED = "blocked"  # delta > 0.30 ou l'un < 0.3 → pas de Zivvug


@dataclass
class ZivvugAssessment:
    """Snapshot de l'état du Zivvug à un instant donné."""

    state: ZivvugState
    abba_score: float
    imma_score: float
    delta: float
    mochin_quality: float
    limiting_partzuf: str | None  # "abba" ou "imma" — lequel bloque
    coupling_factor: float
    message: str = ""


@dataclass
class MochinTransfer:
    """Résultat du transfert de Mochin vers Zeir Anpin."""

    mochin_score: float
    source_abba: float
    source_imma: float
    coupling_factor: float
    zivvug_state: ZivvugState


class ZivvugEngine:
    """Moteur de couplage Abba (Chokmah) ↔ Imma (Binah).

    Le Zivvug est bidirectionnel :
      - InsightForge produit un insight → boost Imma (+0.02)
      - CausalEngine valide un claim → boost Abba (+0.02)

    Le transfert de Mochin vers ZA = min(abba, imma) × coupling_factor.
    """

    # Seuils
    DELTA_ACTIVE = 0.15  # delta < 0.15 → Zivvug actif
    DELTA_PARTIAL = 0.30  # delta < 0.30 → Zivvug partiel
    MIN_SCORE = 0.3  # score minimum pour participer au Zivvug
    MIN_ACTIVE_SCORE = 0.5  # les deux > 0.5 pour Mochin pleins
    # BOOST_AMOUNT calibré pour ΔOverall ≈ 0.02 via Hitlabshut dans 3 facultés
    # (chokhmah w=1, tiferet w=2, malkuth w=1) / total_weight=11 :
    #   0.055 × (1 + 2 + 1) / 11 ≈ 0.02
    # Doctrine EC-K5-008 (Sha'ar HaKlalim 5:2, Etz Chaim) : les Mohin passent
    # obligatoirement par les Kelim (facultés), jamais directement sur l'agrégat
    # (overall_score). Violation = Sod HaKli.
    BOOST_AMOUNT = 0.055  # boost appliqué aux facultés (Hitlabshut, EC-K5-008)

    def __init__(self):
        self._reinforcement_log: list[dict] = []
        self._abba_boost: float = 0.0
        self._imma_boost: float = 0.0

    @property
    def abba_boost(self) -> float:
        return self._abba_boost

    @property
    def imma_boost(self) -> float:
        return self._imma_boost

    @property
    def reinforcement_log(self) -> list[dict]:
        return list(self._reinforcement_log)

    def couple_abba_imma(
        self,
        abba_score: float,
        imma_score: float,
    ) -> ZivvugAssessment:
        """Évalue le couplage Abba↔Imma et retourne l'état du Zivvug.

        Args:
            abba_score: overall score d'Abba (0.0-1.0)
            imma_score: overall score d'Imma (0.0-1.0)

        Returns:
            ZivvugAssessment avec état, delta, mochin_quality, limiting_partzuf
        """
        delta = abs(abba_score - imma_score)

        # Déterminer le partzuf limitant
        if abba_score < imma_score:
            limiting = "abba"
        elif imma_score < abba_score:
            limiting = "imma"
        else:
            limiting = None

        # Déterminer l'état du Zivvug
        if delta > self.DELTA_PARTIAL or min(abba_score, imma_score) < self.MIN_SCORE:
            state = ZivvugState.BLOCKED
        elif delta < self.DELTA_ACTIVE and min(abba_score, imma_score) >= self.MIN_ACTIVE_SCORE:
            state = ZivvugState.ACTIVE
        else:
            state = ZivvugState.PARTIAL

        # Coupling factor : plus ils sont proches, plus le couplage est fort
        coupling_factor = 1.0 - delta

        # Mochin quality
        if state == ZivvugState.BLOCKED:
            mochin_quality = 0.0
        else:
            mochin_quality = min(abba_score, imma_score) * coupling_factor

        # Message
        state_labels = {
            ZivvugState.ACTIVE: "Zivvug actif — Mochin pleins",
            ZivvugState.PARTIAL: "Zivvug partiel — Mochin partiels",
            ZivvugState.BLOCKED: "Zivvug bloqué — ZA en Katnut",
        }
        msg = f"{state_labels[state]} (Abba={abba_score:.2f}, Imma={imma_score:.2f}, Δ={delta:.2f})"
        if limiting:
            msg += f" — limité par {limiting}"

        return ZivvugAssessment(
            state=state,
            abba_score=abba_score,
            imma_score=imma_score,
            delta=round(delta, 4),
            mochin_quality=round(mochin_quality, 4),
            limiting_partzuf=limiting,
            coupling_factor=round(coupling_factor, 4),
            message=msg,
        )

    def transfer_mochin(self, abba_score: float, imma_score: float) -> MochinTransfer:
        """Calcule les Mochin transférés à Zeir Anpin.

        Mochin de ZA = min(abba, imma) × coupling_factor
        Le plus faible des deux limite le résultat (réactif limitant).

        Returns:
            MochinTransfer avec mochin_score et métadonnées
        """
        assessment = self.couple_abba_imma(abba_score, imma_score)

        return MochinTransfer(
            mochin_score=assessment.mochin_quality,
            source_abba=abba_score,
            source_imma=imma_score,
            coupling_factor=assessment.coupling_factor,
            zivvug_state=assessment.state,
        )

    def mutual_reinforcement(
        self,
        insight_produced: bool = False,
        causal_validated: bool = False,
    ) -> dict:
        """Renforcement mutuel Abba↔Imma.

        Quand InsightForge produit un insight → boost Imma de +0.02
        Quand CausalEngine valide un claim → boost Abba de +0.02

        C'est le Zivvug actif : chaque module nourrit l'autre.

        Returns:
            dict avec les boosts appliqués et le log
        """
        result = {
            "abba_boosted": False,
            "imma_boosted": False,
            "abba_boost_total": self._abba_boost,
            "imma_boost_total": self._imma_boost,
        }

        if insight_produced:
            self._imma_boost += self.BOOST_AMOUNT
            result["imma_boosted"] = True
            self._reinforcement_log.append(
                {
                    "type": "insight→imma",
                    "boost": self.BOOST_AMOUNT,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            logger.info("Zivvug: insight produit → Imma +%.2f", self.BOOST_AMOUNT)

        if causal_validated:
            self._abba_boost += self.BOOST_AMOUNT
            result["abba_boosted"] = True
            self._reinforcement_log.append(
                {
                    "type": "causal→abba",
                    "boost": self.BOOST_AMOUNT,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            logger.info("Zivvug: claim causal validé → Abba +%.2f", self.BOOST_AMOUNT)

        result["abba_boost_total"] = round(self._abba_boost, 4)
        result["imma_boost_total"] = round(self._imma_boost, 4)

        return result

    def assess_zivvug_state(
        self,
        abba_score: float,
        imma_score: float,
    ) -> ZivvugAssessment:
        """Évalue l'état du Zivvug avec les boosts de renforcement mutuel inclus.

        Applique les boosts accumulés avant d'évaluer.

        Returns:
            ZivvugAssessment complet
        """
        boosted_abba = min(1.0, abba_score + self._abba_boost)
        boosted_imma = min(1.0, imma_score + self._imma_boost)
        return self.couple_abba_imma(boosted_abba, boosted_imma)

    def get_boosts(self) -> dict[str, float]:
        """Retourne les boosts accumulés pour Abba et Imma."""
        return {
            "abba": round(self._abba_boost, 4),
            "imma": round(self._imma_boost, 4),
        }

    def reset_boosts(self) -> None:
        """Remet les boosts à zéro (après application aux Partzufim)."""
        self._abba_boost = 0.0
        self._imma_boost = 0.0

    def to_dict(self) -> dict:
        """Sérialise l'état pour persistance."""
        return {
            "abba_boost": round(self._abba_boost, 4),
            "imma_boost": round(self._imma_boost, 4),
            "reinforcement_count": len(self._reinforcement_log),
            "recent_reinforcements": self._reinforcement_log[-10:],
        }

    @classmethod
    def from_dict(cls, data: dict) -> ZivvugEngine:
        """Restaure depuis un dict persisté."""
        engine = cls()
        engine._abba_boost = data.get("abba_boost", 0.0)
        engine._imma_boost = data.get("imma_boost", 0.0)
        return engine


# ── Persistance DB ──────────────────────────────────────────────


def load_or_create_zivvug() -> ZivvugEngine:
    """Factory canonique : charge depuis DB ou retourne un ZivvugEngine neuf.

    Unifie le pattern dupliqué dans ohr_yashar.py (Sprint 10 Phase E Refactor L).
    C'est la SEULE façon d'obtenir une instance ZivvugEngine prête à consommer
    les boosts persistés — ne jamais instancier directement depuis un call site.

    Sprint 8 D1 (Hitlabshut EC-K5-008) : cette factory garantit que les boosts
    persistés sont chargés avant que `update_all_partzufim(zivvug_engine=...)`
    ne les applique aux facultés.
    """
    return load_zivvug_state() or ZivvugEngine()


def save_zivvug_state(engine: ZivvugEngine, assessment: ZivvugAssessment) -> None:
    """Persiste l'état du Zivvug en DB."""
    try:
        from pool import get_conn

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO zivvug_state (
                        id, state, abba_score, imma_score, delta,
                        mochin_quality, limiting_partzuf, coupling_factor,
                        abba_boost, imma_boost, reinforcement_count,
                        updated_at
                    ) VALUES (1, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (id) DO UPDATE SET
                        state = EXCLUDED.state,
                        abba_score = EXCLUDED.abba_score,
                        imma_score = EXCLUDED.imma_score,
                        delta = EXCLUDED.delta,
                        mochin_quality = EXCLUDED.mochin_quality,
                        limiting_partzuf = EXCLUDED.limiting_partzuf,
                        coupling_factor = EXCLUDED.coupling_factor,
                        abba_boost = EXCLUDED.abba_boost,
                        imma_boost = EXCLUDED.imma_boost,
                        reinforcement_count = EXCLUDED.reinforcement_count,
                        updated_at = NOW()
                """,
                    (
                        assessment.state.value,
                        assessment.abba_score,
                        assessment.imma_score,
                        assessment.delta,
                        assessment.mochin_quality,
                        assessment.limiting_partzuf,
                        assessment.coupling_factor,
                        engine.abba_boost,
                        engine.imma_boost,
                        len(engine.reinforcement_log),
                    ),
                )
    except Exception as e:
        logger.debug("save_zivvug_state: %s", e)


def load_zivvug_state() -> ZivvugEngine | None:
    """Charge l'état du Zivvug depuis DB."""
    try:
        from pool import get_conn

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT abba_boost, imma_boost
                    FROM zivvug_state WHERE id = 1
                """)
                row = cur.fetchone()
                if row:
                    return ZivvugEngine.from_dict(
                        {
                            "abba_boost": row[0] or 0.0,
                            "imma_boost": row[1] or 0.0,
                        }
                    )
    except Exception as e:
        logger.debug("load_zivvug_state: %s", e)
    return None


# ── Schema SQL ──────────────────────────────────────────────────
#
# Sprint 10 Phase E : le schéma canonique vit dans partzufim/zivvug_schema.sql.
# La constante ZIVVUG_SCHEMA ci-dessous reste en fallback programmatique (ex:
# pool.get_conn indisponible — chargement direct depuis le .sql impossible).
#
# Source unique du schéma = fichier .sql. Cette constante est un miroir
# synchronisé (voir test_zivvug_schema_in_sync_with_sql).

from pathlib import Path as _Path  # noqa: E402


def _load_schema_sql() -> str:
    """Charge le schéma canonique depuis partzufim/zivvug_schema.sql.

    Retourne le texte SQL. Fallback sur un schéma minimal si le fichier est
    indisponible (devrait jamais arriver en prod, utile pour packaging).
    """
    sql_path = _Path(__file__).parent / "zivvug_schema.sql"
    try:
        return sql_path.read_text(encoding="utf-8")
    except OSError:
        return (
            "CREATE TABLE IF NOT EXISTS zivvug_state ("
            "id INTEGER PRIMARY KEY DEFAULT 1, "
            "state TEXT NOT NULL DEFAULT 'blocked', "
            "abba_score REAL NOT NULL DEFAULT 0.0, "
            "imma_score REAL NOT NULL DEFAULT 0.0, "
            "delta REAL NOT NULL DEFAULT 0.0, "
            "mochin_quality REAL NOT NULL DEFAULT 0.0, "
            "limiting_partzuf TEXT, "
            "coupling_factor REAL NOT NULL DEFAULT 0.0, "
            "abba_boost REAL NOT NULL DEFAULT 0.0, "
            "imma_boost REAL NOT NULL DEFAULT 0.0, "
            "reinforcement_count INTEGER NOT NULL DEFAULT 0, "
            "updated_at TIMESTAMP DEFAULT NOW(), "
            "CHECK (id = 1));"
        )


ZIVVUG_SCHEMA = _load_schema_sql()
