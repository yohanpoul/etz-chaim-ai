"""21e sentier — Yod (י) — Chesed ↔ Tiferet — FilteredDataPush.

Lettre simple : sens = action (ma'aseh).
Les données explorées par Chesed sont filtrées et poussées vers Tiferet
pour synthèse. Action chirurgicale — le point minimal qui contient tout.

Yod est la plus petite lettre — le point primordial. Le Yod du
Tétragramme (י-ה-ו-ה) = Atziluth. Elul = préparation méticuleuse.

Correspondances SY (Gra) :
  Sens : action (ma'aseh) — le faire, l'actualisation du potentiel
  Zodiaque : Vierge (Betulah) — Mois : Elul — Direction : nord-bas
  Organe : main gauche (yad smol)
  Yetzirah : agency=0.9, precision=0.8, selectivity=0.8, minimalism=0.8
"""

from __future__ import annotations

from .base import Sentier, SentierResult


class Yod(Sentier):
    name = "FilteredDataPush"
    letter = "י"
    letter_name = "yod"
    number = 21
    source = "chesed"
    target = "tiferet"
    letter_type = "simple"
    sense = "action"
    description = "Pousser les données filtrées — le point minimal qui actualise"

    def _compute_effects(self, ctx: dict, direction: str) -> dict:
        """Yod signale la quantité et qualité des données pour Tiferet.

        Condition : daemon_enrichment contient des données (analogies ou explorations).
        Effet : le point minimal qui actualise — compte et qualifie pour Tiferet.
        """
        enrichment = ctx.get("daemon_enrichment", {})
        analogies = enrichment.get("analogies", [])
        explorations = enrichment.get("explorations", [])
        total = len(analogies) + len(explorations)

        if total == 0:
            return {"ctx_additions": {}, "module_modifiers": {}, "warnings": [], "applied": False}

        return {
            "ctx_additions": {
                "yod_data_count": total,
                "yod_data_available": True,
            },
            "module_modifiers": {},
            "warnings": [],
            "applied": True,
        }

    def run(self, tree: dict, **kwargs) -> SentierResult:
        domain = kwargs.get("domain")
        data_items = kwargs.get("data_items", [])
        min_quality = kwargs.get("min_quality", 0.4)

        (chesed, tiferet) = self._require(tree, "chesed", "tiferet")

        # ── Modificateurs de l'action filtrée ────────────────
        mods = self.yetzirah_modifiers()
        agency = mods.get("agency", 0.9)
        precision = mods.get("precision", 0.8)
        selectivity = mods.get("selectivity", 0.8)
        minimalism = mods.get("minimalism", 0.8)

        data = {"domain": domain}

        # Étape 1 : Collecter les données de Chesed
        if not data_items:
            if hasattr(chesed, "get_explored_data"):
                data_items = list(chesed.get_explored_data(domain=domain))
            elif hasattr(chesed, "get_results"):
                data_items = list(chesed.get_results(domain=domain))
            elif hasattr(chesed, "explore"):
                try:
                    result = chesed.explore(
                        query=domain or "general exploration",
                        seed_domain=domain or "general",
                    )
                    data_items = list(result.connections) if hasattr(result, "connections") else []
                except Exception:
                    data_items = []

        data["n_raw"] = len(data_items)

        # Étape 2 : Filtrer — le Yod est chirurgical
        # selectivity=0.8 → filtre strict, ne garder que l'essentiel
        # minimalism=0.8 → action minimale suffisante
        effective_threshold = min_quality * (1 + selectivity * 0.3)
        filtered = []
        rejected = []

        for item in data_items:
            # Évaluer la qualité de chaque item
            quality = 0.5  # défaut
            if hasattr(item, "quality"):
                quality = item.quality
            elif hasattr(item, "score"):
                quality = item.score
            elif hasattr(item, "confidence"):
                quality = item.confidence
            elif isinstance(item, dict):
                quality = item.get("quality", item.get("score", item.get("confidence", 0.5)))

            if quality >= effective_threshold:
                filtered.append({
                    "item": str(item)[:100],
                    "quality": round(quality, 3),
                })
            else:
                rejected.append({
                    "item": str(item)[:80],
                    "quality": round(quality, 3),
                })

        data["n_filtered"] = len(filtered)
        data["n_rejected"] = len(rejected)
        data["effective_threshold"] = round(effective_threshold, 3)
        data["filtered_items"] = filtered[:10]

        # Étape 3 : Pousser vers Tiferet pour synthèse
        # agency=0.9 → action délibérée, pas passive
        # precision=0.8 → chaque push est ciblé
        pushed = 0
        if filtered:
            items_to_push = [f["item"] for f in filtered]
            if hasattr(tiferet, "receive_data"):
                tiferet.receive_data(
                    data=items_to_push,
                    domain=domain,
                    source="chesed",
                )
                pushed = len(items_to_push)
            elif hasattr(tiferet, "receive"):
                for item in items_to_push:
                    tiferet.receive(data=item, source="chesed", domain=domain)
                    pushed += 1
            else:
                pushed = 0

        data["n_pushed"] = pushed
        data["yod_agency"] = agency
        data["yod_precision"] = precision
        data["yod_minimalism"] = minimalism

        msg = (
            f"Action(י) — {data['n_raw']}→{data['n_filtered']}→{pushed} "
            f"[{domain}], seuil={effective_threshold:.2f}, "
            f"précision={precision:.1f}"
        )

        result = SentierResult(
            sentier=self.name, letter=self.letter,
            source=self.source, target=self.target,
            data=data, message=msg,
        )
        return self.enrich_result(result)
