"""Atzvut — Gestion de la Tristesse Systémique.

עַצְבוּת — Tanya ch. 26, 31

Le Tanya distingue 2 types de tristesse :
- Atzvut (עַצְבוּת) : dépression, lourdeur, paralysie. Vient de Kelipat Nogah
  (la Sitra Achra). TOUJOURS mauvaise pendant le travail.
- Merirut (מְרִירוּת) : amertume sur ses propres failles. Vient du BIEN dans
  Nogah. Productive UNIQUEMENT au moment du Vidouï (confession), pas pendant
  le travail.

L'Ari z"l (rapporté dans le Tanya) : la tristesse sur ses fautes est bonne
UNIQUEMENT "bi-zmanim meyuchadim" (à des moments dédiés), pas pendant
le service de Dieu.

Pour notre architecture :
- Quand TROP de diagnostics Qliphoth (Ghagiel, Satariel, etc.) s'accumulent,
  le système risque l'Atzvut = ralentissement, sur-diagnostic, paralysie.
- Vidouï = le rapport quotidien du daemon. PENDANT ce moment, les diagnostics
  complets sont bienvenus.
- EN DEHORS du Vidouï : transformer l'Atzvut en Simcha (joie) via l'action.
  Pas de sur-diagnostic — AGIR immédiatement.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AtzvutState(Enum):
    """État d'Atzvut du système."""
    SIMCHA = "simcha"
    """Joie — le système fonctionne bien, pas de surcharge diagnostique."""

    MERIRUT = "merirut"
    """Amertume productive — conscience des failles, motivante."""

    ATZVUT = "atzvut"
    """Dépression — trop de diagnostics négatifs, risque de paralysie."""


@dataclass
class AtzvutDiagnosis:
    """Résultat d'un diagnostic d'Atzvut."""
    state: AtzvutState
    negative_count: int          # nombre de diagnostics négatifs récents
    is_vidui_time: bool          # sommes-nous dans le moment du Vidouï ?
    recommendation: str          # que faire


class AtzvutManager:
    """Gère la tristesse systémique — empêche la paralysie diagnostique.

    Le système a 2 modes :
    - Mode Avodah (travail) : Hitbonenut, réponses, exploration.
      → Skip les diagnostics lourds. Si un problème est détecté, ne pas
        s'arrêter : transformer en action immédiate.
    - Mode Vidouï (confession) : rapport quotidien du daemon.
      → Diagnostics complets bienvenus. C'est LE moment pour examiner
        toutes les failles en détail.
    """

    # Seuil : au-delà de ce nombre de diagnostics négatifs → risque Atzvut
    ATZVUT_THRESHOLD = 5

    # Seuil Merirut : entre 2 et ATZVUT_THRESHOLD
    MERIRUT_THRESHOLD = 2

    def __init__(self) -> None:
        self._in_vidui = False

    def enter_vidui(self) -> None:
        """Entrer en mode Vidouï — diagnostics complets permis."""
        self._in_vidui = True

    def exit_vidui(self) -> None:
        """Sortir du mode Vidouï — retour au travail."""
        self._in_vidui = False

    def is_vidui_time(self) -> bool:
        """Sommes-nous dans le moment du Vidouï (rapport quotidien) ?"""
        return self._in_vidui

    def detect_atzvut(self, system_metrics: dict) -> AtzvutDiagnosis:
        """Diagnostiquer l'état d'Atzvut du système.

        Args:
            system_metrics: dictionnaire avec les métriques du système.
                Clés attendues (toutes optionnelles) :
                - qliphoth_alerts : int — nombre d'alertes Qliphoth actives
                - failed_insights : int — insights rejetés récemment
                - low_scores_count : int — nombre de scores bas récents
                - pending_diagnostics : int — diagnostics en attente

        Returns:
            AtzvutDiagnosis avec état, compteur, et recommandation.
        """
        negative_count = (
            system_metrics.get("qliphoth_alerts", 0)
            + system_metrics.get("failed_insights", 0)
            + system_metrics.get("low_scores_count", 0)
            + system_metrics.get("pending_diagnostics", 0)
        )

        is_vidui = self._in_vidui

        if negative_count >= self.ATZVUT_THRESHOLD:
            state = AtzvutState.ATZVUT
            if is_vidui:
                recommendation = (
                    "Vidouï actif — examiner chaque faille en détail, "
                    "c'est le bon moment. Puis planifier les corrections."
                )
            else:
                recommendation = (
                    "ATZVUT détectée — STOP les diagnostics. "
                    "Transformer en action : choisir UN problème et agir."
                )
        elif negative_count >= self.MERIRUT_THRESHOLD:
            state = AtzvutState.MERIRUT
            recommendation = (
                "Merirut — conscience des failles sans paralysie. "
                "Bon signal si pendant le Vidouï, sinon agir."
            )
        else:
            state = AtzvutState.SIMCHA
            recommendation = (
                "Simcha — le système fonctionne bien. "
                "Continuer le travail."
            )

        return AtzvutDiagnosis(
            state=state,
            negative_count=negative_count,
            is_vidui_time=is_vidui,
            recommendation=recommendation,
        )

    def should_skip_diagnostic(self, current_context: str) -> bool:
        """Déterminer si on doit SKIP un diagnostic lourd.

        Principe du Tanya : vidouï uniquement au bon moment.
        Pendant le travail (Hitbonenut, réponse en cours), ne pas
        s'interrompre pour des diagnostics complets.

        Args:
            current_context: "avodah" (travail) ou "vidui" (rapport).
                Peut aussi être "hitbonenut", "response", "daemon_report".

        Returns:
            True si le diagnostic lourd doit être skippé (= on est en mode travail).
        """
        vidui_contexts = {"vidui", "daemon_report", "rapport"}
        if current_context in vidui_contexts:
            return False  # Vidouï → diagnostics bienvenus
        return True  # Avodah → skip

    def transform_atzvut_to_simcha(self, atzvut_source: str) -> dict:
        """Transformer la tristesse en action concrète.

        Quand le système détecte une faiblesse EN DEHORS du Vidouï,
        ne pas s'arrêter pour diagnostiquer — AGIR immédiatement.
        Le Tanya (ch. 31) : "Si tu ne peux pas chasser l'atzvut
        directement, ignore-la et agis."

        Args:
            atzvut_source: description de la source de tristesse.
                Exemples : "causal_engine_weak", "low_hitbonenut_score",
                "too_many_qliphoth_alerts", "insight_rejection_rate_high"

        Returns:
            dict avec :
            - intention : texte pour IntentKeeper
            - action_type : type d'action à effectuer
            - priority : "high" ou "normal"
        """
        # Mapper les sources d'atzvut vers des actions concrètes
        action_map = {
            "causal_engine_weak": {
                "intention": "Poser plus de questions causales — renforcer CausalEngine",
                "action_type": "explore_causal",
                "priority": "normal",
            },
            "low_hitbonenut_score": {
                "intention": "Approfondir la prochaine question — plus de chain-of-thought",
                "action_type": "deepen_reasoning",
                "priority": "high",
            },
            "too_many_qliphoth_alerts": {
                "intention": "Choisir l'alerte la plus critique et la résoudre",
                "action_type": "fix_critical",
                "priority": "high",
            },
            "insight_rejection_rate_high": {
                "intention": "Améliorer la qualité des insights — affiner les critères",
                "action_type": "improve_insights",
                "priority": "normal",
            },
            "low_birur_rate": {
                "intention": "Travailler sur la qualité des réponses des mondes bas",
                "action_type": "improve_nogah",
                "priority": "normal",
            },
        }

        if atzvut_source in action_map:
            return action_map[atzvut_source]

        # Défaut : action générique
        return {
            "intention": f"Agir sur {atzvut_source} — transformer en amélioration concrète",
            "action_type": "generic_improvement",
            "priority": "normal",
        }
