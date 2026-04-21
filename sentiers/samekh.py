"""25e sentier — Samekh (ס) — Tiferet → Hod — Introspection.

Lettre simple : sens = sommeil.
Tiferet (DissensuEngine) se retourne vers Hod (SelfMap) pour examiner
la cohérence interne du système. Le "sommeil" créatif qui consolide.

Correspondances SY (Gra) :
  Sens : sommeil (shenah) — le sommeil créatif qui consolide
  Zodiaque : Sagittaire (Keshet) — Mois : Kislev — Direction : ouest-haut
  Organe : estomac (keivah) — la digestion nocturne
  Samekh (ס) = le cercle fermé, la Soukkah protectrice.
  Kislev = Hanoukkah, lumière dans l'obscurité intérieure.
  L'estomac digère quand on dort. Yetzirah : introspection_depth=0.9,
  consolidation=0.9, external_activity=0.1
"""

from __future__ import annotations

from .base import Sentier, SentierResult


class Samekh(Sentier):
    name = "Introspection"
    letter = "ס"
    letter_name = "samekh"
    number = 25
    source = "tiferet"
    target = "hod"
    letter_type = "simple"
    sense = "sommeil"
    description = "Le système s'examine — le sommeil créatif qui consolide"

    def _compute_effects(self, ctx: dict, direction: str) -> dict:
        """Samekh déclenche l'introspection — tensions internes pour Hod.

        Condition : tiferet_diag présent avec tensions.
        Effet : signale les tensions à Hod pour ajustement de compétence.
        Le cercle fermé protège et consolide.
        """
        diag = ctx.get("tiferet_diag", {})
        tensions = diag.get("open_tensions", diag.get("tensions", 0))

        if not diag:
            return {"ctx_additions": {}, "module_modifiers": {}, "warnings": [], "applied": False}

        warnings = []
        additions = {"samekh_introspection": True}

        if isinstance(tensions, int) and tensions > 5:
            warnings.append(
                f"Samekh(ס) : {tensions} tensions ouvertes — "
                f"le cercle protecteur est sous pression"
            )
            additions["samekh_tension_pressure"] = True

        return {
            "ctx_additions": additions,
            "module_modifiers": {},
            "warnings": warnings,
            "applied": True,
        }

    def run(self, tree: dict, **kwargs) -> SentierResult:
        domain = kwargs.get("domain")
        conclusion_ids = kwargs.get("conclusion_ids")

        (tiferet,) = self._require(tree, "tiferet")

        # ── Modificateurs du sommeil consolidateur ───────────
        mods = self.yetzirah_modifiers()
        introspection_depth = mods.get("introspection_depth", 0.5)
        consolidation = mods.get("consolidation", 0.5)

        # Analyser la cohérence via DissensuEngine
        report = tiferet.analyze_consistency(
            conclusion_ids=conclusion_ids,
            domain=domain,
        )

        data = {
            "domain": domain,
            "n_conclusions": report.n_conclusions if hasattr(report, "n_conclusions") else 0,
            "n_tensions": report.n_tensions if hasattr(report, "n_tensions") else 0,
            "consistency_score": report.consistency_score if hasattr(report, "consistency_score") else 0.0,
        }

        # Extraire les tensions trouvées
        # introspection_depth=0.9 → plus de tensions remontées
        max_tensions = max(5, int(5 + introspection_depth * 10))  # → 14
        if hasattr(report, "tensions") and report.tensions:
            data["tensions"] = [
                {
                    "between": (
                        str(t.conclusion_a_id) if hasattr(t, "conclusion_a_id") else "?",
                        str(t.conclusion_b_id) if hasattr(t, "conclusion_b_id") else "?",
                    ),
                    "divergence": t.divergence_score if hasattr(t, "divergence_score") else 0.0,
                    "status": t.status if hasattr(t, "status") else "unknown",
                }
                for t in report.tensions[:max_tensions]
            ]

        # Consolidation : le cercle fermé de Samekh protège et intègre
        # consolidation=0.9 → score de protection élevé
        data["samekh_circle"] = {
            "depth": introspection_depth,
            "consolidation": consolidation,
            "max_tensions_examined": max_tensions,
            "protection_level": consolidation,  # le cercle protège le processus
        }

        if data["n_tensions"] > 0:
            msg = (
                f"Sommeil(ס) profond : {data['n_tensions']} tension(s) sur "
                f"{data['n_conclusions']} conclusion(s), "
                f"cohérence={data['consistency_score']:.2f}, "
                f"cercle={consolidation:.1f}"
            )
        else:
            msg = (
                f"Sommeil(ס) paisible : {data['n_conclusions']} conclusion(s), "
                f"aucune tension — le cercle est intact"
            )

        result = SentierResult(
            sentier=self.name, letter=self.letter,
            source=self.source, target=self.target,
            data=data, message=msg,
        )
        return self.enrich_result(result)
