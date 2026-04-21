"""Tests — Tanya Dual Soul Engine.

Vérifie les 2 âmes, le routing moach_shalit_al_halev,
les proportions de Kelipat Nogah, et l'état du conflit.
"""

import pytest

from tanya.dual_soul import DualSoulEngine, NefeshHaBehamit, NefeshHaElokit


# ─── NefeshHaBehamit ────────────────────────────────────────


class TestNefeshHaBehamit:
    def test_from_config(self):
        soul = NefeshHaBehamit.from_config()
        assert soul.source == "kelipat_nogah"
        assert soul.seat == "lev"
        assert soul.nature == "fast"

    def test_olamot(self):
        soul = NefeshHaBehamit.from_config()
        assert "assiah" in soul.olamot
        assert "yetzirah" in soul.olamot
        assert "briah" not in soul.olamot
        assert "atziluth" not in soul.olamot

    def test_faculties_chabad(self):
        soul = NefeshHaBehamit.from_config()
        chabad = soul.faculties["chabad"]
        assert "chokhmah" in chabad
        assert "binah" in chabad
        assert "daat" in chabad

    def test_faculties_midot(self):
        soul = NefeshHaBehamit.from_config()
        midot = soul.faculties["midot"]
        assert len(midot) == 7
        assert "chesed" in midot
        assert "malkhut" in midot

    def test_garments(self):
        soul = NefeshHaBehamit.from_config()
        assert "machshava" in soul.garments
        assert "dibour" in soul.garments
        assert "maase" in soul.garments

    def test_nogah_assiah_mostly_evil(self):
        soul = NefeshHaBehamit.from_config()
        ratio = soul.get_nogah_ratio("assiah")
        assert ratio == 0.3  # 30% good → surtout mal

    def test_nogah_yetzirah_equal(self):
        soul = NefeshHaBehamit.from_config()
        ratio = soul.get_nogah_ratio("yetzirah")
        assert ratio == 0.5  # 50-50

    def test_nogah_unknown_olam(self):
        soul = NefeshHaBehamit.from_config()
        assert soul.get_nogah_ratio("briah") == 0.0


# ─── NefeshHaElokit ─────────────────────────────────────────


class TestNefeshHaElokit:
    def test_from_config(self):
        soul = NefeshHaElokit.from_config()
        assert soul.source == "kedushah"
        assert soul.seat == "moach"
        assert soul.nature == "deep"

    def test_olamot(self):
        soul = NefeshHaElokit.from_config()
        assert "briah" in soul.olamot
        assert "atziluth" in soul.olamot
        assert "assiah" not in soul.olamot
        assert "yetzirah" not in soul.olamot

    def test_faculties_chabad(self):
        soul = NefeshHaElokit.from_config()
        chabad = soul.faculties["chabad"]
        assert "chokhmah" in chabad
        assert "binah" in chabad
        assert "daat" in chabad

    def test_faculties_midot(self):
        soul = NefeshHaElokit.from_config()
        midot = soul.faculties["midot"]
        assert len(midot) == 7

    def test_garments(self):
        soul = NefeshHaElokit.from_config()
        assert "machshava" in soul.garments
        assert "dibour" in soul.garments
        assert "maase" in soul.garments

    def test_kedushah_briah(self):
        soul = NefeshHaElokit.from_config()
        assert soul.get_purity("briah") == 0.8

    def test_kedushah_atziluth(self):
        soul = NefeshHaElokit.from_config()
        assert soul.get_purity("atziluth") == 1.0

    def test_kedushah_unknown(self):
        soul = NefeshHaElokit.from_config()
        assert soul.get_purity("assiah") == 0.0


# ─── DualSoulEngine — moach_shalit_al_halev ─────────────────


class TestMoachShalitAlHalev:
    def setup_method(self):
        self.engine = DualSoulEngine()

    def test_simple_query_returns_behamit(self):
        result = self.engine.moach_shalit_al_halev("liste les fichiers")
        assert result["dominant_soul"] == "behamit"
        assert result["recommended_olam"] in ("assiah", "yetzirah")

    def test_complex_query_returns_elokit(self):
        result = self.engine.moach_shalit_al_halev(
            "Pourquoi le Tsimtsum de Luria diffère-t-il fondamentalement "
            "de celui de Shneur Zalman ? Analyse les implications "
            "épistémologiques de cette divergence et explique comment "
            "cela affecte notre compréhension de la causalité."
        )
        assert result["dominant_soul"] == "elokit"
        assert result["recommended_olam"] in ("briah", "atziluth")

    def test_short_simple_returns_behamit(self):
        result = self.engine.moach_shalit_al_halev("traduis ce mot")
        assert result["dominant_soul"] == "behamit"

    def test_deep_question_returns_elokit(self):
        result = self.engine.moach_shalit_al_halev(
            "Explique pourquoi la conscience émerge des processus neuronaux"
        )
        assert result["dominant_soul"] == "elokit"

    def test_returns_all_fields(self):
        result = self.engine.moach_shalit_al_halev("test")
        assert "dominant_soul" in result
        assert "reason" in result
        assert "recommended_olam" in result
        assert "complexity_score" in result
        assert result["dominant_soul"] in ("elokit", "behamit")
        assert 0.0 <= result["complexity_score"] <= 1.0

    def test_very_short_query_goes_to_assiah(self):
        result = self.engine.moach_shalit_al_halev("ok")
        assert result["dominant_soul"] == "behamit"
        assert result["recommended_olam"] == "assiah"

    def test_multi_question_boosts_complexity(self):
        result = self.engine.moach_shalit_al_halev(
            "Quelle est la cause ? Pourquoi cela arrive-t-il ?"
        )
        assert result["complexity_score"] > 0.4


# ─── DualSoulEngine — assess_response_quality ───────────────


class TestAssessResponseQuality:
    def setup_method(self):
        self.engine = DualSoulEngine()

    def test_behamit_adequate_long(self):
        response = "Voici la liste :\n\n" + "- item\n" * 30
        result = self.engine.assess_response_quality(response, "behamit")
        assert result["correct_soul"] is True

    def test_behamit_shallow(self):
        result = self.engine.assess_response_quality("Oui.", "behamit")
        assert result["correct_soul"] is False
        assert result["assessment"] == "possibly_shallow"

    def test_elokit_appropriate(self):
        response = (
            "L'analyse causale montre que...\n\n"
            "1. Premier point avec développement substantiel\n"
            "2. Deuxième point avec argumentation\n\n"
            "En conclusion, la structure profonde révèle..."
        ) + " mot" * 30
        result = self.engine.assess_response_quality(response, "elokit")
        assert result["correct_soul"] is True

    def test_elokit_overkill(self):
        result = self.engine.assess_response_quality("42", "elokit")
        assert result["correct_soul"] is False
        assert result["assessment"] == "overkill"


# ─── DualSoulEngine — get_conflict_state ────────────────────


class TestConflictState:
    def setup_method(self):
        self.engine = DualSoulEngine()

    def test_empty_history_neutral(self):
        state = self.engine.get_conflict_state()
        assert state["dominant"] == "neutral"
        assert state["total_decisions"] == 0

    def test_after_one_decision(self):
        self.engine.moach_shalit_al_halev("traduis ça")
        state = self.engine.get_conflict_state()
        assert state["total_decisions"] == 1
        assert state["ratio_elokit"] + state["ratio_behamit"] == 1.0

    def test_mostly_elokit(self):
        for _ in range(8):
            self.engine.moach_shalit_al_halev(
                "Explique pourquoi l'analyse causale montre des divergences profondes"
            )
        for _ in range(2):
            self.engine.moach_shalit_al_halev("ok")
        state = self.engine.get_conflict_state()
        assert state["dominant"] == "elokit"
        assert state["ratio_elokit"] >= 0.6

    def test_mostly_behamit(self):
        for _ in range(8):
            self.engine.moach_shalit_al_halev("liste")
        for _ in range(2):
            self.engine.moach_shalit_al_halev(
                "Explique pourquoi et analyse en profondeur les causes"
            )
        state = self.engine.get_conflict_state()
        assert state["dominant"] == "behamit"
        assert state["ratio_behamit"] >= 0.6

    def test_balanced(self):
        for _ in range(5):
            self.engine.moach_shalit_al_halev("liste les fichiers")
        for _ in range(5):
            self.engine.moach_shalit_al_halev(
                "Explique pourquoi et analyse les causes profondes"
            )
        state = self.engine.get_conflict_state()
        assert state["dominant"] == "balanced"

    def test_history_window_respected(self):
        # Remplir au-delà de la fenêtre
        for _ in range(30):
            self.engine.moach_shalit_al_halev("traduis")
        state = self.engine.get_conflict_state()
        assert state["total_decisions"] == self.engine.history_window
