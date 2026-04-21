"""17e sentier — Vav (ו) — Chokmah ↔ Chesed — DataFeed.

Lettre simple : sens = ouïe (shmi'ah).
Alimente l'exploration (Chesed) avec les insights bruts de Chokmah.
Canal de données unidirectionnel. L'ouïe reçoit dans la DURÉE — un
flux temporel séquentiel.

Vav = le connecteur, le clou qui joint. La lettre de la conjonction
(ve- = "et"). Le Vav du Tétragramme connecte le supérieur à l'inférieur.

Correspondances SY (Gra) :
  Sens : ouïe (shmi'ah) — écoute du flux séquentiel
  Zodiaque : Taureau (Shor) — Mois : Iyyar — Direction : sud-est
  Organe : rein droit (kulyah yemin)
  Yetzirah : stream_processing=0.9, sequential_processing=0.9, patience=0.7
"""

from __future__ import annotations

from .base import Sentier, SentierResult


class Vav(Sentier):
    name = "DataFeed"
    letter = "ו"
    letter_name = "vav"
    number = 17
    source = "chokmah"
    target = "chesed"
    letter_type = "simple"
    sense = "ouïe"
    description = "Stream de données — le connecteur qui alimente l'exploration"

    def _compute_effects(self, ctx: dict, direction: str) -> dict:
        """Vav connecte — signale le flux d'insights de Chokmah vers Chesed.

        Condition : daemon_enrichment avec chokmah_insights.
        Effet : signale la disponibilité d'insights pour l'exploration.
        Le Vav est le connecteur — il joint le supérieur à l'inférieur.
        """
        enrichment = ctx.get("daemon_enrichment", {})
        insights = enrichment.get("chokmah_insights", [])

        if not insights:
            return {"ctx_additions": {}, "module_modifiers": {}, "warnings": [], "applied": False}

        return {
            "ctx_additions": {
                "vav_insight_feed": True,
                "vav_n_insights": len(insights),
            },
            "module_modifiers": {},
            "warnings": [],
            "applied": True,
        }

    def run(self, tree: dict, **kwargs) -> SentierResult:
        domain = kwargs.get("domain")
        data_items = kwargs.get("data_items", [])
        stream_mode = kwargs.get("stream_mode", True)

        (chokmah, chesed) = self._require(tree, "chokmah", "chesed")

        # ── Modificateurs de l'ouïe séquentielle ────────────
        mods = self.yetzirah_modifiers()
        stream_processing = mods.get("stream_processing", 0.9)
        sequential_processing = mods.get("sequential_processing", 0.9)
        patience = mods.get("patience", 0.7)
        temporal_sensitivity = mods.get("temporal_sensitivity", 0.8)

        data = {"domain": domain, "stream_mode": stream_mode}

        # Étape 1 : Recevoir les insights de Chokmah
        # L'ouïe écoute dans la durée — flux séquentiel
        if not data_items:
            if hasattr(chokmah, "stream_insights"):
                data_items = list(chokmah.stream_insights(domain=domain))
            elif hasattr(chokmah, "get_insights"):
                data_items = list(chokmah.get_insights(domain=domain))
            elif hasattr(chokmah, "explore"):
                data_items = list(chokmah.explore(domain=domain))

        data["n_received"] = len(data_items)

        # Étape 2 : Alimenter Chesed séquentiellement
        # Vav connecte — le clou (vav) qui joint chaque élément
        # sequential_processing=0.9 → traitement dans l'ordre strict
        fed_count = 0
        feed_results = []

        for item in data_items:
            if hasattr(chesed, "feed"):
                result_item = chesed.feed(data=item, domain=domain, source="chokmah")
                fed_count += 1
                feed_results.append({
                    "item": str(item)[:80],
                    "status": "fed",
                })
            elif hasattr(chesed, "receive"):
                chesed.receive(data=item, domain=domain)
                fed_count += 1
                feed_results.append({
                    "item": str(item)[:80],
                    "status": "received",
                })
            else:
                feed_results.append({
                    "item": str(item)[:80],
                    "status": "no_feed_method",
                })

        data["n_fed"] = fed_count
        data["feed_results"] = feed_results[:10]
        data["vav_stream_processing"] = stream_processing
        data["vav_patience"] = patience
        data["vav_temporal_sensitivity"] = temporal_sensitivity

        msg = (
            f"Ouïe(ו) — {fed_count}/{data['n_received']} élément(s) "
            f"transmis de Chokmah vers Chesed [{domain}], "
            f"stream={stream_processing:.1f}"
        )

        result = SentierResult(
            sentier=self.name, letter=self.letter,
            source=self.source, target=self.target,
            data=data, message=msg,
        )
        return self.enrich_result(result)
