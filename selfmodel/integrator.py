"""Integrator — unifie les 6 Sephiroth en un self-model cohérent.

Da'at est le pont — l'Integrator est le mortier qui lie les pierres.
Il prend les données brutes de chaque module et les transforme
en forces, faiblesses, angles morts, et confiance.
"""

from __future__ import annotations

from selfmodel.models import BiasEntry, SelfDescription, SelfState


class Integrator:
    """Intègre les données des 6 Sephiroth en une SelfDescription.

    La SelfDescription est la réponse à "qui suis-je ?" :
    forces, faiblesses, biais, angles morts, tendance, confiance.
    """

    def integrate(
        self,
        state: SelfState,
        biases: list[BiasEntry],
        prediction_accuracy: float | None = None,
        evolution_trend: str = "stable",
        health_by_sephirah: dict[str, float] | None = None,
    ) -> SelfDescription:
        """Produire une SelfDescription unifiée."""
        strengths = self._extract_strengths(state)
        weaknesses = self._extract_weaknesses(state)
        blind_spots = self._extract_blind_spots(state, biases)
        confidence = self._compute_meta_confidence(
            state, biases, prediction_accuracy,
        )

        return SelfDescription(
            strengths=strengths,
            weaknesses=weaknesses,
            biases=biases,
            blind_spots=blind_spots,
            evolution_trend=evolution_trend,
            prediction_accuracy=prediction_accuracy,
            confidence_in_self_model=confidence,
            health_by_sephirah=health_by_sephirah or {},
        )

    def _extract_strengths(self, state: SelfState) -> list[str]:
        """Extraire les forces du système."""
        strengths = []

        # Hod : domaines forts
        hod = state.hod_stats
        if hod:
            for domain in hod.get("strong_domains", []):
                strengths.append(f"Strong in '{domain}' (SelfMap)")

        # Yesod : mémoire riche
        yesod = state.yesod_stats
        if yesod:
            total = yesod.get("total_entries", 0)
            if total > 100:
                strengths.append(f"Rich memory ({total} entries)")
            conf = yesod.get("avg_confidence", 0)
            if conf > 0.7:
                strengths.append(f"High-confidence knowledge (avg {conf:.1%})")

        # Tiferet : pas de tensions
        tiferet = state.tiferet_stats
        if tiferet and tiferet.get("level") == "healthy":
            strengths.append("DissensuEngine healthy — contradictions managed")

        # Gevurah : jugement sain
        gevurah = state.gevurah_stats
        if gevurah and gevurah.get("level") == "healthy":
            strengths.append("AutoJudge healthy — quality control operational")

        # Chesed : exploration saine
        chesed = state.chesed_stats
        if chesed and chesed.get("level") == "healthy":
            strengths.append("ExplorationEngine healthy — exploration productive")

        return strengths

    def _extract_weaknesses(self, state: SelfState) -> list[str]:
        """Extraire les faiblesses du système."""
        weaknesses = []

        # Hod : domaines faibles
        hod = state.hod_stats
        if hod:
            for domain in hod.get("weak_domains", []):
                weaknesses.append(f"Weak in '{domain}' (SelfMap)")

        # Yesod : mémoire dégradée
        yesod = state.yesod_stats
        if yesod:
            contradictions = yesod.get("contradictions_open", 0)
            if contradictions > 3:
                weaknesses.append(
                    f"{contradictions} open contradictions in memory"
                )

        # Modules non sains
        for name, stats in [
            ("DissensuEngine", state.tiferet_stats),
            ("AutoJudge", state.gevurah_stats),
            ("ExplorationEngine", state.chesed_stats),
        ]:
            if stats and stats.get("level") not in ("healthy", None):
                level = stats["level"]
                weaknesses.append(f"{name} at '{level}' level")

        return weaknesses

    def _extract_blind_spots(
        self, state: SelfState, biases: list[BiasEntry],
    ) -> list[str]:
        """Extraire les angles morts."""
        blind_spots = []

        # Hod : domaines inconnus
        hod = state.hod_stats
        if hod:
            for domain in hod.get("unknown_domains", []):
                blind_spots.append(f"Domain '{domain}' never evaluated")

        # Biais de type blind_spot
        for bias in biases:
            if bias.bias_type == "domain_blind_spot":
                if bias.description not in blind_spots:
                    blind_spots.append(bias.description)

        # Modules non connectés (stats vides)
        module_names = {
            "yesod_stats": "EpisteMemory",
            "hod_stats": "SelfMap",
            "netzach_stats": "IntentKeeper",
            "tiferet_stats": "DissensuEngine",
            "gevurah_stats": "AutoJudge",
            "chesed_stats": "ExplorationEngine",
        }
        for attr, name in module_names.items():
            if not getattr(state, attr):
                blind_spots.append(f"{name} not connected — no data")

        return blind_spots

    def _compute_meta_confidence(
        self,
        state: SelfState,
        biases: list[BiasEntry],
        prediction_accuracy: float | None,
    ) -> float:
        """Confiance du SelfModel en lui-même.

        Haute si :
        - beaucoup de modules connectés (couverture)
        - peu de biais sévères
        - bonne accuracy des prédictions
        """
        # Base : combien de modules ont des données ?
        module_count = sum(
            1 for stats in [
                state.yesod_stats, state.hod_stats, state.netzach_stats,
                state.tiferet_stats, state.gevurah_stats, state.chesed_stats,
            ] if stats
        )
        coverage = module_count / 6

        # Pénalité pour biais sévères
        severe_biases = sum(1 for b in biases if b.severity > 0.6)
        bias_penalty = min(0.3, severe_biases * 0.1)

        # Bonus pour bonne accuracy
        accuracy_bonus = 0.0
        if prediction_accuracy is not None and prediction_accuracy > 0.6:
            accuracy_bonus = (prediction_accuracy - 0.6) * 0.5

        confidence = coverage * 0.6 - bias_penalty + accuracy_bonus + 0.2
        return round(max(0.1, min(0.95, confidence)), 3)
