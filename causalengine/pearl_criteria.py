"""PearlCriteria — classification selon la hiérarchie causale de Pearl.

Les 3 niveaux de la hiérarchie de Judea Pearl :
  1. Association : P(Y|X) — observer, corrélation
  2. Intervention : P(Y|do(X)) — intervenir, expérimentation
  3. Counterfactual : P(Y_x|X', Y') — imaginer, que serait-il arrivé

Chaque niveau subsume le précédent mais n'est PAS réductible à lui.
L'escalier est à sens unique : on ne descend que par défaut.

Anti-Satariel Ruach : présenter une observation (niveau 1)
comme si elle suffisait à prouver la causalité (niveau 2+).
"""

from __future__ import annotations

from causalengine.models import (
    CausalClaim,
    CausalGraph,
    Confounder,
    DirectionAssessment,
    EVIDENCE_RANK,
)


# Mapping entre evidence_level des claims et Pearl level des graphes
EVIDENCE_TO_PEARL = {
    "correlation_only": "association",
    "probable_causation": "intervention",
    "demonstrated_causation": "counterfactual",
}

PEARL_TO_EVIDENCE = {v: k for k, v in EVIDENCE_TO_PEARL.items()}

PEARL_RANK = {
    "association": 0,
    "intervention": 1,
    "counterfactual": 2,
}


class PearlCriteria:
    """Classifier les claims/graphs selon les 3 niveaux de Pearl.

    La classification est conservatrice : on ne monte que
    quand les critères sont strictement remplis.
    """

    def classify_claim(self, claim: CausalClaim) -> str:
        """Déterminer le Pearl level d'un claim individuel.

        Returns:
            "association", "intervention", ou "counterfactual"
        """
        return EVIDENCE_TO_PEARL.get(claim.evidence_level, "association")

    def classify_graph(self, graph: CausalGraph) -> str:
        """Déterminer le Pearl level d'un graphe entier.

        Le graphe est aussi fort que son maillon le plus faible.
        """
        if not graph.edges:
            return "association"

        min_rank = 2  # counterfactual
        for edge in graph.edges:
            pearl = EVIDENCE_TO_PEARL.get(edge.evidence_level, "association")
            rank = PEARL_RANK.get(pearl, 0)
            if rank < min_rank:
                min_rank = rank

        rank_to_level = {0: "association", 1: "intervention", 2: "counterfactual"}
        return rank_to_level[min_rank]

    def what_is_needed(
        self,
        current_level: str,
        target_level: str,
    ) -> list[str]:
        """Que faut-il pour monter d'un Pearl level ?

        Returns:
            Liste de critères manquants (vide si déjà au niveau cible).
        """
        current_rank = PEARL_RANK.get(current_level, 0)
        target_rank = PEARL_RANK.get(target_level, 0)

        if current_rank >= target_rank:
            return []

        needed: list[str] = []

        if current_rank < 1 and target_rank >= 1:
            needed.extend([
                "Intervention evidence required: P(Y|do(X)) not just P(Y|X)",
                "Confounders must be identified and controlled",
                "Direction of causation must be verified (A→B, not B→A)",
                "At least 50% of known confounders must be controlled",
            ])

        if current_rank < 2 and target_rank >= 2:
            needed.extend([
                "Counterfactual evidence required: P(Y_x|X', Y')",
                "Must answer: 'what would have happened if X had not occurred?'",
                "Requires RCT, natural experiment, or rigorous causal design",
                "At least 80% of confounders controlled with documented methods",
            ])

        return needed

    def assess_upgrade_feasibility(
        self,
        claim: CausalClaim,
        confounders: list[Confounder],
        direction: DirectionAssessment | None = None,
    ) -> dict:
        """Évaluer la faisabilité d'un upgrade pour un claim.

        Returns:
            {
                "current_pearl": str,
                "next_pearl": str | None,
                "feasible": bool,
                "missing": list[str],
                "progress": float,  # 0.0 - 1.0
            }
        """
        current = self.classify_claim(claim)
        current_rank = PEARL_RANK[current]

        if current_rank >= 2:
            return {
                "current_pearl": current,
                "next_pearl": None,
                "feasible": False,
                "missing": [],
                "progress": 1.0,
            }

        next_levels = {0: "intervention", 1: "counterfactual"}
        next_pearl = next_levels[current_rank]

        missing: list[str] = []
        total_criteria = 0
        met_criteria = 0

        if current_rank == 0:
            # Pour monter de association → intervention
            total_criteria = 4

            # Critère 1 : direction vérifiée
            if claim.direction_verified or (
                direction and direction.verdict in ("forward", "bidirectional")
                and direction.forward_plausibility >= 0.6
            ):
                met_criteria += 1
            else:
                missing.append("Direction not verified")

            # Critère 2 : au moins 3 confounders identifiés
            if len(confounders) >= 3:
                met_criteria += 1
            else:
                missing.append(f"Need >= 3 confounders identified (have {len(confounders)})")

            # Critère 3 : au moins 50% contrôlés
            if confounders:
                controlled = sum(1 for c in confounders if c.controlled)
                ratio = controlled / len(confounders)
                if ratio >= 0.5:
                    met_criteria += 1
                else:
                    missing.append(f"Need >= 50% confounders controlled ({controlled}/{len(confounders)})")
            else:
                missing.append("No confounders to control")

            # Critère 4 : confounders_controlled flag
            if claim.confounders_controlled:
                met_criteria += 1
            else:
                missing.append("Confounders not marked as controlled on claim")

        elif current_rank == 1:
            # Pour monter de intervention → counterfactual
            total_criteria = 3

            # Critère 1 : 80% contrôlés avec méthode documentée
            if confounders:
                controlled_with_method = sum(
                    1 for c in confounders
                    if c.controlled and c.how_controlled
                )
                ratio = controlled_with_method / len(confounders) if confounders else 0
                if ratio >= 0.8:
                    met_criteria += 1
                else:
                    missing.append(
                        f"Need >= 80% confounders controlled with method "
                        f"({controlled_with_method}/{len(confounders)})"
                    )
            else:
                missing.append("No confounders identified")

            # Critère 2 : au moins 3 confounders
            if len(confounders) >= 3:
                met_criteria += 1
            else:
                missing.append(f"Need >= 3 confounders (have {len(confounders)})")

            # Critère 3 : direction vérifiée
            if claim.direction_verified or (
                direction and direction.verdict == "forward"
                and direction.forward_plausibility >= 0.8
            ):
                met_criteria += 1
            else:
                missing.append("Need strong direction evidence (forward, >= 0.8)")

        progress = met_criteria / total_criteria if total_criteria > 0 else 0.0

        return {
            "current_pearl": current,
            "next_pearl": next_pearl,
            "feasible": len(missing) == 0,
            "missing": missing,
            "progress": round(progress, 2),
        }

    def format_pearl_level(self, level: str) -> str:
        """Description lisible d'un Pearl level."""
        descriptions = {
            "association": (
                "Association (Pearl L1) — P(Y|X) : "
                "correlation observed, no causal claim warranted"
            ),
            "intervention": (
                "Intervention (Pearl L2) — P(Y|do(X)) : "
                "causal effect tested via intervention or controlled study"
            ),
            "counterfactual": (
                "Counterfactual (Pearl L3) — P(Y_x|X', Y') : "
                "causal mechanism established via counterfactual reasoning"
            ),
        }
        return descriptions.get(level, f"Unknown Pearl level: {level}")
