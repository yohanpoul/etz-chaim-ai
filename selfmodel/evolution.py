"""Evolution — suivi de l'évolution du système dans le temps.

Le Partzuf de Da'at : comment le système change, s'améliore,
ou se dégrade au fil des snapshots.

"improving", "stable", ou "degrading" — la tendance.
"""

from __future__ import annotations

from selfmodel.models import EvolutionSnapshot, SelfState


# Seuils de tendance
IMPROVING_THRESHOLD = 0.05   # Amélioration > 5% → improving
DEGRADING_THRESHOLD = -0.05  # Dégradation > 5% → degrading


class EvolutionTracker:
    """Suivi de l'évolution du système dans le temps.

    Compare l'état actuel avec l'état précédent pour détecter
    les tendances : amélioration, stabilité, dégradation.
    """

    def __init__(
        self,
        improving_threshold: float = IMPROVING_THRESHOLD,
        degrading_threshold: float = DEGRADING_THRESHOLD,
    ):
        self.improving_threshold = improving_threshold
        self.degrading_threshold = degrading_threshold

    def snapshot(
        self,
        current_state: SelfState,
        previous_snapshot: EvolutionSnapshot | None = None,
    ) -> EvolutionSnapshot:
        """Créer un snapshot d'évolution à partir de l'état courant.

        Compare avec le snapshot précédent pour déterminer la tendance.
        """
        health = self._compute_health(current_state)

        if previous_snapshot is None:
            return EvolutionSnapshot(
                yesod_health=health["yesod"],
                hod_health=health["hod"],
                netzach_health=health["netzach"],
                tiferet_health=health["tiferet"],
                gevurah_health=health["gevurah"],
                chesed_health=health["chesed"],
                overall_health=health["overall"],
                trend="stable",
                trend_details={"reason": "first snapshot, no comparison"},
            )

        # Comparer avec le snapshot précédent
        delta = health["overall"] - previous_snapshot.overall_health
        trend, details = self._determine_trend(health, previous_snapshot, delta)

        return EvolutionSnapshot(
            yesod_health=health["yesod"],
            hod_health=health["hod"],
            netzach_health=health["netzach"],
            tiferet_health=health["tiferet"],
            gevurah_health=health["gevurah"],
            chesed_health=health["chesed"],
            overall_health=health["overall"],
            trend=trend,
            trend_details=details,
        )

    def compute_trend_from_history(
        self, snapshots: list[EvolutionSnapshot],
    ) -> str:
        """Déterminer la tendance globale à partir de l'historique.

        Utilise les 3 derniers snapshots au minimum.
        """
        if len(snapshots) < 2:
            return "stable"

        recent = snapshots[:3]  # Most recent first
        deltas = []
        for i in range(len(recent) - 1):
            deltas.append(recent[i].overall_health - recent[i + 1].overall_health)

        avg_delta = sum(deltas) / len(deltas)

        if avg_delta > self.improving_threshold:
            return "improving"
        elif avg_delta < self.degrading_threshold:
            return "degrading"
        return "stable"

    def _compute_health(self, state: SelfState) -> dict[str, float]:
        """Calculer la santé de chaque Sephirah à partir de l'état."""
        yesod = self._health_yesod(state.yesod_stats)
        hod = self._health_hod(state.hod_stats)
        netzach = self._health_netzach(state.netzach_stats)
        tiferet = self._health_diagnostic(state.tiferet_stats)
        gevurah = self._health_diagnostic(state.gevurah_stats)
        chesed = self._health_diagnostic(state.chesed_stats)

        scores = [yesod, hod, netzach, tiferet, gevurah, chesed]
        overall = sum(scores) / len(scores)

        return {
            "yesod": round(yesod, 3),
            "hod": round(hod, 3),
            "netzach": round(netzach, 3),
            "tiferet": round(tiferet, 3),
            "gevurah": round(gevurah, 3),
            "chesed": round(chesed, 3),
            "overall": round(overall, 3),
        }

    def _health_yesod(self, stats: dict) -> float:
        """Santé de Yesod : mémoire saine ?"""
        if not stats or "error" in stats:
            return 0.5  # Unknown → neutral

        total = stats.get("total_entries", 0)
        if total == 0:
            return 0.5

        active_ratio = stats.get("active_entries", 0) / max(total, 1)
        contradiction_penalty = min(
            0.3, stats.get("contradictions_open", 0) * 0.05
        )
        confidence = stats.get("avg_confidence", 0.5)

        return max(0.0, min(1.0,
            active_ratio * 0.4 + confidence * 0.4 - contradiction_penalty + 0.2
        ))

    def _health_hod(self, stats: dict) -> float:
        """Santé de Hod : self-knowledge précise ?"""
        if not stats or "error" in stats:
            return 0.5

        evaluated = stats.get("evaluated_domains", 0)
        total = stats.get("total_domains", 1)
        coverage = evaluated / max(total, 1)

        avg_comp = stats.get("avg_competence", 0.5)
        decline_penalty = min(0.3, stats.get("decline_rate", 0) * 0.5)

        return max(0.0, min(1.0,
            coverage * 0.4 + avg_comp * 0.4 - decline_penalty + 0.2
        ))

    def _health_netzach(self, stats: dict) -> float:
        """Santé de Netzach : intentions en cours ?"""
        if not stats or "error" in stats:
            return 0.5

        active = stats.get("active_intentions", 0)
        if active == 0:
            return 0.6  # Pas d'intentions = neutre-bon

        # Check progress of active intentions
        intentions = stats.get("intentions", [])
        if not intentions:
            return 0.5

        avg_progress = sum(
            i.get("progress", 0) for i in intentions
        ) / len(intentions)

        return max(0.0, min(1.0, 0.3 + avg_progress * 0.7))

    def _health_diagnostic(self, stats: dict) -> float:
        """Santé d'un module avec diagnostic standard (level/issues)."""
        if not stats or "error" in stats:
            return 0.5

        level = stats.get("level", "healthy")
        health_map = {
            "healthy": 0.9,
            "nogah": 0.7,
            "ruach": 0.5,
            "anan": 0.3,
            "mamash": 0.1,
        }
        return health_map.get(level, 0.5)

    def _determine_trend(
        self,
        current_health: dict[str, float],
        previous: EvolutionSnapshot,
        delta: float,
    ) -> tuple[str, dict]:
        """Déterminer la tendance et les détails."""
        details: dict = {"overall_delta": round(delta, 4)}

        # Track per-sephirah changes
        prev_health = previous.health_by_sephirah
        improving_sephiroth = []
        degrading_sephiroth = []

        for seph in ["yesod", "hod", "netzach", "tiferet", "gevurah", "chesed"]:
            seph_delta = current_health[seph] - prev_health.get(seph, 0.5)
            if seph_delta > self.improving_threshold:
                improving_sephiroth.append(seph)
            elif seph_delta < self.degrading_threshold:
                degrading_sephiroth.append(seph)

        details["improving_sephiroth"] = improving_sephiroth
        details["degrading_sephiroth"] = degrading_sephiroth

        if delta > self.improving_threshold:
            trend = "improving"
        elif delta < self.degrading_threshold:
            trend = "degrading"
        else:
            trend = "stable"

        return trend, details
