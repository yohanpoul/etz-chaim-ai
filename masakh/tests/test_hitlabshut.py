"""Tests Hitlabshut — הִתְלַבְּשׁוּת — enclothement contextuel.

Couvre :
  - enclothe produit un résultat cohérent
  - L'instruction et le principe sont tous deux dans le résultat
  - Principe ou instruction vide → ValueError
  - enclothe_many avec 0, 1, N principes
  - Whitespace trimming
"""

import pytest

from masakh.hitlabshut import Hitlabshut


@pytest.fixture
def hitlabshut():
    return Hitlabshut()


PRINCIPLE = "Rigueur : chaque concept doit être fonctionnellement opérant"
INSTRUCTION = "Implémente la fonction de filtrage"


# ── enclothe basique ──────────────────────────────────────

class TestEnclothe:

    def test_result_contains_instruction(self, hitlabshut):
        result = hitlabshut.enclothe(PRINCIPLE, INSTRUCTION)
        assert INSTRUCTION in result

    def test_result_contains_principle(self, hitlabshut):
        result = hitlabshut.enclothe(PRINCIPLE, INSTRUCTION)
        assert PRINCIPLE in result

    def test_instruction_comes_first(self, hitlabshut):
        result = hitlabshut.enclothe(PRINCIPLE, INSTRUCTION)
        assert result.index(INSTRUCTION) < result.index(PRINCIPLE)

    def test_separator_present(self, hitlabshut):
        result = hitlabshut.enclothe(PRINCIPLE, INSTRUCTION)
        assert "en appliquant le principe" in result

    def test_expected_format(self, hitlabshut):
        result = hitlabshut.enclothe(PRINCIPLE, INSTRUCTION)
        expected = f"{INSTRUCTION} — en appliquant le principe : {PRINCIPLE}"
        assert result == expected


# ── Cas limites ───────────────────────────────────────────

class TestEdgeCases:

    def test_empty_principle_raises(self, hitlabshut):
        with pytest.raises(ValueError, match="principe"):
            hitlabshut.enclothe("", INSTRUCTION)

    def test_whitespace_principle_raises(self, hitlabshut):
        with pytest.raises(ValueError, match="principe"):
            hitlabshut.enclothe("   ", INSTRUCTION)

    def test_empty_instruction_raises(self, hitlabshut):
        with pytest.raises(ValueError, match="instruction"):
            hitlabshut.enclothe(PRINCIPLE, "")

    def test_whitespace_instruction_raises(self, hitlabshut):
        with pytest.raises(ValueError, match="instruction"):
            hitlabshut.enclothe(PRINCIPLE, "  \t  ")

    def test_strips_whitespace(self, hitlabshut):
        result = hitlabshut.enclothe("  principe  ", "  instruction  ")
        assert result == "instruction — en appliquant le principe : principe"

    def test_none_principle_raises(self, hitlabshut):
        with pytest.raises((ValueError, TypeError)):
            hitlabshut.enclothe(None, INSTRUCTION)

    def test_none_instruction_raises(self, hitlabshut):
        with pytest.raises((ValueError, TypeError)):
            hitlabshut.enclothe(PRINCIPLE, None)


# ── enclothe_many ─────────────────────────────────────────

class TestEnclotheMany:

    def test_zero_principles_returns_instruction(self, hitlabshut):
        result = hitlabshut.enclothe_many([], INSTRUCTION)
        assert result == INSTRUCTION

    def test_one_principle_block_format(self, hitlabshut):
        result = hitlabshut.enclothe_many([PRINCIPLE], INSTRUCTION)
        assert INSTRUCTION in result
        assert "[PRINCIPES DIRECTEURS]" in result
        assert f"- {PRINCIPLE}" in result

    def test_two_principles_separated(self, hitlabshut):
        p1 = "Rigueur"
        p2 = "Profondeur"
        result = hitlabshut.enclothe_many([p1, p2], INSTRUCTION)
        assert f"- {p1}" in result
        assert f"- {p2}" in result
        assert INSTRUCTION in result
        assert "[PRINCIPES DIRECTEURS]" in result

    def test_many_principles_all_present(self, hitlabshut):
        principles = ["A", "B", "C", "D"]
        result = hitlabshut.enclothe_many(principles, "do X")
        for p in principles:
            assert f"- {p}" in result
        assert "do X" in result

    def test_many_principles_order(self, hitlabshut):
        """Les principes apparaissent dans l'ordre donné."""
        result = hitlabshut.enclothe_many(["first", "second"], "task")
        assert result.index("- first") < result.index("- second")
