"""22e sentier — Kaph (כ) — Chesed ↔ Netzach — AcquirePersist.

Lettre double : deux modes de pipeline d'acquisition.
  dagesh : tout persister — vie, le Soleil vital, persistance obstinée
  rafeh  : persister sélectivement — mort, lâcher-prise, garbage collection

Chesed (exploration) acquiert et Netzach (persistance des intentions)
conserve. La paume (Kaf) qui tient ou qui lâche.

Correspondances SY (Gra) :
  Planète : Soleil (Chamah) — la vitalité centrale
  Jour : Mardi — Porte : oreille gauche — Direction : ouest
  Opposés : dagesh=vie (chaim) / rafeh=mort (mavet)
  Dagesh : persistence_strength=0.9, abandonment_threshold=0.1
  Rafeh : persistence_strength=0.2, abandonment_threshold=0.9
"""

from __future__ import annotations

from .base import Sentier, SentierResult


class Kaph(Sentier):
    name = "AcquirePersist"
    letter = "כ"
    letter_name = "kaph"
    number = 22
    source = "chesed"
    target = "netzach"
    letter_type = "double"
    dagesh_desc = "Tout persister : vie, le Soleil tient tout en vie"
    rafeh_desc = "Persister sélectivement : mort, le lâcher-prise libère"
    mode = "dagesh"
    description = "Pipeline d'acquisition — la paume qui tient ou lâche"

    def _compute_effects(self, ctx: dict, direction: str) -> dict:
        """Kaph module la rétention des explorations — vie ou mort.

        Condition : daemon_enrichment contient des analogies.
        Dagesh (vie) : garder toutes les analogies.
        Rafeh (mort) : ne garder que les fortes (score > 0.5).
        """
        enrichment = ctx.get("daemon_enrichment", {})
        analogies = enrichment.get("analogies", [])

        if not analogies:
            return {"ctx_additions": {}, "module_modifiers": {}, "warnings": [], "applied": False}

        additions = {"kaph_retention_mode": self.mode}

        if self.mode == "rafeh":
            # Mort : sélection darwinienne
            strong = [a for a in analogies
                      if isinstance(a, dict) and a.get("score", 0) >= 0.5]
            additions["kaph_retained"] = len(strong)
            additions["kaph_pruned"] = len(analogies) - len(strong)
        else:
            additions["kaph_retained"] = len(analogies)
            additions["kaph_pruned"] = 0

        return {
            "ctx_additions": additions,
            "module_modifiers": {},
            "warnings": [],
            "applied": True,
        }

    def run(self, tree: dict, **kwargs) -> SentierResult:
        domain = kwargs.get("domain")
        items = kwargs.get("items", [])
        min_relevance = kwargs.get("min_relevance", 0.3)

        (chesed, netzach) = self._require(tree, "chesed", "netzach")

        # ── Modificateurs vie/mort ───────────────────────────
        mods = self.yetzirah_modifiers()
        persistence_strength = mods.get("persistence_strength", 0.5)
        retry_aggressiveness = mods.get("retry_aggressiveness", 0.5)
        abandonment_threshold = mods.get("abandonment_threshold", 0.5)

        data = {"domain": domain}

        # Étape 1 : Chesed explore et acquiert
        if not items and hasattr(chesed, "acquire"):
            acquired = chesed.acquire(domain=domain)
            items = list(acquired) if acquired else []
        elif not items and hasattr(chesed, "explore"):
            try:
                explored = chesed.explore(
                    query=domain or "general exploration",
                    seed_domain=domain or "general",
                )
                items = list(explored.connections) if hasattr(explored, "connections") else []
            except Exception:
                items = []

        data["n_acquired"] = len(items)

        if self.mode == "dagesh":
            # Vie (chaim) : tout persister, le Soleil donne vie à tout
            # persistence_strength=0.9 → on ne lâche rien
            # abandonment_threshold=0.1 → presque jamais abandonner

            persisted = []
            for item in items:
                # Tenter de persister via Netzach
                if hasattr(netzach, "set_intention"):
                    goal = str(item)[:200] if not isinstance(item, str) else item[:200]
                    intention = netzach.set_intention(
                        goal=f"Persist [{domain}]: {goal}",
                        max_duration_days=30,
                    )
                    persisted.append({
                        "item": goal[:100],
                        "intention_id": str(intention.id) if hasattr(intention, "id") else None,
                        "status": "persisted",
                    })
                elif hasattr(netzach, "persist"):
                    netzach.persist(item=item, domain=domain)
                    persisted.append({
                        "item": str(item)[:100],
                        "status": "persisted",
                    })
                else:
                    persisted.append({
                        "item": str(item)[:100],
                        "status": "no_persist_method",
                    })

            data["n_persisted"] = len(persisted)
            data["persisted"] = persisted[:10]  # limiter l'output
            data["n_abandoned"] = 0
            data["policy"] = (
                f"dagesh/vie — {data['n_persisted']}/{data['n_acquired']} persisté(s), "
                f"force={persistence_strength:.1f}"
            )
        else:
            # Mort (mavet) : lâcher-prise sélectif, garbage collection
            # persistence_strength=0.2 → faible rétention
            # abandonment_threshold=0.9 → abandonner facilement

            persisted = []
            abandoned = []
            for item in items:
                # Évaluer la pertinence avant de persister
                relevance = 0.5  # score par défaut
                if hasattr(item, "relevance"):
                    relevance = item.relevance
                elif hasattr(item, "score"):
                    relevance = item.score
                elif isinstance(item, dict) and "relevance" in item:
                    relevance = item["relevance"]

                # Le seuil est rehaussé par la mort : abandonner facilement
                effective_threshold = min_relevance + (abandonment_threshold * 0.3)

                if relevance >= effective_threshold:
                    if hasattr(netzach, "set_intention"):
                        goal = str(item)[:200] if not isinstance(item, str) else item[:200]
                        intention = netzach.set_intention(
                            goal=f"Persist [{domain}]: {goal}",
                            max_duration_days=7,  # durée courte en mode mort
                        )
                        persisted.append({
                            "item": goal[:100],
                            "intention_id": str(intention.id) if hasattr(intention, "id") else None,
                            "relevance": round(relevance, 2),
                        })
                    else:
                        persisted.append({"item": str(item)[:100], "relevance": round(relevance, 2)})
                else:
                    abandoned.append({
                        "item": str(item)[:100],
                        "relevance": round(relevance, 2),
                        "reason": f"sous seuil ({relevance:.2f} < {effective_threshold:.2f})",
                    })

            data["n_persisted"] = len(persisted)
            data["n_abandoned"] = len(abandoned)
            data["persisted"] = persisted[:10]
            data["abandoned"] = abandoned[:5]
            data["policy"] = (
                f"rafeh/mort — {data['n_persisted']} persisté(s), "
                f"{data['n_abandoned']} abandonné(s), "
                f"seuil={min_relevance + abandonment_threshold * 0.3:.2f}"
            )

        data["kaph_persistence"] = persistence_strength

        result = SentierResult(
            sentier=self.name, letter=self.letter,
            source=self.source, target=self.target,
            mode=self.mode, data=data,
            message=data["policy"],
        )
        return self.enrich_result(result)
