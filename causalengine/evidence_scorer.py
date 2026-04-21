"""EvidenceScorer — scoring du niveau de preuve causale.

Évalue si une affirmation causale est :
- correlation_only : "A est associé à B"
- probable_causation : "A cause probablement B" (confounders vérifiés)
- demonstrated_causation : "A cause B" (intervention, RCT, counterfactual)

Anti-Satariel Nogah : dire "possible" sans vérifier = hedging paresseux.
Le score doit être GAGNÉ, pas supposé.
"""

from __future__ import annotations

from causalengine.models import (
    CausalClaim,
    Confounder,
    DirectionAssessment,
    EVIDENCE_RANK,
)


# Seuils pour monter de niveau
MIN_CONFOUNDERS_CHECKED = 3      # Au moins 3 confounders identifiés
MIN_CONTROL_RATIO = 0.5          # Au moins 50% des confounders contrôlés
MIN_HIGH_CONTROL_RATIO = 0.8     # 80% pour demonstrated_causation
DIRECTION_CONFIDENCE_THRESHOLD = 0.6  # Confiance minimale dans la direction


class EvidenceScorer:
    """Score le niveau de preuve d'une affirmation causale.

    Le scoring est conservateur : on ne monte de niveau
    QUE quand les critères sont strictement remplis.
    """

    def __init__(
        self,
        min_confounders: int = MIN_CONFOUNDERS_CHECKED,
        min_control_ratio: float = MIN_CONTROL_RATIO,
    ):
        self.min_confounders = min_confounders
        self.min_control_ratio = min_control_ratio

    def score(
        self,
        claim: CausalClaim,
        confounders: list[Confounder],
        direction: DirectionAssessment | None = None,
    ) -> str:
        """Déterminer le niveau de preuve d'un claim.

        Logic:
        1. Si pas de direction vérifiée → correlation_only (au mieux)
        2. Si confounders insuffisamment contrôlés → correlation_only
        3. Si direction + confounders contrôlés → probable_causation
        4. Si intervention/RCT documenté → demonstrated_causation

        Returns:
            "correlation_only", "probable_causation", ou "demonstrated_causation"
        """
        # Base : toujours commencer au plus bas
        level = "correlation_only"

        # Critères pour probable_causation
        direction_ok = self._direction_adequate(claim, direction)
        confounders_ok = self._confounders_adequate(confounders)

        if direction_ok and confounders_ok:
            level = "probable_causation"

        # Critères pour demonstrated_causation
        if level == "probable_causation":
            if self._intervention_documented(claim, confounders):
                level = "demonstrated_causation"

        return level

    def compute_confidence(
        self,
        evidence_level: str,
        confounders: list[Confounder],
        direction: DirectionAssessment | None = None,
    ) -> float:
        """Calculer la confiance globale dans le claim.

        Formule recalibrée — distingue les confounders par type :
          - contextual (LLM) : impact maximal, reflètent une analyse spécifique
          - domain-specific : impact modéré, pertinents mais génériques au domaine
          - universal : impact minimal, s'appliquent à tout claim

        L'indétermination de direction est le DÉFAUT, pas une preuve
        négative — pénalité légère (absence d'evidence ≠ evidence d'absence).
        """
        base = {
            "correlation_only": 0.35,
            "observed_association": 0.45,
            "probable_causation": 0.6,
            "demonstrated_causation": 0.85,
        }.get(evidence_level, 0.35)

        # Séparer les confounders par type de pertinence
        contextual = [c for c in confounders if c.confounder_domain == "contextual"]
        universal = [c for c in confounders if c.confounder_domain in ("universal", "")]
        domain_specific = [
            c for c in confounders
            if c.confounder_domain not in ("universal", "contextual", "")
        ]

        # --- Bonus ---

        # Contrôle des confounders (pondéré par type)
        for group, weight in [
            (contextual, 0.15),       # Contrôler un confounder LLM = fort signal
            (domain_specific, 0.08),  # Contrôler un confounder de domaine = signal modéré
            (universal, 0.02),        # Contrôler un universel = signal faible
        ]:
            if group:
                controlled = sum(1 for c in group if c.controlled)
                base += (controlled / len(group)) * weight

        # Avoir été enrichi par le LLM = effort d'analyse effectué
        if contextual:
            base += 0.05

        # Direction vérifiée
        if direction:
            if direction.verdict == "forward":
                base += 0.05
            elif direction.verdict == "bidirectional":
                base += 0.03

        # --- Pénalités ---

        # Direction indéterminée : pénalité légère (c'est le défaut)
        if direction and direction.verdict == "indeterminate":
            base -= 0.02

        # Confounders à haute plausibilité non contrôlés
        # Seuls les contextuels et domain-specific comptent pleinement
        relevant = contextual + domain_specific
        if relevant:
            high_uncontrolled = sum(
                1 for c in relevant
                if c.plausibility >= 0.7 and not c.controlled
            )
            base -= high_uncontrolled * 0.04

        # Universels : pénalité minimale (seulement les très plausibles)
        if universal:
            high_universal = sum(
                1 for c in universal
                if c.plausibility >= 0.8 and not c.controlled
            )
            base -= high_universal * 0.01

        return round(max(0.1, min(0.95, base)), 2)

    def can_upgrade(
        self,
        current_level: str,
        target_level: str,
        confounders: list[Confounder],
        direction: DirectionAssessment | None = None,
    ) -> tuple[bool, list[str]]:
        """Vérifier si on peut monter d'un niveau, et sinon pourquoi.

        Returns:
            (can_upgrade, list of missing criteria)
        """
        current_rank = EVIDENCE_RANK.get(current_level, 0)
        target_rank = EVIDENCE_RANK.get(target_level, 0)

        if target_rank <= current_rank:
            return True, []

        missing: list[str] = []

        if target_level in ("probable_causation", "demonstrated_causation"):
            if not self._direction_adequate(None, direction):
                missing.append(
                    "Direction not verified (need forward verdict "
                    f"with confidence >= {DIRECTION_CONFIDENCE_THRESHOLD})"
                )
            if not self._confounders_adequate(confounders):
                controlled = sum(1 for c in confounders if c.controlled)
                total = len(confounders)
                missing.append(
                    f"Confounders insufficiently controlled "
                    f"({controlled}/{total}, need >= {self.min_control_ratio:.0%})"
                )

        if target_level == "demonstrated_causation":
            if not self._intervention_documented(None, confounders):
                missing.append(
                    "No intervention/RCT evidence (need >= 80% confounders "
                    "controlled with documented methods)"
                )

        return len(missing) == 0, missing

    def _direction_adequate(
        self,
        claim: CausalClaim | None,
        direction: DirectionAssessment | None,
    ) -> bool:
        """La direction est-elle suffisamment vérifiée ?"""
        if claim and claim.direction_verified:
            return True
        if direction is None:
            return False
        return (
            direction.verdict in ("forward", "bidirectional")
            and direction.forward_plausibility >= DIRECTION_CONFIDENCE_THRESHOLD
        )

    def _confounders_adequate(self, confounders: list[Confounder]) -> bool:
        """Les confounders sont-ils suffisamment contrôlés ?"""
        if len(confounders) < self.min_confounders:
            return False

        controlled = sum(1 for c in confounders if c.controlled)
        ratio = controlled / len(confounders) if confounders else 0

        return ratio >= self.min_control_ratio

    def _intervention_documented(
        self,
        claim: CausalClaim | None,
        confounders: list[Confounder],
    ) -> bool:
        """Y a-t-il une preuve d'intervention (RCT, expérimentation) ?"""
        if not confounders:
            return False

        # Pour demonstrated_causation : contrôle élevé + méthodes documentées
        controlled_with_method = sum(
            1 for c in confounders
            if c.controlled and c.how_controlled
        )
        total = len(confounders)

        return (
            total >= self.min_confounders
            and controlled_with_method / total >= MIN_HIGH_CONTROL_RATIO
        )
