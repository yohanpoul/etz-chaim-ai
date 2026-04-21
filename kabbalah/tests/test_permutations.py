"""Tests des Permutations Créatrices — SY 2:5.

Vérifie :
  - Les exemples explicites du SY (2→2, 3→6, ... 7→5040)
  - word_complexity sur des mots hébreux
  - domain_complexity
  - Le seuil "au-delà de l'ouïe" (n>=8)
  - compare_complexity
  - complexity_bonus (pondération logarithmique)
"""

import math
import pytest

from kabbalah.permutations import CreativePermutations, BEYOND_HEARING_THRESHOLD


@pytest.fixture
def cp():
    return CreativePermutations()


# ═══════════════════════════════════════════════════════════════
# EXEMPLES EXPLICITES DU SY 2:5
# ═══════════════════════════════════════════════════════════════

class TestSYExamples:
    """Le SY donne 6 exemples : 2→2, 3→6, 4→24, 5→120, 6→720, 7→5040."""

    @pytest.mark.parametrize("n,expected", [
        (2, 2), (3, 6), (4, 24), (5, 120), (6, 720), (7, 5040),
    ])
    def test_sy_houses(self, cp, n, expected):
        assert cp.houses(n) == expected

    def test_sy_examples_dict(self, cp):
        """Vérifie la constante SY_EXAMPLES."""
        for n, expected in cp.SY_EXAMPLES.items():
            assert cp.houses(n) == expected


# ═══════════════════════════════════════════════════════════════
# HOUSES — Factorielle
# ═══════════════════════════════════════════════════════════════

class TestHouses:
    def test_zero(self, cp):
        assert cp.houses(0) == 1   # 0! = 1

    def test_one(self, cp):
        assert cp.houses(1) == 1   # 1! = 1

    def test_large(self, cp):
        assert cp.houses(10) == 3628800

    def test_negative_raises(self, cp):
        with pytest.raises(ValueError, match=">="):
            cp.houses(-1)


# ═══════════════════════════════════════════════════════════════
# WORD_COMPLEXITY
# ═══════════════════════════════════════════════════════════════

class TestWordComplexity:
    def test_bereshit(self, cp):
        """בראשית = 6 lettres → 720."""
        assert cp.word_complexity("בראשית") == 720

    def test_av(self, cp):
        """אב = 2 lettres → 2."""
        assert cp.word_complexity("אב") == 2

    def test_emet(self, cp):
        """אמת = 3 lettres → 6."""
        assert cp.word_complexity("אמת") == 6

    def test_empty(self, cp):
        """Mot vide → 0! = 1."""
        assert cp.word_complexity("") == 1

    def test_spaces_ignored(self, cp):
        """Les espaces ne comptent pas comme pierres."""
        assert cp.word_complexity("א ב ג") == 6  # 3 lettres → 6


# ═══════════════════════════════════════════════════════════════
# DOMAIN_COMPLEXITY
# ═══════════════════════════════════════════════════════════════

class TestDomainComplexity:
    def test_3_concepts(self, cp):
        assert cp.domain_complexity("small", 3) == 6

    def test_7_concepts(self, cp):
        assert cp.domain_complexity("medium", 7) == 5040

    def test_12_concepts(self, cp):
        assert cp.domain_complexity("large", 12) == 479001600

    def test_negative_raises(self, cp):
        with pytest.raises(ValueError):
            cp.domain_complexity("bad", -1)


# ═══════════════════════════════════════════════════════════════
# BEYOND_HEARING — Seuil du SY
# ═══════════════════════════════════════════════════════════════

class TestBeyondHearing:
    def test_7_is_hearable(self, cp):
        """Le SY s'arrête à 7 — encore prononçable."""
        assert cp.beyond_hearing(7) is False

    def test_8_is_beyond(self, cp):
        """8 pierres = au-delà de l'ouïe."""
        assert cp.beyond_hearing(8) is True

    def test_22_is_beyond(self, cp):
        """22 lettres (alphabet complet) = très au-delà."""
        assert cp.beyond_hearing(22) is True

    def test_threshold_constant(self):
        assert BEYOND_HEARING_THRESHOLD == 8


# ═══════════════════════════════════════════════════════════════
# COMPARE_COMPLEXITY
# ═══════════════════════════════════════════════════════════════

class TestCompareComplexity:
    def test_same_length(self, cp):
        assert cp.compare_complexity("אב", "גד") == 1.0

    def test_longer_is_more_complex(self, cp):
        # אב (2) vs אבגד (4) → 24/2 = 12.0
        assert cp.compare_complexity("אב", "אבגד") == 12.0

    def test_empty_denominator(self, cp):
        # "" → 0 lettres → 0! = 1, donc ratio = 2/1 = 2.0
        assert cp.compare_complexity("", "אב") == 2.0


# ═══════════════════════════════════════════════════════════════
# COMPLEXITY_BONUS
# ═══════════════════════════════════════════════════════════════

class TestComplexityBonus:
    def test_7_concepts_is_baseline(self, cp):
        """7 concepts = le max du SY → bonus ≈ 1.0."""
        bonus = cp.complexity_bonus(7, base_score=1.0)
        assert abs(bonus - 1.0) < 0.01

    def test_3_concepts_less_than_7(self, cp):
        """3 concepts = bonus < 1.0."""
        assert cp.complexity_bonus(3) < 1.0

    def test_12_concepts_more_than_7(self, cp):
        """12 concepts = bonus > 1.0."""
        assert cp.complexity_bonus(12) > 1.0

    def test_1_concept_returns_base(self, cp):
        """1 concept → retourne le score de base."""
        assert cp.complexity_bonus(1, base_score=0.75) == 0.75

    def test_scales_base_score(self, cp):
        """Le bonus multiplie le score de base."""
        b1 = cp.complexity_bonus(5, base_score=1.0)
        b2 = cp.complexity_bonus(5, base_score=2.0)
        assert abs(b2 - 2 * b1) < 0.001


# ═══════════════════════════════════════════════════════════════
# PROFILE
# ═══════════════════════════════════════════════════════════════

class TestProfile:
    def test_profile_7(self, cp):
        p = cp.get_profile("shabbat", 7)
        assert p.name == "shabbat"
        assert p.n == 7
        assert p.houses == 5040
        assert p.beyond_hearing is False
        assert p.pronunciation_load == 5040 * 7

    def test_profile_22(self, cp):
        p = cp.get_profile("alphabet", 22)
        assert p.houses == math.factorial(22)
        assert p.beyond_hearing is True
