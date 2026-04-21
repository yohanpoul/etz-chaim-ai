"""MultiSephirothEvaluator — évaluation sur 5 axes au lieu d'une seule loss.

Gevurah : qualité brute (la métrique dure du domaine).
Chesed  : diversité / originalité.
Tiferet : cohérence avec l'ensemble.
Hod     : interprétabilité / clarté.
Yesod   : reproductibilité / fiabilité.

Anti-Golachab : si on rejette trop, c'est Gevurah qui est malade.
Anti-Thagirion : si la qualité monte MAIS la cohérence baisse.
"""

from __future__ import annotations

import re

from autojudge.models import DomainScore, MultiScore


def _word_set(text: str) -> set[str]:
    """Extract significant words as a set."""
    return {w for w in re.findall(r'\b[a-zA-ZÀ-ÿ]{3,}\b', text.lower())}


class MultiSephirothEvaluator:
    """Évaluation multi-sephirothique — 5 axes + décision harmonisée."""

    def __init__(
        self,
        quality_threshold: float = 0.6,
        quarantine_threshold: float = 0.4,
        tension_check_enabled: bool = True,
        golachab_rejection_ceiling: float = 0.9,
    ):
        self.quality_threshold = quality_threshold
        self.quarantine_threshold = quarantine_threshold
        self.tension_check_enabled = tension_check_enabled
        self.golachab_rejection_ceiling = golachab_rejection_ceiling

    def evaluate(
        self,
        domain_score: DomainScore,
        original: str,
        modified: str,
    ) -> MultiScore:
        """Compute multi-sephirothic score from domain score + content analysis."""
        gevurah = domain_score.quality
        chesed = self._diversity_score(original, modified)
        tiferet = self._consistency_score(original, modified)
        hod = self._interpretability_score(modified)
        yesod = self._reproducibility_score(domain_score)

        return MultiScore(
            gevurah=round(gevurah, 4),
            chesed=round(chesed, 4),
            tiferet=round(tiferet, 4),
            hod=round(hod, 4),
            yesod=round(yesod, 4),
        )

    def holistic_decision(
        self,
        scores: MultiScore,
        recent_rejection_rate: float = 0.0,
    ) -> str:
        """Décision harmonisée — pas juste 'loss a baissé'.

        Anti-Golachab : si rejection_rate > ceiling → quarantine.
        Anti-Thagirion : si qualité ↑ mais cohérence ↓ → tension.
        Sinon : accepted / quarantined / rejected selon seuils.
        """
        # Anti-Golachab : si on rejette trop, relaxer
        if recent_rejection_rate > self.golachab_rejection_ceiling:
            return "quarantined"

        # Anti-Thagirion : qualité haute mais cohérence basse → tension
        if self.tension_check_enabled:
            if scores.gevurah > 0.7 and scores.tiferet < 0.4:
                return "tension_detected"

        if scores.overall >= self.quality_threshold:
            return "accepted"
        elif scores.overall >= self.quarantine_threshold:
            return "quarantined"
        else:
            return "rejected"

    # --- Axes individuels ---

    def _diversity_score(self, original: str, modified: str) -> float:
        """Chesed : diversité / originalité de la modification.

        Mesure les nouveaux mots introduits par la modification.
        """
        orig_words = _word_set(original)
        mod_words = _word_set(modified)

        if not mod_words:
            return 0.0

        new_words = mod_words - orig_words
        if not orig_words:
            return 0.5

        # Ratio of new content
        novelty = len(new_words) / max(len(mod_words), 1)
        # Too much novelty = divergence, not diversity
        if novelty > 0.7:
            return 0.4
        return min(0.3 + novelty, 1.0)

    def _consistency_score(self, original: str, modified: str) -> float:
        """Tiferet : cohérence entre le modifié et l'original.

        Jaccard similarity of word sets — high = consistent, low = divergent.
        """
        orig_words = _word_set(original)
        mod_words = _word_set(modified)

        if not orig_words and not mod_words:
            return 1.0
        if not orig_words or not mod_words:
            return 0.0

        intersection = orig_words & mod_words
        union = orig_words | mod_words

        return len(intersection) / len(union)

    def _interpretability_score(self, text: str) -> float:
        """Hod : interprétabilité / clarté du texte modifié.

        Based on sentence structure and clarity markers.
        """
        if not text or not text.strip():
            return 0.0

        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        if not sentences:
            return 0.0

        words = re.findall(r'\b\w+\b', text)
        word_count = max(len(words), 1)
        sent_count = max(len(sentences), 1)

        avg_sent_len = word_count / sent_count

        # Optimal: 10-20 words per sentence
        if 10 <= avg_sent_len <= 20:
            length_score = 1.0
        elif avg_sent_len < 5 or avg_sent_len > 40:
            length_score = 0.3
        else:
            length_score = 0.6

        # Paragraph structure
        paragraphs = [p for p in text.split("\n\n") if p.strip()]
        has_structure = len(paragraphs) > 1
        structure_bonus = 0.1 if has_structure else 0.0

        return min(length_score + structure_bonus, 1.0)

    def _reproducibility_score(self, domain_score: DomainScore) -> float:
        """Yesod : reproductibilité — confiance dans le score du domaine.

        Higher quality scores with consistent metrics = more reproducible.
        """
        metrics = domain_score.metrics
        if not metrics:
            return 0.5

        values = [v for v in metrics.values() if isinstance(v, (int, float))]
        if not values:
            return 0.5

        # Low variance = reproducible
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)

        # Variance of 0 = perfect consistency → 1.0
        # Variance of 0.25 (max for 0-1 range) → 0.0
        consistency = max(0.0, 1.0 - variance * 4)

        return round(consistency, 4)
