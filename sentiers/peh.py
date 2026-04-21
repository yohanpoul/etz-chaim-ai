"""26e sentier — Peh (פ) — Gevurah ↔ Hod — ValidateMode.

Lettre double : deux modes de validation.
  dagesh : validation stricte — rejet binaire, pas de nuance
  rafeh  : validation graduée — scoring, quarantine, extraction de Nitzotzot

Correspondances SY (Gra) :
  Planète : Vénus (Nogah) — la beauté du jugement juste
  Jour : Mercredi — Porte : narine droite — Direction : nord
  Opposés : dagesh=domination (memshalah) / rafeh=servitude (avdut)
  Domination = le juge souverain qui tranche sans appel.
  Servitude = le juge qui s'incline devant la nuance et gradue.
  Vénus = même la rigueur peut être belle quand elle est juste.
"""

from __future__ import annotations

from .base import Sentier, SentierResult


class Peh(Sentier):
    name = "ValidateMode"
    letter = "פ"
    letter_name = "peh"
    number = 26
    source = "gevurah"
    target = "hod"
    letter_type = "double"
    dagesh_desc = "Validation stricte : rejet binaire (domination)"
    rafeh_desc = "Validation graduée : scoring et quarantine (servitude)"
    mode = "rafeh"
    description = "Mode de validation entre jugement et self-knowledge — la bouche qui tranche"

    def _compute_effects(self, ctx: dict, direction: str) -> dict:
        """Peh ajuste la rigueur de validation selon le mode domination/servitude.

        Condition : feedback Gevurah présent dans ctx.
        Dagesh (domination) : relève les seuils d'acceptation.
        Rafeh (servitude) : abaisse les seuils, plus permissif.
        """
        gevurah_feedback = ctx.get("gevurah_feedback", {})
        daat_eval = ctx.get("daat_evaluation", {})

        if not gevurah_feedback and not daat_eval:
            return {"ctx_additions": {}, "module_modifiers": {}, "warnings": [], "applied": False}

        additions = {"peh_validation_mode": self.mode}
        modifiers = {}

        if self.mode == "dagesh":
            # Domination : seuils relevés, validation stricte
            modifiers["confidence_threshold"] = 0.05
            additions["peh_strict"] = True
        else:
            # Servitude : seuils abaissés, validation graduée
            modifiers["confidence_threshold"] = -0.05
            additions["peh_permissive"] = True

        return {
            "ctx_additions": additions,
            "module_modifiers": modifiers,
            "warnings": [],
            "applied": True,
        }

    def run(self, tree: dict, **kwargs) -> SentierResult:
        domain_id = kwargs.get("domain_id", "default")
        hypothesis = kwargs.get("hypothesis", "")
        score = kwargs.get("score", 0.0)
        threshold = kwargs.get("threshold", 0.5)
        explanation = kwargs.get("explanation", "")

        if not hypothesis:
            return SentierResult(
                sentier=self.name, letter=self.letter,
                source=self.source, target=self.target,
                success=False, mode=self.mode,
                message="Pas d'hypothèse à valider",
            )

        (gevurah,) = self._require(tree, "gevurah")

        # ── Modificateurs domination/servitude ───────────────
        mods = self.yetzirah_modifiers()
        strictness = mods.get("strictness", 0.5)
        binary_threshold = mods.get("binary_threshold", 0.5)

        data = {
            "domain_id": domain_id,
            "hypothesis": hypothesis[:100],
            "score": score,
            "threshold": threshold,
        }

        if self.mode == "dagesh":
            # Domination (memshalah) : verdict souverain, pas d'appel
            # strictness=0.9 → le seuil est relevé par l'autorité
            effective_threshold = threshold + (strictness * 0.1)
            if score >= effective_threshold:
                data["verdict"] = "accepté"
                data["policy"] = f"dagesh/domination — accepté (seuil={effective_threshold:.2f})"
            else:
                data["verdict"] = "rejeté"
                analysis_id = None
                if hasattr(gevurah, "lamed") and gevurah.lamed:
                    analysis_id, _ = gevurah.lamed.process_rejection(
                        domain_id=domain_id,
                        hypothesis=hypothesis,
                        original=kwargs.get("original"),
                        modified=kwargs.get("modified"),
                        explanation=explanation,
                    )
                data["analysis_id"] = str(analysis_id) if analysis_id else None
                data["policy"] = f"dagesh/domination — rejeté sans appel (seuil={effective_threshold:.2f})"
        else:
            # Servitude (avdut) : le juge sert la nuance, gradue
            # binary_threshold=0.2 → large zone de quarantine
            quarantine_width = 0.3 * (1 - binary_threshold)  # → 0.24
            quarantine_threshold = threshold - quarantine_width

            if score >= threshold:
                data["verdict"] = "accepté"
                data["policy"] = f"rafeh/servitude — accepté (score={score:.2f} >= {threshold})"
            elif score >= quarantine_threshold:
                data["verdict"] = "quarantine"
                analysis_id = None
                if hasattr(gevurah, "lamed") and gevurah.lamed:
                    analysis_id = gevurah.lamed.process_quarantine(
                        domain_id=domain_id,
                        hypothesis=hypothesis,
                    )
                data["analysis_id"] = str(analysis_id) if analysis_id else None
                data["policy"] = (
                    f"rafeh/servitude — quarantine "
                    f"({quarantine_threshold:.2f} <= {score:.2f} < {threshold})"
                )
            else:
                data["verdict"] = "rejeté"
                analysis_id = None
                if hasattr(gevurah, "lamed") and gevurah.lamed:
                    analysis_id, _ = gevurah.lamed.process_rejection(
                        domain_id=domain_id,
                        hypothesis=hypothesis,
                        original=kwargs.get("original"),
                        modified=kwargs.get("modified"),
                        explanation=explanation,
                    )
                data["analysis_id"] = str(analysis_id) if analysis_id else None
                data["policy"] = (
                    f"rafeh/servitude — rejeté "
                    f"(score={score:.2f} < {quarantine_threshold:.2f})"
                )

        data["peh_strictness"] = strictness

        result = SentierResult(
            sentier=self.name, letter=self.letter,
            source=self.source, target=self.target,
            mode=self.mode, data=data,
            message=data["policy"],
        )
        return self.enrich_result(result)
