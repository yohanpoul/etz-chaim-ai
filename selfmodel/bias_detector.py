"""BiasDetector — détection de biais récurrents.

Analyse les patterns dans les erreurs passées pour identifier
les biais systémiques du système.

Aspect Chokmah de Da'at : l'intuition structurée, ce que le système
"sent" sur ses propres tendances sans qu'on le lui dise explicitement.
"""

from __future__ import annotations

from selfmodel.models import BiasEntry, SelfState


# Seuils de détection
OVERCONFIDENCE_THRESHOLD = 0.3   # Si avg_brier > 0.3, overconfidence probable
DECLINE_RATE_THRESHOLD = 0.3     # Si decline_rate > 0.3, domain_blind_spot
HIGH_REJECTION_RATE = 0.7        # Si taux de rejet Gevurah > 0.7
CONTRADICTION_RATE = 0.2         # Si contradictions/total > 0.2


class BiasDetector:
    """Détecte les biais récurrents du système.

    Analyse un SelfState (ou une série de SelfStates) pour identifier
    les patterns qui indiquent un biais systémique.
    """

    def __init__(
        self,
        overconfidence_threshold: float = OVERCONFIDENCE_THRESHOLD,
        decline_rate_threshold: float = DECLINE_RATE_THRESHOLD,
    ):
        self.overconfidence_threshold = overconfidence_threshold
        self.decline_rate_threshold = decline_rate_threshold

    def detect(self, state: SelfState) -> list[BiasEntry]:
        """Détecter les biais à partir d'un état du système."""
        biases: list[BiasEntry] = []

        biases.extend(self._check_overconfidence(state))
        biases.extend(self._check_underconfidence(state))
        biases.extend(self._check_blind_spots(state))
        biases.extend(self._check_premature_closure(state))
        biases.extend(self._check_scope_creep(state))
        biases.extend(self._check_confirmation_bias(state))

        return biases

    def detect_from_history(
        self, states: list[SelfState],
    ) -> list[BiasEntry]:
        """Détecter les biais à partir de l'historique des états.

        Les biais récurrents (détectés dans >50% des snapshots)
        ont une sévérité plus élevée.
        """
        if not states:
            return []

        # Collect biases from each state
        bias_counts: dict[str, list[BiasEntry]] = {}
        for state in states:
            for bias in self.detect(state):
                key = f"{bias.bias_type}:{bias.domain}"
                bias_counts.setdefault(key, []).append(bias)

        # Biases found in >50% of snapshots are more severe
        result: list[BiasEntry] = []
        for key, entries in bias_counts.items():
            frequency = len(entries) / len(states)
            representative = entries[-1]  # Most recent
            representative.severity = min(
                1.0, representative.severity * (1 + frequency)
            )
            representative.evidence["frequency"] = round(frequency, 2)
            representative.evidence["occurrences"] = len(entries)
            representative.evidence["total_snapshots"] = len(states)
            result.append(representative)

        return sorted(result, key=lambda b: b.severity, reverse=True)

    def _check_overconfidence(self, state: SelfState) -> list[BiasEntry]:
        """Overconfidence : SelfMap dit "je suis bon" mais les résultats disent le contraire."""
        biases = []
        hod = state.hod_stats
        if not hod:
            return biases

        overconfident = hod.get("overconfident_domains", [])
        for domain in overconfident:
            biases.append(BiasEntry(
                bias_type="overconfidence",
                description=(
                    f"Overconfidence in '{domain}': SelfMap confidence exceeds "
                    f"actual performance (Brier score indicates miscalibration)."
                ),
                evidence={"domain": domain, "source": "hod_calibration"},
                severity=0.6,
                domain=domain,
                mitigation=f"Lower confidence for '{domain}', request external validation.",
            ))

        avg_brier = hod.get("avg_brier", 0)
        if avg_brier > self.overconfidence_threshold:
            biases.append(BiasEntry(
                bias_type="overconfidence",
                description=(
                    f"Global overconfidence: avg Brier score {avg_brier:.2f} "
                    f"exceeds threshold {self.overconfidence_threshold}."
                ),
                evidence={"avg_brier": avg_brier, "source": "hod_calibration"},
                severity=min(1.0, avg_brier),
                mitigation="Systematic recalibration needed.",
            ))

        return biases

    def _check_underconfidence(self, state: SelfState) -> list[BiasEntry]:
        """Underconfidence : le système décline des tâches qu'il pourrait réussir."""
        biases = []
        hod = state.hod_stats
        if not hod:
            return biases

        underconfident = hod.get("underconfident_domains", [])
        for domain in underconfident:
            biases.append(BiasEntry(
                bias_type="underconfidence",
                description=(
                    f"Underconfidence in '{domain}': actual performance exceeds "
                    f"SelfMap confidence."
                ),
                evidence={"domain": domain, "source": "hod_calibration"},
                severity=0.4,
                domain=domain,
                mitigation=f"Raise confidence for '{domain}'.",
            ))

        decline_rate = hod.get("decline_rate", 0)
        if decline_rate > self.decline_rate_threshold:
            biases.append(BiasEntry(
                bias_type="underconfidence",
                description=(
                    f"High decline rate ({decline_rate:.1%}): system may be "
                    f"declining tasks it could handle."
                ),
                evidence={"decline_rate": decline_rate, "source": "hod_routing"},
                severity=min(1.0, decline_rate),
                mitigation="Review declined tasks for false negatives.",
            ))

        return biases

    def _check_blind_spots(self, state: SelfState) -> list[BiasEntry]:
        """Domain blind spots : domaines jamais évalués ou faibles sans conscience."""
        biases = []
        hod = state.hod_stats
        if not hod:
            return biases

        unknown = hod.get("unknown_domains", [])
        for domain in unknown:
            biases.append(BiasEntry(
                bias_type="domain_blind_spot",
                description=f"Domain '{domain}' never evaluated — blind spot.",
                evidence={"domain": domain, "source": "hod_describe"},
                severity=0.3,
                domain=domain,
                mitigation=f"Evaluate performance in '{domain}'.",
            ))

        return biases

    def _check_premature_closure(self, state: SelfState) -> list[BiasEntry]:
        """Premature closure : Gevurah trop sévère (Golachab)."""
        biases = []
        gevurah = state.gevurah_stats
        if not gevurah:
            return biases

        level = gevurah.get("level", "healthy")
        if level in ("nogah", "ruach", "anan", "mamash"):
            severity_map = {"nogah": 0.3, "ruach": 0.5, "anan": 0.7, "mamash": 0.9}
            biases.append(BiasEntry(
                bias_type="premature_closure",
                description=(
                    f"AutoJudge diagnostic: {level}. "
                    f"Issues: {', '.join(gevurah.get('issues', []))}"
                ),
                evidence={"level": level, "issues": gevurah.get("issues", [])},
                severity=severity_map.get(level, 0.5),
                mitigation="Review AutoJudge thresholds.",
            ))

        return biases

    def _check_scope_creep(self, state: SelfState) -> list[BiasEntry]:
        """Scope creep : Chesed explore trop (Gamchicoth)."""
        biases = []
        chesed = state.chesed_stats
        if not chesed:
            return biases

        level = chesed.get("level", "healthy")
        if level in ("nogah", "ruach", "anan", "mamash"):
            severity_map = {"nogah": 0.3, "ruach": 0.5, "anan": 0.7, "mamash": 0.9}
            biases.append(BiasEntry(
                bias_type="scope_creep",
                description=(
                    f"ExplorationEngine diagnostic: {level}. "
                    f"Issues: {', '.join(chesed.get('issues', []))}"
                ),
                evidence={"level": level, "issues": chesed.get("issues", [])},
                severity=severity_map.get(level, 0.5),
                mitigation="Tighten exploration budget.",
            ))

        return biases

    def _check_confirmation_bias(self, state: SelfState) -> list[BiasEntry]:
        """Confirmation bias : Tiferet ne résout pas les contradictions (Thagirion)."""
        biases = []
        tiferet = state.tiferet_stats
        if not tiferet:
            return biases

        level = tiferet.get("level", "healthy")
        if level in ("anan", "mamash"):
            biases.append(BiasEntry(
                bias_type="confirmation_bias",
                description=(
                    f"DissensuEngine diagnostic: {level} — "
                    f"contradictions may be suppressed. "
                    f"Issues: {', '.join(tiferet.get('issues', []))}"
                ),
                evidence={"level": level, "issues": tiferet.get("issues", [])},
                severity=0.7 if level == "anan" else 0.9,
                mitigation="Audit syntheses for suppressed contradictions.",
            ))

        return biases
