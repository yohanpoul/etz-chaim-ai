"""31e sentier — Shin (ש) — Malkuth → Hod — Transformation.

Lettre mère : Feu. Le feu purifie, transforme l'ancien en nouveau.
Prend l'input brut de Malkuth (requête utilisateur) et le transforme
en connaissance structurée pour Hod (SelfMap) : domaine, compétence, routage.

Correspondances SY (Gra) :
  Élément : feu — tête — été — sibilance (shriqa)
  Le feu ABAISSE les seuils : Shin est agressif, rapide, destructeur-créateur.
  Yetzirah : aggressiveness=0.8, speed=0.9, patience=0.2
"""

from __future__ import annotations

from .base import Sentier, SentierResult


class Shin(Sentier):
    name = "Transform"
    letter = "ש"
    letter_name = "shin"
    number = 31
    source = "malkuth"
    target = "hod"
    letter_type = "mother"
    element = "feu"
    description = "Transformer l'input brut en self-knowledge — le feu qui purifie"

    def _compute_effects(self, ctx: dict, direction: str) -> dict:
        """Shin injecte l'énergie du feu — aggressivité et urgence.

        Condition : query courte (< 50 chars) ou mots-clés urgents.
        Effet : boost vitesse, signal de traitement rapide.
        Le feu purifie en détruisant le superflu.
        """
        query = ctx.get("query", "")
        intent = ctx.get("intent", {})
        intent_type = intent.get("type", "")

        # Le feu s'active sur les queries brèves/directes
        is_quick = len(query) < 50 and intent_type in ("factual", "définitionnel", "factuel")

        if not is_quick:
            return {"ctx_additions": {}, "module_modifiers": {}, "warnings": [], "applied": False}

        mods = self.yetzirah_modifiers()
        aggressiveness = mods.get("aggressiveness", 0.8)

        return {
            "ctx_additions": {
                "shin_fire_mode": True,
                "shin_aggressiveness": aggressiveness,
            },
            "module_modifiers": {},
            "warnings": [],
            "applied": True,
        }

    def run(self, tree: dict, **kwargs) -> SentierResult:
        query = kwargs.get("query", "")
        if not query:
            return SentierResult(
                sentier=self.name, letter=self.letter,
                source=self.source, target=self.target,
                success=False, message="Pas de requête à transformer",
            )

        (hod,) = self._require(tree, "hod")

        # ── Charger les modificateurs du feu ─────────────────
        mods = self.yetzirah_modifiers()
        # Le feu abaisse le seuil de déclin : on refuse moins
        # aggressiveness=0.8 → decline_threshold réduit de 80%
        aggressiveness = mods.get("aggressiveness", 0.5)

        # Feu : transformer l'input brut en route structurée
        route = hod.route(query)

        data = {
            "domain": route.detected_domain,
            "competence_score": route.competence_score,
            "routed_to": route.routed_to if hasattr(route, "routed_to") else None,
            "declined": route.did_decline,
        }

        if route.did_decline:
            # Le feu conteste le refus : si l'aggressivité est haute
            # et que le score de compétence est au-dessus d'un seuil
            # ajusté par le feu, on force le passage
            fire_threshold = 0.3 * (1 - aggressiveness)  # → 0.06 avec 0.8
            comp = route.competence_score if hasattr(route, "competence_score") else 0
            if comp > fire_threshold and aggressiveness > 0.6:
                data["fire_override"] = True
                data["original_decline"] = True
                data["fire_threshold"] = fire_threshold
                result = SentierResult(
                    sentier=self.name, letter=self.letter,
                    source=self.source, target=self.target,
                    data=data,
                    message=(
                        f"Feu(ש) force le passage — score={comp:.2f} > "
                        f"seuil_feu={fire_threshold:.2f}"
                    ),
                )
                return self.enrich_result(result)

            data["decline_reason"] = (
                route.decline_reason if hasattr(route, "decline_reason") else "inconnu"
            )
            result = SentierResult(
                sentier=self.name, letter=self.letter,
                source=self.source, target=self.target,
                mode=None, data=data,
                message=f"Décliné — {data['decline_reason']}",
            )
            return self.enrich_result(result)

        result = SentierResult(
            sentier=self.name, letter=self.letter,
            source=self.source, target=self.target,
            data=data,
            message=f"Domaine={route.detected_domain}, score={route.competence_score:.2f}",
        )
        return self.enrich_result(result)
