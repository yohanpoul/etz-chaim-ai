"""Tests — OmerDailyInfluence: modulateur quotidien de l'Arbre."""

from datetime import date

import pytest

from omer.daily_influence import (
    MIDOT_ORDER,
    SEFIRAH_TO_MODULE,
    OmerDailyInfluence,
    OmerInfluence,
    get_omer_day,
    _day_to_grid,
    _apply_delta,
)


@pytest.fixture
def odi():
    return OmerDailyInfluence()


# ── get_omer_day ───────────────────────────────────────────

class TestGetOmerDay:
    def test_day_1(self):
        assert get_omer_day(date(2026, 4, 2)) == 1

    def test_day_49(self):
        assert get_omer_day(date(2026, 5, 20)) == 49

    def test_day_25(self):
        assert get_omer_day(date(2026, 4, 26)) == 25

    def test_before_omer(self):
        assert get_omer_day(date(2026, 4, 1)) is None

    def test_after_omer(self):
        assert get_omer_day(date(2026, 5, 21)) is None

    def test_unknown_year(self):
        assert get_omer_day(date(2099, 4, 15)) is None

    def test_all_49_days_valid(self):
        """Each of the 49 days from start date returns the correct day number."""
        start = date(2026, 4, 2)
        for d in range(49):
            today = date.fromordinal(start.toordinal() + d)
            assert get_omer_day(today) == d + 1


# ── Grid mapping ──────────────────────────────────────────

class TestDayToGrid:
    def test_day_1(self):
        week, diw, primary, secondary = _day_to_grid(1)
        assert (week, diw) == (1, 1)
        assert primary == "chesed"
        assert secondary == "chesed"

    def test_day_2(self):
        week, diw, primary, secondary = _day_to_grid(2)
        assert (week, diw) == (1, 2)
        assert primary == "chesed"
        assert secondary == "gevurah"

    def test_day_8(self):
        """Semaine 2 = Gevurah, jour 1 = Chesed."""
        week, diw, primary, secondary = _day_to_grid(8)
        assert (week, diw) == (2, 1)
        assert primary == "gevurah"
        assert secondary == "chesed"

    def test_day_49(self):
        week, diw, primary, secondary = _day_to_grid(49)
        assert (week, diw) == (7, 7)
        assert primary == "malkuth"
        assert secondary == "malkuth"

    def test_day_17(self):
        """Jour 17 = Tiferet sh'b'Tiferet."""
        week, diw, primary, secondary = _day_to_grid(17)
        assert primary == "tiferet"
        assert secondary == "tiferet"

    def test_all_49_have_valid_sefirot(self):
        for day in range(1, 50):
            week, diw, primary, secondary = _day_to_grid(day)
            assert primary in MIDOT_ORDER
            assert secondary in MIDOT_ORDER
            assert 1 <= week <= 7
            assert 1 <= diw <= 7


# ── OmerInfluence ─────────────────────────────────────────

class TestGetInfluence:
    def test_all_49_days_produce_influence(self, odi):
        for day in range(1, 50):
            inf = odi.get_influence(day)
            assert isinstance(inf, OmerInfluence)
            assert inf.day == day
            assert inf.primary_sefirah in MIDOT_ORDER
            assert inf.secondary_sefirah in MIDOT_ORDER
            assert inf.combination
            assert inf.combination_hebrew
            assert inf.kavvanah
            assert inf.module_boosts

    def test_day_out_of_range(self, odi):
        with pytest.raises(ValueError):
            odi.get_influence(0)
        with pytest.raises(ValueError):
            odi.get_influence(50)

    def test_combination_format(self, odi):
        inf = odi.get_influence(8)
        assert inf.combination == "chesed_sheb_gevurah"

    def test_same_sefirah_amplified(self, odi):
        """Tiferet sh'b'Tiferet (day 17) should have amplified boosts."""
        inf_same = odi.get_influence(17)  # tiferet sh'b tiferet
        inf_diff = odi.get_influence(15)  # chesed sh'b tiferet

        tiferet_module = SEFIRAH_TO_MODULE["tiferet"]

        # Same-sefirah day should have stronger boosts on the primary module
        same_boosts = inf_same.module_boosts.get(tiferet_module, {})
        diff_boosts = inf_diff.module_boosts.get(tiferet_module, {})

        # At least one param should be amplified
        for param in same_boosts:
            if param in diff_boosts:
                assert abs(same_boosts[param]) >= abs(diff_boosts[param])


# ── Boost coherence ───────────────────────────────────────

class TestBoostCoherence:
    def test_gevurah_boosts_autojudge(self, odi):
        """During Gevurah week, AutoJudge gets boosted."""
        inf = odi.get_influence(9)  # gevurah sh'b gevurah
        assert "autojudge" in inf.module_boosts
        boosts = inf.module_boosts["autojudge"]
        assert "quality_threshold" in boosts
        assert boosts["quality_threshold"] > 0  # more strict

    def test_chesed_boosts_exploration(self, odi):
        """During Chesed week, ExplorationEngine gets boosted."""
        inf = odi.get_influence(1)  # chesed sh'b chesed
        assert "explorationengine" in inf.module_boosts
        boosts = inf.module_boosts["explorationengine"]
        assert "explore_breadth" in boosts
        assert boosts["explore_breadth"] > 0  # more exploration

    def test_tiferet_boosts_dissensu(self, odi):
        inf = odi.get_influence(17)  # tiferet sh'b tiferet
        assert "dissensuengine" in inf.module_boosts

    def test_netzach_boosts_intentkeeper(self, odi):
        inf = odi.get_influence(25)  # netzach sh'b netzach
        assert "intentkeeper" in inf.module_boosts

    def test_hod_boosts_selfmap(self, odi):
        inf = odi.get_influence(33)  # hod sh'b hod
        assert "selfmap" in inf.module_boosts

    def test_yesod_boosts_epistememory(self, odi):
        inf = odi.get_influence(41)  # yesod sh'b yesod
        assert "epistememory" in inf.module_boosts

    def test_malkuth_boosts_failuretoinsight(self, odi):
        inf = odi.get_influence(49)  # malkuth sh'b malkuth
        assert "failuretoinsight" in inf.module_boosts

    def test_cross_module_boost(self, odi):
        """Day 8 = Chesed sh'b Gevurah: both autojudge and explorationengine."""
        inf = odi.get_influence(8)
        assert "autojudge" in inf.module_boosts      # primary = gevurah
        assert "explorationengine" in inf.module_boosts  # secondary = chesed


# ── apply_to_modules ──────────────────────────────────────

class TestApplyToModules:
    def test_modifies_attributes(self, odi):
        """apply_to_modules should change module attributes."""

        class FakeAutoJudge:
            quality_threshold = 0.6
            quarantine_threshold = 0.4

        class FakeExploration:
            explore_breadth = 10
            novelty_threshold = 0.3

        tree = {
            "gevurah": FakeAutoJudge(),
            "chesed": FakeExploration(),
        }

        inf = odi.get_influence(9)  # gevurah sh'b gevurah
        changes = odi.apply_to_modules(tree, inf)

        assert "gevurah" in changes
        # quality_threshold should have increased
        assert tree["gevurah"].quality_threshold > 0.6

    def test_missing_module_skipped(self, odi):
        """Modules not in tree are silently skipped."""
        tree = {}  # empty tree
        inf = odi.get_influence(1)
        changes = odi.apply_to_modules(tree, inf)
        assert changes == {}

    def test_missing_attribute_skipped(self, odi):
        """Attributes not on the module are skipped."""

        class Bare:
            pass

        tree = {"gevurah": Bare()}
        inf = odi.get_influence(9)
        changes = odi.apply_to_modules(tree, inf)
        assert "gevurah" not in changes  # no attributes to modify

    def test_float_clamped_0_1(self, odi):
        """Float thresholds stay in [0, 1]."""

        class Edge:
            quality_threshold = 0.98
            quarantine_threshold = 0.99

        tree = {"gevurah": Edge()}
        inf = odi.get_influence(9)
        odi.apply_to_modules(tree, inf)
        assert tree["gevurah"].quality_threshold <= 1.0
        assert tree["gevurah"].quarantine_threshold <= 1.0

    def test_int_stays_positive(self, odi):
        """Int values never go below 1."""

        class Small:
            explore_breadth = 1
            novelty_threshold = 0.05

        tree = {"chesed": Small()}
        inf = odi.get_influence(1)
        odi.apply_to_modules(tree, inf)
        assert tree["chesed"].explore_breadth >= 1


# ── _apply_delta ──────────────────────────────────────────

class TestApplyDelta:
    def test_float_positive(self):
        assert _apply_delta(0.5, 0.1) == 0.6

    def test_float_negative(self):
        assert _apply_delta(0.5, -0.1) == 0.4

    def test_float_clamp_high(self):
        assert _apply_delta(0.95, 0.1) == 1.0

    def test_float_clamp_low(self):
        assert _apply_delta(0.05, -0.1) == 0.0

    def test_int_positive(self):
        result = _apply_delta(10, 0.15)
        assert isinstance(result, int)
        assert result > 10

    def test_int_negative(self):
        result = _apply_delta(10, -0.15)
        assert isinstance(result, int)
        assert result < 10

    def test_int_min_1(self):
        result = _apply_delta(1, -0.5)
        assert result >= 1


# ── get_meditation ────────────────────────────────────────

class TestGetMeditation:
    def test_all_49_days_have_meditation(self, odi):
        for day in range(1, 50):
            med = odi.get_meditation(day)
            assert f"Jour {day}/49" in med
            assert "שב" in med

    def test_day_8_gevurah_week(self, odi):
        med = odi.get_meditation(8)
        assert "גבורה" in med  # primary = gevurah
        assert "חסד" in med    # secondary = chesed (day 1 of week 2)


# ── get_today_influence ───────────────────────────────────

class TestGetTodayInfluence:
    def test_during_omer(self, odi):
        inf = odi.get_today_influence(today=date(2026, 4, 2))
        assert inf is not None
        assert inf.day == 1

    def test_outside_omer(self, odi):
        inf = odi.get_today_influence(today=date(2026, 1, 15))
        assert inf is None
