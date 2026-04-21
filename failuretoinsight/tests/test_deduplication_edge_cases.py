"""Tests FTI dedup edge cases normalisés.

Sprint megaclean T5 — Dette 10 (résiduelle Sprint 8b).

Sprint 8b avait introduit la dédup exact-match `content = %s`. Edge cases
laissés ouverts :
    - Whitespace (trailing, multiples internes)
    - Casse (majuscules/minuscules)
    - Ponctuation terminale ("stratégie" vs "stratégie.")

Fix T5 :
    _normalize_content_for_dedup() applique : strip + collapse whitespace
    + strip trailing punct + lowercase. `recent_insight_exists` charge
    la fenêtre 24h et compare normalisé en Python (pas d'index DB).

Non couvert T5 :
    - Duplicates sémantiques (paraphrase, reformulation) — nécessite
      embeddings. Sprint séparé.
"""

from __future__ import annotations

import pytest

from failuretoinsight.db import _normalize_content_for_dedup


class TestNormalizeContentForDedup:
    """Tests du helper de normalisation."""

    def test_strips_leading_trailing_whitespace(self):
        assert _normalize_content_for_dedup("  hello  ") == "hello"

    def test_collapses_internal_whitespace(self):
        assert _normalize_content_for_dedup("hello  world") == "hello world"
        assert _normalize_content_for_dedup("hello\tworld") == "hello world"
        assert _normalize_content_for_dedup("hello\n\nworld") == "hello world"

    def test_strips_trailing_punctuation(self):
        assert _normalize_content_for_dedup("hello.") == "hello"
        assert _normalize_content_for_dedup("hello!") == "hello"
        assert _normalize_content_for_dedup("hello?") == "hello"
        assert _normalize_content_for_dedup("hello...") == "hello"
        assert _normalize_content_for_dedup("hello —") == "hello"

    def test_lowercases(self):
        assert _normalize_content_for_dedup("Hello World") == "hello world"
        assert _normalize_content_for_dedup("BOUCLE DE RETRY") == "boucle de retry"

    def test_combined_normalization(self):
        """Tous les transforms appliqués ensemble."""
        result = _normalize_content_for_dedup(
            "  Boucle de retry DÉTECTÉE  —  adapter la stratégie.  "
        )
        assert result == "boucle de retry détectée — adapter la stratégie"
        # Note : le "—" interne est préservé (seulement trailing strippé)

    def test_preserves_internal_punctuation(self):
        """La ponctuation INTERNE (entre mots) est préservée."""
        assert _normalize_content_for_dedup("hello, world.") == "hello, world"

    def test_preserves_accents(self):
        """Les accents FR ne doivent pas être perdus."""
        assert _normalize_content_for_dedup("détectée") == "détectée"

    def test_empty_string(self):
        assert _normalize_content_for_dedup("") == ""
        assert _normalize_content_for_dedup("   ") == ""

    def test_only_punctuation(self):
        assert _normalize_content_for_dedup("...") == ""


class TestRecentInsightExistsEdgeCases:
    """Tests d'intégration : la dédup glissante 24h attrape les edge
    cases via la normalisation."""

    def test_trailing_whitespace_variants_match(self, fti_bare):
        analysis1 = fti_bare.analyze_failure(
            description="First failure", domain="test",
        )
        fti_bare.extract_nitzotzot(
            analysis1.id,
            insights_data=[{
                "content": "Boucle de retry détectée",
                "insight_type": "warning",
                "confidence": 0.6,
            }],
        )
        analysis2 = fti_bare.analyze_failure(
            description="Second failure", domain="test",
        )
        inserted = fti_bare.extract_nitzotzot(
            analysis2.id,
            insights_data=[{
                "content": "Boucle de retry détectée  ",  # trailing spaces
                "insight_type": "warning",
                "confidence": 0.6,
            }],
        )
        assert inserted == [], (
            "Variations whitespace doivent matcher comme duplicate."
        )

    def test_trailing_punctuation_variants_match(self, fti_bare):
        analysis1 = fti_bare.analyze_failure(
            description="First", domain="test",
        )
        fti_bare.extract_nitzotzot(
            analysis1.id,
            insights_data=[{
                "content": "Stratégie adaptative nécessaire",
                "insight_type": "constraint",
                "confidence": 0.7,
            }],
        )
        analysis2 = fti_bare.analyze_failure(
            description="Second", domain="test",
        )
        inserted = fti_bare.extract_nitzotzot(
            analysis2.id,
            insights_data=[{
                "content": "Stratégie adaptative nécessaire.",  # point
                "insight_type": "constraint",
                "confidence": 0.7,
            }],
        )
        assert inserted == [], (
            "Variations ponctuation terminale doivent matcher."
        )

    def test_case_variants_match(self, fti_bare):
        analysis1 = fti_bare.analyze_failure(
            description="First", domain="test",
        )
        fti_bare.extract_nitzotzot(
            analysis1.id,
            insights_data=[{
                "content": "Pattern duplicate observed",
                "insight_type": "pattern",
                "confidence": 0.7,
            }],
        )
        analysis2 = fti_bare.analyze_failure(
            description="Second", domain="test",
        )
        inserted = fti_bare.extract_nitzotzot(
            analysis2.id,
            insights_data=[{
                "content": "PATTERN DUPLICATE OBSERVED",  # casse
                "insight_type": "pattern",
                "confidence": 0.7,
            }],
        )
        assert inserted == [], (
            "Variations de casse doivent matcher comme duplicate."
        )

    def test_internal_whitespace_collapsed_matches(self, fti_bare):
        analysis1 = fti_bare.analyze_failure(
            description="First", domain="test",
        )
        fti_bare.extract_nitzotzot(
            analysis1.id,
            insights_data=[{
                "content": "Retry loop without backoff",
                "insight_type": "anti_pattern",
                "confidence": 0.6,
            }],
        )
        analysis2 = fti_bare.analyze_failure(
            description="Second", domain="test",
        )
        inserted = fti_bare.extract_nitzotzot(
            analysis2.id,
            insights_data=[{
                "content": "Retry  loop   without    backoff",  # multi-spaces
                "insight_type": "anti_pattern",
                "confidence": 0.6,
            }],
        )
        assert inserted == [], (
            "Whitespace multiples internes doivent matcher après collapse."
        )

    def test_truly_different_content_still_inserts(self, fti_bare):
        """Non-régression : le fix ne doit PAS sur-dédupliquer.
        Des contents VRAIMENT différents doivent bien s'insérer.
        """
        analysis1 = fti_bare.analyze_failure(
            description="Alpha", domain="test",
        )
        fti_bare.extract_nitzotzot(
            analysis1.id,
            insights_data=[{
                "content": "First unique insight about X",
                "insight_type": "opportunity",
                "confidence": 0.6,
            }],
        )
        analysis2 = fti_bare.analyze_failure(
            description="Beta", domain="test",
        )
        inserted = fti_bare.extract_nitzotzot(
            analysis2.id,
            insights_data=[{
                "content": "Second unique insight about Y",
                "insight_type": "opportunity",
                "confidence": 0.6,
            }],
        )
        assert len(inserted) == 1, (
            "Contents distincts doivent s'insérer normalement."
        )

    def test_combined_edge_cases_normalize_same(self, fti_bare):
        """Multiple edge cases combinés (casse + whitespace + punctuation)."""
        analysis1 = fti_bare.analyze_failure(
            description="First", domain="test",
        )
        fti_bare.extract_nitzotzot(
            analysis1.id,
            insights_data=[{
                "content": "Warning: circular dependency found",
                "insight_type": "warning",
                "confidence": 0.8,
            }],
        )
        analysis2 = fti_bare.analyze_failure(
            description="Second", domain="test",
        )
        inserted = fti_bare.extract_nitzotzot(
            analysis2.id,
            insights_data=[{
                "content": "  WARNING:  circular  dependency  found.  ",
                "insight_type": "warning",
                "confidence": 0.8,
            }],
        )
        assert inserted == [], (
            "Casse + whitespace + ponctuation combinés doivent matcher."
        )
