"""11e sentier — Mem (מ) — Gevurah ↔ Hod — Reception.

Lettre mère : Eau. L'eau qui descend naturellement, prend la forme
du récipient sans résistance. Flux descendant passif.

Gevurah (jugement) filtre et transmet ses règles de validation vers
Hod (self-knowledge/évaluation). L'eau descend — ce sentier est un
canal passif, pas une transformation active. Il transmet fidèlement
les critères de Gevurah pour que Hod puisse s'auto-évaluer.

Correspondances SY (Gra) :
  Élément : eau — ventre — hiver — murmure (hamah)
  Mem RELÈVE les seuils d'acceptation et ABAISSE la vitesse.
  L'opération accueille plus d'input, conserve plus d'information.
  Yetzirah : receptivity=0.9, patience=0.9, speed=0.3,
  aggressiveness=0.2, destruction_tolerance=0.1
"""

from __future__ import annotations

from .base import Sentier, SentierResult


class Mem(Sentier):
    name = "Reception"
    letter = "מ"
    letter_name = "mem"
    number = 11
    source = "gevurah"
    target = "hod"
    letter_type = "mother"
    element = "eau"
    description = "Transmettre les règles de validation — l'eau qui descend sans forcer"

    def _compute_effects(self, ctx: dict, direction: str) -> dict:
        """Mem reçoit passivement — l'eau transmet les critères de jugement.

        Condition : gevurah_feedback présent dans ctx.
        Effet : signale que les critères de validation descendent vers Hod.
        L'eau descend naturellement — Mem ne force rien, elle transmet.
        """
        gevurah = ctx.get("gevurah_feedback", {})
        autojudge = ctx.get("autojudge_rejections", [])

        if not gevurah and not autojudge:
            return {"ctx_additions": {}, "module_modifiers": {}, "warnings": [], "applied": False}

        additions = {"mem_validation_flow": True}

        # Compter les critères transmis
        n_criteria = 0
        if isinstance(gevurah, dict):
            n_criteria = len(gevurah)
        n_criteria += len(autojudge)
        additions["mem_n_criteria"] = n_criteria

        return {
            "ctx_additions": additions,
            "module_modifiers": {},
            "warnings": [],
            "applied": True,
        }

    def run(self, tree: dict, **kwargs) -> SentierResult:
        domain = kwargs.get("domain", "default")
        rules = kwargs.get("rules")
        evaluation_data = kwargs.get("evaluation_data")

        (gevurah, hod) = self._require(tree, "gevurah", "hod")

        # ── Modificateurs de l'eau réceptrice ────────────────
        mods = self.yetzirah_modifiers()
        receptivity = mods.get("receptivity", 0.9)
        patience = mods.get("patience", 0.9)
        destruction_tolerance = mods.get("destruction_tolerance", 0.1)

        data = {"domain": domain}

        # Étape 1 : Recevoir les règles de Gevurah
        # L'eau prend la forme du récipient — réception fidèle
        if rules is not None:
            received_rules = rules
        elif hasattr(gevurah, "get_validation_rules"):
            received_rules = gevurah.get_validation_rules(domain=domain)
        elif hasattr(gevurah, "get_rules"):
            received_rules = gevurah.get_rules(domain=domain)
        else:
            received_rules = None

        if received_rules is not None:
            if isinstance(received_rules, (list, tuple)):
                data["n_rules"] = len(received_rules)
                data["rules"] = [str(r)[:100] for r in received_rules[:20]]
            elif isinstance(received_rules, dict):
                data["n_rules"] = len(received_rules)
                data["rules"] = {str(k): str(v)[:100] for k, v in list(received_rules.items())[:20]}
            else:
                data["n_rules"] = 1
                data["rules"] = str(received_rules)[:200]
        else:
            data["n_rules"] = 0
            data["rules"] = []

        # Étape 2 : Transmettre à Hod pour auto-évaluation
        # L'eau conserve quasi tout (destruction_tolerance=0.1)
        # Pas de filtrage agressif — transmission fidèle
        transmitted = False
        if received_rules is not None and hasattr(hod, "receive_validation_rules"):
            hod.receive_validation_rules(
                rules=received_rules,
                domain=domain,
                source="gevurah",
            )
            transmitted = True
        elif received_rules is not None and hasattr(hod, "update_rules"):
            hod.update_rules(rules=received_rules, domain=domain)
            transmitted = True

        data["transmitted"] = transmitted

        # Étape 3 : Si des données d'évaluation sont fournies, les évaluer
        # receptivity=0.9 → accepter presque tout input pour évaluation
        if evaluation_data is not None:
            if hasattr(hod, "evaluate"):
                eval_result = hod.evaluate(
                    data=evaluation_data,
                    domain=domain,
                )
                data["evaluation"] = {
                    "score": eval_result.score if hasattr(eval_result, "score") else None,
                    "passed": eval_result.passed if hasattr(eval_result, "passed") else None,
                }
            else:
                data["evaluation"] = None

        # L'eau murmure (hamah) — le message est doux, pas assertif
        # patience=0.9 → le processus est lent et graduel
        data["mem_receptivity"] = receptivity
        data["mem_patience"] = patience
        data["flow_type"] = "descendant_passif"

        if transmitted:
            msg = (
                f"Eau(מ) — {data['n_rules']} règle(s) transmise(s) "
                f"de Gevurah vers Hod [{domain}], "
                f"réceptivité={receptivity:.1f}"
            )
        else:
            msg = (
                f"Eau(מ) — {data['n_rules']} règle(s) reçue(s) [{domain}], "
                f"transmission en attente"
            )

        result = SentierResult(
            sentier=self.name, letter=self.letter,
            source=self.source, target=self.target,
            data=data,
            message=msg,
        )
        return self.enrich_result(result)
