"""Tests ange incomplet — matière sans forme (Tanya ch. 39)."""

from malakhim.samael import detect_incomplete_angel
from malakhim.models import MalakhResult


class TestIncompleteAngel:
    """Ni succès ni échec — entité difforme qui pollue le système."""

    def test_good_response_not_incomplete(self):
        """Score élevé → pas incomplet."""
        assert detect_incomplete_angel("Réponse solide et spécifique.", "analytic", 0.8) is False

    def test_bad_response_not_incomplete(self):
        """Score très bas → c'est un échec (Kategor), pas un incomplet."""
        assert detect_incomplete_angel("", "analytic", 0.1) is False

    def test_generic_response_is_incomplete(self):
        """Réponse générique avec score moyen → ange incomplet."""
        generic = (
            "Il est important de noter que dans l'ensemble, "
            "il convient de considérer que cela dépend de "
            "plusieurs facteurs. En général, il faut considérer "
            "les différentes approches possibles."
        )
        assert detect_incomplete_angel(generic, "strategic", 0.45) is True

    def test_specific_response_not_incomplete(self):
        """Réponse spécifique avec score moyen → pas incomplet."""
        specific = (
            "Je recommande l'option B parce que le coût est 30% "
            "inférieur et spécifiquement adaptée à notre contrainte "
            "de latence sous 100ms. Concrètement, implémenter le "
            "cache Redis avec TTL de 5 minutes."
        )
        assert detect_incomplete_angel(specific, "strategic", 0.5) is False

    def test_malakh_result_incomplete_flag(self):
        """Le flag incomplete existe sur MalakhResult."""
        result = MalakhResult(response="test", success=True)
        assert result.incomplete is False
        result.incomplete = True
        assert result.incomplete is True
