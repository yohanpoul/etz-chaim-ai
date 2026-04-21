"""Compression — Stratégies d'Aviut distinctes pour le Masakh.

עֲבִיוּת — L'épaisseur du Masakh détermine COMMENT la Lumière est
transformée, pas seulement COMBIEN est rejetée. Chaque niveau d'Aviut
produit un résultat qualitativement différent :

  compression_forte   : extraction des phrases-clés (essence pure)
  compression_moderee : sélection de phrases scorées (structure préservée)
  resume              : tête + phrases-clés extraites du milieu

Les 2 autres modes (troncation, aucune) restent dans Masakh.toch()
car ils ne nécessitent pas de scoring.

Scoring TF basique — sans LLM, sans dépendance externe.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Ratio tête/extraction pour le mode resume (Bet/Yetzirah).
# Synchronisé avec la doc du module masakh — si modifié ici,
# mettre à jour le docstring de resume() ci-dessous.
RESUME_HEAD_RATIO = 0.60


# ── Sentence splitting ────────────────────────────────────

# Split on sentence boundaries: period, question mark, exclamation,
# or double newlines (paragraph breaks).
_SENT_RE = re.compile(r'(?<=[.!?])\s+|\n{2,}')


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences, preserving non-empty segments."""
    parts = _SENT_RE.split(text)
    return [s.strip() for s in parts if s.strip()]


# ── Word frequency scoring ────────────────────────────────

_STOPWORDS_FR = frozenset(
    "le la les un une des de du d l à au aux en et ou "
    "que qui quoi dont où est sont a ont été sera seront "
    "pour par sur dans avec sans pas ne plus aussi mais "
    "ce cette ces il elle ils elles je tu nous vous on "
    "son sa ses mon ma mes ton ta tes leur leurs se si "
    "car donc ni bien très tout comme même entre autre "
    "être avoir fait faire peut quand alors encore déjà".split()
)

_STOPWORDS_EN = frozenset(
    "the a an is are was were be been being have has had "
    "do does did will would shall should can could may might "
    "to of in for on with at by from as into through during "
    "and or but not no nor so yet both either neither each "
    "this that these those it its he she they we you I my "
    "his her their our your me him them us if then than when".split()
)

_STOPWORDS = _STOPWORDS_FR | _STOPWORDS_EN

_WORD_RE = re.compile(r'[a-zA-ZÀ-ÿ]{3,}')


def _word_freq(text: str) -> dict[str, float]:
    """Compute normalized word frequencies, excluding stopwords."""
    words = [w.lower() for w in _WORD_RE.findall(text)
             if w.lower() not in _STOPWORDS]
    if not words:
        return {}
    counts: dict[str, int] = {}
    for w in words:
        counts[w] = counts.get(w, 0) + 1
    max_count = max(counts.values())
    return {w: c / max_count for w, c in counts.items()}


# ── Sentence scoring ─────────────────────────────────────

@dataclass
class ScoredSentence:
    """A sentence with its computed relevance score."""
    text: str
    index: int       # position in original text
    score: float


def _score_sentences(
    sentences: list[str],
    freq: dict[str, float],
) -> list[ScoredSentence]:
    """Score each sentence by word frequency + position bias.

    Score = mean(word_freq for content words) + position_bonus.
    Position bonus: first 10% and last 10% of sentences get +0.2.
    Longer sentences get a slight bonus (more information).
    """
    n = len(sentences)
    scored: list[ScoredSentence] = []

    for i, sent in enumerate(sentences):
        words = [w.lower() for w in _WORD_RE.findall(sent)
                 if w.lower() not in _STOPWORDS]

        # Word frequency score
        if words and freq:
            word_score = sum(freq.get(w, 0.0) for w in words) / len(words)
        else:
            word_score = 0.0

        # Position bias: beginning and end of document
        pos_ratio = i / max(n - 1, 1)
        if pos_ratio < 0.1 or pos_ratio > 0.9:
            position_bonus = 0.2
        elif pos_ratio < 0.25 or pos_ratio > 0.75:
            position_bonus = 0.1
        else:
            position_bonus = 0.0

        # Length bonus: longer sentences carry more content (capped)
        length_bonus = min(len(words) / 30.0, 0.15)

        score = word_score + position_bonus + length_bonus
        scored.append(ScoredSentence(text=sent, index=i, score=score))

    return scored


# ── Strategies ─────────────────────────────────────────────

def compression_forte(text: str, budget_chars: int) -> str:
    """Compression forte — extraction de phrases-clés uniquement.

    Dalet / Atziluth : le Masakh le plus épais. Ne laisse passer
    que l'essence. Les phrases sont triées par score décroissant
    et accumulées jusqu'au budget. L'ordre original est restauré.

    Produit un résultat radicalement différent de head+tail :
    les phrases viennent de PARTOUT dans le texte, seules les
    plus denses en information survivent.
    """
    sentences = _split_sentences(text)

    # Fallback: no sentence boundaries → truncate
    if len(sentences) <= 1:
        return text[:budget_chars]

    freq = _word_freq(text)
    scored = _score_sentences(sentences, freq)

    # Sort by score descending — pick the most informative
    by_score = sorted(scored, key=lambda s: s.score, reverse=True)

    selected_indices: set[int] = set()
    total_chars = 0

    for s in by_score:
        s_len = len(s.text) + 2  # +2 for ". " join
        if total_chars + s_len > budget_chars:
            if not selected_indices:
                # First sentence too large: truncate it
                selected_indices.add(s.index)
            break
        selected_indices.add(s.index)
        total_chars += s_len

    # Restore original order for readability
    selected = [s for s in scored if s.index in selected_indices]
    selected.sort(key=lambda s: s.index)

    result = ". ".join(s.text for s in selected)
    return result[:budget_chars]


def compression_moderee(text: str, budget_chars: int) -> str:
    """Compression modérée — sélection scorée avec structure.

    Gimel / Briah : le Masakh modéré. Préserve la structure du
    texte en gardant le début, la fin, et les phrases les plus
    scorées du milieu. Différent de compression_forte car :
    - Début et fin sont TOUJOURS inclus (ancrage contextuel)
    - Les phrases du milieu sont filtrées par score
    - Le résultat reste cohérent narrativement

    Différent de head+tail car les phrases du milieu sont
    sélectionnées par pertinence, pas ignorées.
    """
    sentences = _split_sentences(text)

    # Fallback: no sentence boundaries → truncate
    if len(sentences) <= 1:
        return text[:budget_chars]

    freq = _word_freq(text)
    scored = _score_sentences(sentences, freq)
    n = len(scored)

    if n <= 3:
        result = ". ".join(s.text for s in scored)
        return result[:budget_chars]

    # Always include first and last sentence (context anchors)
    first = scored[0]
    last = scored[-1]
    anchor_chars = len(first.text) + len(last.text) + 20  # separators

    # Middle sentences: score and select
    middle = scored[1:-1]
    middle_sorted = sorted(middle, key=lambda s: s.score, reverse=True)

    remaining_budget = budget_chars - anchor_chars
    selected_middle: list[ScoredSentence] = []

    for s in middle_sorted:
        s_len = len(s.text) + 2
        if remaining_budget < s_len:
            continue
        selected_middle.append(s)
        remaining_budget -= s_len

    # Restore original order
    selected_middle.sort(key=lambda s: s.index)

    parts = [first.text]
    for s in selected_middle:
        parts.append(s.text)
    parts.append(last.text)

    result = ". ".join(parts)
    return result[:budget_chars]


def resume(text: str, budget_chars: int) -> str:
    """Résumé — tête intacte + phrases-clés extraites du reste.

    Bet / Yetzirah : le Masakh léger. Priorité absolue au début
    du texte (60% du budget), le reste est rempli par les phrases
    les plus informatives du milieu et de la fin.

    Différent de head+tail car :
    - La partie "tail" n'est pas les derniers caractères mais
      les phrases les plus pertinentes du reste du texte
    - Le contenu important du milieu n'est pas perdu
    """
    head_budget = int(budget_chars * RESUME_HEAD_RATIO)
    separator = "\n[...]\n"
    extract_budget = budget_chars - head_budget - len(separator)

    # Head: preserve intact
    head = text[:head_budget]

    # Remaining text: extract key phrases
    remaining_text = text[head_budget:]
    if not remaining_text.strip() or extract_budget < 20:
        return head

    sentences = _split_sentences(remaining_text)
    if not sentences:
        return head

    freq = _word_freq(remaining_text)
    scored = _score_sentences(sentences, freq)
    by_score = sorted(scored, key=lambda s: s.score, reverse=True)

    selected: list[ScoredSentence] = []
    total_chars = 0

    for s in by_score:
        s_len = len(s.text) + 2
        if total_chars + s_len > extract_budget:
            continue
        selected.append(s)
        total_chars += s_len

    if not selected:
        return head

    # Restore original order
    selected.sort(key=lambda s: s.index)
    extracted = ". ".join(s.text for s in selected)

    return head + separator + extracted
