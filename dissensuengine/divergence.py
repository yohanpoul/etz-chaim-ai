"""Mesure de divergence — Gevurah de Tiferet.

Détecte les contradictions entre conclusions par analyse de contenu.
Combinaison : marqueurs de contradiction × similarité thématique.

Si deux conclusions parlent du MÊME sujet et se contredisent → haute divergence.
Si deux conclusions parlent de sujets DIFFÉRENTS → basse divergence (pas de conflit).
"""

from __future__ import annotations

import re

# Paires d'antonymes / marqueurs de contradiction
CONTRADICTION_PAIRS = [
    ("increase", "decrease"), ("augmente", "diminue"),
    ("true", "false"), ("vrai", "faux"),
    ("always", "never"), ("toujours", "jamais"),
    ("all", "none"), ("tous", "aucun"),
    ("better", "worse"), ("meilleur", "pire"),
    ("positive", "negative"), ("positif", "négatif"),
    ("success", "failure"), ("succès", "échec"),
    ("confirms", "refutes"), ("confirme", "réfute"),
    ("supports", "contradicts"), ("soutient", "contredit"),
    ("possible", "impossible"),
    ("necessary", "unnecessary"), ("nécessaire", "inutile"),
    ("sufficient", "insufficient"), ("suffisant", "insuffisant"),
    ("effective", "ineffective"), ("efficace", "inefficace"),
    ("significant", "insignificant"), ("significatif", "insignifiant"),
    ("present", "absent"),
    ("cause", "not a cause"),
    ("correlated", "uncorrelated"), ("corrélé", "non corrélé"),
    ("high", "low"), ("haut", "bas"),
    ("more", "less"), ("plus", "moins"),
    ("agree", "disagree"), ("accord", "désaccord"),
    ("convergent", "divergent"),
    ("compatible", "incompatible"),
]

# Marqueurs de négation
NEGATION_MARKERS = [
    "not", "no", "never", "neither", "nor", "n't", "cannot", "won't",
    "ne pas", "ne jamais", "aucun", "ni", "pas de", "sans",
    "unlikely", "improbable", "impossible",
]

# Mots vides à ignorer dans la similarité thématique
STOP_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "and", "but", "or", "nor", "for", "yet", "so", "in", "on", "at",
    "to", "of", "by", "with", "from", "as", "into", "through", "during",
    "before", "after", "above", "below", "between", "out", "off", "over",
    "under", "again", "further", "then", "once", "that", "this", "these",
    "those", "it", "its", "he", "she", "they", "them", "their", "we",
    "le", "la", "les", "un", "une", "des", "du", "de", "et", "ou",
    "est", "sont", "être", "avoir", "fait", "dans", "sur", "par",
    "pour", "avec", "qui", "que", "ce", "cette", "ces",
}


def _tokenize(text: str) -> set[str]:
    """Tokenisation simple — mots significatifs en minuscules."""
    # Split + filter instead of regex to avoid catastrophic backtracking
    # on long texts with Unicode characters
    result = set()
    for word in text.lower().split():
        # Strip non-alpha chars from edges
        w = word.strip(".,;:!?()[]{}\"'«»—–-_/\\@#$%^&*+=<>~`|")
        if len(w) >= 3 and w.isalpha() and w not in STOP_WORDS:
            result.add(w)
    return result


def compute_topic_similarity(text_a: str, text_b: str) -> float:
    """Similarité thématique par overlap de mots-clés (Jaccard).

    Retourne 0.0 (sujets différents) à 1.0 (même sujet).
    """
    tokens_a = _tokenize(text_a)
    tokens_b = _tokenize(text_b)

    if not tokens_a or not tokens_b:
        return 0.0

    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b

    return len(intersection) / len(union)


def _word_in_text(word: str, text: str) -> bool:
    """Check if word appears as a complete word."""
    if " " in word:
        return word in text
    # Fast path: check if the word is in the token set (pre-split)
    # Falls back to substring check for efficiency vs regex
    idx = text.find(word)
    if idx == -1:
        return False
    # Verify word boundaries without regex
    before_ok = (idx == 0 or not text[idx - 1].isalnum())
    end = idx + len(word)
    after_ok = (end == len(text) or not text[end].isalnum())
    return before_ok and after_ok


def compute_contradiction_score(text_a: str, text_b: str) -> float:
    """Score de contradiction entre deux textes.

    Détecte : paires d'antonymes, négations asymétriques.
    Retourne 0.0 (pas de contradiction) à 1.0 (contradiction forte).
    """
    lower_a = text_a.lower()
    lower_b = text_b.lower()
    signals = 0
    max_signals = 0

    # Check antonym pairs — only count when both sides exist across texts
    for word_pos, word_neg in CONTRADICTION_PAIRS:
        a_has_pos = _word_in_text(word_pos, lower_a)
        a_has_neg = _word_in_text(word_neg, lower_a)
        b_has_pos = _word_in_text(word_pos, lower_b)
        b_has_neg = _word_in_text(word_neg, lower_b)

        pos_found = a_has_pos or b_has_pos
        neg_found = a_has_neg or b_has_neg
        if pos_found and neg_found:
            max_signals += 1
            # A dit le positif, B dit le négatif (ou inverse)
            if (a_has_pos and b_has_neg) or (a_has_neg and b_has_pos):
                signals += 1

    # Check negation asymmetry
    neg_a = sum(1 for marker in NEGATION_MARKERS if _word_in_text(marker, lower_a))
    neg_b = sum(1 for marker in NEGATION_MARKERS if _word_in_text(marker, lower_b))
    negation_asymmetry = abs(neg_a - neg_b) / max(neg_a + neg_b, 1)

    if max_signals == 0:
        # No antonym pairs found — rely on negation asymmetry only
        return min(negation_asymmetry * 0.6, 1.0)

    antonym_score = signals / max_signals
    return min((antonym_score * 0.7 + negation_asymmetry * 0.3), 1.0)


def measure_divergence(text_a: str, text_b: str) -> float:
    """Score de divergence entre deux textes.

    Divergence = contradiction × similarité_thématique

    Deux textes sur des sujets DIFFÉRENTS ne sont pas en divergence.
    Deux textes sur le MÊME sujet qui se contredisent → haute divergence.

    Retourne 0.0 (accord ou sujets différents) à 1.0 (contradiction sur même sujet).
    """
    topic_sim = compute_topic_similarity(text_a, text_b)
    contradiction = compute_contradiction_score(text_a, text_b)

    # Pondération : la similarité thématique amplifie la contradiction
    # Base faible : sans overlap thématique, la contradiction ne prouve rien
    raw = contradiction * (0.25 + 0.75 * topic_sim)
    return min(raw, 1.0)


def classify_tension_type(
    divergence_score: float,
    topic_similarity: float,
    contradiction_score: float,
) -> str:
    """Classifier le type de tension basé sur les scores.

    - contradiction : haute divergence, haut topic overlap, haute contradiction
    - scope_conflict : haute topic similarity mais contradiction modérée
    - framing_difference : topic overlap moyen, contradiction modérée
    - nuance : basse divergence
    """
    if divergence_score >= 0.6 and contradiction_score >= 0.5:
        return "contradiction"
    if topic_similarity >= 0.4 and contradiction_score >= 0.3:
        return "scope_conflict"
    if topic_similarity >= 0.2 and contradiction_score >= 0.2:
        return "framing_difference"
    return "nuance"
