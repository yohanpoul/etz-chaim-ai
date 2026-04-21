"""32e sentier — Tav (ת) — Malkuth ↔ Yesod — OutputMode.

Lettre double : deux modes de sortie.
  dagesh : output brut — données telles quelles, pas de formatage
  rafeh  : output enrichi — données + contexte, confiance, avertissements

Le premier sentier de l'initié : Malkuth reçoit de Yesod.

Correspondances SY (Gra) :
  Planète : Lune (Levanah) — le reflet qui change de forme
  Jour : Vendredi — Porte : bouche — Direction : centre
  Opposés : dagesh=grâce (chen) / rafeh=laideur (ki'ur)
  Interprétation opératoire : dagesh (dur) = la vérité brute qui peut
  être laide, rafeh (doux) = la grâce de la présentation enrichie.
  La Lune reflète — l'output est toujours un reflet de Yesod.
"""

from __future__ import annotations

from .base import Sentier, SentierResult


class Tav(Sentier):
    name = "OutputMode"
    letter = "ת"
    letter_name = "tav"
    number = 32
    source = "yesod"
    target = "malkuth"
    letter_type = "double"
    dagesh_desc = "Output brut : données telles quelles"
    rafeh_desc = "Output enrichi : données + contexte et confiance"
    mode = "rafeh"
    description = "Formater la sortie de Yesod pour Malkuth — le middleware de présentation"

    def _compute_effects(self, ctx: dict, direction: str) -> dict:
        """Tav vérifie la cohérence entre l'intention originale et le ctx accumulé.

        Toujours actif (chemin katnut Yesod→Malkuth). La Lune reflète —
        Tav s'assure que le reflet final est fidèle à l'intention initiale.
        Si dérive détectée, injecte un warning de recentrage.
        """
        intent = ctx.get("intent", {})
        original_type = intent.get("type", "")
        original_depth = intent.get("depth", "")

        warnings = []

        # Check 1 : si l'intention était factuelle mais le ctx a accumulé
        # des explorations profondes → dérive
        if original_type == "factual" and original_depth == "shallow":
            n_enrichments = len(ctx.get("sentier_enrichments", []))
            if n_enrichments > 8:
                warnings.append(
                    "Recentre sur l'intention originale : question factuelle simple, "
                    "mais le pipeline a accumulé beaucoup de traversées"
                )

        # Check 2 : si le domaine a changé entre Hod et l'intention
        mochin_domain = ctx.get("mochin", {}).get("domain", "")
        route_domain = ""
        route = ctx.get("route_decision")
        if route and hasattr(route, "detected_domain"):
            route_domain = route.detected_domain or ""
        if (mochin_domain and route_domain
                and mochin_domain != route_domain
                and route_domain != "general"):
            warnings.append(
                f"Dérive domaine : intent={mochin_domain}, route={route_domain}"
            )

        # Check 3 : mémoires rappelées mais aucune pertinente
        memories = ctx.get("memories", [])
        if memories:
            high_conf = [m for m in memories
                         if hasattr(m, "confidence") and m.confidence > 0.5]
            if len(high_conf) == 0 and len(memories) > 2:
                warnings.append(
                    "Aucune mémoire de haute confiance rappelée — "
                    "la réponse reposera principalement sur le LLM"
                )

        if warnings:
            return {
                "ctx_additions": {"tav_coherence_check": True},
                "module_modifiers": {},
                "warnings": warnings,
                "applied": True,
            }
        return {"ctx_additions": {}, "module_modifiers": {}, "warnings": [], "applied": False}

    def run(self, tree: dict, **kwargs) -> SentierResult:
        query = kwargs.get("query", "")
        limit = kwargs.get("limit", 5)
        if not query:
            return SentierResult(
                sentier=self.name, letter=self.letter,
                source=self.source, target=self.target,
                success=False, mode=self.mode, message="Pas de requête",
            )

        (yesod,) = self._require(tree, "yesod")
        memories = yesod.recall(query, limit=limit)

        # ── Modificateurs lunaires selon le mode ─────────────
        mods = self.yetzirah_modifiers()
        # verbosity et enrichment pilotent le niveau de détail
        verbosity = mods.get("verbosity", 0.5)
        enrichment = mods.get("enrichment", 0.5)

        if self.mode == "dagesh":
            # Dagesh = laideur utile : la vérité brute, sans ornement
            # rawness=0.9 → contenu seul, pas de métadonnées
            items = []
            for m in memories:
                items.append({
                    "content": m.content if hasattr(m, "content") else str(m),
                })
            result = SentierResult(
                sentier=self.name, letter=self.letter,
                source=self.source, target=self.target,
                mode="dagesh", data={"entries": items, "count": len(items)},
                message=f"{len(items)} entrée(s) — mode brut (laideur/vérité nue)",
            )
            return self.enrich_result(result)
        else:
            # Rafeh = grâce : l'enrichissement contextuel élégant
            # enrichment=0.9 → contexte maximal, confiance, avertissements
            items = []
            warnings = []
            for m in memories:
                entry = {
                    "content": m.content if hasattr(m, "content") else str(m),
                    "confidence": m.confidence if hasattr(m, "confidence") else 0.0,
                    "status": m.epistemic_status if hasattr(m, "epistemic_status") else "unknown",
                    "domain": m.domain if hasattr(m, "domain") else None,
                    "source_sephirah": m.source_sephirah if hasattr(m, "source_sephirah") else None,
                }
                # Grâce lunaire : enrichir proportionnellement au modificateur
                if enrichment > 0.5:
                    entry["moon_phase"] = "waxing"  # Lune croissante = plus de détail
                if hasattr(m, "warning") and m.warning:
                    entry["warning"] = m.warning
                    warnings.append(m.warning)
                items.append(entry)

            result = SentierResult(
                sentier=self.name, letter=self.letter,
                source=self.source, target=self.target,
                mode="rafeh",
                data={
                    "entries": items,
                    "count": len(items),
                    "avg_confidence": sum(e["confidence"] for e in items) / len(items) if items else 0,
                    "warnings": warnings,
                },
                message=f"{len(items)} entrée(s) enrichie(s) (grâce), {len(warnings)} avertissement(s)",
            )
            return self.enrich_result(result)
