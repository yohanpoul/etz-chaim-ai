"""Kashiut — Filtrage par pertinence du Masakh.

קָשִׁיוּת — La dureté du Masakh, sa capacité de REJET.

Le Masakh a une double propriété (EC-SHK-020, EC-SHK-085) :
  Kashiut = rejet par PERTINENCE (ce qui n'est pas pertinent ne passe pas)
  Aviut   = transformation par COMPRESSION (ce qui passe est transformé)

Kashiut opère AVANT Aviut. Un bloc non pertinent est rejeté
entièrement — pas compressé, pas tronqué. Éliminé.

Scoring rapide sans LLM : overlap de mots-clés avec matching
morphologique basique (préfixe 5 chars). Réutilise les stopwords
et le regex de masakh.compression.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from masakh.compression import _STOPWORDS, _WORD_RE

# Synchronisé avec masakh.CHARS_PER_TOKEN — défini ici pour éviter
# l'import circulaire masakh.kashiut → masakh.__init__.
CHARS_PER_TOKEN = 4


# ── Block splitting ───────────────────────────────────────

_BLOCK_SEP = re.compile(r'\n{2,}')

# Blocs plus courts que ce seuil passent toujours (marqueurs, séparateurs)
_MIN_BLOCK_CHARS = 20

# Longueur minimale de préfixe pour le matching morphologique
_STEM_PREFIX_LEN = 5

# Blocs pipeline-injectés : directives, pas du contexte filtrable.
# Le Kashiut filtre le contenu informationnel, pas les instructions
# du pipeline (Kavvanah = intention, Tzelem = archétype, Da'at bridge, etc.).
# Regex : bloc commençant par "[" + lettres majuscules/apostrophes = tag pipeline.
_PROTECTED_TAG_RE = re.compile(r'^\[[A-ZÀ-Ÿ\'/]')


@dataclass
class ScoredBlock:
    """Un bloc de texte avec son score de pertinence."""
    text: str
    index: int
    score: float


def split_blocks(prompt: str) -> list[str]:
    """Découpe un prompt en blocs (séparés par double newline).

    Préserve l'ordre. Filtre les blocs vides.
    """
    parts = _BLOCK_SEP.split(prompt)
    return [p for p in parts if p.strip()]


def extract_keywords(text: str) -> set[str]:
    """Extraire les mots-clés (non-stopwords, 3+ caractères, lowercase)."""
    return {
        w.lower()
        for w in _WORD_RE.findall(text)
        if w.lower() not in _STOPWORDS
    }


def _compute_pertinence(
    block_keywords: set[str],
    query_keywords: set[str],
) -> float:
    """Score de pertinence d'un ensemble de mots-clés bloc vs query.

    Pour chaque mot-clé de la query :
      - Match exact = 1.0 crédit
      - Match par préfixe (5+ chars) = 0.7 crédit
        (gère « analyse/analyser », « compress/compression », etc.)

    Returns:
        Score normalisé dans [0.0, 1.0].
    """
    if not query_keywords:
        return 1.0

    score = 0.0
    for qw in query_keywords:
        if qw in block_keywords:
            score += 1.0
        elif len(qw) >= _STEM_PREFIX_LEN:
            prefix = qw[:_STEM_PREFIX_LEN]
            if any(bw.startswith(prefix) for bw in block_keywords):
                score += 0.7

    return min(1.0, score / len(query_keywords))


def score_block(block: str, query_keywords: set[str]) -> float:
    """Score de pertinence d'un bloc par rapport à la query.

    Retourne toujours 1.0 pour :
      - Blocs très courts (< 20 chars) : marqueurs, séparateurs
      - Blocs pipeline-injectés : KAVVANAH, TZELEM, HITLABSHUT, DA'AT
        (directives du pipeline, pas du contexte filtrable)

    Args:
        block: Texte du bloc
        query_keywords: Mots-clés extraits de la query

    Returns:
        Score dans [0.0, 1.0].
    """
    if not query_keywords:
        return 1.0

    stripped = block.strip()

    if len(stripped) < _MIN_BLOCK_CHARS:
        return 1.0

    # Blocs pipeline-injectés (tags [KAVVANAH], [TZELEM], [DA'AT], etc.)
    # Ce sont des directives du pipeline, pas du contexte filtrable.
    if _PROTECTED_TAG_RE.match(stripped):
        return 1.0

    block_keywords = extract_keywords(block)
    if not block_keywords:
        return 0.0

    return _compute_pertinence(block_keywords, query_keywords)


def score_blocks(
    blocks: list[str],
    query_keywords: set[str],
) -> list[ScoredBlock]:
    """Scorer tous les blocs d'un prompt.

    Args:
        blocks: Liste de blocs (sortie de split_blocks)
        query_keywords: Mots-clés de la query

    Returns:
        Liste de ScoredBlock avec index et score.
    """
    return [
        ScoredBlock(text=block, index=i, score=score_block(block, query_keywords))
        for i, block in enumerate(blocks)
    ]


def filter_by_kashiut(
    prompt: str,
    query: str,
    threshold: float,
) -> tuple[str, list[dict]]:
    """Filtrer les blocs du prompt par pertinence vs la query.

    EC-SHK-020 : le Kashiut rejette ce qui n'est pas pertinent.
    EC-SHK-085 : le seuil dépend du niveau (Dalet=0.8, Shoresh=0.0).

    Args:
        prompt: Le prompt complet à filtrer
        query: La question/requête de l'utilisateur
        threshold: Seuil de kashiut (0.0 = tout passe, 0.8 = strict)

    Returns:
        (prompt_filtré, liste_des_blocs_rejetés)
        Si threshold <= 0.0 ou si la query n'a pas de mots-clés,
        retourne le prompt original sans rejet.
    """
    if threshold <= 0.0:
        return prompt, []

    blocks = split_blocks(prompt)
    if len(blocks) <= 1:
        # Un seul bloc : rien à filtrer (on ne rejette pas tout)
        return prompt, []

    query_keywords = extract_keywords(query)
    if len(query_keywords) < 2:
        # Pas assez de signal dans la query pour scorer la pertinence.
        # Une query d'un seul mot-clé produit du scoring trop binaire.
        return prompt, []

    scored = score_blocks(blocks, query_keywords)

    kept: list[str] = []
    rejected: list[dict] = []

    for sb in scored:
        if sb.score >= threshold:
            kept.append(sb.text)
        else:
            rejected.append({
                "block_index": sb.index,
                "score": round(sb.score, 3),
                "threshold": threshold,
                "chars": len(sb.text),
                "tokens_est": max(1, len(sb.text) // CHARS_PER_TOKEN),
                "preview": sb.text[:80].replace('\n', ' '),
            })

    if not kept:
        # Sécurité : ne jamais retourner un prompt vide.
        # Si tout est rejeté, garder le bloc le mieux scoré.
        best = max(scored, key=lambda s: s.score)
        kept.append(best.text)
        rejected = [r for r in rejected if r["block_index"] != best.index]

    return "\n\n".join(kept), rejected
