"""29e sentier — Qoph (ק) — Hod ↔ Yesod — SchemaPersist.

Lettre simple : sens = méditation.
Hod (SelfMap) évalue un domaine et persiste le schéma résultant en Yesod (EpisteMemory).
La méditation : le système réfléchit sur ses compétences et en fixe la trace.

Correspondances SY (Gra) :
  Sens : méditation (shenah amuqah) — le sommeil profond qui filtre
  Zodiaque : Poissons (Dagim) — Mois : Adar — Direction : sud-bas
  Organe : rate (techol) — le filtre du sang
  La rate filtre le sang comme la méditation filtre le savoir brut.
  Adar = le mois du renversement (Pourim) — ce qui semble superficiel
  se révèle profond. Yetzirah : reflection_depth=0.9, filtration=0.8
"""

from __future__ import annotations

from .base import Sentier, SentierResult


class Qoph(Sentier):
    name = "SchemaPersist"
    letter = "ק"
    letter_name = "qoph"
    number = 29
    source = "hod"
    target = "yesod"
    letter_type = "simple"
    sense = "méditation"
    description = "Persister les schémas de compétence — la méditation qui fixe le savoir"

    def _compute_effects(self, ctx: dict, direction: str) -> dict:
        """Qoph enrichit le recall Yesod avec le domaine détecté par Hod.

        Toujours actif (chemin katnut Hod→Yesod). Le sens de Qoph est
        la méditation — filtrer le recall par domaine pertinent.
        """
        # Lire le domaine depuis Hod (SelfMap route decision)
        route = ctx.get("route_decision")
        domain = None
        if route and hasattr(route, "detected_domain"):
            domain = route.detected_domain
        if not domain:
            domain = ctx.get("mochin", {}).get("domain")

        if domain:
            return {
                "ctx_additions": {"recall_domain": domain},
                "module_modifiers": {},
                "warnings": [],
                "applied": True,
            }
        return {"ctx_additions": {}, "module_modifiers": {}, "warnings": [], "applied": False}

    def run(self, tree: dict, **kwargs) -> SentierResult:
        domain = kwargs.get("domain", "general")
        query = kwargs.get("query", "")

        (hod, yesod) = self._require(tree, "hod", "yesod")

        # ── Modificateurs méditatifs ─────────────────────────
        mods = self.yetzirah_modifiers()
        reflection_depth = mods.get("reflection_depth", 0.5)
        filtration = mods.get("filtration", 0.5)

        # Direction 1 : Hod → Yesod — lire la compétence et persister
        # read_competence = lecture DB seule (pas d'eval LLM destructive)
        score = hod.read_competence(domain)

        data = {
            "domain": domain,
            "score": score.score if score else 0.0,
            "n_evals": score.n_evals if score else 0,
        }

        # Direction 2 : Yesod → Hod — rappeler les schémas existants
        # La méditation approfondit le rappel : reflection_depth augmente le limit
        if query:
            # reflection_depth=0.9 → limit augmenté (méditation profonde = plus de rappel)
            recall_limit = max(3, int(3 + reflection_depth * 5))
            memories = yesod.recall(query, limit=recall_limit)

            # Filtration (rate) : ne garder que les souvenirs au-dessus du seuil
            # filtration=0.8 → seuil de confiance relevé
            min_conf = filtration * 0.4  # → 0.32
            recalled = []
            filtered_out = 0
            for m in memories:
                conf = m.confidence if hasattr(m, "confidence") else 0.0
                if conf >= min_conf:
                    recalled.append({
                        "content": m.content if hasattr(m, "content") else str(m),
                        "confidence": conf,
                    })
                else:
                    filtered_out += 1

            data["recalled"] = recalled
            data["n_recalled"] = len(recalled)
            data["n_filtered_out"] = filtered_out
            data["meditation_depth"] = reflection_depth
        else:
            data["recalled"] = []
            data["n_recalled"] = 0
            data["n_filtered_out"] = 0

        result = SentierResult(
            sentier=self.name, letter=self.letter,
            source=self.source, target=self.target,
            data=data,
            message=(
                f"Méditation({domain}): score={data['score']:.2f}, "
                f"{data['n_recalled']} schéma(s) retenu(s), "
                f"{data.get('n_filtered_out', 0)} filtré(s) par la rate"
            ),
        )
        return self.enrich_result(result)
