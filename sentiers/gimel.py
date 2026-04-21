"""14e sentier — Gimel (ג) — Keter ↔ Binah — CacheStrategy.

Lettre double : deux stratégies de cache entre Keter (stratégie) et
Binah (analyse causale).
  dagesh : cache agressif — richesse de ressources, tout pré-charger
  rafeh  : pas de cache — pauvreté, tout recalculer à la demande

Le chameau (Gamal) traverse le désert avec ses réserves — ou sans.
Jupiter = expansion généreuse vs contrainte qui force l'efficience.

Correspondances SY (Gra) :
  Planète : Jupiter (Tzedek) — l'expansion généreuse
  Jour : Dimanche — Porte : oeil gauche — Direction : bas
  Opposés : dagesh=richesse (osher) / rafeh=pauvreté (oni)
  Dagesh : resource_allocation=0.9, cache_aggressiveness=0.8
  Rafeh : resource_allocation=0.2, cache_aggressiveness=0.2
"""

from __future__ import annotations

from .base import Sentier, SentierResult


class Gimel(Sentier):
    name = "CacheStrategy"
    letter = "ג"
    letter_name = "gimel"
    number = 14
    source = "keter"
    target = "binah"
    letter_type = "double"
    dagesh_desc = "Cache agressif : richesse, pré-chargement, anticipation"
    rafeh_desc = "Pas de cache : pauvreté, recalcul à la demande, économie stricte"
    mode = "dagesh"
    description = "Stratégie de cache entre stratégie et analyse — le chameau et ses réserves"

    def _compute_effects(self, ctx: dict, direction: str) -> dict:
        """Gimel module la stratégie de cache — richesse ou pauvreté.

        Condition : query de profondeur briah/deep.
        Dagesh (richesse) : signale le pré-chargement, budget élargi.
        Rafeh (pauvreté) : signale l'économie stricte, budget réduit.
        Le chameau traverse le désert — avec ou sans réserves.
        """
        intent = ctx.get("intent", {})
        depth = intent.get("depth", "")

        if depth not in ("briah", "deep", "philosophical"):
            return {"ctx_additions": {}, "module_modifiers": {}, "warnings": [], "applied": False}

        additions = {"gimel_cache_strategy": self.mode}
        modifiers = {}

        if self.mode == "dagesh":
            # Richesse : budget élargi pour analyse causale profonde
            additions["gimel_preload"] = True
        else:
            # Pauvreté : on-demand, budget réduit
            additions["gimel_on_demand"] = True

        return {
            "ctx_additions": additions,
            "module_modifiers": modifiers,
            "warnings": [],
            "applied": True,
        }

    def run(self, tree: dict, **kwargs) -> SentierResult:
        domain = kwargs.get("domain")
        query = kwargs.get("query")
        force_refresh = kwargs.get("force_refresh", False)

        # Keter n'est pas encore implémenté — Gimel fonctionne avec Binah seul
        (binah,) = self._require(tree, "binah")
        keter = tree.get("keter")  # optionnel

        # ── Modificateurs richesse/pauvreté ──────────────────
        mods = self.yetzirah_modifiers()
        resource_allocation = mods.get("resource_allocation", 0.5)
        preloading = mods.get("preloading", 0.5)
        cache_aggressiveness = mods.get("cache_aggressiveness", 0.5)

        data = {"domain": domain, "force_refresh": force_refresh}

        if self.mode == "dagesh":
            # Richesse (osher) : le chameau chargé, réserves pleines
            # Jupiter = expansion. Pré-charger agressivement.
            data["cache_policy"] = "aggressive"

            # Tenter de récupérer du cache de Binah d'abord
            cached_result = None
            if not force_refresh and hasattr(binah, "get_cached_analysis"):
                cached_result = binah.get_cached_analysis(domain=domain, query=query)

            if cached_result is not None:
                data["cache_hit"] = True
                data["result"] = str(cached_result)[:300]
                data["policy"] = (
                    f"dagesh/richesse — cache hit [{domain}], "
                    f"allocation={resource_allocation:.1f}"
                )
            else:
                data["cache_hit"] = False
                # Lancer l'analyse ET la stocker en cache
                if hasattr(binah, "analyze"):
                    analysis = binah.analyze(domain=domain, query=query)
                    data["result"] = str(analysis)[:300]
                    # Pré-charger les analyses adjacentes (preloading=0.8)
                    if preloading > 0.5 and hasattr(binah, "preload_related"):
                        preloaded = binah.preload_related(domain=domain)
                        data["preloaded_count"] = preloaded if isinstance(preloaded, int) else 0
                elif hasattr(binah, "run_analysis"):
                    analysis = binah.run_analysis(domain=domain, query=query)
                    data["result"] = str(analysis)[:300]
                else:
                    data["result"] = None

                data["policy"] = (
                    f"dagesh/richesse — cache miss, analyse lancée + cache warm, "
                    f"preloading={preloading:.1f}"
                )
        else:
            # Pauvreté (oni) : pas de cache, tout recalculer
            # Le chameau sans eau — efficience par la contrainte
            data["cache_policy"] = "none"
            data["cache_hit"] = False

            if hasattr(binah, "analyze"):
                analysis = binah.analyze(domain=domain, query=query)
                data["result"] = str(analysis)[:300]
            elif hasattr(binah, "run_analysis"):
                analysis = binah.run_analysis(domain=domain, query=query)
                data["result"] = str(analysis)[:300]
            else:
                data["result"] = None

            # Pas de stockage en cache — pauvreté = recalcul systématique
            data["policy"] = (
                f"rafeh/pauvreté — recalcul direct, pas de cache, "
                f"allocation={resource_allocation:.1f}"
            )

        data["gimel_cache_aggressiveness"] = cache_aggressiveness

        result = SentierResult(
            sentier=self.name, letter=self.letter,
            source=self.source, target=self.target,
            mode=self.mode, data=data,
            message=data["policy"],
        )
        return self.enrich_result(result)
