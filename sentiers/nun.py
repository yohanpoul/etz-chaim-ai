"""24e sentier — Nun (נ) — Tiferet → Netzach — TaskDispatch.

Lettre simple : sens = marche.
Tiferet (DissensuEngine) confie les tâches longues à Netzach (IntentKeeper).
La marche : progression pas à pas vers un objectif.

Correspondances SY (Gra) :
  Sens : marche (hilukh) — progression pas à pas
  Zodiaque : Scorpion (Akrav) — Mois : Cheshvan — Direction : nord-ouest
  Organe : intestins (dayim) — la digestion lente et complète
  Nun final (ן) descend sous la ligne — là où Lamed monte, Nun descend.
  Cheshvan = le mois sans fêtes, le travail pur et persévérant.
  Les intestins digèrent lentement mais complètement.
  Yetzirah : step_by_step=0.9, patience=0.8, thoroughness=0.8
"""

from __future__ import annotations

from .base import Sentier, SentierResult


class Nun(Sentier):
    name = "TaskDispatch"
    letter = "נ"
    letter_name = "nun"
    number = 24
    source = "tiferet"
    target = "netzach"
    letter_type = "simple"
    sense = "marche"
    description = "Confier les tâches de synthèse à la persistance — la marche pas à pas"

    def _compute_effects(self, ctx: dict, direction: str) -> dict:
        """Nun vérifie si la synthèse Tiferet fait avancer une intention active.

        Condition : ctx contient une synthèse Tiferet (tiferet_diag ou tiferet_result).
        Effet : vérifie l'alignement synthèse↔intention → ctx_additions['intent_alignment'].

        Les intestins digèrent lentement mais complètement. Nun descend sous la ligne.
        La marche (hilukh) = progression pas à pas vers l'objectif.
        """
        tiferet_data = ctx.get("tiferet_diag", {})
        has_synthesis = tiferet_data.get("syntheses", 0) > 0 or ctx.get("tiferet_result")

        if not has_synthesis:
            return {"ctx_additions": {}, "module_modifiers": {}, "warnings": [], "applied": False}

        # Vérifier s'il y a des intentions actives dans le ctx
        intent = ctx.get("intent", {})
        query_type = intent.get("type", "")

        # Simple heuristique : si la query a un type identifié,
        # la synthèse est probablement alignée avec l'intention
        aligned = query_type not in ("", "unknown")

        additions = {"intent_alignment": aligned}
        warnings = []

        if not aligned:
            warnings.append(
                "Synthèse Tiferet sans intention identifiée — "
                "la réponse risque de manquer de direction"
            )

        return {
            "ctx_additions": additions,
            "module_modifiers": {},
            "warnings": warnings,
            "applied": True,
        }

    def run(self, tree: dict, **kwargs) -> SentierResult:
        domain = kwargs.get("domain")
        conclusion_ids = kwargs.get("conclusion_ids")
        auto_intent = kwargs.get("auto_intent", True)

        (tiferet, netzach) = self._require(tree, "tiferet", "netzach")

        # ── Modificateurs de la marche intestinale ───────────
        mods = self.yetzirah_modifiers()
        thoroughness = mods.get("thoroughness", 0.5)
        step_by_step = mods.get("step_by_step", 0.5)

        # Étape 1 : Tiferet synthétise ou constate le dissensus
        synthesis = tiferet.synthesize_or_dissent(
            conclusion_ids=conclusion_ids,
            domain=domain,
        )

        data = {
            "domain": domain,
            "mode": synthesis.mode if hasattr(synthesis, "mode") else "unknown",
            "content": (synthesis.content if hasattr(synthesis, "content") else "")[:200],
            "n_sources": synthesis.n_sources if hasattr(synthesis, "n_sources") else 0,
        }

        # Étape 2 : si synthèse réussie et auto_intent, créer une intention
        # Nun marche pas à pas : thoroughness=0.8 → durée augmentée pour digestion
        if auto_intent and hasattr(synthesis, "mode") and synthesis.mode == "synthesis":
            goal = f"Intégrer synthèse [{domain or 'global'}] : {data['content'][:80]}"
            # Les intestins prennent leur temps : durée modulée par thoroughness
            dispatch_days = int(7 * (1 + thoroughness * 0.3))  # → 8-9 jours
            intention = netzach.set_intention(goal=goal, max_duration_days=dispatch_days)
            data["intention_id"] = str(intention.id)
            data["dispatched"] = True
            data["nun_thoroughness"] = thoroughness
            data["digestion_days"] = dispatch_days
            msg = f"Marche(נ) → intention créée ({dispatch_days}j): {goal[:50]}"
        elif hasattr(synthesis, "mode") and synthesis.mode == "dissensus":
            data["dispatched"] = False
            data["dissensus_reason"] = (
                synthesis.dissensus_reason
                if hasattr(synthesis, "dissensus_reason") else "divergence trop forte"
            )
            # Le scorpion attend : le dissensus n'est pas un échec, c'est une digestion
            data["nun_patience"] = mods.get("patience", 0.5)
            msg = f"Dissensus maintenu — Nun attend ({data['dissensus_reason'][:50]})"
        else:
            data["dispatched"] = False
            msg = f"Mode={data['mode']} — dispatch non applicable"

        result = SentierResult(
            sentier=self.name, letter=self.letter,
            source=self.source, target=self.target,
            data=data, message=msg,
        )
        return self.enrich_result(result)
