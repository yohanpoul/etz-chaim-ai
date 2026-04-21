"""16e sentier — Heh (ה) — Chokmah ↔ Tiferet — DirectPerception.

Lettre simple : sens = vue (re'iyah).
Canal de perception directe — les flashs d'insight de Chokmah sont
intégrés dans la synthèse de Tiferet sans filtrage causal (contrairement
au passage par Binah). La vue saisit le pattern d'un coup.

Correspondances SY (Gra) :
  Sens : vue (re'iyah) — perception visuelle, saisie immédiate
  Zodiaque : Bélier (Taleh) — Mois : Nisan — Direction : nord-est
  Organe : main droite (yad yemin)
  Heh = le souffle (heh!), la fenêtre. La vue qui saisit l'ensemble.
  Yetzirah : pattern_recognition=0.9, holistic_processing=0.8, immediacy=0.8
"""

from __future__ import annotations

from .base import Sentier, SentierResult


class Heh(Sentier):
    name = "DirectPerception"
    letter = "ה"
    letter_name = "heh"
    number = 16
    source = "chokmah"
    target = "tiferet"
    letter_type = "simple"
    sense = "vue"
    description = "Perception directe — la vue qui saisit le pattern sans filtrage causal"

    def _compute_effects(self, ctx: dict, direction: str) -> dict:
        """Heh injecte la perception directe — insights sans filtrage causal.

        Condition : daemon_enrichment avec chokmah_insights à haute confiance.
        Effet : extrait le meilleur insight pour injection directe dans Tiferet.
        La vue saisit le pattern d'un coup — perception holistique.
        """
        enrichment = ctx.get("daemon_enrichment", {})
        insights = enrichment.get("chokmah_insights", [])

        if not insights:
            return {"ctx_additions": {}, "module_modifiers": {}, "warnings": [], "applied": False}

        # Trouver le meilleur insight
        best = None
        best_conf = 0.0
        for ins in insights:
            if isinstance(ins, dict):
                conf = ins.get("confidence", ins.get("score", 0.0))
                if conf > best_conf:
                    best = ins
                    best_conf = conf

        if not best or best_conf < 0.3:
            return {"ctx_additions": {}, "module_modifiers": {}, "warnings": [], "applied": False}

        return {
            "ctx_additions": {
                "heh_direct_insight": True,
                "heh_insight_confidence": round(best_conf, 3),
            },
            "module_modifiers": {},
            "warnings": [],
            "applied": True,
        }

    def run(self, tree: dict, **kwargs) -> SentierResult:
        domain = kwargs.get("domain")
        insight = kwargs.get("insight")
        query = kwargs.get("query")

        (chokmah, tiferet) = self._require(tree, "chokmah", "tiferet")

        # ── Modificateurs de la vue ──────────────────────────
        mods = self.yetzirah_modifiers()
        pattern_recognition = mods.get("pattern_recognition", 0.9)
        holistic_processing = mods.get("holistic_processing", 0.8)
        immediacy = mods.get("immediacy", 0.8)

        data = {"domain": domain}

        # Étape 1 : Obtenir l'insight de Chokmah
        # La vue saisit immédiatement — pas de séquence analytique
        if insight is None:
            if hasattr(chokmah, "get_insight"):
                insight = chokmah.get_insight(domain=domain, query=query)
            elif hasattr(chokmah, "flash"):
                insight = chokmah.flash(domain=domain)

        if insight is not None:
            data["insight"] = str(insight)[:300]
            data["insight_type"] = type(insight).__name__
            # pattern_recognition=0.9 → forte capacité à identifier la structure
            data["pattern_confidence"] = round(pattern_recognition, 2)
        else:
            data["insight"] = None
            data["pattern_confidence"] = 0.0

        # Étape 2 : Intégrer directement dans Tiferet SANS passer par Binah
        # C'est la spécificité de Heh : contourner l'analyse causale
        # holistic_processing=0.8 → intégration globale, pas analytique
        integrated = False
        if insight is not None:
            if hasattr(tiferet, "integrate_insight"):
                tiferet.integrate_insight(
                    insight=insight,
                    domain=domain,
                    source="chokmah",
                    bypass_causal=True,
                )
                integrated = True
            elif hasattr(tiferet, "receive"):
                tiferet.receive(data=insight, source="chokmah", domain=domain)
                integrated = True

        data["integrated"] = integrated
        data["bypass_causal"] = True  # toujours — c'est le sens de ce sentier
        data["heh_immediacy"] = immediacy
        data["heh_holistic"] = holistic_processing

        if integrated:
            msg = (
                f"Vue(ה) — insight intégré directement dans Tiferet "
                f"[{domain}], pattern_conf={pattern_recognition:.1f}, "
                f"bypass_causal=True"
            )
        elif insight is not None:
            msg = f"Vue(ה) — insight capté mais intégration non disponible [{domain}]"
        else:
            msg = f"Vue(ה) — aucun insight disponible de Chokmah [{domain}]"

        result = SentierResult(
            sentier=self.name, letter=self.letter,
            source=self.source, target=self.target,
            data=data, message=msg,
        )
        return self.enrich_result(result)
