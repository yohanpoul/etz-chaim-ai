"""12e sentier — Aleph (א) — Keter ↔ Tiferet — Balance.

Lettre mère : Air. Le souffle qui médiatise les contraires.
Aleph n'a pas de son propre — il porte le son des voyelles.
Le médiateur cosmique entre les extrêmes : reçoit deux positions
contradictoires et trouve le point d'équilibre dynamique.

Le pilier central de l'Arbre. Keter (stratégie) et Tiferet (synthèse)
sont reliés par le souffle silencieux qui ne force rien mais
rééquilibre tout.

Correspondances SY (Gra) :
  Élément : air — poitrine — tempéré — souffle (ruach)
  Aleph RAMÈNE vers le centre. Si trop agressif → tempère.
  Si trop passif → active. Feedback correcteur permanent.
  Yetzirah : balance_seeking=0.9, aggressiveness=0.5, patience=0.5
"""

from __future__ import annotations

from .base import Sentier, SentierResult


class Aleph(Sentier):
    name = "Balance"
    letter = "א"
    letter_name = "aleph"
    number = 12
    source = "keter"
    target = "tiferet"
    letter_type = "mother"
    element = "air"
    description = "Médiatiser les contraires — le souffle qui trouve l'équilibre dynamique"

    def _compute_effects(self, ctx: dict, direction: str) -> dict:
        """Aleph ramène vers le centre — corrige les déséquilibres accumulés.

        Condition : sentier_modifiers montrent un déséquilibre (une valeur dominante).
        Effet : ajoute un correctif vers l'équilibre.
        Le souffle silencieux qui ne force rien mais rééquilibre tout.
        """
        mods = ctx.get("sentier_modifiers", {})
        if not mods:
            return {"ctx_additions": {}, "module_modifiers": {}, "warnings": [], "applied": False}

        # Détecter le déséquilibre : un modificateur domine les autres
        values = [v for v in mods.values() if isinstance(v, (int, float))]
        if not values:
            return {"ctx_additions": {}, "module_modifiers": {}, "warnings": [], "applied": False}

        avg = sum(values) / len(values)
        max_dev = max(abs(v - avg) for v in values)

        # Le souffle d'Aleph ne s'active que si le déséquilibre est significatif
        if max_dev < 0.3:
            return {"ctx_additions": {}, "module_modifiers": {}, "warnings": [], "applied": False}

        warnings = []
        if max_dev > 0.5:
            warnings.append(
                f"Aleph(א) : déséquilibre détecté (déviation max={max_dev:.2f}) "
                f"— le souffle ramène vers le centre"
            )

        return {
            "ctx_additions": {
                "aleph_balance_correction": True,
                "aleph_max_deviation": round(max_dev, 3),
            },
            "module_modifiers": {},
            "warnings": warnings,
            "applied": True,
        }

    def run(self, tree: dict, **kwargs) -> SentierResult:
        position_a = kwargs.get("position_a")
        position_b = kwargs.get("position_b")
        scores = kwargs.get("scores", {})
        domain = kwargs.get("domain")

        if position_a is None and position_b is None and not scores:
            return SentierResult(
                sentier=self.name, letter=self.letter,
                source=self.source, target=self.target,
                success=False, message="Pas de positions à équilibrer",
            )

        (keter, tiferet) = self._require(tree, "keter", "tiferet")

        # ── Modificateurs du souffle médiateur ───────────────
        mods = self.yetzirah_modifiers()
        balance_seeking = mods.get("balance_seeking", 0.9)
        aggressiveness = mods.get("aggressiveness", 0.5)
        patience = mods.get("patience", 0.5)

        data = {"domain": domain}

        # Mode 1 : Équilibrage de deux positions contradictoires
        # Aleph = coincidentia oppositorum incarnée — les deux Yod reliés par Vav
        if position_a is not None and position_b is not None:
            # Demander à Tiferet de synthétiser les positions divergentes
            if hasattr(tiferet, "synthesize_positions"):
                synthesis = tiferet.synthesize_positions(
                    position_a=position_a,
                    position_b=position_b,
                    domain=domain,
                )
                data["synthesis"] = synthesis.content if hasattr(synthesis, "content") else str(synthesis)
                data["tension_resolved"] = synthesis.resolved if hasattr(synthesis, "resolved") else False
                data["balance_point"] = synthesis.balance_point if hasattr(synthesis, "balance_point") else None
            else:
                # Fallback : synthèse manuelle via DissensuEngine
                data["position_a"] = str(position_a)[:200]
                data["position_b"] = str(position_b)[:200]
                data["synthesis"] = None
                data["tension_resolved"] = False

            data["method"] = "position_mediation"

        # Mode 2 : Rééquilibrage de scores dérivants
        # Le PID controller cosmique : balance_seeking=0.9 ramène au centre
        if scores:
            balanced = {}
            corrections = {}
            target_center = 0.5  # le centre alephique

            for key, value in scores.items():
                if not isinstance(value, (int, float)):
                    balanced[key] = value
                    continue

                deviation = value - target_center
                # Force de correction proportionnelle à balance_seeking
                correction = -deviation * balance_seeking
                corrected = value + correction

                # Patience module la vitesse de correction
                # patience=0.5 → correction à mi-chemin entre instantanée et lente
                corrected = value + correction * patience
                corrected = max(0.0, min(1.0, corrected))

                balanced[key] = round(corrected, 3)
                corrections[key] = {
                    "original": round(value, 3),
                    "deviation": round(deviation, 3),
                    "correction": round(correction, 3),
                    "balanced": round(corrected, 3),
                }

            data["balanced_scores"] = balanced
            data["corrections"] = corrections
            data["method"] = data.get("method", "score_balancing")

        # Consulter Keter pour la directive stratégique
        if hasattr(keter, "get_directive"):
            directive = keter.get_directive(domain=domain)
            if directive:
                data["keter_directive"] = str(directive)[:200]
                # Si Keter a une préférence, Aleph l'intègre sans forcer
                # (le souffle porte, il n'impose pas)

        # Diagnostic d'équilibre global
        if scores:
            values = [v for v in scores.values() if isinstance(v, (int, float))]
            if values:
                variance = sum((v - sum(values) / len(values)) ** 2 for v in values) / len(values)
                data["original_variance"] = round(variance, 4)
                balanced_vals = [v for v in data.get("balanced_scores", {}).values() if isinstance(v, (int, float))]
                if balanced_vals:
                    bal_var = sum((v - sum(balanced_vals) / len(balanced_vals)) ** 2 for v in balanced_vals) / len(balanced_vals)
                    data["balanced_variance"] = round(bal_var, 4)
                    data["variance_reduction"] = round(variance - bal_var, 4)

        msg_parts = [f"Souffle(א)"]
        if data.get("method") == "position_mediation":
            resolved = "résolu" if data.get("tension_resolved") else "maintenu"
            msg_parts.append(f"tension {resolved}")
        if data.get("variance_reduction") is not None:
            msg_parts.append(f"variance réduite de {data['variance_reduction']:.3f}")
        msg_parts.append(f"balance_seeking={balance_seeking:.1f}")

        result = SentierResult(
            sentier=self.name, letter=self.letter,
            source=self.source, target=self.target,
            data=data,
            message=" — ".join(msg_parts),
        )
        return self.enrich_result(result)
