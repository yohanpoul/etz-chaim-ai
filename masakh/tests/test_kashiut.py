"""Tests du Kashiut — קָשִׁיוּת.

F1 fix — Le Kashiut filtre par PERTINENCE (pas par budget).
Couvre :
  - Découpage en blocs (split_blocks)
  - Extraction de mots-clés (extract_keywords)
  - Scoring de pertinence (score_block, _compute_pertinence)
  - Filtrage complet (filter_by_kashiut)
  - Matching morphologique (préfixes 5 chars)
  - Cas limites (prompt vide, un seul bloc, query sans mots-clés)
  - Intégration avec toch() et sof()
  - Shoresh (kashiut=0.0) laisse tout passer
"""

import pytest

from masakh import Masakh, CHARS_PER_TOKEN, clear_log
from masakh.kashiut import (
    split_blocks,
    extract_keywords,
    score_block,
    score_blocks,
    filter_by_kashiut,
    _compute_pertinence,
    ScoredBlock,
)


# ── Helpers ─────────────────────────────────────────────────

def _make_prompt(n_tokens: int) -> str:
    """Créer un prompt d'environ n_tokens tokens."""
    return "x" * (n_tokens * CHARS_PER_TOKEN)


def _multi_block_prompt(blocks: list[str]) -> str:
    """Assembler des blocs séparés par double newline."""
    return "\n\n".join(blocks)


# ── split_blocks ────────────────────────────────────────────

class TestSplitBlocks:

    def test_single_block(self):
        assert split_blocks("hello world") == ["hello world"]

    def test_two_blocks(self):
        result = split_blocks("block one\n\nblock two")
        assert result == ["block one", "block two"]

    def test_multiple_newlines(self):
        result = split_blocks("a\n\n\n\nb")
        assert result == ["a", "b"]

    def test_empty_blocks_filtered(self):
        result = split_blocks("a\n\n\n\n\n\nb")
        assert result == ["a", "b"]

    def test_preserves_internal_newlines(self):
        result = split_blocks("line1\nline2\n\nblock2")
        assert len(result) == 2
        assert "line1\nline2" == result[0]

    def test_empty_string(self):
        assert split_blocks("") == []

    def test_whitespace_only(self):
        assert split_blocks("   \n\n   ") == []


# ── extract_keywords ────────────────────────────────────────

class TestExtractKeywords:

    def test_basic_extraction(self):
        kw = extract_keywords("The Masakh filters context during each call")
        assert "masakh" in kw
        assert "filters" in kw
        assert "context" in kw
        # Stopwords excluded
        assert "the" not in kw
        assert "during" not in kw
        assert "each" not in kw

    def test_short_words_excluded(self):
        kw = extract_keywords("AI is ok")
        # "AI" is 2 chars, "is" stopword, "ok" 2 chars
        assert len(kw) == 0

    def test_french_stopwords(self):
        kw = extract_keywords("le Masakh est un filtre pour les prompts")
        assert "masakh" in kw
        assert "filtre" in kw
        assert "prompts" in kw
        assert "est" not in kw
        assert "les" not in kw

    def test_empty_string(self):
        assert extract_keywords("") == set()

    def test_case_insensitive(self):
        kw = extract_keywords("Masakh MASAKH masakh")
        assert kw == {"masakh"}


# ── score_block ─────────────────────────────────────────────

class TestScoreBlock:

    def test_perfect_overlap(self):
        query_kw = extract_keywords("Masakh filtering context")
        block = "The Masakh performs context filtering operations"
        score = score_block(block, query_kw)
        assert score >= 0.8

    def test_no_overlap(self):
        query_kw = extract_keywords("Masakh filtering context")
        block = "The weather today is sunny and warm outside"
        score = score_block(block, query_kw)
        assert score < 0.3

    def test_partial_overlap(self):
        query_kw = extract_keywords("Masakh filtering context budget")
        block = "The Masakh controls the budget allocation"
        score = score_block(block, query_kw)
        assert 0.2 < score < 0.8

    def test_short_block_always_passes(self):
        """Blocs < 20 chars = marqueurs/séparateurs, toujours 1.0."""
        query_kw = extract_keywords("something completely different")
        assert score_block("[KAVVANAH]", query_kw) == 1.0
        assert score_block("---", query_kw) == 1.0

    def test_empty_query_keywords(self):
        assert score_block("any block content here", set()) == 1.0

    def test_kavvanah_block_always_passes(self):
        """Blocs [KAVVANAH] protégés — directives pipeline, pas du contexte."""
        query_kw = extract_keywords("something completely unrelated")
        kavvanah = "[KAVVANAH]\nIntention : analyser\nSucces si : pertinent\n[/KAVVANAH]"
        assert score_block(kavvanah, query_kw) == 1.0

    def test_tzelem_block_always_passes(self):
        """Blocs [TZELEM] protégés."""
        query_kw = extract_keywords("totally different topic here")
        tzelem = "[TZELEM] analytique\nRaisonner avec rigueur et precision\n[/TZELEM]"
        assert score_block(tzelem, query_kw) == 1.0

    def test_block_no_keywords(self):
        """Bloc sans mots-clés extractibles → score 0.0."""
        query_kw = extract_keywords("Masakh filtering")
        # Block with 20+ chars but only short/stopword tokens
        assert score_block("xx yy zz aa bb cc dd ee ff gg hh", query_kw) == 0.0


# ── Matching morphologique ──────────────────────────────────

class TestMorphologicalMatching:

    def test_prefix_match_analyse_analyser(self):
        """'analyse' dans query matche 'analyser' dans bloc (préfixe 5 chars)."""
        query_kw = extract_keywords("analyse du Zohar")
        block = "Il faut analyser ce passage attentivement"
        score = score_block(block, query_kw)
        # "analyse" → prefix "analy" → matches "analyser"
        assert score > 0.3

    def test_prefix_match_compress_compression(self):
        query_kw = extract_keywords("compress the data")
        block = "The compression algorithm reduces data size"
        score = score_block(block, query_kw)
        # "compress" prefix-matches "compression" (0.7), "data" exact (1.0) → 1.7/2 = 0.85
        assert score > 0.5

    def test_no_prefix_match_short_words(self):
        """Mots < 5 chars ne bénéficient pas du matching par préfixe."""
        query_kw = {"test"}
        block_kw = {"testing"}
        # "test" is only 4 chars, no prefix matching
        score = _compute_pertinence(block_kw, query_kw)
        assert score == 0.0

    def test_exact_match_preferred(self):
        """Le match exact donne 1.0 de crédit, le préfixe 0.7."""
        query_kw = {"masakh", "filtrage"}
        # Exact match
        exact_score = _compute_pertinence({"masakh", "filtrage"}, query_kw)
        # Prefix match only
        prefix_score = _compute_pertinence({"masakhim", "filtrages"}, query_kw)
        assert exact_score > prefix_score


# ── filter_by_kashiut ──────────────────────────────────────

class TestFilterByKashiut:

    def test_threshold_zero_passes_all(self):
        """Seuil 0.0 (Shoresh) → pas de rejet."""
        prompt = _multi_block_prompt([
            "Completely irrelevant weather report",
            "The Masakh filters context",
        ])
        filtered, rejected = filter_by_kashiut(prompt, "Masakh filtering", 0.0)
        assert filtered == prompt
        assert rejected == []

    def test_relevant_blocks_kept(self):
        prompt = _multi_block_prompt([
            "The Masakh filters context according to Kashiut pertinence levels",
            "The weather today is sunny and warm in the city with rain",
            "Kashiut Masakh determines the rejection pertinence threshold",
        ])
        filtered, rejected = filter_by_kashiut(
            prompt, "Masakh Kashiut filtering pertinence", 0.3,
        )
        assert "Masakh filters context" in filtered
        assert "Kashiut Masakh determines" in filtered
        # Weather block should be rejected
        assert len(rejected) >= 1
        assert any("weather" in r["preview"].lower() or "sunny" in r["preview"].lower()
                    for r in rejected)

    def test_high_threshold_strict(self):
        """Seuil Dalet (0.8) → seuls les blocs très pertinents passent."""
        blocks = [
            "Masakh Kashiut filtering pertinence scoring threshold",
            "The architecture uses layers and attention mechanisms",
            "Database optimization for PostgreSQL queries performance",
        ]
        prompt = _multi_block_prompt(blocks)
        filtered, rejected = filter_by_kashiut(
            prompt, "Masakh Kashiut pertinence filtering scoring", 0.8,
        )
        # First block very relevant, others not
        assert "Masakh Kashiut" in filtered
        assert len(rejected) >= 1

    def test_single_block_never_rejected(self):
        """Un seul bloc ne peut pas être rejeté (sécurité)."""
        prompt = "Completely irrelevant single block content"
        filtered, rejected = filter_by_kashiut(prompt, "Masakh filtering", 0.9)
        assert filtered == prompt
        assert rejected == []

    def test_all_rejected_keeps_best(self):
        """Si tout serait rejeté, garder le meilleur bloc."""
        blocks = [
            "Somewhat related to Masakh concept here",
            "Totally unrelated weather forecast report",
            "Another unrelated cooking recipe document",
        ]
        prompt = _multi_block_prompt(blocks)
        filtered, rejected = filter_by_kashiut(
            prompt, "Masakh filtering context", 0.99,
        )
        # Should keep the best-scoring block (the one mentioning Masakh)
        assert "Masakh" in filtered
        assert len(rejected) >= 1

    def test_no_query_keywords_passes_all(self):
        """Query sans mots-clés extractibles → pas de rejet."""
        prompt = _multi_block_prompt(["block one", "block two"])
        filtered, rejected = filter_by_kashiut(prompt, "is a", 0.8)
        assert filtered == prompt
        assert rejected == []

    def test_single_keyword_query_passes_all(self):
        """Query avec 1 seul mot-clé → pas assez de signal, pas de rejet."""
        prompt = _multi_block_prompt([
            "Completely irrelevant weather data report",
            "Another unrelated block here",
        ])
        filtered, rejected = filter_by_kashiut(prompt, "Masakh", 0.8)
        assert filtered == prompt
        assert rejected == []

    def test_rejected_blocks_have_metadata(self):
        """Les blocs rejetés ont index, score, seuil, chars, preview."""
        blocks = [
            "The Masakh filters context according to levels",
            "Irrelevant weather information and temperature data across cities",
        ]
        prompt = _multi_block_prompt(blocks)
        _, rejected = filter_by_kashiut(
            prompt, "Masakh filtering context", 0.5,
        )
        if rejected:
            r = rejected[0]
            assert "block_index" in r
            assert "score" in r
            assert "threshold" in r
            assert "chars" in r
            assert "tokens_est" in r
            assert "preview" in r
            assert isinstance(r["score"], float)
            assert r["threshold"] == 0.5


# ── Intégration toch() + kashiut ────────────────────────────

class TestTochKashiut:

    def test_toch_without_query_no_kashiut(self):
        """Sans query, toch() ne fait que de l'Aviut (rétro-compatible)."""
        m = Masakh("atziluth")  # dalet, kashiut=0.8
        blocks = [
            "Completely irrelevant weather report for today",
            "More irrelevant content about cooking recipes",
        ]
        prompt = _multi_block_prompt(blocks)
        # Without query, kashiut doesn't fire
        result = m.toch(prompt, budget_tokens=10000)
        assert result == prompt  # within budget, no filtering
        assert m._kashiut_rejected == []

    def test_toch_with_query_rejects_irrelevant(self):
        """Avec query, toch() rejette les blocs non pertinents."""
        m = Masakh("yetzirah")  # bet, kashiut=0.6
        blocks = [
            "The Masakh filtering mechanism uses Kashiut for pertinence scoring Aviut compression",
            "Irrelevant weather information about temperature and rainfall data outside today",
            "The Aviut Masakh Kashiut compression transforms filtered pertinence content scoring",
        ]
        prompt = _multi_block_prompt(blocks)
        result = m.toch(
            prompt, budget_tokens=10000,
            query="Masakh Kashiut Aviut filtering compression pertinence scoring",
        )
        # Relevant blocks should survive
        assert "Masakh filtering" in result
        assert "Aviut Masakh" in result
        # Weather block should be gone
        assert "temperature" not in result
        # Rejection recorded
        assert len(m._kashiut_rejected) >= 1

    def test_toch_shoresh_no_kashiut(self):
        """Shoresh (kashiut=0.0) → pas de rejet même avec query."""
        m = Masakh("briah", level="shoresh")
        blocks = [
            "Relevant content about Masakh",
            "Irrelevant weather data here",
        ]
        prompt = _multi_block_prompt(blocks)
        result = m.toch(
            prompt, budget_tokens=10000,
            query="Masakh filtering",
        )
        assert result == prompt
        assert m._kashiut_rejected == []

    def test_toch_kashiut_then_aviut(self):
        """Kashiut filtre d'abord, puis Aviut compresse le reste."""
        m = Masakh("atziluth")  # dalet: kashiut=0.8, compression_forte
        # Build a prompt with relevant + irrelevant + lots of padding
        relevant = "The Masakh Kashiut pertinence filtering scoring mechanism works well"
        irrelevant = "Weather forecast sunny temperature rainfall humidity wind data"
        padding = " ".join(["Masakh filtering content padding. "] * 50)
        prompt = _multi_block_prompt([relevant, irrelevant, padding])

        result = m.toch(
            prompt, budget_tokens=100,
            query="Masakh Kashiut pertinence filtering scoring",
        )
        # Irrelevant block should be kashiut-rejected
        assert "weather" not in result.lower()
        # Result should be compressed (within budget)
        assert len(result) < len(prompt)

    def test_toch_kashiut_per_level_strictness(self):
        """Niveaux plus hauts = kashiut plus strict = plus de rejets."""
        blocks = [
            "The Masakh Kashiut filtering mechanism is essential for pertinence",
            "Architecture layers involve attention and transformer mechanisms",
            "Database performance optimization requires careful query planning",
            "Network protocols handle packet routing and error correction",
        ]
        prompt = _multi_block_prompt(blocks)
        query = "Masakh Kashiut filtering pertinence"

        # Aleph (0.5) should reject less
        m_aleph = Masakh("assiah")  # kashiut=0.5
        m_aleph.toch(prompt, budget_tokens=10000, query=query)
        rejected_aleph = len(m_aleph._kashiut_rejected)

        # Dalet (0.8) should reject more
        m_dalet = Masakh("atziluth")  # kashiut=0.8
        m_dalet.toch(prompt, budget_tokens=10000, query=query)
        rejected_dalet = len(m_dalet._kashiut_rejected)

        assert rejected_dalet >= rejected_aleph


# ── Intégration sof() + kashiut ─────────────────────────────

class TestSofKashiut:

    def test_sof_includes_kashiut_fields(self):
        """sof() inclut les métriques de rejet Kashiut."""
        m = Masakh("briah")  # gimel
        blocks = [
            "Masakh Kashiut filtering pertinence scoring mechanism works",
            "Irrelevant weather temperature rainfall humidity data",
        ]
        prompt = _multi_block_prompt(blocks)
        filtered = m.toch(
            prompt, budget_tokens=10000,
            query="Masakh Kashiut filtering pertinence scoring",
        )
        log = m.sof(prompt, filtered)

        assert "kashiut_rejected_count" in log
        assert "kashiut_rejected_tokens" in log
        assert "kashiut_rejected_blocks" in log
        assert isinstance(log["kashiut_rejected_count"], int)
        assert isinstance(log["kashiut_rejected_tokens"], int)
        assert isinstance(log["kashiut_rejected_blocks"], list)

    def test_sof_no_kashiut_zero_fields(self):
        """Sans kashiut, les champs sont à 0/vide."""
        m = Masakh("assiah")
        prompt = "Short prompt"
        # No query → no kashiut
        filtered = m.toch(prompt, budget_tokens=10000)
        log = m.sof(prompt, filtered)
        assert log["kashiut_rejected_count"] == 0
        assert log["kashiut_rejected_tokens"] == 0
        assert log["kashiut_rejected_blocks"] == []

    def test_sof_rejection_reason_includes_kashiut(self):
        """rejection_reason mentionne kashiut quand des blocs sont rejetés."""
        m = Masakh("briah")
        blocks = [
            "Masakh Kashiut pertinence filtering scoring mechanism here",
            "Completely irrelevant weather temperature rainfall humidity wind data report",
        ]
        prompt = _multi_block_prompt(blocks)
        filtered = m.toch(
            prompt, budget_tokens=10000,
            query="Masakh Kashiut pertinence filtering scoring",
        )
        log = m.sof(prompt, filtered)

        if log["kashiut_rejected_count"] > 0:
            assert "kashiut" in log["rejection_reason"].lower()

    def test_sof_was_filtered_true_on_kashiut_only(self):
        """was_filtered=True même si seul le Kashiut a rejeté (pas l'Aviut)."""
        m = Masakh("briah")
        blocks = [
            "Masakh Kashiut pertinence filtering scoring mechanism relevance",
            "Totally irrelevant weather temperature humidity rainfall wind data",
        ]
        prompt = _multi_block_prompt(blocks)
        filtered = m.toch(
            prompt, budget_tokens=10000,
            query="Masakh Kashiut pertinence filtering scoring",
        )
        log = m.sof(prompt, filtered)

        if m._kashiut_rejected:
            assert log["was_filtered"] is True


# ── Intégration apply() + kashiut ───────────────────────────

class TestApplyKashiut:

    def setup_method(self):
        clear_log()

    def test_toch_with_query(self):
        """toch() avec query active le scoring Kashiut."""
        m = Masakh("briah")
        blocks = [
            "Masakh Kashiut filtering pertinence scoring mechanism relevant content",
            "Irrelevant weather temperature rainfall humidity wind data report today",
        ]
        prompt = _multi_block_prompt(blocks)
        params = m.rosh(prompt, context_window=32768)
        filtered = m.toch(
            prompt, params["budget_tokens"],
            query="Masakh Kashiut pertinence filtering scoring",
        )
        log = m.sof(prompt, filtered)
        assert "kashiut_rejected_count" in log

    def test_toch_without_query_backward_compat(self):
        """toch() sans query fonctionne (Aviut seul, pas de Kashiut)."""
        m = Masakh("assiah")
        prompt = "Simple short prompt"
        params = m.rosh(prompt, context_window=8192)
        filtered = m.toch(prompt, params["budget_tokens"])
        log = m.sof(prompt, filtered)
        assert filtered == prompt
        assert log["kashiut_rejected_count"] == 0
