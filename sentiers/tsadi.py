"""28e sentier — Tsadi (צ) — Netzach → Yesod — CheckpointWrite.

Lettre simple : sens = pensée.
Netzach (IntentKeeper) écrit ses checkpoints en Yesod (EpisteMemory).
La pensée fixée : chaque intention posée laisse une trace en mémoire.

Correspondances SY (Gra) :
  Sens : pensée (hirhurim) — méditation, imagination structurée
  Zodiaque : Verseau (Deli) — Mois : Shevat — Direction : sud-haut
  Organe : oesophage (veshet) — le passage qui fixe
  Le tzaddik (juste) fixe sa pensée — ni errante ni volatile.
  Shevat = Tu Bishvat, l'arbre qui s'enracine. La pensée s'enracine
  en checkpoint. Yetzirah : thought_structuring=0.9, fixation=0.9
"""

from __future__ import annotations

from .base import Sentier, SentierResult


class Tsadi(Sentier):
    name = "CheckpointWrite"
    letter = "צ"
    letter_name = "tsadi"
    number = 28
    source = "netzach"
    target = "yesod"
    letter_type = "simple"
    sense = "pensée"
    description = "Écrire les checkpoints d'intention en mémoire — la pensée qui se fixe"

    def _compute_effects(self, ctx: dict, direction: str) -> dict:
        """Tsadi enracine la pensée — connecte les intentions au rappel mémoire.

        Condition : des intentions actives existent dans ctx.
        Effet : ajoute le contexte d'intention pour guider le recall Yesod.
        Le tzaddik fixe sa pensée — la mémoire s'aligne sur l'intention.
        """
        intent = ctx.get("intent", {})
        intent_type = intent.get("type", "")
        intent_depth = intent.get("depth", "")

        # Le tzaddik ne s'active que sur les intentions structurées
        if not intent_type or intent_type in ("", "greeting"):
            return {"ctx_additions": {}, "module_modifiers": {}, "warnings": [], "applied": False}

        additions = {
            "tsadi_intent_guided_recall": True,
            "tsadi_intent_type": intent_type,
        }

        # Si la profondeur est élevée, renforcer la fixation
        if intent_depth in ("briah", "deep", "philosophical"):
            additions["tsadi_deep_fixation"] = True

        return {
            "ctx_additions": additions,
            "module_modifiers": {},
            "warnings": [],
            "applied": True,
        }

    def run(self, tree: dict, **kwargs) -> SentierResult:
        action = kwargs.get("action", "create")
        goal = kwargs.get("goal", "")
        intention_id = kwargs.get("intention_id")
        reason = kwargs.get("reason", "")

        (netzach,) = self._require(tree, "netzach")

        # ── Modificateurs du tzaddik ─────────────────────────
        mods = self.yetzirah_modifiers()
        intentionality = mods.get("intentionality", 0.5)
        rootedness = mods.get("rootedness", 0.5)

        data = {"action": action}

        if action == "create":
            if not goal:
                return SentierResult(
                    sentier=self.name, letter=self.letter,
                    source=self.source, target=self.target,
                    success=False, message="Pas de goal pour l'intention",
                )
            # Le tzaddik enracine : rootedness=0.8 → durée augmentée
            base_days = kwargs.get("max_duration_days", 7)
            rooted_days = int(base_days * (1 + rootedness * 0.5))  # → 10 jours

            intention = netzach.set_intention(
                goal=goal,
                max_duration_days=rooted_days,
                strategy=kwargs.get("strategy"),
            )
            data["intention_id"] = str(intention.id)
            data["goal"] = intention.goal
            data["status"] = intention.status
            data["rooted_days"] = rooted_days
            data["tsadi_rootedness"] = rootedness
            msg = f"Pensée enracinée : {intention.goal} ({rooted_days}j)"

        elif action == "complete":
            if not intention_id:
                return SentierResult(
                    sentier=self.name, letter=self.letter,
                    source=self.source, target=self.target,
                    success=False, message="Pas d'intention_id pour compléter",
                )
            netzach.complete(intention_id)
            data["intention_id"] = str(intention_id)
            msg = f"Intention complétée : {intention_id}"

        elif action == "abandon":
            if not intention_id or not reason:
                return SentierResult(
                    sentier=self.name, letter=self.letter,
                    source=self.source, target=self.target,
                    success=False, message="intention_id et reason requis pour abandonner",
                )
            # Le tzaddik ne lâche pas facilement : intentionality=0.8
            # → on note la résistance à l'abandon
            data["abandon_resistance"] = intentionality
            netzach.abandon(intention_id, reason)
            data["intention_id"] = str(intention_id)
            data["reason"] = reason
            msg = f"Intention abandonnée (résistance={intentionality:.1f}) : {intention_id} — {reason}"

        else:
            return SentierResult(
                sentier=self.name, letter=self.letter,
                source=self.source, target=self.target,
                success=False, message=f"Action inconnue : {action}",
            )

        result = SentierResult(
            sentier=self.name, letter=self.letter,
            source=self.source, target=self.target,
            data=data, message=msg,
        )
        return self.enrich_result(result)
