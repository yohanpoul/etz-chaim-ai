"""WritingJudge — AutoResearch pour l'écriture.

La 'loss function' de l'écriture : clarté, diversité, structure, concision.
Évaluation heuristique — pas de LLM, métriques computables.
"""

from __future__ import annotations

import re
from collections import Counter

from autojudge.domains.base import DomainJudge
from autojudge.models import DomainScore

# Mots de remplissage (EN + FR)
FILLER_WORDS = {
    "very", "really", "basically", "actually", "just", "quite",
    "simply", "literally", "totally", "completely", "absolutely",
    "obviously", "clearly", "essentially", "virtually", "practically",
    "vraiment", "simplement", "absolument", "totalement", "évidemment",
    "clairement", "essentiellement", "pratiquement", "fondamentalement",
}

# Connecteurs structurants (signe de bonne structure)
STRUCTURE_MARKERS = {
    "however", "therefore", "moreover", "furthermore", "consequently",
    "nevertheless", "although", "whereas", "specifically", "notably",
    "cependant", "donc", "néanmoins", "toutefois", "par conséquent",
    "en outre", "de plus", "notamment", "en revanche", "ainsi",
    "premièrement", "deuxièmement", "enfin", "d'abord", "ensuite",
    "firstly", "secondly", "finally", "first", "second", "third",
}


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s for s in sentences if s.strip()]


def _get_words(text: str) -> list[str]:
    """Extract words from text."""
    return re.findall(r'\b[a-zA-ZÀ-ÿ]+\b', text.lower())


class WritingJudge(DomainJudge):
    """AutoResearch pour l'écriture — évaluation heuristique de qualité textuelle."""

    def compute_metrics(self, text: str) -> dict[str, float]:
        """Compute all text quality metrics. Returns dict with values 0-1."""
        if not text or not text.strip():
            return {
                "readability": 0.0, "diversity": 0.0,
                "structure": 0.0, "concision": 0.0, "precision": 0.0,
            }

        words = _get_words(text)
        sentences = _split_sentences(text)
        word_count = len(words)
        sentence_count = max(len(sentences), 1)

        # Readability: penalize very long and very short sentences
        avg_len = word_count / sentence_count
        # Optimal range: 10-20 words per sentence
        if avg_len < 5:
            readability = 0.3
        elif avg_len <= 20:
            readability = 0.6 + 0.4 * (1 - abs(avg_len - 15) / 15)
        elif avg_len <= 30:
            readability = 0.6 - (avg_len - 20) * 0.03
        else:
            readability = max(0.1, 0.3 - (avg_len - 30) * 0.01)

        # Diversity: type-token ratio (unique words / total words)
        if word_count == 0:
            diversity = 0.0
        else:
            unique = len(set(words))
            ttr = unique / word_count
            # TTR naturally decreases with length, normalize
            # For short texts (<50 words), TTR is naturally high
            if word_count < 50:
                diversity = min(ttr, 1.0)
            else:
                # Adjusted: TTR of 0.4+ for long texts is excellent
                diversity = min(ttr * 1.5, 1.0)

        # Structure: paragraph breaks, connectors, section markers
        paragraph_count = len([p for p in text.split("\n\n") if p.strip()])
        connector_count = sum(
            1 for w in words if w in STRUCTURE_MARKERS
        )
        # Score based on connectors per 100 words + paragraph structure
        connector_density = connector_count / max(word_count / 100, 1)
        para_score = min(paragraph_count / max(word_count / 100, 1), 1.0)
        structure = min((connector_density * 0.3 + para_score * 0.3 + 0.4), 1.0)

        # Concision: penalize filler words
        filler_count = sum(1 for w in words if w in FILLER_WORDS)
        filler_ratio = filler_count / max(word_count, 1)
        concision = max(0.0, 1.0 - filler_ratio * 5)

        # Precision: specificity of language (numbers, proper nouns, technical terms)
        numbers = len(re.findall(r'\b\d+\.?\d*\b', text))
        # Words > 8 chars as proxy for technical terms
        technical = sum(1 for w in words if len(w) > 8)
        precision_density = (numbers + technical) / max(word_count, 1)
        precision = min(precision_density * 3, 1.0)

        return {
            "readability": round(max(0, min(readability, 1)), 4),
            "diversity": round(max(0, min(diversity, 1)), 4),
            "structure": round(max(0, min(structure, 1)), 4),
            "concision": round(max(0, min(concision, 1)), 4),
            "precision": round(max(0, min(precision, 1)), 4),
        }

    def generate_hypothesis(self, current_state: str) -> str:
        """Analyze text metrics, find weakest dimension, suggest improvement."""
        metrics = self.compute_metrics(current_state)
        weaknesses: list[tuple[float, str, str]] = []

        if metrics["readability"] < 0.6:
            weaknesses.append(
                (metrics["readability"], "readability",
                 "Simplifier les phrases longues pour améliorer la lisibilité")
            )
        if metrics["diversity"] < 0.5:
            weaknesses.append(
                (metrics["diversity"], "diversity",
                 "Enrichir le vocabulaire pour éviter les répétitions")
            )
        if metrics["concision"] < 0.7:
            weaknesses.append(
                (metrics["concision"], "concision",
                 "Supprimer les mots de remplissage pour gagner en concision")
            )
        if metrics["structure"] < 0.5:
            weaknesses.append(
                (metrics["structure"], "structure",
                 "Ajouter de la structure avec des paragraphes et connecteurs")
            )
        if metrics["precision"] < 0.4:
            weaknesses.append(
                (metrics["precision"], "precision",
                 "Ajouter des détails spécifiques et des données précises")
            )

        if not weaknesses:
            return "Améliorer la qualité générale du texte"

        weaknesses.sort(key=lambda x: x[0])
        return weaknesses[0][2]

    def apply_modification(self, content: str, hypothesis: str) -> str:
        """Apply text transformations based on hypothesis."""
        hyp_lower = hypothesis.lower()

        if "remplissage" in hyp_lower or "concision" in hyp_lower:
            return self._remove_fillers(content)

        if "phrases" in hyp_lower or "lisibilité" in hyp_lower or "simplifier" in hyp_lower:
            return self._split_long_sentences(content)

        if "structure" in hyp_lower or "paragraphe" in hyp_lower or "connecteur" in hyp_lower:
            return self._add_structure(content)

        if "vocabulaire" in hyp_lower or "répétition" in hyp_lower:
            return self._reduce_repetitions(content)

        # Default: remove fillers as safe transformation
        return self._remove_fillers(content)

    def evaluate(self, original: str, modified: str) -> DomainScore:
        """Compare original and modified text quality."""
        orig_m = self.compute_metrics(original)
        mod_m = self.compute_metrics(modified)

        # Weighted quality score: how much did the modification improve things?
        weights = {
            "readability": 0.30,
            "diversity": 0.20,
            "structure": 0.20,
            "concision": 0.15,
            "precision": 0.15,
        }

        quality = 0.0
        for key, weight in weights.items():
            orig_val = orig_m.get(key, 0.5)
            mod_val = mod_m.get(key, 0.5)
            # Score component: improvement ratio mapped to 0-1
            # 0.5 = no change, >0.5 = improvement, <0.5 = regression
            if orig_val == 0:
                component = 0.7 if mod_val > 0 else 0.5
            else:
                ratio = mod_val / orig_val
                component = min(max(ratio / 2, 0), 1)
            quality += component * weight

        # Normalize: quality is the weighted sum
        quality = min(max(quality, 0), 1)

        explanation_parts = []
        for key in weights:
            diff = mod_m[key] - orig_m[key]
            if abs(diff) > 0.05:
                direction = "↑" if diff > 0 else "↓"
                explanation_parts.append(f"{key} {direction}{abs(diff):.2f}")

        return DomainScore(
            quality=round(quality, 4),
            metrics=mod_m,
            explanation=", ".join(explanation_parts) if explanation_parts else "no change",
        )

    def get_loss_description(self) -> str:
        return (
            "Text quality: weighted combination of readability (0.30), "
            "diversity (0.20), structure (0.20), concision (0.15), "
            "precision (0.15). Higher is better."
        )

    # --- Transformations internes ---

    def _remove_fillers(self, text: str) -> str:
        """Remove filler words while preserving sentence structure."""
        def replace_filler(match):
            word = match.group(0)
            if word.lower() in FILLER_WORDS:
                return ""
            return word

        result = re.sub(
            r'\b(' + '|'.join(re.escape(w) for w in FILLER_WORDS) + r')\b\s*',
            "",
            text,
            flags=re.IGNORECASE,
        )
        # Clean up double spaces
        result = re.sub(r'  +', ' ', result)
        return result.strip()

    def _split_long_sentences(self, text: str) -> str:
        """Split sentences longer than 25 words at natural break points."""
        sentences = _split_sentences(text)
        result = []

        for sent in sentences:
            words = sent.split()
            if len(words) > 25:
                # Find a comma or semicolon near the middle
                mid = len(words) // 2
                best_split = None
                for offset in range(8):
                    for pos in [mid + offset, mid - offset]:
                        if 0 <= pos < len(words) and re.search(r'[,;:]', words[pos]):
                            best_split = pos
                            break
                    if best_split is not None:
                        break

                if best_split is not None:
                    first = " ".join(words[:best_split + 1]).rstrip(",;:") + "."
                    second = " ".join(words[best_split + 1:])
                    if second:
                        second = second[0].upper() + second[1:] if len(second) > 1 else second.upper()
                    result.append(first)
                    if second.strip():
                        result.append(second)
                else:
                    result.append(sent)
            else:
                result.append(sent)

        return " ".join(result)

    def _add_structure(self, text: str) -> str:
        """Add paragraph breaks and connectors."""
        sentences = _split_sentences(text)
        if len(sentences) <= 3:
            return text

        # Add paragraph break at natural points
        mid = len(sentences) // 2
        first_half = " ".join(sentences[:mid])
        second_half = " ".join(sentences[mid:])

        # Add a connector at the start of the second paragraph
        connectors = ["De plus, ", "En outre, ", "Par ailleurs, "]
        first_word = second_half.split()[0] if second_half.split() else ""
        if first_word.lower() not in {c.strip().rstrip(",").lower() for c in connectors}:
            second_half = connectors[0] + second_half[0].lower() + second_half[1:]

        return first_half + "\n\n" + second_half

    def _reduce_repetitions(self, text: str) -> str:
        """Reduce word repetitions by removing redundant occurrences."""
        words = text.split()
        if len(words) < 10:
            return text

        # Find most repeated content words (>3 chars, not filler, not stop)
        content_words = [w.lower().strip(".,;:!?") for w in words if len(w) > 3]
        counts = Counter(content_words)
        over_repeated = {w for w, c in counts.items() if c > 3}

        if not over_repeated:
            return text

        # Remove second+ occurrences of heavily repeated words
        seen_counts: dict[str, int] = {}
        result = []
        for word in words:
            clean = word.lower().strip(".,;:!?")
            if clean in over_repeated:
                seen_counts[clean] = seen_counts.get(clean, 0) + 1
                if seen_counts[clean] <= 2:
                    result.append(word)
                # Skip 3rd+ occurrence
            else:
                result.append(word)

        return " ".join(result)
