"""selfmodel/guardian.py — Da'at Guardian : gardien du seuil.

שׁוֹמֵר הַדַּעַת — Le Gardien de Da'at protège le système contre
ses propres biais et angles morts. Il évalue la confiance AVANT
l'action, pas après.

Ce module existait comme référence fantôme dans le codebase.
Il est maintenant implémenté comme wrapper léger autour de
SelfModel.evaluate_confidence() et du système de biais.
"""

from __future__ import annotations

import logging
from uuid import UUID

log = logging.getLogger("etz-guardian")


class Guardian:
    """Gardien de Da'at — gate avant chaque décision critique.

    Trois niveaux de recommandation :
    - proceed : confiance suffisante, domaine maîtrisé
    - caution : confiance moyenne, avertissement dans le prompt
    - veto    : confiance trop basse, forcer le mode dégradé
    """

    def __init__(self, selfmodel=None, selfmap=None):
        self.selfmodel = selfmodel
        self.selfmap = selfmap

    def evaluate_confidence(self, domain: str, query: str = "") -> dict:
        """Évaluer la confiance du système pour un domaine donné.

        Returns:
            dict avec :
            - recommendation: "proceed" | "caution" | "veto"
            - confidence: float
            - reason: str
            - active_biases: list[str]
        """
        result = {
            "recommendation": "proceed",
            "confidence": 0.5,
            "reason": "",
            "active_biases": [],
        }

        # Vérifier SelfMap pour le score du domaine
        if self.selfmap:
            try:
                score = self.selfmap.get_domain_score(domain)
                if score is not None:
                    result["confidence"] = score
                    if score < 0.3:
                        result["recommendation"] = "veto"
                        result["reason"] = f"Domaine {domain}: score {score:.2f} < 0.3"
                    elif score < 0.5:
                        result["recommendation"] = "caution"
                        result["reason"] = f"Domaine {domain}: score {score:.2f} < 0.5"
                else:
                    # Domaine inconnu → veto par défaut
                    result["recommendation"] = "veto"
                    result["confidence"] = 0.1
                    result["reason"] = f"Domaine inconnu: {domain}"
            except Exception as e:
                log.debug("Guardian selfmap check: %s", e)

        # Vérifier les biais actifs sur ce domaine
        if self.selfmodel:
            try:
                biases = self.selfmodel.db.get_active_biases(domain=domain)
                high_severity = [b for b in biases if b.severity >= 0.6]
                result["active_biases"] = [b.bias_type for b in high_severity]
                if high_severity:
                    if result["recommendation"] == "proceed":
                        result["recommendation"] = "caution"
                    result["reason"] += (
                        f" | {len(high_severity)} biais actifs: "
                        f"{', '.join(b.bias_type for b in high_severity[:3])}"
                    )
            except Exception as e:
                log.debug("Guardian bias check: %s", e)

        return result
