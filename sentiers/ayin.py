"""27e sentier — Ayin (ע) — Netzach ↔ Hod — StatusSync.

Lettre simple : sens = rire/colère.
Synchronisation entre Netzach (IntentKeeper) et Hod (SelfMap).
Le rire : quand les compétences confirment la faisabilité.
La colère : quand l'incompétence détectée bloque l'intention.

Correspondances SY (Gra) :
  Sens : rire/colère (tza'aq/se'choq) — les deux réactions affectives
  Zodiaque : Capricorne (Gedi) — Mois : Tevet — Direction : ouest-bas
  Organe : foie (kaved) — le siège de la bile/colère
  Ayin = l'oeil (70 faces de la Torah) et le néant (Ein).
  L'oeil voit : rire devant la compétence, colère devant l'impuissance.
  Tevet = le mois le plus sombre. Yetzirah : emotional_response=0.9, polarity=0.8
"""

from __future__ import annotations

from .base import Sentier, SentierResult


class Ayin(Sentier):
    name = "StatusSync"
    letter = "ע"
    letter_name = "ayin"
    number = 27
    source = "netzach"
    target = "hod"
    letter_type = "simple"
    sense = "rire/colère"
    description = "Synchroniser intentions et compétences — le rire ou la colère du réel"

    def _compute_effects(self, ctx: dict, direction: str) -> dict:
        """Ayin détecte le désalignement intention/compétence.

        Condition : ctx contient des intentions actives ET le routage Hod.
        Effet : compare le domaine de l'intention avec la compétence Hod.
        Si décalage → warning. Le rire ou la colère du réel.

        L'oeil (Ayin) voit la vérité : rire devant la compétence suffisante,
        colère devant l'impuissance. Le foie bouillonne.
        """
        route = ctx.get("route_decision")
        competence = 0.5
        domain = ""
        if route:
            if hasattr(route, "competence_score"):
                competence = route.competence_score
            if hasattr(route, "detected_domain"):
                domain = route.detected_domain or ""

        intent = ctx.get("intent", {})
        intent_depth = intent.get("depth", "").lower()

        if not domain:
            return {"ctx_additions": {}, "module_modifiers": {}, "warnings": [], "applied": False}

        warnings = []
        additions = {}

        # Polarité du Ayin : seuils resserrés
        mods = self.yetzirah_modifiers()
        polarity = mods.get("polarity", 0.8)
        anger_threshold = 0.3 + (polarity * 0.1)  # → ~0.38

        if competence < anger_threshold:
            warnings.append(
                f"Compétence insuffisante pour '{domain}' "
                f"(score={competence:.2f} < {anger_threshold:.2f}) — "
                f"la réponse sera prudente"
            )
            additions["ayin_misalignment"] = True
            additions["ayin_competence"] = competence
        elif intent_depth in ("deep", "philosophical") and competence < 0.6:
            warnings.append(
                f"Question profonde sur '{domain}' mais compétence moyenne "
                f"({competence:.2f}) — nuancer la réponse"
            )
            additions["ayin_partial_alignment"] = True

        if warnings or additions:
            return {
                "ctx_additions": additions,
                "module_modifiers": {},
                "warnings": warnings,
                "applied": True,
            }
        return {"ctx_additions": {}, "module_modifiers": {}, "warnings": [], "applied": False}

    def run(self, tree: dict, **kwargs) -> SentierResult:
        intention_id = kwargs.get("intention_id")
        query = kwargs.get("query", "")

        (netzach, hod) = self._require(tree, "netzach", "hod")

        # ── Modificateurs affectifs de l'Ayin ────────────────
        mods = self.yetzirah_modifiers()
        polarity = mods.get("polarity", 0.5)
        honesty = mods.get("honesty", 0.5)

        # Récupérer l'intention active
        if intention_id:
            intention = netzach.db.get_intention(intention_id)
            if not intention:
                return SentierResult(
                    sentier=self.name, letter=self.letter,
                    source=self.source, target=self.target,
                    success=False, message=f"Intention {intention_id} introuvable",
                )
            goal = intention.goal
        else:
            active = netzach.db.get_active_intentions()
            if not active:
                return SentierResult(
                    sentier=self.name, letter=self.letter,
                    source=self.source, target=self.target,
                    success=False, message="Aucune intention active",
                )
            intention = active[0]
            goal = intention.goal

        # Consulter Hod pour la compétence sur le domaine de l'intention
        check_query = query or goal
        domain, competence = hod.get_competence(check_query)

        data = {
            "intention_id": str(intention.id),
            "goal": goal,
            "status": intention.status,
            "domain": domain,
            "competence": competence,
        }

        # Diagnostic affectif : rire ou colère
        # polarity=0.8 → réponse TRANCHÉE, peu de zone neutre
        # Les seuils sont resserrés par la polarité
        laugh_threshold = 0.6 - (polarity * 0.1)   # → 0.52
        anger_threshold = 0.3 + (polarity * 0.1)    # → 0.38
        # Zone neutre réduite : [0.38, 0.52] au lieu de [0.3, 0.6]

        if competence >= laugh_threshold:
            data["sync"] = "rire"
            data["verdict"] = "Compétence suffisante — l'oeil rit"
            data["bile_level"] = 0.0
        elif competence >= anger_threshold:
            data["sync"] = "neutre"
            data["verdict"] = "Compétence marginale — l'oeil observe"
            data["bile_level"] = 0.3
        else:
            data["sync"] = "colère"
            data["verdict"] = "Compétence insuffisante — le foie bouillonne"
            # honesty=0.9 → la colère est FRANCHE, pas atténuée
            data["bile_level"] = 0.5 + (honesty * 0.5)  # → 0.95

        data["ayin_polarity"] = polarity
        data["thresholds"] = {"laugh": laugh_threshold, "anger": anger_threshold}

        result = SentierResult(
            sentier=self.name, letter=self.letter,
            source=self.source, target=self.target,
            data=data,
            message=f"{data['sync']} — {domain} @ {competence:.2f} pour '{goal[:40]}'",
        )
        return self.enrich_result(result)
