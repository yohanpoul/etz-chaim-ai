"""20e sentier — Teth (ט) — Chesed ↔ Gevurah — QualityFeedback.

Lettre simple : sens = goût (te'imah).
Boucle de feedback entre exploration (Chesed) et jugement (Gevurah).
Chesed propose, Gevurah évalue, le feedback revient.
Le goût exige le CONTACT DIRECT — on ne goûte qu'en touchant.

Teth = le serpent (selon certains), le bien caché. Le Lion = force
du jugement direct.

Correspondances SY (Gra) :
  Sens : goût (te'imah) — discernement par contact intime
  Zodiaque : Lion (Arieh) — Mois : Av — Direction : nord-haut
  Organe : oesophage (veshet)
  Yetzirah : direct_feedback=0.9, experiential_testing=0.9,
  proxy_reliance=0.1, intimacy=0.8
"""

from __future__ import annotations

from .base import Sentier, SentierResult


class Teth(Sentier):
    name = "QualityFeedback"
    letter = "ט"
    letter_name = "teth"
    number = 20
    source = "chesed"
    target = "gevurah"
    letter_type = "simple"
    sense = "goût"
    description = "Feedback direct — le goût qui teste par contact intime"

    def _compute_effects(self, ctx: dict, direction: str) -> dict:
        """Teth filtre les explorations faibles AVANT Gevurah.

        Condition : ctx contient des résultats d'exploration (analogies, connexions).
        Effet : filtre les items avec score < 0.3, injecte pre_filtered=True.

        Le goût (te'imah) exige le contact direct — seules les explorations
        qui passent le test du goût arrivent à Gevurah pour jugement formel.
        """
        # Chercher les résultats d'exploration dans le ctx
        daemon_data = ctx.get("daemon_enrichment", {})
        analogies = daemon_data.get("analogies", [])
        explorations = daemon_data.get("explorations", [])

        items = analogies + explorations
        if not items:
            return {"ctx_additions": {}, "module_modifiers": {}, "warnings": [], "applied": False}

        # Filtrer les items faibles (< 0.3)
        mods = self.yetzirah_modifiers()
        threshold = mods.get("experiential_testing", 0.9) * 0.33  # → ~0.3

        strong = []
        weak = []
        for item in items:
            score = item.get("score", item.get("confidence", 0.5))
            if isinstance(score, (int, float)) and score < threshold:
                weak.append(item)
            else:
                strong.append(item)

        if weak:
            return {
                "ctx_additions": {
                    "pre_filtered": True,
                    "teth_filtered_count": len(weak),
                    "teth_kept_count": len(strong),
                },
                "module_modifiers": {},
                "warnings": [],
                "applied": True,
            }
        return {"ctx_additions": {}, "module_modifiers": {}, "warnings": [], "applied": False}

    def run(self, tree: dict, **kwargs) -> SentierResult:
        domain = kwargs.get("domain")
        proposal = kwargs.get("proposal")
        proposals = kwargs.get("proposals", [])
        threshold = kwargs.get("threshold", 0.5)

        (chesed, gevurah) = self._require(tree, "chesed", "gevurah")

        # ── Modificateurs du goût direct ─────────────────────
        mods = self.yetzirah_modifiers()
        direct_feedback = mods.get("direct_feedback", 0.9)
        experiential_testing = mods.get("experiential_testing", 0.9)
        intimacy = mods.get("intimacy", 0.8)
        judgment_speed = mods.get("judgment_speed", 0.7)

        data = {"domain": domain}

        # Étape 1 : Collecter les propositions de Chesed
        if proposal is not None:
            proposals = [proposal] + list(proposals)
        elif not proposals and hasattr(chesed, "get_proposals"):
            proposals = list(chesed.get_proposals(domain=domain))
        elif not proposals and hasattr(chesed, "explore"):
            try:
                result = chesed.explore(
                    query=domain or "general exploration",
                    seed_domain=domain or "general",
                )
                proposals = list(result.connections) if hasattr(result, "connections") else []
            except Exception:
                proposals = []

        data["n_proposals"] = len(proposals)

        # Étape 2 : Gevurah goûte chaque proposition par contact direct
        # direct_feedback=0.9 → pas de proxy, test par expérience
        # experiential_testing=0.9 → le goût ne ment pas
        feedback_results = []
        accepted = 0
        rejected = 0

        for p in proposals:
            # Soumettre directement à Gevurah pour jugement
            if hasattr(gevurah, "judge"):
                judgment = gevurah.judge(
                    hypothesis=str(p),
                    domain=domain,
                    threshold=threshold,
                )
                score = judgment.score if hasattr(judgment, "score") else 0.5
                passed = judgment.passed if hasattr(judgment, "passed") else score >= threshold
            elif hasattr(gevurah, "evaluate"):
                judgment = gevurah.evaluate(proposal=p, domain=domain)
                score = judgment.score if hasattr(judgment, "score") else 0.5
                passed = score >= threshold
            else:
                score = 0.5
                passed = True

            # Le goût est intime (intimacy=0.8) — feedback détaillé
            feedback_entry = {
                "proposal": str(p)[:100],
                "score": round(score, 3),
                "passed": passed,
            }

            if passed:
                accepted += 1
            else:
                rejected += 1

            # Renvoyer le feedback à Chesed pour apprentissage
            # Le feedback loop est direct — pas de médiation
            if hasattr(chesed, "receive_feedback"):
                chesed.receive_feedback(
                    proposal=p,
                    score=score,
                    passed=passed,
                    domain=domain,
                )
                feedback_entry["feedback_sent"] = True
            else:
                feedback_entry["feedback_sent"] = False

            feedback_results.append(feedback_entry)

        data["feedback_results"] = feedback_results[:10]
        data["n_accepted"] = accepted
        data["n_rejected"] = rejected
        data["acceptance_rate"] = round(accepted / len(proposals), 2) if proposals else 0.0
        data["teth_direct_feedback"] = direct_feedback
        data["teth_intimacy"] = intimacy

        msg = (
            f"Goût(ט) — {accepted}/{len(proposals)} accepté(s), "
            f"{rejected} rejeté(s) [{domain}], "
            f"feedback_direct={direct_feedback:.1f}"
        )

        result = SentierResult(
            sentier=self.name, letter=self.letter,
            source=self.source, target=self.target,
            data=data, message=msg,
        )
        return self.enrich_result(result)
