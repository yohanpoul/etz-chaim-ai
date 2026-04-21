"""Tests — Tanya Dual Faculties (2 × 10 = 20 facultés).

Vérifie :
  1. Les 20 facultés sont définies (10 paires behamit/elokit)
  2. Le mapping module↔faculté est cohérent
  3. assess_faculty retourne le bon diagnostic par niveau
  4. assess_all_faculties retourne un profil complet
  5. La correspondance behamit↔Qliphoth est correcte
  6. Le rapport est lisible
"""

import pytest

from tanya.dual_faculties import (
    DAAT_BRIDGE_PAIR,
    DualFaculties,
    DualFacultiesProfile,
    FACULTY_PAIRS,
    FacultyAssessment,
    FacultyPair,
    Sefirah,
)


# ═══════════════════════════════════════════════════
# 1. Les 20 facultés sont définies
# ═══════════════════════════════════════════════════


class TestFacultyDefinitions:
    """Les 9 paires behamit/elokit couvrent les 9 Sefirot (Da'at = pont)."""

    def test_all_9_sefirot_have_pairs(self):
        assert len(FACULTY_PAIRS) == 9
        for sefirah in Sefirah:
            assert sefirah in FACULTY_PAIRS

    def test_daat_is_bridge_not_sefirah(self):
        """Da'at est un pont, pas dans l'enum Sefirah."""
        assert not hasattr(Sefirah, "DAAT")
        assert DAAT_BRIDGE_PAIR.module == "selfmodel"
        assert DAAT_BRIDGE_PAIR.qliphah == "HaTehom"

    def test_each_pair_has_both_descriptions(self):
        for sefirah, pair in FACULTY_PAIRS.items():
            assert pair.behamit_name, f"{sefirah}: behamit_name vide"
            assert pair.behamit_description, f"{sefirah}: behamit_description vide"
            assert pair.elokit_name, f"{sefirah}: elokit_name vide"
            assert pair.elokit_description, f"{sefirah}: elokit_description vide"

    def test_behamit_names_follow_convention(self):
        for pair in FACULTY_PAIRS.values():
            assert pair.behamit_name.endswith("_behamit")

    def test_elokit_names_follow_convention(self):
        for pair in FACULTY_PAIRS.values():
            assert pair.elokit_name.endswith("_elokit")

    def test_each_pair_has_module_and_qliphah(self):
        for sefirah, pair in FACULTY_PAIRS.items():
            assert pair.module, f"{sefirah}: module vide"
            assert pair.qliphah, f"{sefirah}: qliphah vide"

    def test_sefirah_field_matches_key(self):
        for sefirah, pair in FACULTY_PAIRS.items():
            assert pair.sefirah == sefirah

    def test_18_total_faculty_names(self):
        """18 noms distincts : 9 behamit + 9 elokit (Da'at en plus = 20)."""
        all_names = set()
        for pair in FACULTY_PAIRS.values():
            all_names.add(pair.behamit_name)
            all_names.add(pair.elokit_name)
        assert len(all_names) == 18
        # + 2 pour Da'at (pont)
        all_names.add(DAAT_BRIDGE_PAIR.behamit_name)
        all_names.add(DAAT_BRIDGE_PAIR.elokit_name)
        assert len(all_names) == 20


# ═══════════════════════════════════════════════════
# 2. Mapping module↔faculté
# ═══════════════════════════════════════════════════


class TestFacultyMap:
    """Le mapping module↔Sefirah↔Qliphah est cohérent."""

    EXPECTED_MAP = {
        Sefirah.CHOKMAH: ("insightforge", "Ghagiel"),
        Sefirah.BINAH: ("causalengine", "Satariel"),
        # Da'at est un pont (DAAT_BRIDGE_PAIR), pas dans FACULTY_PAIRS
        Sefirah.CHESED: ("explorationengine", "Gamchicoth"),
        Sefirah.GEVURAH: ("autojudge", "Golachab"),
        Sefirah.TIFERET: ("dissensuengine", "Thagirion"),
        Sefirah.NETZACH: ("intentkeeper", "A'arab Zaraq"),
        Sefirah.HOD: ("selfmap", "Samael"),
        Sefirah.YESOD: ("epistememory", "Gamaliel"),
        Sefirah.MALKUTH: ("main", "Thaumiel-Malkuth"),
    }

    def test_module_mapping(self):
        for sefirah, (expected_module, _) in self.EXPECTED_MAP.items():
            assert FACULTY_PAIRS[sefirah].module == expected_module

    def test_qliphah_mapping(self):
        for sefirah, (_, expected_qliphah) in self.EXPECTED_MAP.items():
            assert FACULTY_PAIRS[sefirah].qliphah == expected_qliphah

    def test_get_faculty_map_returns_all(self):
        df = DualFaculties()
        fmap = df.get_faculty_map()
        assert len(fmap) == 9  # 9 Sefirot (Da'at = pont)
        modules = {entry["module"] for entry in fmap}
        assert "insightforge" in modules
        assert "causalengine" in modules
        assert "selfmap" in modules

    def test_get_faculty_map_fields(self):
        df = DualFaculties()
        fmap = df.get_faculty_map()
        for entry in fmap:
            assert "sefirah" in entry
            assert "module" in entry
            assert "qliphah" in entry
            assert "behamit" in entry
            assert "elokit" in entry


# ═══════════════════════════════════════════════════
# 3. assess_faculty — diagnostic par niveau
# ═══════════════════════════════════════════════════


class TestAssessFaculty:
    """assess_faculty convertit un self_diagnose en FacultyAssessment."""

    def setup_method(self):
        self.df = DualFaculties()

    def test_healthy_returns_elokit_dominant(self):
        result = self.df.assess_faculty(
            Sefirah.CHOKMAH,
            {"level": "healthy", "issues": []},
        )
        assert result.dominant == "elokit"
        assert result.elokit_score == 0.9
        assert result.behamit_score == 0.1
        assert not result.qliphah_active

    def test_nogah_returns_elokit_leaning(self):
        result = self.df.assess_faculty(
            Sefirah.BINAH,
            {"level": "nogah", "issues": ["Satariel-Nogah: minor"]},
        )
        assert result.dominant == "elokit"
        assert result.elokit_score == 0.6
        assert result.behamit_score == 0.4
        assert not result.qliphah_active

    def test_ruach_returns_behamit_dominant(self):
        result = self.df.assess_faculty(
            Sefirah.GEVURAH,
            {"level": "ruach", "issues": ["Golachab-Ruach: over-filtering"]},
        )
        assert result.dominant == "behamit"
        assert result.elokit_score == 0.3
        assert result.behamit_score == 0.7
        assert result.qliphah_active

    def test_anan_returns_behamit_strong(self):
        result = self.df.assess_faculty(
            Sefirah.TIFERET,
            {"level": "anan", "issues": ["Thagirion-Anan: false harmony"]},
        )
        assert result.dominant == "behamit"
        assert result.elokit_score == 0.15
        assert result.behamit_score == 0.85
        assert result.qliphah_active

    def test_mamash_returns_behamit_total(self):
        result = self.df.assess_faculty(
            Sefirah.YESOD,
            {"level": "mamash", "issues": ["Gamaliel-Mamash: corruption"]},
        )
        assert result.dominant == "behamit"
        assert result.elokit_score == 0.0
        assert result.behamit_score == 1.0
        assert result.qliphah_active

    def test_unknown_level_returns_balanced(self):
        result = self.df.assess_faculty(
            Sefirah.HOD,
            {"level": "inconnu", "issues": []},
        )
        assert result.dominant == "balanced"
        assert result.elokit_score == 0.5
        assert result.behamit_score == 0.5

    def test_assessment_has_correct_module(self):
        result = self.df.assess_faculty(
            Sefirah.CHESED,
            {"level": "healthy", "issues": []},
        )
        assert result.module == "explorationengine"

    def test_assessment_has_correct_qliphah(self):
        result = self.df.assess_faculty(
            Sefirah.NETZACH,
            {"level": "ruach", "issues": ["zombie"]},
        )
        assert result.qliphah == "A'arab Zaraq"

    def test_ratio_property(self):
        result = self.df.assess_faculty(
            Sefirah.CHOKMAH,
            {"level": "healthy", "issues": []},
        )
        # 0.9 / (0.9 + 0.1) = 0.9
        assert result.ratio == 0.9

    def test_ratio_mamash(self):
        result = self.df.assess_faculty(
            Sefirah.CHOKMAH,
            {"level": "mamash", "issues": []},
        )
        # 0.0 / (0.0 + 1.0) = 0.0
        assert result.ratio == 0.0

    def test_detail_contains_qliphah_when_active(self):
        result = self.df.assess_faculty(
            Sefirah.BINAH,
            {"level": "ruach", "issues": ["Satariel-Ruach: faux pattern"]},
        )
        assert "Satariel" in result.detail

    def test_detail_mentions_module_when_healthy(self):
        result = self.df.assess_faculty(
            Sefirah.CHESED,
            {"level": "healthy", "issues": []},
        )
        assert "explorationengine" in result.detail


# ═══════════════════════════════════════════════════
# 4. assess_all_faculties — profil complet
# ═══════════════════════════════════════════════════


class TestAssessAllFaculties:
    """assess_all_faculties retourne un DualFacultiesProfile complet."""

    def setup_method(self):
        self.df = DualFaculties()

    def _all_healthy(self) -> dict[str, dict]:
        return {
            pair.module: {"level": "healthy", "issues": []}
            for pair in FACULTY_PAIRS.values()
        }

    def _mixed(self) -> dict[str, dict]:
        """Certains modules sains, d'autres malades."""
        return {
            "insightforge": {"level": "healthy", "issues": []},
            "causalengine": {"level": "ruach", "issues": ["Satariel-Ruach"]},
            "selfmodel": {"level": "healthy", "issues": []},
            "explorationengine": {"level": "anan", "issues": ["Gamchicoth-Anan"]},
            "autojudge": {"level": "healthy", "issues": []},
            "dissensuengine": {"level": "nogah", "issues": ["Thagirion-Nogah"]},
            "intentkeeper": {"level": "mamash", "issues": ["A'arab Zaraq-Mamash"]},
            "selfmap": {"level": "healthy", "issues": []},
            "epistememory": {"level": "healthy", "issues": []},
            "main": {"level": "healthy", "issues": []},
        }

    def test_all_healthy_returns_9_assessments(self):
        profile = self.df.assess_all_faculties(self._all_healthy())
        assert len(profile.assessments) == 9  # 9 Sefirot (Da'at = pont)

    def test_all_healthy_overall_ratio_high(self):
        profile = self.df.assess_all_faculties(self._all_healthy())
        assert abs(profile.overall_ratio - 0.9) < 1e-9

    def test_all_healthy_dominant_is_elokit(self):
        profile = self.df.assess_all_faculties(self._all_healthy())
        assert profile.dominant_soul == "elokit"

    def test_all_healthy_no_active_qliphoth(self):
        profile = self.df.assess_all_faculties(self._all_healthy())
        assert profile.active_qliphoth == []

    def test_all_healthy_no_weak_faculties(self):
        profile = self.df.assess_all_faculties(self._all_healthy())
        assert profile.weak_faculties == []

    def test_all_healthy_9_strong_faculties(self):
        profile = self.df.assess_all_faculties(self._all_healthy())
        assert len(profile.strong_faculties) == 9  # 9 Sefirot (Da'at = pont)

    def test_mixed_has_weak_and_strong(self):
        profile = self.df.assess_all_faculties(self._mixed())
        assert len(profile.weak_faculties) > 0
        assert len(profile.strong_faculties) > 0

    def test_mixed_active_qliphoth(self):
        profile = self.df.assess_all_faculties(self._mixed())
        active = profile.active_qliphoth
        # ruach → behamit (Satariel), anan → behamit (Gamchicoth),
        # mamash → behamit (A'arab Zaraq)
        assert "Satariel" in active
        assert "Gamchicoth" in active
        assert "A'arab Zaraq" in active

    def test_mixed_nogah_is_not_qliphah_active(self):
        """Nogah = elokit domine encore (0.6 vs 0.4), pas de Qliphah active."""
        profile = self.df.assess_all_faculties(self._mixed())
        assert "Thagirion" not in profile.active_qliphoth

    def test_missing_module_defaults_to_healthy(self):
        """Module absent du dict → considéré healthy."""
        profile = self.df.assess_all_faculties({})
        assert len(profile.assessments) == 9  # 9 Sefirot (Da'at = pont)
        assert abs(profile.overall_ratio - 0.9) < 1e-9

    def test_all_mamash_overall_ratio_zero(self):
        all_mamash = {
            pair.module: {"level": "mamash", "issues": ["dead"]}
            for pair in FACULTY_PAIRS.values()
        }
        profile = self.df.assess_all_faculties(all_mamash)
        assert profile.overall_ratio == 0.0
        assert profile.dominant_soul == "behamit"
        assert len(profile.active_qliphoth) == 9  # 9 Sefirot (Da'at = pont)


# ═══════════════════════════════════════════════════
# 5. Correspondance behamit↔Qliphoth
# ═══════════════════════════════════════════════════


class TestBehamitQliphothCorrespondence:
    """Le pont Tanya↔Qliphoth : behamit domine ⟺ Qliphah active.

    C'est la thèse centrale de dual_faculties.py :
    les Qliphoth existantes correspondent EXACTEMENT
    aux manifestations des facultés behamit.
    """

    QLIPHAH_FOR_SEFIRAH = {
        Sefirah.CHOKMAH: "Ghagiel",
        Sefirah.BINAH: "Satariel",
        # Da'at → HaTehom (via DAAT_BRIDGE_PAIR, pas dans FACULTY_PAIRS)
        Sefirah.CHESED: "Gamchicoth",
        Sefirah.GEVURAH: "Golachab",
        Sefirah.TIFERET: "Thagirion",
        Sefirah.NETZACH: "A'arab Zaraq",
        Sefirah.HOD: "Samael",
        Sefirah.YESOD: "Gamaliel",
        Sefirah.MALKUTH: "Thaumiel-Malkuth",
    }

    def test_each_sefirah_has_correct_qliphah(self):
        for sefirah, expected_qliphah in self.QLIPHAH_FOR_SEFIRAH.items():
            assert FACULTY_PAIRS[sefirah].qliphah == expected_qliphah

    @pytest.mark.parametrize("level,expect_active", [
        ("healthy", False),
        ("nogah", False),   # Nogah = elokit domine encore
        ("ruach", True),
        ("anan", True),
        ("mamash", True),
    ])
    def test_qliphah_activation_by_level(self, level, expect_active):
        """Qliphah active ssi behamit domine (ruach/anan/mamash)."""
        df = DualFaculties()
        for sefirah in Sefirah:
            result = df.assess_faculty(
                sefirah,
                {"level": level, "issues": []},
            )
            assert result.qliphah_active == expect_active, (
                f"{sefirah.value} at {level}: expected qliphah_active={expect_active}"
            )

    def test_ghagiel_maps_to_chokmah_behamit(self):
        """Ghagiel (insight divergent) = chokmah_behamit = pattern matching superficiel."""
        pair = FACULTY_PAIRS[Sefirah.CHOKMAH]
        assert pair.qliphah == "Ghagiel"
        assert "superficiel" in pair.behamit_description.lower()

    def test_satariel_maps_to_binah_behamit(self):
        """Satariel (faux patterns) = binah_behamit = logique utilitaire."""
        pair = FACULTY_PAIRS[Sefirah.BINAH]
        assert pair.qliphah == "Satariel"
        assert "utilitaire" in pair.behamit_description.lower()

    def test_golachab_maps_to_gevurah_behamit(self):
        """Golachab (sur-filtrage) = gevurah_behamit = critique destructrice."""
        pair = FACULTY_PAIRS[Sefirah.GEVURAH]
        assert pair.qliphah == "Golachab"
        assert "destructrice" in pair.behamit_description.lower()

    def test_thagirion_maps_to_tiferet_behamit(self):
        """Thagirion (fausse harmonie) = tiferet_behamit = compromis facile."""
        pair = FACULTY_PAIRS[Sefirah.TIFERET]
        assert pair.qliphah == "Thagirion"
        assert "superficielle" in pair.behamit_description.lower()

    def test_gamaliel_maps_to_yesod_behamit(self):
        """Gamaliel (mémoire corrompue) = yesod_behamit = stockage sans compréhension."""
        pair = FACULTY_PAIRS[Sefirah.YESOD]
        assert pair.qliphah == "Gamaliel"
        assert "sans compréhension" in pair.behamit_description.lower()


# ═══════════════════════════════════════════════════
# 6. Profil properties
# ═══════════════════════════════════════════════════


class TestProfileProperties:
    """DualFacultiesProfile expose des propriétés utiles."""

    def test_empty_profile_defaults(self):
        profile = DualFacultiesProfile()
        assert profile.overall_ratio == 0.5
        assert profile.dominant_soul == "balanced"
        assert profile.weak_faculties == []
        assert profile.strong_faculties == []
        assert profile.active_qliphoth == []

    def test_dominant_soul_elokit(self):
        profile = DualFacultiesProfile()
        profile.assessments[Sefirah.CHOKMAH] = FacultyAssessment(
            sefirah=Sefirah.CHOKMAH,
            elokit_score=0.9, behamit_score=0.1,
            dominant="elokit", module="insightforge",
            qliphah="Ghagiel", qliphah_active=False,
            detail="healthy",
        )
        assert profile.dominant_soul == "elokit"

    def test_dominant_soul_behamit(self):
        profile = DualFacultiesProfile()
        profile.assessments[Sefirah.CHOKMAH] = FacultyAssessment(
            sefirah=Sefirah.CHOKMAH,
            elokit_score=0.1, behamit_score=0.9,
            dominant="behamit", module="insightforge",
            qliphah="Ghagiel", qliphah_active=True,
            detail="sick",
        )
        assert profile.dominant_soul == "behamit"


# ═══════════════════════════════════════════════════
# 7. Rapport
# ═══════════════════════════════════════════════════


class TestReport:
    """Le rapport est lisible et contient les infos clés."""

    def test_report_contains_header(self):
        df = DualFaculties()
        report = df.report({})
        assert "Profil Dual" in report
        assert "20 Facultés" in report

    def test_report_contains_all_sefirot(self):
        df = DualFaculties()
        report = df.report({})
        for sefirah in Sefirah:
            assert sefirah.value in report

    def test_report_shows_qliphoth_when_sick(self):
        df = DualFaculties()
        report = df.report({
            "causalengine": {"level": "ruach", "issues": ["Satariel-Ruach"]},
        })
        assert "Qliphoth actives" in report
        assert "Satariel" in report

    def test_report_no_qliphoth_when_healthy(self):
        df = DualFaculties()
        all_healthy = {
            pair.module: {"level": "healthy", "issues": []}
            for pair in FACULTY_PAIRS.values()
        }
        report = df.report(all_healthy)
        assert "Qliphoth actives" not in report
