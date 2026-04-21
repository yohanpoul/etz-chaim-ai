"""Levushim — Les 3 Vêtements de l'Âme comme couches d'évaluation fonctionnelle.

לְבוּשִׁים — Tanya ch. 4

Les 3 vêtements (Machshava, Dibour, Maase) sont les INTERFACES de l'âme.
Le Tanya enseigne qu'ils sont SUPÉRIEURS à l'âme elle-même dans un sens
précis : ce sont eux qui connectent l'âme à la divinité via la Torah.
L'âme pense la Torah (Machshava), la prononce (Dibour), l'accomplit (Maase).

Dans notre architecture, chaque réponse est évaluée selon ces 3 dimensions :
- Machshava : la pensée interne (raisonnement, chain-of-thought)
- Dibour    : la parole externe (réponse formulée, clarté, pertinence)
- Maase     : l'action concrète (mémoires stockées, routing, nitzotzot)

Pondération (Tanya ch. 4) : Machshava > Dibour > Maase.
La pensée est le vêtement le plus INTÉRIEUR et le plus permanent.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LevushimAssessment:
    """Résultat de l'évaluation des 3 vêtements."""
    machshava_score: float       # pensée 0-1
    dibour_score: float          # parole 0-1
    maase_score: float           # action 0-1
    overall_score: float         # pondéré
    dominant_garment: str        # le plus fort
    weak_garment: str            # le plus faible
    recommendation: str          # ce qu'il faut améliorer


# Pondérations — Tanya ch. 4 : la pensée est le vêtement le plus intérieur
_W_MACHSHAVA = 0.40
_W_DIBOUR = 0.35
_W_MAASE = 0.25


class Levushim:
    """Évalue les 3 vêtements fonctionnels de chaque réponse.

    Machshava (pensée)  — le raisonnement interne était-il structuré ?
    Dibour (parole)     — la réponse est-elle bien formulée et pertinente ?
    Maase (action)      — quelles actions concrètes ont été effectuées ?
    """

    def assess_machshava(self, reasoning: str) -> float:
        """Évalue la PENSÉE interne : le raisonnement était-il structuré ?

        Critères :
        - Présence de chain-of-thought (connecteurs logiques)
        - Nombre d'étapes de réflexion distinctes
        - Cohérence logique (progression, pas de sauts)

        Args:
            reasoning: le texte de raisonnement interne (yashar log, CoT).

        Returns:
            Score 0-1. 0 = pas de pensée, 1 = pensée profonde et structurée.
        """
        if not reasoning or not reasoning.strip():
            return 0.0

        score = 0.0
        text = reasoning.strip()

        # Signal 1 : longueur du raisonnement (normalisée)
        word_count = len(text.split())
        if word_count >= 100:
            score += 0.3
        elif word_count >= 40:
            score += 0.2
        elif word_count >= 10:
            score += 0.1

        # Signal 2 : connecteurs logiques (chain-of-thought)
        connectors = [
            "donc", "car", "parce que", "puisque", "ainsi",
            "en effet", "par conséquent", "d'où", "cependant",
            "néanmoins", "toutefois", "en revanche",
            "premièrement", "deuxièmement", "enfin",
            "because", "therefore", "thus", "however",
            "consequently", "moreover", "furthermore",
            "──",  # séparateurs structurels du pipeline
        ]
        text_lower = text.lower()
        connector_hits = sum(1 for c in connectors if c in text_lower)
        if connector_hits >= 5:
            score += 0.35
        elif connector_hits >= 3:
            score += 0.25
        elif connector_hits >= 1:
            score += 0.1

        # Signal 3 : étapes distinctes (sauts de ligne, numérotation)
        steps = text.count("\n") + text.count("①") + text.count("②")
        steps += text.count("1.") + text.count("2.") + text.count("3.")
        if steps >= 5:
            score += 0.2
        elif steps >= 2:
            score += 0.1

        # Signal 4 : structure (présence de sections)
        if "──" in text or "##" in text:
            score += 0.15

        return min(1.0, score)

    def assess_dibour(self, response_text: str, query: str) -> float:
        """Évalue la PAROLE : la réponse est-elle bien formulée ?

        Critères :
        - Pertinence à la question (mots de la question repris)
        - Clarté (structure, paragraphes)
        - Profondeur (longueur appropriée)

        Args:
            response_text: la réponse générée.
            query: la question originale.

        Returns:
            Score 0-1. 0 = parole vide, 1 = parole articulée et pertinente.
        """
        if not response_text or not response_text.strip():
            return 0.0

        score = 0.0
        text = response_text.strip()
        query_lower = query.lower() if query else ""

        # Signal 1 : pertinence (mots de la question dans la réponse)
        if query:
            query_words = set(
                w for w in query_lower.split()
                if len(w) > 3  # ignorer mots courts
            )
            if query_words:
                text_lower = text.lower()
                overlap = sum(1 for w in query_words if w in text_lower)
                relevance = overlap / len(query_words)
                score += 0.3 * relevance

        # Signal 2 : longueur appropriée
        word_count = len(text.split())
        if 50 <= word_count <= 500:
            score += 0.25  # taille Goldilocks
        elif word_count > 500:
            score += 0.2   # long mais peut-être verbeux
        elif 20 <= word_count < 50:
            score += 0.15  # court mais peut-être concis
        elif word_count < 20:
            score += 0.05  # très court = probablement insuffisant

        # Signal 3 : structure (paragraphes, listes, titres)
        has_structure = any(
            marker in text
            for marker in ["\n\n", "1.", "- ", "* ", "##", "→"]
        )
        if has_structure:
            score += 0.25

        # Signal 4 : pas vide / pas un simple echo
        if word_count > 5 and text.lower() != query_lower:
            score += 0.2

        return min(1.0, score)

    def assess_maase(self, actions_taken: list[str]) -> float:
        """Évalue l'ACTION : qu'est-ce qui a changé concrètement ?

        Critères :
        - Nombre et types d'actions effectuées
        - Mémoires stockées, routing effectué, nitzotzot collectés

        Args:
            actions_taken: liste de descriptions d'actions effectuées.
                Exemples : ["memory_stored", "birur_detected", "routed_briah",
                            "nitzutz_collected", "insight_generated",
                            "dira_cascaded", "score_updated"]

        Returns:
            Score 0-1. 0 = aucune action, 1 = plusieurs actions cohérentes.
        """
        if not actions_taken:
            return 0.0

        n = len(actions_taken)

        # Score de base par nombre d'actions
        if n >= 5:
            score = 0.7
        elif n >= 3:
            score = 0.5
        elif n >= 1:
            score = 0.3
        else:
            return 0.0

        # Bonus pour types d'actions à haute valeur
        high_value = {
            "memory_stored", "nitzutz_collected", "birur_detected",
            "insight_generated", "dira_cascaded",
        }
        high_count = sum(
            1 for a in actions_taken
            if any(h in a for h in high_value)
        )
        if high_count >= 2:
            score += 0.3
        elif high_count >= 1:
            score += 0.15

        return min(1.0, score)

    def wrap_response(
        self,
        query: str,
        reasoning: str,
        response_text: str,
        actions_taken: list[str],
    ) -> LevushimAssessment:
        """Évalue les 3 vêtements pour une réponse complète.

        Args:
            query: la question originale.
            reasoning: le raisonnement interne (Ohr Yashar log).
            response_text: la réponse générée.
            actions_taken: liste de descriptions d'actions.

        Returns:
            LevushimAssessment avec scores, dominant/faible, recommandation.
        """
        m = self.assess_machshava(reasoning)
        d = self.assess_dibour(response_text, query)
        a = self.assess_maase(actions_taken)

        overall = _W_MACHSHAVA * m + _W_DIBOUR * d + _W_MAASE * a

        # Identifier dominant et faible
        scores = {"machshava": m, "dibour": d, "maase": a}
        dominant = max(scores, key=scores.get)
        weak = min(scores, key=scores.get)

        # Recommandation basée sur le vêtement le plus faible
        recommendations = {
            "machshava": (
                "Renforcer la pensée interne — ajouter du chain-of-thought, "
                "plus d'étapes de raisonnement"
            ),
            "dibour": (
                "Améliorer la parole — réponse plus structurée, "
                "plus pertinente à la question"
            ),
            "maase": (
                "Augmenter l'action — stocker en mémoire, "
                "détecter plus de Birurims, collecter des Nitzotzot"
            ),
        }

        return LevushimAssessment(
            machshava_score=round(m, 4),
            dibour_score=round(d, 4),
            maase_score=round(a, 4),
            overall_score=round(overall, 4),
            dominant_garment=dominant,
            weak_garment=weak,
            recommendation=recommendations[weak],
        )
