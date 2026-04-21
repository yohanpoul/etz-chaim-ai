"""Tests LanguageEnforcer — forcer le langage approprié.

Anti-Satariel Ruach : ne JAMAIS dire "cause" quand on a
seulement une corrélation.
"""

import pytest

from causalengine.language_enforcer import LanguageEnforcer
from causalengine.models import LanguageCorrection


@pytest.fixture
def enforcer():
    return LanguageEnforcer(strictness="strict")


@pytest.fixture
def enforcer_moderate():
    return LanguageEnforcer(strictness="moderate")


@pytest.fixture
def enforcer_permissive():
    return LanguageEnforcer(strictness="permissive")


# ── Check ──────────────────────────────────────────────

class TestCheck:
    def test_causal_verb_in_correlation_only(self, enforcer):
        corrections = enforcer.check("X causes Y", "correlation_only")
        assert len(corrections) >= 1
        assert corrections[0].original.lower() == "causes"

    def test_no_correction_for_demonstrated(self, enforcer):
        corrections = enforcer.check("X causes Y", "demonstrated_causation")
        assert len(corrections) == 0

    def test_moderate_causal_detected(self, enforcer):
        corrections = enforcer.check("X leads to Y", "correlation_only")
        assert len(corrections) >= 1

    def test_implicit_causal_detected(self, enforcer):
        corrections = enforcer.check("X improves Y", "correlation_only")
        assert len(corrections) >= 1

    def test_french_causal_detected(self, enforcer):
        corrections = enforcer.check("X provoque Y", "correlation_only")
        assert len(corrections) >= 1

    def test_french_implicit_detected(self, enforcer):
        corrections = enforcer.check("X améliore Y", "correlation_only")
        assert len(corrections) >= 1

    def test_no_causal_language_no_correction(self, enforcer):
        corrections = enforcer.check(
            "X is associated with Y", "correlation_only",
        )
        assert len(corrections) == 0

    def test_probable_causation_still_corrects_strong(self, enforcer):
        """Même probable_causation ne justifie pas 'causes'."""
        corrections = enforcer.check("X causes Y", "probable_causation")
        assert len(corrections) >= 1

    def test_probable_causation_no_correction_on_moderate(self, enforcer):
        """Probable_causation peut utiliser 'contributes to' etc."""
        # "leads to" est moderate_causal → corrigé en probable_causation
        corrections = enforcer.check("X leads to Y", "probable_causation")
        assert len(corrections) >= 1
        # Mais la correction devrait être douce
        for c in corrections:
            assert c.corrected != ""


# ── Enforce ────────────────────────────────────────────

class TestEnforce:
    def test_enforce_replaces_text(self, enforcer):
        corrected, corrections = enforcer.enforce(
            "Fasting causes better HRV", "correlation_only",
        )
        assert "causes" not in corrected.lower()
        assert "associated" in corrected.lower() or len(corrections) > 0

    def test_enforce_no_change_when_appropriate(self, enforcer):
        original = "Fasting is associated with better HRV"
        corrected, corrections = enforcer.enforce(original, "correlation_only")
        assert corrected == original
        assert len(corrections) == 0

    def test_enforce_demonstrated_no_change(self, enforcer):
        original = "Smoking causes cancer"
        corrected, corrections = enforcer.enforce(
            original, "demonstrated_causation",
        )
        assert corrected == original
        assert len(corrections) == 0

    def test_permissive_does_not_modify(self, enforcer_permissive):
        original = "X causes Y"
        corrected, corrections = enforcer_permissive.enforce(
            original, "correlation_only",
        )
        # Permissive : texte inchangé mais corrections listées
        assert corrected == original
        assert len(corrections) >= 1


# ── Appropriate language ───────────────────────────────

class TestAppropriateLanguage:
    def test_correlation_language(self, enforcer):
        lang = enforcer.appropriate_language("correlation_only")
        assert "is associated with" in lang
        assert "is correlated with" in lang

    def test_probable_language(self, enforcer):
        lang = enforcer.appropriate_language("probable_causation")
        assert "likely contributes to" in lang

    def test_demonstrated_language(self, enforcer):
        lang = enforcer.appropriate_language("demonstrated_causation")
        assert "causes" in lang
        assert "leads to" in lang

    def test_unknown_level_empty(self, enforcer):
        lang = enforcer.appropriate_language("unknown")
        assert lang == []


# ── Suggest rewrite ────────────────────────────────────

class TestSuggestRewrite:
    def test_strict_rewrite(self, enforcer):
        result = enforcer.suggest_rewrite(
            "Coffee causes alertness", "correlation_only",
        )
        assert "causes" not in result.lower()

    def test_moderate_adds_note(self, enforcer_moderate):
        result = enforcer_moderate.suggest_rewrite(
            "Coffee causes alertness", "correlation_only",
        )
        assert "[Note:" in result

    def test_no_rewrite_needed(self, enforcer):
        original = "Coffee is associated with alertness"
        result = enforcer.suggest_rewrite(original, "correlation_only")
        assert result == original


# ── Strictness validation ──────────────────────────────

class TestStrictness:
    def test_invalid_strictness_raises(self):
        with pytest.raises(ValueError, match="Invalid strictness"):
            LanguageEnforcer(strictness="ultra")

    def test_valid_strictnesses(self):
        for s in ("strict", "moderate", "permissive"):
            e = LanguageEnforcer(strictness=s)
            assert e.strictness == s


# ── Reason formatting ──────────────────────────────────

class TestReasonFormatting:
    def test_reason_contains_evidence_level(self, enforcer):
        corrections = enforcer.check("X causes Y", "correlation_only")
        assert any("correlation_only" in c.reason for c in corrections)

    def test_reason_contains_category(self, enforcer):
        corrections = enforcer.check("X causes Y", "correlation_only")
        assert any("causal" in c.reason.lower() for c in corrections)
