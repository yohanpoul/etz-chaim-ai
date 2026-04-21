"""15e sentier — Daleth (ד) — Chokmah ↔ Binah — ExploreScope.

Lettre double : deux portées d'exploration entre Chokmah (intuition/
générateur de candidats) et Binah (analyse causale/filtre).
  dagesh : scope large — fertilité, ouvrir toutes les portes (breadth-first)
  rafeh  : scope étroit — désolation, une seule porte à la fois (depth-first)

La porte (Delet) qui ouvre ou ferme. Mars = le courage de choisir.

Correspondances SY (Gra) :
  Planète : Mars (Maadim) — la force qui tranche
  Jour : Lundi — Porte : oreille droite — Direction : est
  Opposés : dagesh=fertilité (zera) / rafeh=désolation (shemamah)
  Dagesh : exploration_breadth=0.9, generative_capacity=0.8
  Rafeh : exploration_breadth=0.2, generative_capacity=0.2
"""

from __future__ import annotations

from .base import Sentier, SentierResult


class Daleth(Sentier):
    name = "ExploreScope"
    letter = "ד"
    letter_name = "daleth"
    number = 15
    source = "chokmah"
    target = "binah"
    letter_type = "double"
    dagesh_desc = "Scope large : fertilité, toutes les portes ouvertes (breadth-first)"
    rafeh_desc = "Scope étroit : désolation, une seule porte (depth-first)"
    mode = "dagesh"
    description = "Portée d'exploration — la porte qui ouvre ou ferme les possibilités"

    def _compute_effects(self, ctx: dict, direction: str) -> dict:
        """Daleth prépare les insights Chokmah pour l'analyse causale Binah.

        Condition : ctx contient des insights ou daemon_enrichment avec insights.
        Effet : filtre et structure les insights pour Binah.
        La porte (Delet) s'ouvre ou se ferme selon le mode dagesh/rafeh.
        """
        # Chercher les insights dans le ctx
        insights = []
        daemon = ctx.get("daemon_enrichment", {})
        if daemon.get("insights"):
            insights.extend(daemon["insights"])
        if daemon.get("analogies"):
            insights.extend(daemon["analogies"])

        if not insights:
            return {"ctx_additions": {}, "module_modifiers": {}, "warnings": [], "applied": False}

        # En dagesh (fertilité) : passer tous les insights
        # En rafeh (désolation) : ne garder que le meilleur
        if self.mode == "rafeh" and len(insights) > 1:
            # Trier par score/confidence et ne garder que le top
            sorted_insights = sorted(
                insights,
                key=lambda x: x.get("confidence", x.get("score", 0)),
                reverse=True,
            )
            insights = sorted_insights[:1]

        return {
            "ctx_additions": {
                "insights_for_analysis": insights,
                "daleth_mode": self.mode,
                "daleth_n_insights": len(insights),
            },
            "module_modifiers": {},
            "warnings": [],
            "applied": True,
        }

    def run(self, tree: dict, **kwargs) -> SentierResult:
        domain = kwargs.get("domain")
        query = kwargs.get("query")
        max_candidates = kwargs.get("max_candidates", 10)

        (chokmah, binah) = self._require(tree, "chokmah", "binah")

        # ── Modificateurs fertilité/désolation ───────────────
        mods = self.yetzirah_modifiers()
        exploration_breadth = mods.get("exploration_breadth", 0.5)
        generative_capacity = mods.get("generative_capacity", 0.5)
        openness = mods.get("openness", 0.5)

        data = {"domain": domain}

        if self.mode == "dagesh":
            # Fertilité (zera) : ouvrir toutes les portes
            # Mars en mode conquérant — exploration maximale
            effective_max = int(max_candidates * (1 + exploration_breadth))

            # Chokmah génère un large spectre de candidats
            if hasattr(chokmah, "generate_candidates"):
                candidates = chokmah.generate_candidates(
                    domain=domain,
                    query=query,
                    limit=effective_max,
                )
            elif hasattr(chokmah, "explore"):
                candidates = chokmah.explore(domain=domain, limit=effective_max)
            else:
                candidates = []

            candidates_list = list(candidates) if candidates else []
            data["n_generated"] = len(candidates_list)

            # Binah filtre causalement — mais en mode fertile, filtre léger
            # openness=0.9 → seuil de filtrage abaissé
            filter_threshold = 0.1 * (1 - openness)  # → 0.01
            if hasattr(binah, "filter_candidates"):
                filtered = binah.filter_candidates(
                    candidates=candidates_list,
                    domain=domain,
                    threshold=filter_threshold,
                )
                filtered_list = list(filtered) if filtered else []
            else:
                filtered_list = candidates_list

            data["n_filtered"] = len(filtered_list)
            data["filter_threshold"] = round(filter_threshold, 3)
            data["policy"] = (
                f"dagesh/fertilité — {data['n_generated']} candidats générés, "
                f"{data['n_filtered']} retenus (seuil={filter_threshold:.3f})"
            )
        else:
            # Désolation (shemamah) : une seule porte, profondeur max
            # generative_capacity=0.2 → peu de candidats mais approfondis
            effective_max = max(1, int(max_candidates * generative_capacity))

            if hasattr(chokmah, "generate_candidates"):
                candidates = chokmah.generate_candidates(
                    domain=domain,
                    query=query,
                    limit=effective_max,
                )
            elif hasattr(chokmah, "explore"):
                candidates = chokmah.explore(domain=domain, limit=effective_max)
            else:
                candidates = []

            candidates_list = list(candidates) if candidates else []
            data["n_generated"] = len(candidates_list)

            # Filtrage strict en mode désolation
            filter_threshold = 0.5 * (1 + (1 - openness))  # → 0.9
            if hasattr(binah, "filter_candidates"):
                filtered = binah.filter_candidates(
                    candidates=candidates_list,
                    domain=domain,
                    threshold=filter_threshold,
                )
                filtered_list = list(filtered) if filtered else []
            else:
                filtered_list = candidates_list[:1]  # un seul en mode austère

            data["n_filtered"] = len(filtered_list)
            data["filter_threshold"] = round(filter_threshold, 3)
            data["policy"] = (
                f"rafeh/désolation — {data['n_generated']} candidat(s), "
                f"{data['n_filtered']} retenu(s) (seuil={filter_threshold:.3f})"
            )

        data["daleth_openness"] = openness

        result = SentierResult(
            sentier=self.name, letter=self.letter,
            source=self.source, target=self.target,
            mode=self.mode, data=data,
            message=data["policy"],
        )
        return self.enrich_result(result)
