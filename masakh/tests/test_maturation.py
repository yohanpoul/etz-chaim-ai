"""Tests de la Maturation — Ibur / Yenikah / Mochin.

Couvre :
  - assess_stage pour les 3 stades
  - Seuils de transition
  - Cas limites
  - Mode memoire (sans DB)
"""

import pytest

from masakh import clear_reshimot, _RESHIMOT_LOG
from masakh.maturation import (
    Maturation,
    IBUR, YENIKAH, MOCHIN,
    IBUR_RESHIMOT_MAX, IBUR_SCORE_MAX,
    MOCHIN_RESHIMOT_MIN, MOCHIN_SCORE_MIN, MOCHIN_TIKKUN_MIN,
)


@pytest.fixture(autouse=True)
def _clean():
    clear_reshimot()
    yield
    clear_reshimot()


class TestAssessStage:

    def test_ibur_no_data(self):
        """Sans donnees → ibur."""
        m = Maturation()
        assert m.assess_stage(reshimot_count=0, avg_score=0.0, tikkun_count=0) == IBUR

    def test_ibur_low_reshimot(self):
        """Peu de reshimot → ibur, meme si score haut."""
        m = Maturation()
        assert m.assess_stage(reshimot_count=5, avg_score=0.9, tikkun_count=10) == IBUR

    def test_ibur_low_score(self):
        """Score bas → ibur, meme si beaucoup de reshimot."""
        m = Maturation()
        assert m.assess_stage(reshimot_count=100, avg_score=0.1, tikkun_count=10) == IBUR

    def test_yenikah_middle_ground(self):
        """Entre les seuils → yenikah."""
        m = Maturation()
        assert m.assess_stage(reshimot_count=25, avg_score=0.5, tikkun_count=3) == YENIKAH

    def test_yenikah_high_score_low_tikkun(self):
        """Score haut mais pas assez de tikkun → yenikah."""
        m = Maturation()
        assert m.assess_stage(reshimot_count=60, avg_score=0.8, tikkun_count=3) == YENIKAH

    def test_mochin_all_conditions_met(self):
        """Toutes les conditions → mochin."""
        m = Maturation()
        assert m.assess_stage(reshimot_count=60, avg_score=0.8, tikkun_count=10) == MOCHIN

    def test_mochin_exact_thresholds(self):
        """Seuils exacts → mochin."""
        m = Maturation()
        assert m.assess_stage(
            reshimot_count=MOCHIN_RESHIMOT_MIN,
            avg_score=MOCHIN_SCORE_MIN,
            tikkun_count=MOCHIN_TIKKUN_MIN,
        ) == MOCHIN

    def test_ibur_exact_threshold(self):
        """Exactement au seuil ibur → yenikah (>= n'est pas <)."""
        m = Maturation()
        assert m.assess_stage(
            reshimot_count=IBUR_RESHIMOT_MAX,
            avg_score=IBUR_SCORE_MAX,
            tikkun_count=0,
        ) == YENIKAH


class TestMaturationFromMemory:

    def test_empty_memory_is_ibur(self):
        """Memoire vide → ibur."""
        m = Maturation()
        assert m.assess_stage(olam="briah") == IBUR

    def test_with_reshimot_in_memory(self):
        """Avec des reshimot en memoire, le stade change."""
        m = Maturation()
        # Ajouter 15 reshimot avec score moyen 0.5
        for i in range(15):
            _RESHIMOT_LOG.append({
                "olam": "briah",
                "reshimo_aviut": {"score": 0.5},
                "reshimo_hitlabshut": {},
            })
        assert m.assess_stage(olam="briah") == YENIKAH


class TestConstants:

    def test_ibur_reshimot_max(self):
        assert IBUR_RESHIMOT_MAX == 10

    def test_mochin_reshimot_min(self):
        assert MOCHIN_RESHIMOT_MIN == 50

    def test_ibur_score_max(self):
        assert IBUR_SCORE_MAX == 0.3

    def test_mochin_score_min(self):
        assert MOCHIN_SCORE_MIN == 0.6

    def test_mochin_tikkun_min(self):
        assert MOCHIN_TIKKUN_MIN == 5
