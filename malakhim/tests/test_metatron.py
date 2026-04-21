"""Tests Metatron — médiateur vertical adaptatif + juridiction."""

import pytest

from malakhim.metatron import (
    adapt_to_olam,
    translate_across_worlds,
    jurisdictional_check,
    LevushAdaptation,
)


class TestLevushAdaptation:
    """Levush — la même intention revêtue différemment par monde."""

    def test_atziluth_emphasis_vision(self):
        result = adapt_to_olam("analyse ce code", "base prompt", "atziluth")
        assert isinstance(result, LevushAdaptation)
        assert "vision" in result.emphasis
        assert "INTENTION" in result.adapted_system_prompt
        assert result.olam == "atziluth"

    def test_briah_emphasis_architecture(self):
        result = adapt_to_olam("analyse ce code", "base prompt", "briah")
        assert "architecture" in result.emphasis.lower()
        assert "ARCHITECTURE" in result.adapted_system_prompt

    def test_yetzirah_emphasis_execution(self):
        result = adapt_to_olam("analyse ce code", "base prompt", "yetzirah")
        assert "plan" in result.emphasis.lower() or "étapes" in result.emphasis.lower()

    def test_assiah_emphasis_implementation(self):
        result = adapt_to_olam("analyse ce code", "base prompt", "assiah")
        assert "implémentation" in result.emphasis.lower() or "exécution" in result.emphasis.lower()

    def test_prompt_unchanged(self):
        """Le prompt reste invariant — c'est le cadre qui change."""
        original = "ma requête spécifique"
        result = adapt_to_olam(original, "system", "briah")
        assert result.adapted_prompt == original

    def test_system_prompt_enriched(self):
        """Le system prompt est enrichi avec le cadre du monde."""
        result = adapt_to_olam("test", "base system", "yetzirah")
        assert "base system" in result.adapted_system_prompt
        assert "YETZIRAH" in result.adapted_system_prompt

    def test_different_worlds_different_prompts(self):
        """Chaque monde produit un system prompt différent."""
        results = {
            olam: adapt_to_olam("même requête", "même base", olam)
            for olam in ["atziluth", "briah", "yetzirah", "assiah"]
        }
        prompts = [r.adapted_system_prompt for r in results.values()]
        assert len(set(prompts)) == 4  # 4 prompts uniques


class TestTranslateAcrossWorlds:
    """Metatron traduit d'un monde à un autre."""

    def test_briah_to_assiah(self):
        result = translate_across_worlds(
            "analyse stratégique", "system", "briah", "assiah",
        )
        assert result.olam == "assiah"
        assert "EXÉCUTION" in result.adapted_system_prompt


class TestJurisdictionalCheck:
    """Échelle de Jacob — juridiction territorialement limitée."""

    def test_in_jurisdiction(self):
        allowed, reason = jurisdictional_check(["code", "security"], "code")
        assert allowed is True

    def test_out_of_jurisdiction(self):
        allowed, reason = jurisdictional_check(["code", "security"], "poetry")
        assert allowed is False
        assert "HORS juridiction" in reason

    def test_general_agent_always_allowed(self):
        allowed, _ = jurisdictional_check(["general"], "anything")
        assert allowed is True

    def test_no_domains_universal(self):
        """Agent sans domaine → Ishim, juridiction universelle."""
        allowed, reason = jurisdictional_check([], "anything")
        assert allowed is True
        assert "Ishim" in reason
