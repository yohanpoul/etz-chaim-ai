"""19e sentier — Cheth (ח) — Binah ↔ Gevurah — ValidationRules.

Lettre simple : sens = parole (si'ach).
Binah fournit les règles de validation structurelle à Gevurah pour le
jugement. Les patterns causaux deviennent des critères de jugement.
La parole qui délimite — nommer c'est séparer.

Cheth = la barrière (cheth = clôture). Cancer = la carapace protectrice.

Correspondances SY (Gra) :
  Sens : parole (si'ach) — articulation, formulation de règles
  Zodiaque : Cancer (Sartan) — Mois : Tammouz — Direction : est-bas
  Organe : main droite (variante : estomac)
  Yetzirah : articulation=0.9, rule_generation=0.8, boundary_setting=0.8,
  protection=0.7
"""

from __future__ import annotations

from .base import Sentier, SentierResult


class Cheth(Sentier):
    name = "ValidationRules"
    letter = "ח"
    letter_name = "cheth"
    number = 19
    source = "binah"
    target = "gevurah"
    letter_type = "simple"
    sense = "parole"
    description = "Formuler les règles de validation — la barrière qui protège l'intégrité"

    def _compute_effects(self, ctx: dict, direction: str) -> dict:
        """Cheth articule des règles de validation — la barrière protectrice.

        Condition : binah_causal dans daemon_enrichment (claims causaux disponibles).
        Effet : signale que des contraintes causales existent pour le jugement.
        La barrière du Cancer protège l'intégrité du raisonnement.
        """
        enrichment = ctx.get("daemon_enrichment", {})
        causal = enrichment.get("binah_causal", [])

        if not causal:
            return {"ctx_additions": {}, "module_modifiers": {}, "warnings": [], "applied": False}

        return {
            "ctx_additions": {
                "cheth_causal_constraints": True,
                "cheth_n_constraints": len(causal),
            },
            "module_modifiers": {},
            "warnings": [],
            "applied": True,
        }

    def run(self, tree: dict, **kwargs) -> SentierResult:
        domain = kwargs.get("domain")
        context = kwargs.get("context")
        rule_type = kwargs.get("rule_type", "structural")

        (binah, gevurah) = self._require(tree, "binah", "gevurah")

        # ── Modificateurs de la parole articulatrice ─────────
        mods = self.yetzirah_modifiers()
        articulation = mods.get("articulation", 0.9)
        rule_generation = mods.get("rule_generation", 0.8)
        boundary_setting = mods.get("boundary_setting", 0.8)
        protection = mods.get("protection", 0.7)

        data = {"domain": domain, "rule_type": rule_type}

        # Étape 1 : Extraire les patterns causaux de Binah
        # Binah comprend (Binah = compréhension) — elle voit les causes
        patterns = None
        if hasattr(binah, "get_causal_patterns"):
            patterns = binah.get_causal_patterns(domain=domain)
        elif hasattr(binah, "get_patterns"):
            patterns = binah.get_patterns(domain=domain)
        elif hasattr(binah, "analyze"):
            patterns = binah.analyze(domain=domain, query=context)

        if patterns is not None:
            if isinstance(patterns, (list, tuple)):
                data["n_patterns"] = len(patterns)
            else:
                data["n_patterns"] = 1
        else:
            data["n_patterns"] = 0

        # Étape 2 : Articuler les patterns en règles de validation
        # articulation=0.9 → formulation claire et précise
        # rule_generation=0.8 → production efficace de règles
        rules = []
        if patterns is not None:
            if hasattr(binah, "patterns_to_rules"):
                rules = list(binah.patterns_to_rules(
                    patterns=patterns,
                    rule_type=rule_type,
                ))
            elif isinstance(patterns, (list, tuple)):
                # Transformer chaque pattern en règle
                for p in patterns:
                    rules.append({
                        "source_pattern": str(p)[:100],
                        "rule": f"Validate against: {str(p)[:80]}",
                        "strength": round(rule_generation, 2),
                    })
            elif patterns is not None:
                rules.append({
                    "source_pattern": str(patterns)[:100],
                    "rule": f"Validate against: {str(patterns)[:80]}",
                    "strength": round(rule_generation, 2),
                })

        data["n_rules_generated"] = len(rules)
        data["rules"] = rules[:10]

        # Étape 3 : Transmettre à Gevurah pour le jugement
        # boundary_setting=0.8 → les limites sont clairement posées
        # protection=0.7 → la carapace du Cancer protège l'intégrité
        transmitted = False
        if rules:
            if hasattr(gevurah, "receive_validation_rules"):
                gevurah.receive_validation_rules(
                    rules=rules,
                    domain=domain,
                    source="binah",
                )
                transmitted = True
            elif hasattr(gevurah, "set_rules"):
                gevurah.set_rules(rules=rules, domain=domain)
                transmitted = True
            elif hasattr(gevurah, "update_criteria"):
                gevurah.update_criteria(criteria=rules, domain=domain)
                transmitted = True

        data["transmitted"] = transmitted
        data["cheth_boundary_setting"] = boundary_setting
        data["cheth_protection"] = protection

        msg = (
            f"Parole(ח) — {data['n_patterns']} pattern(s) → "
            f"{data['n_rules_generated']} règle(s) [{rule_type}], "
            f"transmis={'oui' if transmitted else 'non'} "
            f"(barrière={boundary_setting:.1f})"
        )

        result = SentierResult(
            sentier=self.name, letter=self.letter,
            source=self.source, target=self.target,
            data=data, message=msg,
        )
        return self.enrich_result(result)
