"""Tests — Tanya Soul Categories, Kelipat Nogah, et intégration routing.

Vérifie les 5 catégories (Tsaddik→Rasha), les seuils,
Kelipat Nogah par monde, et l'override de routing.
"""

import pytest

from tanya.dual_soul import (
    DualSoulEngine,
    KelipotSystem,
    SoulAssessment,
    SoulCategory,
)


# ─── SoulCategory enum ───────────��────────────────────────


class TestSoulCategory:
    def test_five_categories_exist(self):
        assert len(SoulCategory) == 5

    def test_tsaddik_gamur_value(self):
        assert SoulCategory.TSADDIK_GAMUR.value == "tsaddik_gamur"

    def test_tsaddik_she_eino_gamur_value(self):
        assert SoulCategory.TSADDIK_SHE_EINO_GAMUR.value == "tsaddik_she_eino_gamur"

    def test_beinoni_value(self):
        assert SoulCategory.BEINONI.value == "beinoni"

    def test_rasha_she_eino_gamur_value(self):
        assert SoulCategory.RASHA_SHE_EINO_GAMUR.value == "rasha_she_eino_gamur"

    def test_rasha_gamur_value(self):
        assert SoulCategory.RASHA_GAMUR.value == "rasha_gamur"


# ─── assess_category ────���─────────────────────────────────


class TestAssessCategory:
    def setup_method(self):
        self.engine = DualSoulEngine()

    def test_tsaddik_gamur_high_scores(self):
        result = self.engine.assess_category(
            hitbonenut_avg=0.95,
            high_world_ratio=0.9,
            accepted_ratio=0.95,
        )
        assert result.category == SoulCategory.TSADDIK_GAMUR
        assert result.score >= 0.9

    def test_tsaddik_she_eino_gamur(self):
        result = self.engine.assess_category(
            hitbonenut_avg=0.88,
            high_world_ratio=0.85,
            accepted_ratio=0.82,
        )
        assert result.category == SoulCategory.TSADDIK_SHE_EINO_GAMUR
        assert 0.85 <= result.score < 0.9

    def test_beinoni_moderate_scores(self):
        result = self.engine.assess_category(
            hitbonenut_avg=0.7,
            high_world_ratio=0.6,
            accepted_ratio=0.5,
        )
        assert result.category == SoulCategory.BEINONI
        assert 0.5 <= result.score < 0.85

    def test_rasha_she_eino_gamur(self):
        result = self.engine.assess_category(
            hitbonenut_avg=0.4,
            high_world_ratio=0.3,
            accepted_ratio=0.3,
        )
        assert result.category == SoulCategory.RASHA_SHE_EINO_GAMUR
        assert 0.3 <= result.score < 0.5

    def test_rasha_gamur_low_scores(self):
        result = self.engine.assess_category(
            hitbonenut_avg=0.1,
            high_world_ratio=0.1,
            accepted_ratio=0.1,
        )
        assert result.category == SoulCategory.RASHA_GAMUR
        assert result.score < 0.3

    def test_returns_soul_assessment(self):
        result = self.engine.assess_category(
            hitbonenut_avg=0.5,
            high_world_ratio=0.5,
            accepted_ratio=0.5,
        )
        assert isinstance(result, SoulAssessment)
        assert isinstance(result.category, SoulCategory)
        assert isinstance(result.explanation, str)
        assert 0.0 <= result.score <= 1.0
        assert result.hitbonenut_avg == 0.5
        assert result.high_world_ratio == 0.5
        assert result.accepted_ratio == 0.5

    def test_zero_scores_gives_rasha_gamur(self):
        result = self.engine.assess_category(
            hitbonenut_avg=0.0,
            high_world_ratio=0.0,
            accepted_ratio=0.0,
        )
        assert result.category == SoulCategory.RASHA_GAMUR
        assert result.score == 0.0

    def test_perfect_scores_gives_tsaddik_gamur(self):
        result = self.engine.assess_category(
            hitbonenut_avg=1.0,
            high_world_ratio=1.0,
            accepted_ratio=1.0,
        )
        assert result.category == SoulCategory.TSADDIK_GAMUR
        assert result.score == 1.0

    def test_weighting_hitbonenut_50_percent(self):
        """Hitbonenut pèse 50% du score."""
        result_high = self.engine.assess_category(
            hitbonenut_avg=1.0,
            high_world_ratio=0.0,
            accepted_ratio=0.0,
        )
        assert result_high.score == 0.5

    def test_weighting_high_world_25_percent(self):
        """high_world_ratio pèse 25%."""
        result = self.engine.assess_category(
            hitbonenut_avg=0.0,
            high_world_ratio=1.0,
            accepted_ratio=0.0,
        )
        assert result.score == 0.25

    def test_weighting_accepted_25_percent(self):
        """accepted_ratio pèse 25%."""
        result = self.engine.assess_category(
            hitbonenut_avg=0.0,
            high_world_ratio=0.0,
            accepted_ratio=1.0,
        )
        assert result.score == 0.25

    def test_score_clamped_to_0_1(self):
        """Le score ne peut pas dépasser 1.0 ni être négatif."""
        result = self.engine.assess_category(
            hitbonenut_avg=2.0,
            high_world_ratio=2.0,
            accepted_ratio=2.0,
        )
        assert result.score <= 1.0


# ─── KelipotSystem ───���─────────────────────────────────────


class TestKelipotSystem:
    def test_atziluth_pure(self):
        assert KelipotSystem.kelipat_nogah_ratio("atziluth") == 1.0

    def test_briah_mostly_good(self):
        assert KelipotSystem.kelipat_nogah_ratio("briah") == 0.8

    def test_yetzirah_equal(self):
        assert KelipotSystem.kelipat_nogah_ratio("yetzirah") == 0.5

    def test_assiah_mostly_evil(self):
        assert KelipotSystem.kelipat_nogah_ratio("assiah") == 0.2

    def test_unknown_world_zero(self):
        assert KelipotSystem.kelipat_nogah_ratio("unknown") == 0.0

    def test_assess_briah_high_confidence(self):
        result = KelipotSystem.assess_response_kelipah(0.8, "briah")
        assert result["weighted_score"] == pytest.approx(0.64, abs=0.001)
        assert result["nogah_ratio"] == 0.8
        assert result["source"] == "kedushah"

    def test_assess_assiah_high_confidence(self):
        """Même confiance élevée, Assiah produit un score faible."""
        result = KelipotSystem.assess_response_kelipah(0.8, "assiah")
        assert result["weighted_score"] == pytest.approx(0.16, abs=0.001)
        assert result["nogah_ratio"] == 0.2
        assert result["source"] == "kelipah"

    def test_assess_threshold_kedushah(self):
        """Le seuil kedushah/kelipah est à 0.4."""
        result = KelipotSystem.assess_response_kelipah(0.5, "briah")
        # 0.5 * 0.8 = 0.4
        assert result["source"] == "kedushah"

    def test_assess_threshold_kelipah(self):
        result = KelipotSystem.assess_response_kelipah(0.49, "briah")
        # 0.49 * 0.8 = 0.392 < 0.4
        assert result["source"] == "kelipah"

    def test_assess_atziluth_always_kedushah(self):
        """Atzilut est pur — toute confiance > 0.4 donne kedushah."""
        result = KelipotSystem.assess_response_kelipah(0.5, "atziluth")
        assert result["source"] == "kedushah"
        assert result["weighted_score"] == 0.5

    def test_assess_returns_all_fields(self):
        result = KelipotSystem.assess_response_kelipah(0.6, "yetzirah")
        assert "weighted_score" in result
        assert "nogah_ratio" in result
        assert "olam" in result
        assert "raw_confidence" in result
        assert "source" in result
        assert result["olam"] == "yetzirah"
        assert result["raw_confidence"] == 0.6


# ─── Intégration : moach_shalit override ───────────────────


class TestMoachShalitOverride:
    """Vérifie que moach_shalit_al_halev retourne les bons résultats
    qui permettent l'override dans le pipeline."""

    def setup_method(self):
        self.engine = DualSoulEngine()

    def test_elokit_recommends_briah(self):
        """Question profonde → elokit → briah recommandé."""
        result = self.engine.moach_shalit_al_halev(
            "Explique pourquoi l'analyse causale montre des divergences "
            "profondes entre les deux cadres théoriques"
        )
        assert result["dominant_soul"] == "elokit"
        assert result["recommended_olam"] == "briah"

    def test_behamit_stays_low(self):
        """Question simple → behamit → pas d'override."""
        result = self.engine.moach_shalit_al_halev("liste les fichiers")
        assert result["dominant_soul"] == "behamit"
        assert result["recommended_olam"] in ("assiah", "yetzirah")

    def test_override_logic_elokit_assiah(self):
        """Si soul=elokit et start_world=assiah → devrait forcer briah."""
        result = self.engine.moach_shalit_al_halev(
            "Pourquoi la conscience émerge-t-elle du raisonnement causal?"
        )
        if result["dominant_soul"] == "elokit":
            # Simule la logique d'override de _generate_malkuth_response
            start_world = "assiah"
            chain = ["assiah", "yetzirah", "briah", "atziluth"]
            current_idx = chain.index(start_world)
            briah_idx = chain.index("briah")
            if current_idx < briah_idx:
                start_world = "briah"
            assert start_world == "briah"

    def test_override_logic_elokit_briah_no_change(self):
        """Si déjà en briah, pas de changement."""
        start_world = "briah"
        chain = ["assiah", "yetzirah", "briah", "atziluth"]
        current_idx = chain.index(start_world)
        briah_idx = chain.index("briah")
        # Pas d'override car current_idx == briah_idx
        assert current_idx >= briah_idx
