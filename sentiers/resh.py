"""30e sentier — Resh (ר) — Yesod ↔ Hod — PersistPolicy.

Lettre double : deux politiques de persistance.
  dagesh : stockage immédiat — toute évaluation SelfMap est persistée en Yesod
  rafeh  : stockage sélectif — seules les évaluations à haute confiance sont persistées

Correspondances SY (Gra) :
  Planète : Mercure (Kokhav) — le messager rapide
  Jour : Jeudi — Porte : narine gauche — Direction : sud
  Opposés : dagesh=paix (shalom) / rafeh=guerre (milchamah)
  Paix = coexistence de toutes les données (store everything).
  Guerre = sélection darwinienne, seuls les forts persistent.
  Mercure = rapidité du transit mémoire↔connaissance.
"""

from __future__ import annotations

from .base import Sentier, SentierResult


class Resh(Sentier):
    name = "PersistPolicy"
    letter = "ר"
    letter_name = "resh"
    number = 30
    source = "yesod"
    target = "hod"
    letter_type = "double"
    dagesh_desc = "Stockage immédiat : toute évaluation persistée (paix)"
    rafeh_desc = "Stockage sélectif : seules les hautes confiances persistées (guerre)"
    mode = "rafeh"
    description = "Politique de persistance entre mémoire et self-knowledge"

    def _compute_effects(self, ctx: dict, direction: str) -> dict:
        """Resh module la politique de mémoire selon le mode paix/guerre.

        Condition : des mémoires ont été rappelées (ctx['memories']).
        Dagesh (paix) : toutes les mémoires comptent.
        Rafeh (guerre) : seules les mémoires haute confiance comptent, warning si trop faibles.
        """
        memories = ctx.get("memories", [])
        if not memories:
            return {"ctx_additions": {}, "module_modifiers": {}, "warnings": [], "applied": False}

        warnings = []
        additions = {"resh_persist_mode": self.mode}

        if self.mode == "rafeh":
            # Guerre : filtrer les faibles
            high_conf = [m for m in memories
                         if hasattr(m, "confidence") and m.confidence >= 0.5]
            if len(high_conf) < len(memories) // 2:
                warnings.append(
                    f"Resh(guerre) : {len(memories) - len(high_conf)}/{len(memories)} "
                    f"mémoires sous le seuil — la réponse repose sur peu de données fiables"
                )
            additions["resh_high_conf_count"] = len(high_conf)

        return {
            "ctx_additions": additions,
            "module_modifiers": {},
            "warnings": warnings,
            "applied": True,
        }

    def run(self, tree: dict, **kwargs) -> SentierResult:
        domain = kwargs.get("domain", "general")
        min_confidence = kwargs.get("min_confidence", 0.5)

        (yesod, hod) = self._require(tree, "yesod", "hod")

        # ── Modificateurs paix/guerre ────────────────────────
        mods = self.yetzirah_modifiers()
        selectivity = mods.get("selectivity", 0.5)
        conflict_tolerance = mods.get("conflict_tolerance", 0.5)

        # Lire la compétence via Hod (lecture DB, pas d'eval LLM)
        score = hod.read_competence(domain)

        data = {
            "domain": domain,
            "score": score.score if score else 0.0,
            "n_evals": score.n_evals if score else 0,
            "persisted": False,
        }

        # Décision de persistance selon le mode
        confidence = min(0.5 + (data["n_evals"] * 0.05), 0.9)

        if self.mode == "dagesh":
            # Paix (shalom) : tout coexiste, tout est persisté
            # conflict_tolerance=0.9 → même les contradictions persistent
            yesod.remember(
                content=f"SelfMap eval via Resh [paix]: {domain} → {data['score']:.2f}",
                source_sephirah="hod",
                confidence=confidence,
                domain="selfmap",
                tags=["eval", domain, "resh-paix"],
                ttl_days=30,
            )
            data["persisted"] = True
            data["policy"] = "dagesh/paix — persisté (coexistence)"
        else:
            # Guerre (milchamah) : sélection impitoyable
            # selectivity=0.9 → seuil de confiance relevé par la guerre
            war_threshold = min_confidence + (selectivity * 0.2)
            if confidence >= war_threshold:
                yesod.remember(
                    content=f"SelfMap eval via Resh [guerre]: {domain} → {data['score']:.2f}",
                    source_sephirah="hod",
                    confidence=confidence,
                    domain="selfmap",
                    tags=["eval", domain, "resh-guerre"],
                    ttl_days=60,
                )
                data["persisted"] = True
                data["policy"] = (
                    f"rafeh/guerre — persisté "
                    f"(conf={confidence:.2f} >= seuil_guerre={war_threshold:.2f})"
                )
            else:
                data["policy"] = (
                    f"rafeh/guerre — éliminé "
                    f"(conf={confidence:.2f} < seuil_guerre={war_threshold:.2f})"
                )

        data["war_selectivity"] = selectivity

        result = SentierResult(
            sentier=self.name, letter=self.letter,
            source=self.source, target=self.target,
            mode=self.mode, data=data,
            message=data["policy"],
        )
        return self.enrich_result(result)
