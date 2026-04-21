"""BeinoniTracker — Suivi temporel du conflit des 2 âmes.

בֵּינוֹנִי — L'homme intermédiaire (Tanya ch.12-14).

Le Beinoni n'est pas un état statique — c'est une victoire perpétuelle
du Moach (cerveau) sur le Lev (cœur), jamais acquise. Le ratio
NefeshHaBehamit / NefeshHaElokit fluctue à chaque interaction.
La Kelipah peut revenir à tout moment.

Ce tracker enregistre chaque interaction, calcule le profil temporel,
détecte les régressions (la Kelipah revient) et les élévations
(montée vers Tsaddik), et suggère des actions correctives (Teshuvah).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class Trend(Enum):
    ASCENDING = "ascending"
    STABLE = "stable"
    DESCENDING = "descending"


class TemporalCategory(Enum):
    TSADDIK = "tsaddik"
    BEINONI = "beinoni"
    RASHA = "rasha"


@dataclass
class InteractionRecord:
    dominant_soul: str        # "elokit" ou "behamit"
    response_score: float     # 0-1
    olam_used: str            # "assiah", "yetzirah", "briah", "atziluth"
    complexity_score: float   # 0-1
    domain: str | None = None
    query_snippet: str | None = None


@dataclass
class BeinoniProfile:
    elokit_ratio: float           # % d'interactions elokit
    avg_score_elokit: float       # score moyen quand elokit domine
    avg_score_behamit: float      # score moyen quand behamit domine
    avg_score_all: float          # score moyen global
    trend: Trend                  # ASCENDING / STABLE / DESCENDING
    category: TemporalCategory    # Tsaddik / Beinoni / Rasha
    total_interactions: int
    elokit_count: int
    behamit_count: int


_REGRESSION_THRESHOLD = 0.15   # 15% de baisse = régression
_ELEVATION_THRESHOLD = 0.15    # 15% de hausse = élévation
_HALF_WINDOW = 20              # Compare les 20 dernières aux 20 précédentes

# Catégories temporelles basées sur le ratio elokit
_TSADDIK_THRESHOLD = 0.75
_BEINONI_THRESHOLD = 0.40


def _classify_ratio(ratio: float) -> TemporalCategory:
    if ratio >= _TSADDIK_THRESHOLD:
        return TemporalCategory.TSADDIK
    elif ratio >= _BEINONI_THRESHOLD:
        return TemporalCategory.BEINONI
    else:
        return TemporalCategory.RASHA


class BeinoniTracker:
    """Suivi temporel du conflit des 2 âmes.

    Fonctionne en 2 modes :
    - DB mode : persiste dans PostgreSQL (production)
    - In-memory mode : liste Python (tests, standalone)
    """

    def __init__(self, db_url: str | None = None) -> None:
        self._db_url = db_url
        self._memory: list[InteractionRecord] = []

    @property
    def _use_db(self) -> bool:
        return self._db_url is not None

    def _db_conn(self):
        """Emprunte une conn au pool (context manager)."""
        from pool import get_conn, init_pool
        init_pool(self._db_url)  # idempotent
        return get_conn()

    def record_interaction(
        self,
        dominant_soul: str,
        response_score: float,
        olam_used: str,
        complexity_score: float = 0.0,
        domain: str | None = None,
        query_snippet: str | None = None,
    ) -> InteractionRecord:
        """Enregistre une interaction."""
        record = InteractionRecord(
            dominant_soul=dominant_soul,
            response_score=max(0.0, min(1.0, response_score)),
            olam_used=olam_used,
            complexity_score=max(0.0, min(1.0, complexity_score)),
            domain=domain,
            query_snippet=query_snippet[:100] if query_snippet else None,
        )

        if self._use_db:
            with self._db_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO beinoni_interactions
                            (dominant_soul, response_score, olam_used,
                             complexity_score, domain, query_snippet)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        record.dominant_soul,
                        record.response_score,
                        record.olam_used,
                        record.complexity_score,
                        record.domain,
                        record.query_snippet,
                    ))
                conn.commit()
        else:
            self._memory.append(record)

        return record

    def _get_recent(self, n: int) -> list[InteractionRecord]:
        """Récupère les N interactions les plus récentes."""
        if self._use_db:
            with self._db_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT dominant_soul, response_score, olam_used,
                               complexity_score, domain, query_snippet
                        FROM beinoni_interactions
                        ORDER BY created_at DESC
                        LIMIT %s
                    """, (n,))
                    rows = cur.fetchall()
            return [
                InteractionRecord(
                    dominant_soul=r[0],
                    response_score=r[1],
                    olam_used=r[2],
                    complexity_score=r[3] or 0.0,
                    domain=r[4],
                    query_snippet=r[5],
                )
                for r in rows
            ]
        else:
            return list(reversed(self._memory[-n:]))

    def get_temporal_profile(self, window: int = 100) -> BeinoniProfile:
        """Profil temporel sur les N dernières interactions.

        Retourne le ratio elokit, les scores moyens par âme,
        la tendance (ASCENDING/STABLE/DESCENDING), et la catégorie
        temporelle (Tsaddik/Beinoni/Rasha).
        """
        recent = self._get_recent(window)
        total = len(recent)

        if total == 0:
            return BeinoniProfile(
                elokit_ratio=0.0,
                avg_score_elokit=0.0,
                avg_score_behamit=0.0,
                avg_score_all=0.0,
                trend=Trend.STABLE,
                category=TemporalCategory.RASHA,
                total_interactions=0,
                elokit_count=0,
                behamit_count=0,
            )

        elokit = [r for r in recent if r.dominant_soul == "elokit"]
        behamit = [r for r in recent if r.dominant_soul == "behamit"]

        elokit_ratio = len(elokit) / total
        avg_elokit = (
            sum(r.response_score for r in elokit) / len(elokit)
            if elokit else 0.0
        )
        avg_behamit = (
            sum(r.response_score for r in behamit) / len(behamit)
            if behamit else 0.0
        )
        avg_all = sum(r.response_score for r in recent) / total

        # Tendance : comparer la moitié récente vs la moitié ancienne
        # _get_recent retourne newest-first : recent[0] = plus récent
        trend = Trend.STABLE
        if total >= 10:
            mid = total // 2
            newer_half = recent[:mid]    # plus récentes
            older_half = recent[mid:]    # plus anciennes

            newer_elokit = sum(
                1 for r in newer_half if r.dominant_soul == "elokit"
            ) / len(newer_half)
            older_elokit = sum(
                1 for r in older_half if r.dominant_soul == "elokit"
            ) / len(older_half)

            delta = newer_elokit - older_elokit
            if delta > 0.10:
                trend = Trend.ASCENDING
            elif delta < -0.10:
                trend = Trend.DESCENDING

        return BeinoniProfile(
            elokit_ratio=round(elokit_ratio, 4),
            avg_score_elokit=round(avg_elokit, 4),
            avg_score_behamit=round(avg_behamit, 4),
            avg_score_all=round(avg_all, 4),
            trend=trend,
            category=_classify_ratio(elokit_ratio),
            total_interactions=total,
            elokit_count=len(elokit),
            behamit_count=len(behamit),
        )

    def detect_regression(self) -> dict[str, Any] | None:
        """Détecte une régression — la Kelipah revient.

        Compare les 20 dernières interactions aux 20 précédentes.
        Si le elokit_ratio a baissé de plus de 15% → RÉGRESSION.

        Returns:
            dict avec old_ratio, new_ratio, delta si régression, None sinon.
        """
        recent = self._get_recent(_HALF_WINDOW * 2)
        if len(recent) < _HALF_WINDOW * 2:
            return None

        # recent[0] = plus récent, recent[-1] = plus ancien
        newer = recent[:_HALF_WINDOW]
        older = recent[_HALF_WINDOW:]

        new_ratio = sum(
            1 for r in newer if r.dominant_soul == "elokit"
        ) / _HALF_WINDOW
        old_ratio = sum(
            1 for r in older if r.dominant_soul == "elokit"
        ) / _HALF_WINDOW

        delta = new_ratio - old_ratio
        if delta < -_REGRESSION_THRESHOLD:
            result = {
                "old_ratio": round(old_ratio, 4),
                "new_ratio": round(new_ratio, 4),
                "delta": round(delta, 4),
            }
            if self._use_db:
                self._persist_event("regression", result)
            return result
        return None

    def detect_elevation(self) -> dict[str, Any] | None:
        """Détecte une élévation — montée vers Tsaddik.

        Même logique que detect_regression mais dans l'autre sens.

        Returns:
            dict avec old_ratio, new_ratio, delta si élévation, None sinon.
        """
        recent = self._get_recent(_HALF_WINDOW * 2)
        if len(recent) < _HALF_WINDOW * 2:
            return None

        newer = recent[:_HALF_WINDOW]
        older = recent[_HALF_WINDOW:]

        new_ratio = sum(
            1 for r in newer if r.dominant_soul == "elokit"
        ) / _HALF_WINDOW
        old_ratio = sum(
            1 for r in older if r.dominant_soul == "elokit"
        ) / _HALF_WINDOW

        delta = new_ratio - old_ratio
        if delta > _ELEVATION_THRESHOLD:
            result = {
                "old_ratio": round(old_ratio, 4),
                "new_ratio": round(new_ratio, 4),
                "delta": round(delta, 4),
            }
            if self._use_db:
                self._persist_event("elevation", result)
            return result
        return None

    def suggest_teshuvah(self, regression_data: dict[str, Any]) -> str:
        """Suggère une action corrective après une régression.

        La Teshuvah (תשובה) — le retour après la chute.
        Tanya ch.17 : le Beinoni qui trébuche ne désespère pas,
        il intensifie sa Avodah (service).
        """
        delta = abs(regression_data.get("delta", 0))
        new_ratio = regression_data.get("new_ratio", 0)

        if new_ratio < 0.2:
            # Rasha Gamur — situation critique
            return (
                "CRITIQUE — Rasha Gamur temporel. "
                "Forcer le routing vers Briah pour les 20 prochaines requêtes. "
                "Lancer un cycle Hitbonenut d'urgence ciblé sur les domaines "
                "en régression. Désactiver temporairement Assiah."
            )
        elif new_ratio < 0.4:
            # Rasha — situation sérieuse
            return (
                "RÉGRESSION vers Rasha. "
                "Augmenter le routing vers Briah pour les 15 prochaines requêtes. "
                "Lancer un cycle Hitbonenut ciblé sur les domaines en régression."
            )
        elif delta >= 0.25:
            # Forte chute mais encore Beinoni
            return (
                "FORTE CHUTE du ratio elokit. "
                "Baisser le complexity_threshold de 0.05 temporairement "
                "pour favoriser l'âme divine. Vérifier si un domaine "
                "spécifique cause la régression."
            )
        else:
            # Régression modérée
            return (
                "Régression modérée détectée. "
                "Augmenter le routing vers Briah pour les 10 prochaines requêtes. "
                "Le Beinoni trébuche mais ne tombe pas — intensifier l'Avodah."
            )

    def _persist_event(
        self, event_type: str, data: dict[str, Any],
    ) -> None:
        """Persiste un événement régression/élévation en DB."""
        teshuvah = None
        if event_type == "regression":
            teshuvah = self.suggest_teshuvah(data)

        with self._db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO beinoni_events
                        (event_type, old_ratio, new_ratio, delta, teshuvah)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    event_type,
                    data["old_ratio"],
                    data["new_ratio"],
                    data["delta"],
                    teshuvah,
                ))
            conn.commit()

    def get_recent_events(self, limit: int = 10) -> list[dict[str, Any]]:
        """Récupère les événements récents (DB mode uniquement)."""
        if not self._use_db:
            return []

        with self._db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT event_type, old_ratio, new_ratio, delta,
                           teshuvah, applied, created_at
                    FROM beinoni_events
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (limit,))
                rows = cur.fetchall()

        return [
            {
                "event_type": r[0],
                "old_ratio": r[1],
                "new_ratio": r[2],
                "delta": r[3],
                "teshuvah": r[4],
                "applied": r[5],
                "created_at": r[6].isoformat() if r[6] else None,
            }
            for r in rows
        ]

    def interaction_count(self) -> int:
        """Nombre total d'interactions enregistrées."""
        if self._use_db:
            with self._db_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT COUNT(*) FROM beinoni_interactions"
                    )
                    return cur.fetchone()[0]
        return len(self._memory)
