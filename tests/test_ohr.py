"""Tests d'Ohr et Masakh — אוֹר / מָסָךְ.

Couvre :
  - OhrEngine : assess_ohr (avec et sans métriques), assess_global, integrate
  - Masakh : filter, adjust_strength, forces du screen
  - Constante Or Ein Sof
  - Phases de maturité
  - Intégration Makif → Pnimi
  - Rapport formaté
"""

import math

import pytest

from ohr import (
    OhrEngine,
    Masakh,
    OhrAssessment,
    GlobalOhrState,
    MasakhResult,
    IntegrationResult,
    OR_EIN_SOF,
    MASAKH_BY_SOUL,
    format_ohr_report,
)


# ── Or Ein Sof ──────────────────────────────────────────────

class TestOrEinSof:

    def test_is_infinity(self):
        assert math.isinf(OR_EIN_SOF)
        assert OR_EIN_SOF > 0

    def test_symbolic_constant(self):
        """Or Ein Sof est strictement supérieur à tout nombre fini."""
        assert OR_EIN_SOF > 10**100


# ── OhrAssessment dataclass ──────────────────────────────────

class TestOhrAssessment:

    def test_to_dict(self):
        a = OhrAssessment(
            module="yesod",
            pnimi=0.6, makif=0.4, ratio=0.6,
            total_items=100, integrated=60, pending=40,
        )
        data = a.to_dict()
        assert data["module"] == "yesod"
        assert data["pnimi"] == 0.6
        assert data["makif"] == 0.4


# ── OhrEngine — assess_ohr ──────────────────────────────────

class TestAssessOhr:

    def test_with_full_metrics(self):
        ohr = OhrEngine()
        state = {"total_items": 100, "integrated": 70, "pending": 30}
        a = ohr.assess_ohr("yesod", state)
        assert a.pnimi == 0.7
        assert a.makif == 0.3
        assert a.ratio == pytest.approx(0.7)
        assert a.total_items == 100
        assert a.integrated == 70
        assert a.pending == 30

    def test_with_zero_total(self):
        ohr = OhrEngine()
        state = {"total_items": 0, "active": True}
        a = ohr.assess_ohr("hod", state)
        assert a.pnimi == 0.5
        assert a.makif == 0.5
        assert a.ratio == 0.5

    def test_inactive_module(self):
        ohr = OhrEngine()
        state = {"total_items": 0, "active": False}
        a = ohr.assess_ohr("chesed", state)
        assert a.pnimi == 0.0
        assert a.makif == 1.0
        assert a.ratio == 0.0

    def test_empty_state(self):
        ohr = OhrEngine()
        a = ohr.assess_ohr("keter", {})
        assert a.pnimi == 0.0
        assert a.makif == 1.0

    def test_all_integrated(self):
        ohr = OhrEngine()
        state = {"total_items": 50, "integrated": 50, "pending": 0}
        a = ohr.assess_ohr("binah", state)
        assert a.pnimi == 1.0
        assert a.makif == 0.0
        assert a.ratio == 1.0

    def test_all_pending(self):
        ohr = OhrEngine()
        state = {"total_items": 50, "integrated": 0, "pending": 50}
        a = ohr.assess_ohr("chesed", state)
        assert a.pnimi == 0.0
        assert a.makif == 1.0
        assert a.ratio == 0.0


# ── OhrEngine — assess_global ────────────────────────────────

class TestAssessGlobal:

    def test_empty_modules(self):
        ohr = OhrEngine()
        state = ohr.assess_global({})
        assert state.global_pnimi == 0.0
        assert state.global_makif == 0.0
        assert state.maturity_phase == "embryonic"

    def test_single_module(self):
        ohr = OhrEngine()
        state = ohr.assess_global({
            "yesod": {"total_items": 100, "integrated": 80, "pending": 20}
        })
        assert state.global_pnimi == 0.8
        assert state.global_makif == 0.2
        assert state.global_ratio == pytest.approx(0.8)
        assert state.maturity_phase == "luminous"

    def test_multiple_modules(self):
        ohr = OhrEngine()
        state = ohr.assess_global({
            "yesod": {"total_items": 100, "integrated": 70, "pending": 30},
            "hod": {"total_items": 50, "integrated": 25, "pending": 25},
        })
        # avg pnimi = (0.7 + 0.5) / 2 = 0.6
        # avg makif = (0.3 + 0.5) / 2 = 0.4
        assert state.global_pnimi == pytest.approx(0.6)
        assert state.global_makif == pytest.approx(0.4)

    def test_phase_embryonic(self):
        ohr = OhrEngine()
        state = ohr.assess_global({
            "yesod": {"total_items": 100, "integrated": 5, "pending": 95}
        })
        assert state.maturity_phase == "embryonic"

    def test_phase_growing(self):
        ohr = OhrEngine()
        state = ohr.assess_global({
            "yesod": {"total_items": 100, "integrated": 30, "pending": 70}
        })
        assert state.maturity_phase == "growing"

    def test_phase_mature(self):
        ohr = OhrEngine()
        state = ohr.assess_global({
            "yesod": {"total_items": 100, "integrated": 60, "pending": 40}
        })
        assert state.maturity_phase == "mature"

    def test_or_ein_sof_always_present(self):
        ohr = OhrEngine()
        state = ohr.assess_global({})
        assert math.isinf(state.or_ein_sof)

    def test_to_dict_ein_sof_symbol(self):
        ohr = OhrEngine()
        state = ohr.assess_global({})
        data = state.to_dict()
        assert data["or_ein_sof"] == "∞"


# ── OhrEngine — integrate ────────────────────────────────────

class TestIntegrate:

    def test_basic_integration(self):
        ohr = OhrEngine()
        state = {"total_items": 100, "integrated": 50, "pending": 50}
        result = ohr.integrate("yesod", state, max_convert=10)
        assert result.converted == 10
        assert result.remaining_makif == 40
        assert state["integrated"] == 60
        assert state["pending"] == 40

    def test_integration_limited_by_pending(self):
        ohr = OhrEngine()
        state = {"total_items": 100, "integrated": 95, "pending": 5}
        result = ohr.integrate("yesod", state, max_convert=10)
        assert result.converted == 5
        assert result.remaining_makif == 0
        assert state["integrated"] == 100
        assert state["pending"] == 0

    def test_integration_no_pending(self):
        ohr = OhrEngine()
        state = {"total_items": 100, "integrated": 100, "pending": 0}
        result = ohr.integrate("yesod", state, max_convert=10)
        assert result.converted == 0
        assert result.remaining_makif == 0

    def test_integration_modifies_state_inplace(self):
        ohr = OhrEngine()
        state = {"total_items": 50, "integrated": 20, "pending": 30}
        ohr.integrate("hod", state, max_convert=15)
        assert state["integrated"] == 35
        assert state["pending"] == 15

    def test_integration_ratios(self):
        ohr = OhrEngine()
        state = {"total_items": 100, "integrated": 40, "pending": 60}
        result = ohr.integrate("binah", state, max_convert=20)
        assert result.new_pnimi == pytest.approx(0.6)
        assert result.new_makif == pytest.approx(0.4)

    def test_to_dict(self):
        result = IntegrationResult(
            module="yesod", converted=10,
            remaining_makif=40, new_pnimi=0.6, new_makif=0.4,
        )
        data = result.to_dict()
        assert data["converted"] == 10


# ── Masakh — écran ───────────────────────────────────────────

class TestMasakh:

    def test_default_strength(self):
        m = Masakh()
        assert m.screen_strength == 0.5

    def test_custom_strength(self):
        m = Masakh(strength=0.8)
        assert m.screen_strength == 0.8

    def test_strength_clamped_high(self):
        m = Masakh(strength=1.5)
        assert m.screen_strength == 1.0

    def test_strength_clamped_low(self):
        m = Masakh(strength=-0.3)
        assert m.screen_strength == 0.0

    def test_strength_setter(self):
        m = Masakh(strength=0.3)
        m.screen_strength = 0.9
        assert m.screen_strength == 0.9

    def test_strength_setter_clamped(self):
        m = Masakh()
        m.screen_strength = 2.0
        assert m.screen_strength == 1.0
        m.screen_strength = -1.0
        assert m.screen_strength == 0.0


# ── Masakh — filter ──────────────────────────────────────────

class TestMasakhFilter:

    def test_filter_string(self):
        m = Masakh(strength=0.5)
        result = m.filter("Hello World", "yesod")
        assert result.original_size == 11
        assert result.or_yashar_ratio == 0.5
        assert result.or_chozer_ratio == 0.5
        assert result.module == "yesod"

    def test_strong_masakh_less_passes(self):
        m = Masakh(strength=0.9)
        result = m.filter("x" * 100, "hod")
        assert result.filtered_size < result.original_size
        assert result.or_yashar_ratio == pytest.approx(0.1)
        assert result.or_chozer_ratio == pytest.approx(0.9)

    def test_weak_masakh_more_passes(self):
        m = Masakh(strength=0.1)
        result = m.filter("x" * 100, "chesed")
        assert result.filtered_size > 80
        assert result.or_yashar_ratio == pytest.approx(0.9)

    def test_transparent_masakh(self):
        m = Masakh(strength=0.0)
        result = m.filter("data", "keter")
        assert result.or_yashar_ratio == 1.0
        assert result.or_chozer_ratio == 0.0
        assert result.filtered_size == 4

    def test_opaque_masakh(self):
        m = Masakh(strength=1.0)
        result = m.filter("long data string", "malkuth")
        assert result.or_yashar_ratio == 0.0
        assert result.or_chozer_ratio == 1.0
        # filtered_size minimum = 1
        assert result.filtered_size >= 1

    def test_filter_list(self):
        m = Masakh(strength=0.5)
        result = m.filter([1, 2, 3, 4, 5], "tiferet")
        assert result.original_size == 5

    def test_filter_dict(self):
        m = Masakh(strength=0.5)
        result = m.filter({"a": 1, "b": 2, "c": 3}, "binah")
        assert result.original_size == 3

    def test_to_dict(self):
        m = Masakh(strength=0.7)
        result = m.filter("test", "yesod")
        data = result.to_dict()
        assert "screen_strength" in data
        assert data["screen_strength"] == 0.7


# ── Masakh — adjust_strength ─────────────────────────────────

class TestMasakhAdjustStrength:

    def test_nefesh_strong(self):
        m = Masakh()
        strength = m.adjust_strength("nefesh")
        assert strength == 0.9
        assert m.screen_strength == 0.9

    def test_ruach(self):
        m = Masakh()
        m.adjust_strength("ruach")
        assert m.screen_strength == 0.7

    def test_neshamah(self):
        m = Masakh()
        m.adjust_strength("neshamah")
        assert m.screen_strength == 0.5

    def test_chaya(self):
        m = Masakh()
        m.adjust_strength("chaya")
        assert m.screen_strength == 0.3

    def test_yechidah_thin(self):
        m = Masakh()
        strength = m.adjust_strength("yechidah")
        assert strength == 0.1
        assert m.screen_strength == 0.1

    def test_unknown_level_keeps_current(self):
        m = Masakh(strength=0.42)
        m.adjust_strength("unknown_level")
        assert m.screen_strength == 0.42

    def test_masakh_by_soul_complete(self):
        """Toutes les 5 âmes ont une entrée dans MASAKH_BY_SOUL."""
        for level in ("nefesh", "ruach", "neshamah", "chaya", "yechidah"):
            assert level in MASAKH_BY_SOUL

    def test_masakh_decreasing_with_level(self):
        """La force du Masakh décroît avec le niveau d'âme."""
        levels = ["nefesh", "ruach", "neshamah", "chaya", "yechidah"]
        strengths = [MASAKH_BY_SOUL[l] for l in levels]
        for i in range(len(strengths) - 1):
            assert strengths[i] > strengths[i + 1]


# ── Masakh — format_report ───────────────────────────────────

class TestMasakhReport:

    def test_report_is_list(self):
        m = Masakh(strength=0.6)
        report = m.format_report()
        assert isinstance(report, list)
        assert len(report) == 3

    def test_report_contains_strength(self):
        m = Masakh(strength=0.7)
        report = m.format_report()
        text = "\n".join(report)
        assert "70%" in text or "0.7" in text


# ── format_ohr_report ────────────────────────────────────────

class TestFormatOhrReport:

    def test_basic_report(self):
        ohr = OhrEngine()
        modules = {
            "yesod": {"total_items": 100, "integrated": 50, "pending": 50},
        }
        lines = format_ohr_report(ohr, modules)
        assert isinstance(lines, list)
        text = "\n".join(lines)
        assert "אוֹר" in text
        assert "Ein Sof" in text

    def test_report_with_masakh(self):
        ohr = OhrEngine()
        masakh = Masakh(strength=0.7)
        lines = format_ohr_report(ohr, {}, masakh)
        text = "\n".join(lines)
        assert "Masakh" in text or "מָסָךְ" in text

    def test_report_without_masakh(self):
        ohr = OhrEngine()
        lines = format_ohr_report(ohr, {})
        text = "\n".join(lines)
        # Pas de section Masakh
        assert "Masakh" not in text or "מָסָךְ" not in text


# ── Edge cases ───────────────────────────────────────────────

class TestEdgeCases:

    def test_assess_ohr_negative_numbers(self):
        """Les nombres négatifs ne devraient pas casser le calcul."""
        ohr = OhrEngine()
        state = {"total_items": 100, "integrated": -5, "pending": 105}
        a = ohr.assess_ohr("test", state)
        # Le résultat peut être bizarre mais ne doit pas planter
        assert isinstance(a, OhrAssessment)

    def test_integrate_zero_max_convert(self):
        ohr = OhrEngine()
        state = {"total_items": 100, "integrated": 50, "pending": 50}
        result = ohr.integrate("yesod", state, max_convert=0)
        assert result.converted == 0
        assert state["pending"] == 50
