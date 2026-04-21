"""Tests du fix punctuation-aware Jaccard dans NoveltyAssessor._matches_any.

Sprint megaclean T4 — Dette 9 (résiduelle Sprint 5.2).

Dette :
    DB etz_chaim montrait 516/634 candidat_insights (81%) avec
    novelty_score=0.0. avg_novelty stored = 0.173 (proche 0.154 cité
    Sprint 5.2). Pattern bimodal : 516 zéros + 118 candidats ≥ 0.85,
    gap vide entre les deux.

Cause racine :
    `_matches_any` utilisait `set(text.lower().split())` pour extraire
    les mots. `.split()` ne strip pas la ponctuation, donc :
      - "structures." restait attaché → ≠ "structures"
      - "?" et "." devenaient des tokens
      - Les stop words (qui sont des mots propres) n'étaient pas appliqués
        aux tokens ponctués ("que," ≠ "que" dans _STOP_WORDS)

    Conséquence : les descriptions template-générées par ExplorationEngine
    ("Both hitbonenut and {X} exhibit cycle structures. The cycle in
    hitbonenut may be...") matchaient >82% Jaccard entre elles (malgré
    X différent), flaguant les candidats comme `already_known` et
    retournant novelty_score=0.0.

Fix :
    Remplacement `.split()` par regex `\\b[a-zA-ZÀ-ÿ]{3,}\\b` qui :
    - extrait uniquement des mots alphabétiques propres
    - strip la ponctuation
    - filtre les tokens < 3 char
    - préserve les accents français (À-ÿ)
    Aligne la logique sur `explorationengine/novelty_scorer.py`.

Impact runtime attendu post-kickstart :
    - Nouveaux candidats : less de faux positifs `already_known`
    - avg_novelty devrait remonter sur les nouvelles sessions
    - 516 zéros historiques restent en DB (pas de rewrite data).
"""

from __future__ import annotations

import pytest

from insightforge.models import CandidateInsight
from insightforge.novelty_assessor import NoveltyAssessor


def _make_candidate(description: str, confidence: float = 0.6) -> CandidateInsight:
    return CandidateInsight(
        description=description,
        source_module="test",
        domain="test",
        confidence=confidence,
        connects_domains=["a", "b"],
    )


class TestPunctuationStripping:
    """Les mots ponctués doivent être extraits proprement."""

    def test_punctuation_stripped_from_content_words(self):
        """Core du fix T4 : `.split()` attachait la ponctuation
        ("structures." ≠ "structures" → stop words inopérants).
        Avec regex `\\b[a-zA-ZÀ-ÿ]{3,}\\b`, tokens propres.
        """
        existing = ["The system has cycle structures."]  # avec point
        candidate = _make_candidate("The system has cycle structures")  # sans point

        assessor = NoveltyAssessor(
            similarity_threshold=0.5,
            existing_knowledge=existing,
        )
        # Après fix : "structures." → "structures", match sur content identique
        assert assessor._matches_any(candidate.description, existing), (
            "Avec le fix regex, 'structures.' et 'structures' sont le "
            "même mot — doit matcher sur contenu identique."
        )

    def test_split_would_have_kept_punctuation_distinct(self):
        """Démonstration : `.split()` naïf aurait gardé la ponctuation
        attachée, rendant les deux descriptions non-matching malgré
        contenu sémantique identique.
        """
        # Avec .split() : "structures." et "structures" sont des tokens
        # distincts → Jaccard baisse artificiellement.
        old_words_a = set("The system has cycle structures.".lower().split())
        old_words_b = set("The system has cycle structures".lower().split())
        # Intersection ne contient pas "structures." (ponctué)
        assert "structures." in old_words_a
        assert "structures" in old_words_b
        assert old_words_a != old_words_b

        # Avec regex (fix) : les deux sets sont identiques
        import re
        word_re = re.compile(r"\b[a-zA-ZÀ-ÿ]{3,}\b")
        new_words_a = set(word_re.findall("The system has cycle structures.".lower()))
        new_words_b = set(word_re.findall("The system has cycle structures".lower()))
        assert new_words_a == new_words_b, (
            "Regex fix : les deux descriptions donnent le même set content."
        )

    def test_short_tokens_filtered(self):
        """Regex `{3,}` filtre les mots < 3 char (a, à, le, de, ...).
        Ces tokens ne doivent pas polluer la similarité.
        """
        assessor = NoveltyAssessor()
        # "a b c" — aucun mot 3+ char
        words = assessor._matches_any.__func__(
            assessor, "a b c", ["d e f"],
        )
        # Le corpus n'a pas non plus de mots 3+ char → pas de match
        assert not words, "Mots < 3 char ne doivent pas déclencher match."

    def test_accented_french_words_preserved(self):
        """Regex [a-zA-ZÀ-ÿ]{3,} doit préserver les accents FR."""
        existing = ["La séphirah de la sagesse"]
        candidate = _make_candidate("La séphirah de la sagesse")

        assessor = NoveltyAssessor(
            similarity_threshold=0.5,
            existing_knowledge=existing,
        )
        assert assessor._matches_any(candidate.description, existing), (
            "Les mots accentués doivent être extraits correctement."
        )

    def test_empty_corpus_no_match(self):
        assessor = NoveltyAssessor()
        assert not assessor._matches_any("any text here", [])

    def test_empty_text_no_match(self):
        assessor = NoveltyAssessor()
        # Texte sans mots 3+ char → text_words vide → False
        assert not assessor._matches_any(" . , !", ["any non-empty corpus"])


class TestNoveltyBugScope:
    """Tests documentant la portée du fix T4 et les dettes résiduelles.

    Le fix punctuation adresse UNE cause du 81% zero-novelty (ponctuation
    attachée). D'autres causes subsistent :
    - _STOP_WORDS inclut des noms de domaines ("hitbonenut", "kabbale",
      "sephirah", ...) — descriptions template se réduisent à peu de mots
      content. → Sprint dédié pour redesign stop_words.
    - similarity_threshold=0.82 aggressive sur template court.
    - template ExplorationEngine trop répétitif en amont.
    """

    def test_identical_descriptions_still_detected_as_duplicates(self):
        """Non-régression : le fix ne casse PAS la détection des vrais
        duplicates (textes strictement identiques).
        """
        candidates = [
            _make_candidate("Le système présente une structure cyclique."),
            _make_candidate("Le système présente une structure cyclique."),
        ]
        assessor = NoveltyAssessor(similarity_threshold=0.82)
        results = assessor.assess_batch(candidates)

        assert results[1].novelty_score == 0.0
        assert results[1].is_reformulation

    def test_distinct_content_words_improve_novelty(self):
        """Deux descriptions distinctes par leurs mots CONTENT (pas
        seulement par la ponctuation ni par des domaines stop-word)
        reçoivent bien des scores > 0 et distincts.
        """
        existing = [
            "The ocean is deep and contains many fish species worldwide."
        ]
        candidate = _make_candidate(
            "Mathematics develops elegant proofs through logical rigor."
        )
        assessor = NoveltyAssessor(
            similarity_threshold=0.82,
            existing_knowledge=existing,
        )
        result = assessor.assess(candidate)
        assert not result.already_known, (
            "Deux descriptions sur des sujets distincts ne doivent pas "
            "matcher avec threshold=0.82."
        )
        assert result.novelty_score > 0

    def test_punctuation_only_difference_matches(self):
        """Deux descriptions qui ne diffèrent QUE par la ponctuation
        matchent bien après le fix (avant : ne matchaient pas).
        """
        existing = ["Discover a new pattern in cosmic rays."]
        candidate = _make_candidate("Discover a new pattern in cosmic rays")

        assessor = NoveltyAssessor(
            similarity_threshold=0.82,
            existing_knowledge=existing,
        )
        # Content après regex : identique (pas de mot ≥ 3 char en différence)
        assert assessor._matches_any(candidate.description, existing)
