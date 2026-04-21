"""Predictor — prédiction d'erreurs AVANT qu'elles ne se produisent.

Le cœur prophétique de Da'at. Utilise le self-model pour anticiper
les erreurs sur une tâche donnée, AVANT de la lancer.

"Pour cette tâche en chimie organique, je prédis :
 - 70% de chance de sur-confiance (biais détecté)
 - domaine à 0.3 sur SelfMap
 - 3 échecs similaires dans le graphe FailureToInsight"
"""

from __future__ import annotations

import re

from selfmodel.models import BiasEntry, Prediction, SelfState


# Mots-clés associés aux domaines connus
DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "machine_learning": [
        "ml", "deep learning", "neural", "transformer", "attention",
        "gradient", "backpropagation", "model", "training", "loss",
    ],
    "neuroscience": [
        "brain", "neuron", "cortex", "hippocampus", "synapse",
        "cognitive", "neural", "plasticity",
    ],
    "kabbale": [
        "sefirot", "kabbale", "kabbalah", "zohar", "tsimtsum",
        "arbre", "tikkun", "qliphoth",
    ],
    "biology": [
        "biology", "cell", "gene", "evolution", "organism",
        "metabolism", "protein",
    ],
    "physics": [
        "physics", "quantum", "entropy", "energy", "field",
        "thermodynamic", "conservation",
    ],
    "writing": [
        "writing", "essay", "narrative", "style", "prose",
        "paragraph", "clarity",
    ],
    "code": [
        "code", "python", "function", "class", "algorithm",
        "debug", "refactor", "test",
    ],
}


def _detect_domains(text: str) -> list[str]:
    """Détecter les domaines mentionnés dans un texte."""
    words = set(re.findall(r'\b[a-zA-ZÀ-ÿ]{2,}\b', text.lower()))
    scores: dict[str, int] = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in words)
        if score > 0:
            scores[domain] = score
    return sorted(scores, key=scores.get, reverse=True)


class Predictor:
    """Prédit les erreurs du système AVANT l'exécution d'une tâche.

    Utilise :
    - L'état courant du système (SelfState)
    - Les biais actifs (BiasEntry)
    - La description de la tâche
    """

    def predict(
        self,
        task_description: str,
        state: SelfState | None = None,
        active_biases: list[BiasEntry] | None = None,
        prediction_history: list[Prediction] | None = None,
    ) -> list[Prediction]:
        """Prédire les erreurs probables pour une tâche donnée.

        Returns:
            Liste de Prediction ordonnées par confiance décroissante.
        """
        predictions: list[Prediction] = []
        biases = active_biases or []

        # Détecter les domaines de la tâche
        domains = _detect_domains(task_description)
        primary_domain = domains[0] if domains else ""

        # 1. Prédictions basées sur les biais actifs
        predictions.extend(
            self._predict_from_biases(biases, primary_domain, task_description)
        )

        # 2. Prédictions basées sur l'état du système
        if state:
            predictions.extend(
                self._predict_from_state(state, primary_domain, task_description)
            )

        # 3. Ajuster la confiance en fonction de l'historique
        if prediction_history:
            self._adjust_confidence(predictions, prediction_history)

        # Trier par confiance décroissante
        predictions.sort(key=lambda p: p.predicted_confidence, reverse=True)

        return predictions

    def _predict_from_biases(
        self,
        biases: list[BiasEntry],
        domain: str,
        task: str,
    ) -> list[Prediction]:
        """Prédictions basées sur les biais connus."""
        predictions = []

        for bias in biases:
            # Biais global ou spécifique au domaine de la tâche
            if bias.domain and bias.domain != domain and domain:
                continue

            confidence = bias.severity * 0.8  # Severity modulates confidence

            predictions.append(Prediction(
                prediction=(
                    f"Bias '{bias.bias_type}' likely to manifest: "
                    f"{bias.description}"
                ),
                domain=domain or bias.domain,
                predicted_error_type=_bias_to_qliphah(bias.bias_type),
                predicted_confidence=round(min(1.0, confidence), 2),
            ))

        return predictions

    def _predict_from_state(
        self,
        state: SelfState,
        domain: str,
        task: str,
    ) -> list[Prediction]:
        """Prédictions basées sur l'état du système."""
        predictions = []

        # Hod : domaine faible ?
        hod = state.hod_stats
        if hod and domain:
            weak = hod.get("weak_domains", [])
            if domain in weak:
                predictions.append(Prediction(
                    prediction=(
                        f"Domain '{domain}' is weak (SelfMap). "
                        f"High probability of poor quality output."
                    ),
                    domain=domain,
                    predicted_error_type="samael",
                    predicted_confidence=0.7,
                ))

            unknown = hod.get("unknown_domains", [])
            if domain in unknown:
                predictions.append(Prediction(
                    prediction=(
                        f"Domain '{domain}' is unknown (never evaluated). "
                        f"Output quality unpredictable."
                    ),
                    domain=domain,
                    predicted_error_type="satariel",
                    predicted_confidence=0.6,
                ))

        # Yesod : mémoire dégradée ?
        yesod = state.yesod_stats
        if yesod:
            contradictions = yesod.get("contradictions_open", 0)
            if contradictions > 5:
                predictions.append(Prediction(
                    prediction=(
                        f"{contradictions} open contradictions in EpisteMemory. "
                        f"Risk of using conflicting knowledge."
                    ),
                    domain=domain,
                    predicted_error_type="thagirion",
                    predicted_confidence=min(0.8, contradictions * 0.1),
                ))

        # Gevurah : juge malade ?
        gevurah = state.gevurah_stats
        if gevurah and gevurah.get("level") != "healthy":
            predictions.append(Prediction(
                prediction=(
                    f"AutoJudge is unhealthy ({gevurah.get('level')}). "
                    f"Quality control may be unreliable."
                ),
                domain=domain,
                predicted_error_type="golachab",
                predicted_confidence=0.5,
            ))

        return predictions

    def _adjust_confidence(
        self,
        predictions: list[Prediction],
        history: list[Prediction],
    ) -> None:
        """Ajuster la confiance en fonction de l'historique.

        Si nos prédictions passées pour ce type d'erreur étaient souvent
        fausses, baisser la confiance. Si elles étaient justes, augmenter.
        """
        if not history:
            return

        # Calculer accuracy par error_type
        accuracy_by_type: dict[str, tuple[int, int]] = {}
        for p in history:
            if p.was_correct is None:
                continue
            t = p.predicted_error_type
            correct, total = accuracy_by_type.get(t, (0, 0))
            accuracy_by_type[t] = (
                correct + (1 if p.was_correct else 0),
                total + 1,
            )

        # Ajuster chaque prédiction
        for pred in predictions:
            stats = accuracy_by_type.get(pred.predicted_error_type)
            if stats and stats[1] >= 3:  # Au moins 3 prédictions vérifiées
                accuracy = stats[0] / stats[1]
                # Si accuracy < 0.5, on est mauvais → baisser
                # Si accuracy > 0.5, on est bon → augmenter légèrement
                adjustment = (accuracy - 0.5) * 0.4
                pred.predicted_confidence = round(
                    max(0.1, min(0.95, pred.predicted_confidence + adjustment)),
                    2,
                )


def _bias_to_qliphah(bias_type: str) -> str:
    """Mapper un type de biais vers la Qliphah correspondante."""
    mapping = {
        "overconfidence": "samael",
        "underconfidence": "samael",
        "domain_blind_spot": "satariel",
        "recency_bias": "gamaliel",
        "confirmation_bias": "thagirion",
        "anchoring": "ghagiel",
        "scope_creep": "gamchicoth",
        "premature_closure": "golachab",
    }
    return mapping.get(bias_type, "unknown")
