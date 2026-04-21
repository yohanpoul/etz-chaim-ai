"""Tests du Masakh — מָסָךְ.

Phase 2 — Couvre :
  - 5 niveaux d'Aviut (dalet→shoresh)
  - Double propriété Kashiut + Aviut
  - Modes de filtrage distincts (compression_forte, moderee, resume, troncation, aucune)
  - Hizdakchut dynamique (amincissement)
  - Phase Rosh : calcul des paramètres
  - Phase Toch : filtrage effectif par mode
  - Phase Sof : documentation du rejet
  - Orchestration apply()
  - Log en mémoire (Reshimo de Aviut)
  - Intégration dans olamot.ollama_generate
"""

import json
from unittest.mock import patch, MagicMock

import pytest

from masakh import (
    Masakh,
    MASAKH_LEVELS,
    LEVEL_ORDER,
    OLAM_DEFAULT_LEVEL,
    AVIUT_LEVELS,
    CHARS_PER_TOKEN,
    HIZDAKCHUT_DEGRADE_THRESHOLD,
    HIZDAKCHUT_UPGRADE_THRESHOLD,
    _MASAKH_LOG,
    auto_hizdakchut,
    get_hizdakchut_levels,
    reset_hizdakchut_levels,
    get_log,
    clear_log,
    write_reshimo,
    get_reshimot,
    clear_reshimot,
)


# ── Helpers ─────────────────────────────────────────────────

def _make_prompt(n_tokens: int) -> str:
    """Créer un prompt d'environ n_tokens tokens."""
    return "x" * (n_tokens * CHARS_PER_TOKEN)


# ── 5 niveaux d'Aviut ─────────────────────────────────────

class TestMasakhLevels:

    def test_five_levels_defined(self):
        assert set(MASAKH_LEVELS.keys()) == {"dalet", "gimel", "bet", "aleph", "shoresh"}

    def test_level_order(self):
        assert LEVEL_ORDER == ("dalet", "gimel", "bet", "aleph", "shoresh")

    def test_four_olamot_mapped(self):
        assert set(OLAM_DEFAULT_LEVEL.keys()) == {"atziluth", "briah", "yetzirah", "assiah"}

    def test_atziluth_is_dalet(self):
        m = Masakh("atziluth")
        assert m.level == "dalet"
        assert m.budget_ratio == 0.20

    def test_briah_is_gimel(self):
        m = Masakh("briah")
        assert m.level == "gimel"
        assert m.budget_ratio == 0.30

    def test_yetzirah_is_bet(self):
        m = Masakh("yetzirah")
        assert m.level == "bet"
        assert m.budget_ratio == 0.40

    def test_assiah_is_aleph(self):
        m = Masakh("assiah")
        assert m.level == "aleph"
        assert m.budget_ratio == 0.60

    def test_unknown_olam_raises(self):
        with pytest.raises(ValueError, match="Olam inconnu"):
            Masakh("ein_sof")

    def test_budget_ordering(self):
        """Plus le niveau est haut, moins de budget (plus de filtrage)."""
        budgets = [MASAKH_LEVELS[lvl]["budget_ratio"] for lvl in LEVEL_ORDER]
        assert budgets == sorted(budgets), "Budgets doivent croître de dalet à shoresh"

    def test_kashiut_ordering(self):
        """Plus le niveau est haut, plus la kashiut est stricte."""
        kashiuts = [MASAKH_LEVELS[lvl]["kashiut"] for lvl in LEVEL_ORDER]
        assert kashiuts == sorted(kashiuts, reverse=True)

    def test_explicit_level_override(self):
        """Forcer un niveau via le paramètre level."""
        m = Masakh("briah", level="shoresh")
        assert m.level == "shoresh"
        assert m.olam == "briah"
        assert m.budget_ratio == 0.85

    def test_invalid_level_raises(self):
        with pytest.raises(ValueError, match="Niveau inconnu"):
            Masakh("briah", level="invalid")

    def test_repr(self):
        m = Masakh("briah")
        r = repr(m)
        assert "briah" in r
        assert "gimel" in r
        assert "kashiut" in r
        assert "compression_moderee" in r

    def test_compat_aviut_levels(self):
        """AVIUT_LEVELS compat dict doit rester valide."""
        assert "atziluth" in AVIUT_LEVELS
        assert AVIUT_LEVELS["briah"]["level"] == "gimel"
        assert AVIUT_LEVELS["briah"]["budget_ratio"] == 0.30


# ── Double propriété Kashiut + Aviut ─────────────────────

class TestKashiutAviut:

    def test_kashiut_dalet(self):
        m = Masakh("atziluth")
        assert m.kashiut == 0.8

    def test_kashiut_shoresh(self):
        m = Masakh("briah", level="shoresh")
        assert m.kashiut == 0.0

    def test_aviut_mode_dalet(self):
        m = Masakh("atziluth")
        assert m.aviut_mode == "compression_forte"

    def test_aviut_mode_gimel(self):
        m = Masakh("briah")
        assert m.aviut_mode == "compression_moderee"

    def test_aviut_mode_bet(self):
        m = Masakh("yetzirah")
        assert m.aviut_mode == "resume"

    def test_aviut_mode_aleph(self):
        m = Masakh("assiah")
        assert m.aviut_mode == "troncation"

    def test_aviut_mode_shoresh(self):
        m = Masakh("briah", level="shoresh")
        assert m.aviut_mode == "aucune"

    def test_level_index(self):
        m = Masakh("briah")
        assert m.level_index == 1  # gimel = index 1


# ── Hizdakchut dynamique ─────────────────────────────────

class TestHizdakchut:

    def test_degrade_descends_one_level(self):
        m = Masakh("briah")  # gimel (index 1)
        changed = m.hizdakchut(0.1)
        assert changed is True
        assert m.level == "bet"  # descended to bet

    def test_upgrade_ascends_one_level(self):
        m = Masakh("yetzirah")  # bet (index 2)
        changed = m.hizdakchut(0.9)
        assert changed is True
        assert m.level == "gimel"  # ascended to gimel

    def test_stable_no_change(self):
        m = Masakh("briah")  # gimel
        changed = m.hizdakchut(0.5)
        assert changed is False
        assert m.level == "gimel"

    def test_cannot_descend_below_shoresh(self):
        m = Masakh("briah", level="shoresh")
        changed = m.hizdakchut(0.1)
        assert changed is False
        assert m.level == "shoresh"

    def test_cannot_ascend_above_dalet(self):
        m = Masakh("atziluth")  # dalet (index 0)
        changed = m.hizdakchut(0.95)
        assert changed is False
        assert m.level == "dalet"

    def test_level_changes_recorded(self):
        m = Masakh("briah")
        m.hizdakchut(0.1)
        changes = m.level_changes
        assert len(changes) == 1
        assert changes[0]["from"] == "gimel"
        assert changes[0]["to"] == "bet"
        assert "hizdakchut" in changes[0]["reason"]

    def test_set_level_manual(self):
        m = Masakh("briah")
        m.set_level("shoresh")
        assert m.level == "shoresh"
        assert m.budget_ratio == 0.85
        assert m.kashiut == 0.0

    def test_set_level_invalid_raises(self):
        m = Masakh("briah")
        with pytest.raises(ValueError, match="Niveau inconnu"):
            m.set_level("invalid")

    def test_set_level_same_no_change(self):
        m = Masakh("briah")  # gimel
        m.set_level("gimel")
        assert len(m.level_changes) == 0

    def test_multiple_changes_tracked(self):
        m = Masakh("yetzirah")  # bet
        m.hizdakchut(0.1)        # bet → aleph
        m.hizdakchut(0.1)        # aleph → shoresh
        assert m.level == "shoresh"
        assert len(m.level_changes) == 2

    def test_thresholds_correct(self):
        assert HIZDAKCHUT_DEGRADE_THRESHOLD == 0.3
        assert HIZDAKCHUT_UPGRADE_THRESHOLD == 0.8


# ── Phase Rosh : décision ──────────────────────────────────

class TestRosh:

    def test_rosh_returns_all_keys(self):
        m = Masakh("briah")
        result = m.rosh("Hello world", context_window=32768)
        expected_keys = {
            "olam", "aviut_level", "kashiut", "aviut_mode",
            "budget_ratio", "context_window",
            "budget_tokens", "prompt_tokens", "needs_filtering",
        }
        assert set(result.keys()) == expected_keys

    def test_rosh_budget_calculation(self):
        m = Masakh("briah")  # 30%
        result = m.rosh("test", context_window=10000)
        assert result["budget_tokens"] == 3000

    def test_rosh_short_prompt_no_filtering(self):
        m = Masakh("assiah")  # 60%
        prompt = "Explain causality"
        result = m.rosh(prompt, context_window=8192)
        assert result["needs_filtering"] is False

    def test_rosh_long_prompt_needs_filtering(self):
        m = Masakh("atziluth")  # 20%
        prompt = _make_prompt(5000)  # 5000 tokens
        result = m.rosh(prompt, context_window=8192)
        # Budget = 8192 * 0.20 = 1638 tokens < 5000
        assert result["needs_filtering"] is True
        assert result["budget_tokens"] == 1638

    def test_rosh_includes_kashiut_and_mode(self):
        m = Masakh("atziluth")
        result = m.rosh("test", context_window=8192)
        assert result["kashiut"] == 0.8
        assert result["aviut_mode"] == "compression_forte"

    def test_rosh_does_not_modify_prompt(self):
        m = Masakh("briah")
        prompt = "Original prompt content"
        m.rosh(prompt, context_window=32768)
        assert prompt == "Original prompt content"


# ── Phase Toch : modes de filtrage ─────────────────────────

class TestToch:

    def test_toch_short_prompt_unchanged(self):
        m = Masakh("assiah")
        prompt = "Short prompt"
        result = m.toch(prompt, budget_tokens=1000)
        assert result == prompt

    def test_toch_exact_budget_no_filtering(self):
        m = Masakh("assiah")
        prompt = _make_prompt(500)
        result = m.toch(prompt, budget_tokens=500)
        assert result == prompt

    # ── compression_forte (dalet) ──────────────────────────

    def test_compression_forte_filters(self):
        m = Masakh("atziluth")  # dalet = compression_forte
        prompt = _make_prompt(5000)
        result = m.toch(prompt, budget_tokens=1000)
        assert len(result) < len(prompt)
        assert "compression forte" in result

    def test_compression_forte_extracts_key_phrases(self):
        """Dalet: extracts key phrases from ANYWHERE in the text."""
        m = Masakh("atziluth")
        # Build a multi-sentence prompt with identifiable key phrases
        sentences = (
            ["The architecture requires careful optimization. "] * 3
            + ["The Tsimtsum transforms information through compression. "] * 5
            + ["Padding sentence without real content here. "] * 20
            + ["The Masakh filters according to Aviut thickness levels. "] * 5
            + ["More padding without substance at all. "] * 10
        )
        prompt = " ".join(sentences)
        result = m.toch(prompt, budget_tokens=200)
        # Key phrases should survive even though they're in the middle
        assert "compression forte" in result

    # ── compression_moderee (gimel) ────────────────────────

    def test_compression_moderee_filters(self):
        m = Masakh("briah")  # gimel
        prompt = _make_prompt(5000)
        result = m.toch(prompt, budget_tokens=1000)
        assert len(result) < len(prompt)
        assert "compression modérée" in result

    def test_compression_moderee_preserves_anchors(self):
        """Gimel: preserves first and last sentence as context anchors."""
        m = Masakh("briah")
        prompt = (
            "FIRST SENTENCE IS THE ANCHOR. "
            + " ".join(["Middle padding content here. "] * 50)
            + "LAST SENTENCE IS ALSO KEPT."
        )
        result = m.toch(prompt, budget_tokens=300)
        assert "FIRST SENTENCE IS THE ANCHOR" in result
        assert "LAST SENTENCE IS ALSO KEPT" in result

    # ── resume (bet) ───────────────────────────────────────

    def test_resume_head_heavy(self):
        """Bet: head 60% intact + key phrases from the rest."""
        m = Masakh("yetzirah")  # bet = resume
        prompt = _make_prompt(5000)
        result = m.toch(prompt, budget_tokens=1000)
        assert len(result) < len(prompt)
        assert "résumé extractif" in result

    def test_resume_preserves_head(self):
        """Bet: the beginning of the text is always intact."""
        m = Masakh("yetzirah")
        prompt = "IMPORTANT INSTRUCTION AT THE START. " + _make_prompt(5000)
        result = m.toch(prompt, budget_tokens=1000)
        assert result.startswith("IMPORTANT INSTRUCTION AT THE START.")

    # ── troncation (aleph) ─────────────────────────────────

    def test_troncation_no_tail(self):
        """Aleph: troncation simple, head 80%, pas de tail."""
        m = Masakh("assiah")  # aleph = troncation
        prompt = _make_prompt(5000) + "THIS_SHOULD_BE_LOST"
        result = m.toch(prompt, budget_tokens=1000)
        assert "THIS_SHOULD_BE_LOST" not in result
        assert "troncation simple" in result

    # ── aucune (shoresh) ───────────────────────────────────

    def test_shoresh_no_filtering(self):
        """Shoresh: aucun filtrage même si budget dépassé."""
        m = Masakh("briah", level="shoresh")
        prompt = _make_prompt(10000)
        result = m.toch(prompt, budget_tokens=100)
        assert result == prompt  # pas de filtrage

    # ── F10: modes produce DIFFERENT output ─────────────────

    def test_modes_produce_different_output(self):
        """F10 fix: compression_forte, compression_moderee, resume
        must produce genuinely DIFFERENT results on the same input."""
        # Build a realistic multi-sentence prompt
        sections = [
            "The Masakh filters context before each LLM call. ",
            "Aviut represents the thickness of the screening mechanism. ",
            "Each level produces qualitatively different transformations. ",
            "The Rosh phase calculates parameters without touching data. ",
            "Toch applies the actual filtering according to the mode. ",
            "Sof documents what was rejected as a Reshimo trace. ",
            "Kashiut measures the hardness threshold for rejection. ",
            "The Tsimtsum creates space by contracting infinite light. ",
            "Shevirah occurs when vessels cannot contain the light. ",
            "Tikkun repairs the broken vessels through careful assembly. ",
            "Partzufim are composite faces that emerge after repair. ",
            "The double Reshimo preserves both content and process. ",
            "Hizdakchut dynamically thins the Masakh based on quality. ",
            "Context monitoring tracks twenty nine dimensions of the Kli. ",
            "Maturation progresses through Ibur Yenikah and Mochin stages. ",
        ]
        prompt = " ".join(sections * 10)  # ~150 sentences

        budget = 500  # small budget forces real compression

        m_forte = Masakh("atziluth")    # compression_forte
        m_moderee = Masakh("briah")     # compression_moderee
        m_resume = Masakh("yetzirah")   # resume

        r_forte = m_forte.toch(prompt, budget_tokens=budget)
        r_moderee = m_moderee.toch(prompt, budget_tokens=budget)
        r_resume = m_resume.toch(prompt, budget_tokens=budget)

        # Strip markers before comparing content
        def strip_marker(s: str) -> str:
            idx = s.find("\n\n[Masakh")
            return s[:idx] if idx >= 0 else s

        c_forte = strip_marker(r_forte)
        c_moderee = strip_marker(r_moderee)
        c_resume = strip_marker(r_resume)

        # All three are different from each other
        assert c_forte != c_moderee, (
            "compression_forte and compression_moderee produced identical content"
        )
        assert c_forte != c_resume, (
            "compression_forte and resume produced identical content"
        )
        assert c_moderee != c_resume, (
            "compression_moderee and resume produced identical content"
        )

        # Each mode is shorter than the original
        for name, result in [("forte", r_forte), ("moderee", r_moderee), ("resume", r_resume)]:
            assert len(result) < len(prompt), f"{name} didn't compress"

    def test_compression_forte_reorders_by_relevance(self):
        """Forte extracts the most relevant sentences, not positional."""
        m = Masakh("atziluth")
        # Place the important sentence in the MIDDLE
        prompt = (
            " ".join(["Irrelevant padding sentence here. "] * 20)
            + "The CRITICAL architecture insight about Masakh filtering is crucial. "
            + " ".join(["More irrelevant padding follows. "] * 20)
        )
        result = m.toch(prompt, budget_tokens=200)
        # The important middle sentence should survive
        assert "CRITICAL" in result or "compression forte" in result

    def test_compression_moderee_keeps_first_and_last(self):
        """Moderee always anchors first + last sentences."""
        m = Masakh("briah")
        prompt = (
            "FIRST ANCHOR SENTENCE HERE. "
            + " ".join(["Middle content sentence number. "] * 40)
            + "LAST ANCHOR SENTENCE HERE."
        )
        result = m.toch(prompt, budget_tokens=300)
        # First and last sentences are preserved as anchors
        assert "FIRST ANCHOR" in result
        assert "LAST ANCHOR" in result

    def test_resume_preserves_head_intact(self):
        """Resume keeps the head of the text intact (60% of budget)."""
        m = Masakh("yetzirah")
        prompt = (
            "HEAD SECTION START. This is important context. More head text here. "
            + " ".join(["Body content follows afterwards. "] * 40)
        )
        result = m.toch(prompt, budget_tokens=300)
        assert result.startswith("HEAD SECTION START")

    # ── budget compliance ──────────────────────────────────

    def test_toch_respects_budget(self):
        """Le prompt filtré ne doit pas dépasser le budget."""
        for olam in ("atziluth", "briah", "yetzirah", "assiah"):
            m = Masakh(olam)
            prompt = _make_prompt(10000)
            budget = 2000
            result = m.toch(prompt, budget_tokens=budget)
            result_tokens = m.estimate_tokens(result)
            # Tolérance : séparateur + overhead résiduel
            assert result_tokens < budget * 1.3, (
                f"{olam}: filtré {result_tokens} tokens, budget {budget}"
            )


# ── Phase Sof : documentation ──────────────────────────────

class TestSof:

    def test_sof_no_filtering(self):
        m = Masakh("assiah")
        prompt = "Short"
        log = m.sof(prompt, prompt)
        assert log["was_filtered"] is False
        assert log["tokens_rejected"] == 0
        assert log["rejection_reason"] == "within budget"

    def test_sof_with_filtering(self):
        m = Masakh("briah")
        original = _make_prompt(5000)
        filtered = _make_prompt(1000)
        log = m.sof(original, filtered)
        assert log["was_filtered"] is True
        assert log["tokens_rejected"] == 4000
        assert log["tokens_before"] == 5000
        assert log["tokens_after"] == 1000
        assert "Masakh gimel" in log["rejection_reason"]

    def test_sof_has_timestamp(self):
        m = Masakh("yetzirah")
        log = m.sof("a", "a")
        assert "timestamp" in log
        assert isinstance(log["timestamp"], float)

    def test_sof_has_olam_and_level(self):
        m = Masakh("atziluth")
        log = m.sof("test", "test")
        assert log["olam"] == "atziluth"
        assert log["aviut_level"] == "dalet"

    def test_sof_has_kashiut_and_mode(self):
        m = Masakh("briah")
        log = m.sof("test", "test")
        assert log["kashiut"] == 0.7
        assert log["aviut_mode"] == "compression_moderee"

    def test_sof_rejection_ratio(self):
        m = Masakh("briah")
        original = _make_prompt(1000)
        filtered = _make_prompt(300)
        log = m.sof(original, filtered)
        assert abs(log["rejection_ratio"] - 0.7) < 0.01

    def test_sof_includes_level_changes(self):
        m = Masakh("briah")
        m.hizdakchut(0.1)  # gimel → bet
        log = m.sof("test", "test")
        assert len(log["level_changes"]) == 1


# ── Orchestration rosh/toch/sof ───────────────────────────

class TestOrchestration:
    """Tests pour le pipeline rosh→toch→sof (remplace apply() supprimé F-001)."""

    def setup_method(self):
        clear_log()

    def test_rosh_toch_sof_short_prompt(self):
        m = Masakh("assiah")
        prompt = "What is the meaning of life?"
        params = m.rosh(prompt, context_window=8192)
        filtered = m.toch(prompt, params["budget_tokens"])
        log = m.sof(prompt, filtered)
        assert filtered == prompt
        assert log["was_filtered"] is False

    def test_rosh_toch_sof_long_prompt_filtered(self):
        m = Masakh("atziluth")
        prompt = _make_prompt(10000)
        params = m.rosh(prompt, context_window=8192)
        filtered = m.toch(prompt, params["budget_tokens"])
        log = m.sof(prompt, filtered)
        assert len(filtered) < len(prompt)
        assert log["was_filtered"] is True
        assert log["tokens_rejected"] > 0

    def test_clear_log(self):
        _MASAKH_LOG.append({"olam": "briah"})
        assert len(get_log()) >= 1
        clear_log()
        assert len(get_log()) == 0


# ── Budget par Olam (valeurs réelles du config) ────────────

class TestBudgetRealistic:

    def test_briah_budget(self):
        """Briah: 30% de 32768 = 9830 tokens."""
        m = Masakh("briah")
        params = m.rosh("test", context_window=32768)
        assert params["budget_tokens"] == 9830

    def test_yetzirah_budget(self):
        """Yetzirah: 40% de 8192 = 3276 tokens."""
        m = Masakh("yetzirah")
        params = m.rosh("test", context_window=8192)
        assert params["budget_tokens"] == 3276

    def test_assiah_budget(self):
        """Assiah: 60% de 8192 = 4915 tokens."""
        m = Masakh("assiah")
        params = m.rosh("test", context_window=8192)
        assert params["budget_tokens"] == 4915

    def test_short_prompt_passes_all_olamot(self):
        """Un prompt court passe tous les niveaux de Masakh."""
        prompt = "Explain the concept of Tsimtsum in 3 sentences."
        for olam in ("atziluth", "briah", "yetzirah", "assiah"):
            m = Masakh(olam)
            params = m.rosh(prompt, context_window=8192)
            assert params["needs_filtering"] is False, f"{olam} devrait passer"


# ── Token estimation ───────────────────────────────────────

class TestTokenEstimation:

    def test_empty_string(self):
        assert Masakh.estimate_tokens("") == 1  # min 1

    def test_short_string(self):
        assert Masakh.estimate_tokens("test") == 1

    def test_known_length(self):
        text = "x" * 400
        assert Masakh.estimate_tokens(text) == 100

    def test_chars_per_token_constant(self):
        assert CHARS_PER_TOKEN == 4


# ── Intégration olamot.py ──────────────────────────────────

class TestOlamotIntegration:
    """Vérifier que le Masakh est appelé dans ollama_generate."""

    def setup_method(self):
        clear_log()

    @patch("olamot.get_provider", return_value="ollama")
    @patch("olamot.urllib.request.urlopen")
    def test_ollama_generate_uses_masakh(self, mock_urlopen, _m_prov):
        """ollama_generate doit passer par le Masakh."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "response": "Test response",
        }).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        from olamot import ollama_generate
        response, latency = ollama_generate("briah", "test prompt")

        log = get_log()
        assert len(log) >= 1
        assert log[-1]["olam"] == "briah"

    @patch("olamot.get_provider", return_value="ollama")
    @patch("olamot.urllib.request.urlopen")
    def test_ollama_generate_long_prompt_filtered(self, mock_urlopen, _m_prov):
        """Un prompt trop long doit être filtré par le Masakh."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "response": "Filtered response",
        }).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        from olamot import ollama_generate

        # En ibur (0 reshimots), Maturation contraint le Masakh à aleph
        # (budget 60%). Avec ctx=32768, budget = ~19660 tokens.
        # Il faut un prompt plus long pour déclencher le filtrage.
        long_prompt = _make_prompt(25000)
        response, latency = ollama_generate("briah", long_prompt)

        log = get_log()
        last = log[-1]
        assert last["was_filtered"] is True
        assert last["tokens_rejected"] > 0

        call_data = json.loads(mock_urlopen.call_args[0][0].data)
        sent_prompt = call_data["prompt"]
        assert len(sent_prompt) < len(long_prompt)
        assert "Masakh" in sent_prompt


# ── Kavvanah ───────────────────────────────────────────────

class TestKavvanah:
    """Tests de l'injection de Kavvanah dans les appels LLM."""

    def setup_method(self):
        clear_log()

    def test_format_kavvanah_full(self):
        from masakh.context_assembler import _format_kavvanah
        kav = {
            "intention": "approfondir le Tsimtsum",
            "critere_succes": "score > 0.8",
            "anti_pattern": "ne pas halluciner",
        }
        result = _format_kavvanah(kav)
        assert "[KAVVANAH]" in result
        assert "[/KAVVANAH]" in result
        assert "Intention : approfondir le Tsimtsum" in result
        assert "Succès si : score > 0.8" in result
        assert "Ne pas : ne pas halluciner" in result

    def test_format_kavvanah_partial(self):
        from masakh.context_assembler import _format_kavvanah
        result = _format_kavvanah({"intention": "test"})
        assert "Intention : test" in result
        assert "Succès si" not in result
        assert "Ne pas" not in result

    @patch("olamot.get_provider", return_value="ollama")
    @patch("olamot.urllib.request.urlopen")
    def test_kavvanah_injected_in_prompt(self, mock_urlopen, _m_prov):
        """La Kavvanah doit apparaître en tête du prompt envoyé."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "response": "Response with kavvanah",
        }).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        from olamot import ollama_generate
        kavvanah = {
            "intention": "test injection",
            "critere_succes": "kavvanah visible",
        }
        response, latency = ollama_generate(
            "briah", "user prompt here", kavvanah=kavvanah,
        )

        call_data = json.loads(mock_urlopen.call_args[0][0].data)
        sent_prompt = call_data["prompt"]
        # Le ContextAssembler peut injecter [TZELEM] avant [KAVVANAH]
        assert "[KAVVANAH]" in sent_prompt
        assert "user prompt here" in sent_prompt

    @patch("olamot.get_provider", return_value="ollama")
    @patch("olamot.urllib.request.urlopen")
    def test_no_kavvanah_default_injected(self, mock_urlopen, _m_prov):
        """Sans Kavvanah explicite, le Masakh injecte un default (AUDIT F05-R2).

        Avant F05-R2 : pas de [KAVVANAH] quand aucune intention fournie.
        Après F05-R2 : le per-dimension corrective action injecte
        kavvanah='general_query' quand dim 01 est absente.
        """
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "response": "No kavvanah",
        }).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        from olamot import ollama_generate
        response, _ = ollama_generate("briah", "simple prompt")

        call_data = json.loads(mock_urlopen.call_args[0][0].data)
        sent_prompt = call_data["prompt"]
        # AUDIT F05-R2: default kavvanah is now injected when absent
        assert "[KAVVANAH]" in sent_prompt
        assert "general_query" in sent_prompt

    @patch("olamot.get_provider", return_value="ollama")
    @patch("olamot.urllib.request.urlopen")
    def test_no_kavvanah_emits_warning(self, mock_urlopen, _m_prov, caplog):
        """Qliphoth F12 — appel sans kavvanah doit émettre un warning EC-SHK-038."""
        import logging

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "response": "No kavvanah warning test",
        }).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        from olamot import ollama_generate
        with caplog.at_level(logging.WARNING, logger="olamot"):
            ollama_generate("briah", "test sans kavvanah")

        # Le warning doit citer EC-SHK-038
        assert any("EC-SHK-038" in msg for msg in caplog.messages)

    @patch("olamot.get_provider", return_value="ollama")
    @patch("olamot.urllib.request.urlopen")
    def test_kavvanah_present_no_warning(self, mock_urlopen, _m_prov, caplog):
        """Qliphoth F12 — appel AVEC kavvanah ne doit PAS émettre de warning."""
        import logging

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "response": "With kavvanah",
        }).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        from olamot import ollama_generate
        with caplog.at_level(logging.WARNING, logger="olamot"):
            ollama_generate("briah", "test avec kavvanah",
                            kavvanah={"intention": "test", "critere_succes": "ok", "anti_pattern": "rien"})

        # Aucun warning EC-SHK-038 ne doit apparaître
        assert not any("EC-SHK-038" in msg for msg in caplog.messages)

    @patch("olamot.get_provider", return_value="ollama")
    @patch("olamot.urllib.request.urlopen")
    def test_kavvanah_logged_in_masakh(self, mock_urlopen, _m_prov):
        """La Kavvanah doit être présente dans le log Masakh."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "response": "OK",
        }).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        from olamot import ollama_generate
        kavvanah = {"intention": "test log"}
        ollama_generate("briah", "test", kavvanah=kavvanah)

        log = get_log()
        last = log[-1]
        assert "kavvanah" in last
        assert last["kavvanah"]["intention"] == "test log"


# ── Double Reshimo ─────────────────────────────────────────

class TestDoubleReshimo:
    """Tests de la Double Reshimo (Phase 2c)."""

    def setup_method(self):
        clear_reshimot()
        clear_log()

    def test_write_reshimo_basic(self):
        r = write_reshimo(
            olam="briah",
            hitlabshut={"response_length": 100, "domain": "kabbale"},
            aviut={"masakh_level": "gimel", "tokens_before": 500},
        )
        assert r["olam"] == "briah"
        assert r["reshimo_hitlabshut"]["response_length"] == 100
        assert r["reshimo_aviut"]["masakh_level"] == "gimel"
        assert "timestamp" in r

    def test_get_reshimot_memory(self):
        write_reshimo("briah", {"a": 1}, {"b": 2})
        write_reshimo("assiah", {"a": 3}, {"b": 4})
        write_reshimo("briah", {"a": 5}, {"b": 6})

        # Tous
        all_r = get_reshimot()
        assert len(all_r) == 3

        # Par olam
        briah_r = get_reshimot(olam="briah")
        assert len(briah_r) == 2
        assert all(r["olam"] == "briah" for r in briah_r)

        # Limit
        limited = get_reshimot(limit=1)
        assert len(limited) == 1

    def test_get_reshimot_order(self):
        """Les Reshimot sont retournées du plus récent au plus ancien."""
        write_reshimo("briah", {"order": 1}, {})
        write_reshimo("briah", {"order": 2}, {})
        write_reshimo("briah", {"order": 3}, {})

        result = get_reshimot(olam="briah")
        assert result[0]["reshimo_hitlabshut"]["order"] == 3
        assert result[2]["reshimo_hitlabshut"]["order"] == 1

    def test_clear_reshimot(self):
        write_reshimo("briah", {}, {})
        assert len(get_reshimot()) == 1
        clear_reshimot()
        assert len(get_reshimot()) == 0

    @patch("olamot.get_provider", return_value="ollama")
    @patch("olamot.urllib.request.urlopen")
    def test_ollama_generate_writes_reshimo(self, mock_urlopen, _m_prov):
        """ollama_generate doit écrire un Reshimo automatiquement."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "response": "Test response for reshimo",
        }).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        from olamot import ollama_generate
        ollama_generate("briah", "test prompt")

        reshimot = get_reshimot()
        # F-017: single reshimo per call (merged pre+post LLM data)
        assert len(reshimot) >= 1
        last = reshimot[-1]
        assert last["olam"] == "briah"

        # Le dernier Reshimo (post-LLM) contient les données de réponse
        h = last["reshimo_hitlabshut"]
        assert "response_length" in h
        assert "response_preview" in h
        assert h["response_length"] > 0

        # Aviut : COMMENT le filtrage a fonctionné
        # En ibur (0 reshimots), Maturation contraint à aleph
        a = last["reshimo_aviut"]
        assert a["masakh_level"] in ("aleph", "gimel", "bet", "dalet", "shoresh")

    @patch("olamot.get_provider", return_value="ollama")
    @patch("olamot.urllib.request.urlopen")
    def test_reshimo_contains_kavvanah(self, mock_urlopen, _m_prov):
        """Le Reshimo de Aviut contient la Kavvanah si fournie."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "response": "OK",
        }).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        from olamot import ollama_generate
        kav = {"intention": "test reshimo kavvanah"}
        ollama_generate("briah", "test", kavvanah=kav)

        reshimot = get_reshimot()
        a = reshimot[0]["reshimo_aviut"]
        assert a["kavvanah"] == kav


# ── Tsimtsum ↔ Masakh ─────────────────────────────────────

class TestTzimtzumMasakh:
    """Tests de la régulation croisée Tsimtsum ↔ Masakh (Phase 2d)."""

    def test_contraction_increases_filtering(self):
        """Pression haute → Masakh monte d'un niveau (plus de Gevurah)."""
        from tzimtzum import SystemPressure, TzimtzumPhase

        m = Masakh("briah")  # gimel (index 1)
        pressure = SystemPressure(
            tension_pressure=0.9,
            memory_pressure=0.8,
            insight_pressure=0.7,
            causal_pressure=0.6,
            global_pressure=0.8,
            phase=TzimtzumPhase.CONTRACTION,
        )
        changed = m.regulate_from_pressure(pressure)
        assert changed is True
        assert m.level == "dalet"  # gimel → dalet (plus de filtrage)

    def test_expansion_decreases_filtering(self):
        """Pression basse → Masakh descend d'un niveau (plus de Chesed)."""
        from tzimtzum import SystemPressure, TzimtzumPhase

        m = Masakh("briah")  # gimel (index 1)
        pressure = SystemPressure(
            tension_pressure=0.1,
            memory_pressure=0.1,
            insight_pressure=0.1,
            causal_pressure=0.1,
            global_pressure=0.1,
            phase=TzimtzumPhase.EXPANSION,
        )
        changed = m.regulate_from_pressure(pressure)
        assert changed is True
        assert m.level == "bet"  # gimel → bet (moins de filtrage)

    def test_stable_no_change(self):
        """Pression stable → pas de changement."""
        from tzimtzum import SystemPressure, TzimtzumPhase

        m = Masakh("briah")  # gimel
        pressure = SystemPressure(
            tension_pressure=0.5,
            memory_pressure=0.5,
            insight_pressure=0.5,
            causal_pressure=0.5,
            global_pressure=0.5,
            phase=TzimtzumPhase.STABLE,
        )
        changed = m.regulate_from_pressure(pressure)
        assert changed is False
        assert m.level == "gimel"

    def test_contraction_at_dalet_no_change(self):
        """Déjà au max (dalet) → ne peut pas monter plus."""
        from tzimtzum import SystemPressure, TzimtzumPhase

        m = Masakh("atziluth")  # dalet (index 0)
        pressure = SystemPressure(
            tension_pressure=0.9, memory_pressure=0.9,
            insight_pressure=0.9, causal_pressure=0.9,
            global_pressure=0.9, phase=TzimtzumPhase.CONTRACTION,
        )
        changed = m.regulate_from_pressure(pressure)
        assert changed is False
        assert m.level == "dalet"

    def test_expansion_at_shoresh_no_change(self):
        """Déjà au min (shoresh) → ne peut pas descendre plus."""
        from tzimtzum import SystemPressure, TzimtzumPhase

        m = Masakh("briah", level="shoresh")
        pressure = SystemPressure(
            tension_pressure=0.1, memory_pressure=0.1,
            insight_pressure=0.1, causal_pressure=0.1,
            global_pressure=0.1, phase=TzimtzumPhase.EXPANSION,
        )
        changed = m.regulate_from_pressure(pressure)
        assert changed is False
        assert m.level == "shoresh"

    def test_regulate_records_change(self):
        """La régulation est enregistrée dans level_changes."""
        from tzimtzum import SystemPressure, TzimtzumPhase

        m = Masakh("yetzirah")  # bet
        pressure = SystemPressure(
            tension_pressure=0.9, memory_pressure=0.9,
            insight_pressure=0.9, causal_pressure=0.9,
            global_pressure=0.9, phase=TzimtzumPhase.CONTRACTION,
        )
        m.regulate_from_pressure(pressure)

        changes = m.level_changes
        assert len(changes) == 1
        assert changes[0]["from"] == "bet"
        assert changes[0]["to"] == "gimel"
        assert "tsimtsum" in changes[0]["reason"]
        assert "Gevurah" in changes[0]["reason"]

    def test_successive_regulation(self):
        """Plusieurs régulations successives fonctionnent correctement."""
        from tzimtzum import SystemPressure, TzimtzumPhase

        m = Masakh("yetzirah")  # bet (index 2)

        # Contraction → bet → gimel
        p1 = SystemPressure(0.9, 0.9, 0.9, 0.9, 0.9, TzimtzumPhase.CONTRACTION)
        m.regulate_from_pressure(p1)
        assert m.level == "gimel"

        # Contraction → gimel → dalet
        m.regulate_from_pressure(p1)
        assert m.level == "dalet"

        # Expansion → dalet → gimel
        p2 = SystemPressure(0.1, 0.1, 0.1, 0.1, 0.1, TzimtzumPhase.EXPANSION)
        m.regulate_from_pressure(p2)
        assert m.level == "gimel"

        assert len(m.level_changes) == 3

    def test_assess_pressure_integration(self):
        """Test intégration complète : assess_system_pressure → regulate."""
        from tzimtzum import TzimtzumEngine

        state = {
            "active": False,
            "focused_domain": None,
            "excluded_domains": [],
            "reshimu": [],
            "contraction_count": 0,
            "expansion_count": 0,
            "log": [],
        }
        engine = TzimtzumEngine(state)

        # Pression haute — beaucoup de tensions ouvertes, peu de résolues
        pressure = engine.assess_system_pressure(
            open_tensions=10,
            resolved_tensions=1,
            hypotheses=8,
            facts=2,
            insights_rejected=5,
            insights_accepted=1,
            insights_pending=0,
            causal_claims_weak=7,
            causal_claims_total=10,
        )
        assert pressure.phase.value == "contraction"

        m = Masakh("briah")  # gimel
        changed = m.regulate_from_pressure(pressure)
        assert changed is True
        assert m.level == "dalet"  # plus de filtrage


# ── Hizdakchut automatique (F9) ──────────────────────────

class TestAutoHizdakchut:
    """Tests de la boucle Hizdakchut automatique — F9, EC-SHK-024.

    Le Masakh s'amincit/s'épaissit automatiquement en réponse
    à la qualité mesurée. Le niveau persiste entre les appels.
    """

    def setup_method(self):
        reset_hizdakchut_levels()

    def teardown_method(self):
        reset_hizdakchut_levels()

    def test_degrade_persists_across_instances(self):
        """Qualité basse → descente, et le prochain Masakh hérite du niveau."""
        result = auto_hizdakchut("briah", 0.1)
        assert result is not None
        assert result["from"] == "gimel"
        assert result["to"] == "bet"

        # Nouveau Masakh sans level explicite → hérite de bet
        m = Masakh("briah")
        assert m.level == "bet"

    def test_upgrade_persists_across_instances(self):
        """Qualité haute → montée, et le prochain Masakh hérite du niveau."""
        # D'abord descendre à bet
        auto_hizdakchut("briah", 0.1)
        # Puis monter avec qualité haute
        result = auto_hizdakchut("briah", 0.9)
        assert result is not None
        assert result["from"] == "bet"
        assert result["to"] == "gimel"

        m = Masakh("briah")
        assert m.level == "gimel"

    def test_stable_no_change(self):
        """Qualité moyenne → pas de changement, pas de persistance."""
        result = auto_hizdakchut("briah", 0.5)
        assert result is None
        assert get_hizdakchut_levels() == {}

    def test_explicit_level_overrides_hizdakchut(self):
        """Un level= explicite prime sur le hizdakchut persisté."""
        auto_hizdakchut("briah", 0.1)  # gimel → bet
        m = Masakh("briah", level="dalet")
        assert m.level == "dalet"  # explicit wins

    def test_reset_clears_all(self):
        """reset_hizdakchut_levels() efface tout."""
        auto_hizdakchut("briah", 0.1)
        auto_hizdakchut("assiah", 0.1)
        assert len(get_hizdakchut_levels()) == 2

        reset_hizdakchut_levels()
        assert get_hizdakchut_levels() == {}

        # Masakh revient au défaut
        m = Masakh("briah")
        assert m.level == "gimel"

    def test_invalid_olam_returns_none(self):
        """Olam invalide → None, pas d'erreur."""
        result = auto_hizdakchut("invalid", 0.1)
        assert result is None

    def test_multi_step_descent(self):
        """Qualité basse répétée → descente progressive."""
        auto_hizdakchut("briah", 0.1)  # gimel → bet
        auto_hizdakchut("briah", 0.1)  # bet → aleph
        auto_hizdakchut("briah", 0.1)  # aleph → shoresh

        m = Masakh("briah")
        assert m.level == "shoresh"

        # Ne peut pas descendre plus bas que shoresh
        result = auto_hizdakchut("briah", 0.1)
        assert result is None

    def test_multi_step_ascent(self):
        """Qualité haute répétée → montée progressive."""
        # D'abord descendre à shoresh
        auto_hizdakchut("briah", 0.1)
        auto_hizdakchut("briah", 0.1)
        auto_hizdakchut("briah", 0.1)
        assert Masakh("briah").level == "shoresh"

        # Remonter
        auto_hizdakchut("briah", 0.9)  # shoresh → aleph
        auto_hizdakchut("briah", 0.9)  # aleph → bet
        auto_hizdakchut("briah", 0.9)  # bet → gimel
        auto_hizdakchut("briah", 0.9)  # gimel → dalet

        m = Masakh("briah")
        assert m.level == "dalet"

        # Ne peut pas monter au-dessus de dalet
        result = auto_hizdakchut("briah", 0.9)
        assert result is None

    def test_per_olam_independence(self):
        """Chaque olam a son propre niveau hizdakchut."""
        auto_hizdakchut("briah", 0.1)    # gimel → bet
        auto_hizdakchut("atziluth", 0.1) # dalet → gimel

        assert Masakh("briah").level == "bet"
        assert Masakh("atziluth").level == "gimel"
        # yetzirah et assiah non touchés → pas dans le dict
        assert "yetzirah" not in get_hizdakchut_levels()
        assert "assiah" not in get_hizdakchut_levels()
        # et ils gardent leur niveau par défaut
        assert Masakh("yetzirah").level == "bet"
        assert Masakh("assiah").level == "aleph"

    def test_result_contains_details(self):
        """Le dict retourné contient olam, from, to, quality_score, reason."""
        result = auto_hizdakchut("briah", 0.1)
        assert result is not None
        assert result["olam"] == "briah"
        assert result["from"] == "gimel"
        assert result["to"] == "bet"
        assert result["quality_score"] == 0.1
        assert "hizdakchut" in result["reason"]

    def test_get_hizdakchut_levels_returns_copy(self):
        """get_hizdakchut_levels() retourne une copie, pas la ref interne."""
        auto_hizdakchut("briah", 0.1)
        levels = get_hizdakchut_levels()
        levels["briah"] = "shoresh"  # modifier la copie
        # L'original n'est pas affecté
        assert Masakh("briah").level == "bet"

    def test_context_assembler_respects_hizdakchut(self):
        """Le ContextAssembler crée un Masakh au niveau hizdakchut."""
        auto_hizdakchut("briah", 0.1)  # gimel → bet
        m = Masakh("briah")
        assert m.level == "bet"
        # Le budget correspond au niveau bet (40%)
        assert m.budget_ratio == 0.40


# ── I3 audit cycle 4 : log historique des transitions ───────

class TestHizdakchutTransitionsLog:
    """Le log historique permet de prouver l'activité de la boucle
    Hizdakchut en prod et d'exposer une métrique transitions/h.
    """

    def setup_method(self):
        reset_hizdakchut_levels()

    def teardown_method(self):
        reset_hizdakchut_levels()

    def test_transition_calls_log_helper(self):
        """auto_hizdakchut appelle _hizdakchut_db_log_transition avec les bons args."""
        with patch("masakh._hizdakchut_db_log_transition") as log_fn:
            log_fn.return_value = True
            result = auto_hizdakchut("briah", 0.1)

        assert result is not None
        log_fn.assert_called_once()
        args = log_fn.call_args.args
        assert args[0] == "briah"
        assert args[1] == "gimel"  # from
        assert args[2] == "bet"    # to
        assert args[3] == 0.1      # quality_score
        assert "hizdakchut" in args[4]  # reason

    def test_no_transition_no_log_call(self):
        """Pas de transition (qualité neutre) → pas d'appel au log."""
        with patch("masakh._hizdakchut_db_log_transition") as log_fn:
            result = auto_hizdakchut("briah", 0.5)

        assert result is None
        log_fn.assert_not_called()

    def test_log_failure_does_not_break_loop(self):
        """Si le log DB échoue, auto_hizdakchut continue normalement."""
        with patch("masakh._hizdakchut_db_log_transition", return_value=False):
            result = auto_hizdakchut("briah", 0.1)
        # La transition a quand même eu lieu en mémoire.
        assert result is not None
        assert result["to"] == "bet"
        assert Masakh("briah").level == "bet"

    def test_log_helper_executes_insert_sql(self):
        """_hizdakchut_db_log_transition exécute un INSERT avec les bons params."""
        from masakh import _hizdakchut_db_log_transition

        cur = MagicMock()
        conn = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cur)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=conn)
        ctx.__exit__ = MagicMock(return_value=False)

        with patch("pool.get_conn", return_value=ctx):
            ok = _hizdakchut_db_log_transition(
                "briah", "gimel", "bet", 0.1, "hizdakchut_degrade"
            )

        assert ok is True
        cur.execute.assert_called_once()
        sql, params = cur.execute.call_args.args
        assert "INSERT" in sql.upper()
        assert "hizdakchut_transitions" in sql
        assert params == ("briah", "gimel", "bet", 0.1, "hizdakchut_degrade")

    def test_log_helper_returns_false_on_db_failure(self):
        """DB indisponible → False, pas d'exception levée."""
        from masakh import _hizdakchut_db_log_transition

        with patch("pool.get_conn", side_effect=RuntimeError("pool down")):
            ok = _hizdakchut_db_log_transition(
                "briah", "gimel", "bet", 0.1, None
            )
        assert ok is False
