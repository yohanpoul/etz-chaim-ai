"""LamedBridge — Pont vers FailureToInsight.

Le sentier Lamed (ל) : Gevurah→Tiferet.
Les rejets ne sont plus jetés — ils passent par FailureToInsight,
sont classifiés par la taxonomie des Qliphoth, et transformés en Nitzotzot.

"Même dans les Qliphoth les plus denses, des Nitzotzot attendent."
"""

from __future__ import annotations

from uuid import UUID

from autojudge.models import Experiment, IterationResult, MultiScore


class LamedBridge:
    """Pont vers FailureToInsight — les rejets deviennent des insights."""

    def __init__(self, failure_to_insight=None):
        self.fti = failure_to_insight

    @property
    def connected(self) -> bool:
        return self.fti is not None

    def process_rejection(
        self,
        domain_id: str,
        hypothesis: str,
        original: str | None,
        modified: str | None,
        multi_score: MultiScore | None = None,
        explanation: str = "",
    ) -> tuple[UUID | None, bool]:
        """Chaque rejet passe par le sentier Lamed.

        Returns (failure_analysis_id, nitzotzot_extracted).
        """
        if not self.fti:
            return None, False

        # Construire la description de l'échec
        desc_parts = [f"Experiment rejected in domain '{domain_id}'"]
        desc_parts.append(f"Hypothesis: {hypothesis}")
        if explanation:
            desc_parts.append(f"Reason: {explanation}")
        if multi_score:
            desc_parts.append(
                f"Scores: gevurah={multi_score.gevurah:.2f}, "
                f"chesed={multi_score.chesed:.2f}, "
                f"tiferet={multi_score.tiferet:.2f}, "
                f"hod={multi_score.hod:.2f}, "
                f"yesod={multi_score.yesod:.2f}, "
                f"overall={multi_score.overall:.2f}"
            )

        description = ". ".join(desc_parts)

        # Classifier la qliphah basée sur les scores
        qliphah = self._infer_qliphah(multi_score)

        context = {
            "domain": domain_id,
            "hypothesis": hypothesis,
        }
        if multi_score:
            context["scores"] = {
                "gevurah": multi_score.gevurah,
                "chesed": multi_score.chesed,
                "tiferet": multi_score.tiferet,
                "hod": multi_score.hod,
                "yesod": multi_score.yesod,
                "overall": multi_score.overall,
            }

        # Analyser via FailureToInsight
        analysis = self.fti.analyze_failure(
            description=description,
            source_type="experiment",
            context=context,
            domain=domain_id,
            qliphah_override=qliphah,
        )

        # Extraire les Nitzotzot
        nitzotzot = self.fti.extract_nitzotzot(analysis.id)
        extracted = len(nitzotzot) > 0

        return analysis.id, extracted

    def process_quarantine(
        self,
        domain_id: str,
        hypothesis: str,
        multi_score: MultiScore | None = None,
    ) -> tuple[UUID | None, bool]:
        """Enregistrer une mise en quarantaine — pas un échec complet.

        Returns (failure_analysis_id, nitzotzot_extracted).
        Même une quarantaine contient des Nitzotzot — le Birur opère
        sur tout ce qui passe par le sentier Lamed.
        """
        if not self.fti:
            return None, False

        description = (
            f"Experiment quarantined in domain '{domain_id}'. "
            f"Hypothesis: {hypothesis}. Promising but below threshold."
        )
        if multi_score:
            description += (
                f" Overall: {multi_score.overall:.2f}"
            )

        analysis = self.fti.analyze_failure(
            description=description,
            source_type="experiment",
            domain=domain_id,
            qliphah_override="golachab",
            severity_override="nogah",
        )

        # Extraire les Nitzotzot — même une quarantaine enseigne
        nitzotzot = self.fti.extract_nitzotzot(analysis.id)
        extracted = len(nitzotzot) > 0

        return analysis.id, extracted

    def get_guidance(self, domain: str | None = None):
        """Obtenir guidance du graphe d'échecs pour les prochaines hypothèses."""
        if not self.fti:
            return None
        return self.fti.guide_next_hypothesis(domain=domain)

    def _infer_qliphah(self, scores: MultiScore | None) -> str:
        """Inférer la qliphah à partir des scores.

        - golachab : sur-filtrage (rejet systématique, quality basse)
        - thagirion : fausse harmonie (quality haute mais cohérence basse)
        - samael : fausse confiance (tout semble bon mais ne l'est pas)
        """
        if not scores:
            return "golachab"

        # Quality haute mais cohérence basse → thagirion
        if scores.gevurah > 0.6 and scores.tiferet < 0.3:
            return "thagirion"

        # Tout bas → golachab (sur-filtrage)
        if scores.overall < 0.3:
            return "golachab"

        # Default pour les rejets
        return "golachab"
