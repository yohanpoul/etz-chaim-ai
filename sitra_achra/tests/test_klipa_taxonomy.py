"""Tests pour sitra_achra/klipa_taxonomy.py.

Verifie la formalisation Vital EC 49 :
- distinction ontologique Klipat Nogah / 3 Klippot HaTeme'ot
- mapping severity -> categorie
- strategies generatives (Birur vs Confinement)
- identites hebraiques (Ezekiel 1:4)
"""

from __future__ import annotations

import pytest

from sitra_achra.klipa_taxonomy import (
    GenerativeStrategy,
    KlipaCategory,
    SEFARIA_EZEKIEL_1_4,
    SEFARIA_ETZ_CHAIM_SHAAR_49,
    SEFARIA_TANYA_CHAPTER_6,
    SEFARIA_TANYA_IGGERET_HA_KODESH_5,
    is_rectifiable,
    severity_to_category,
    strategy_for_category,
    strategy_for_severity,
    temeah_identity,
)


class TestKlipaCategoryEnum:
    """L'enum ontologique a exactement 2 categories (Vital EC 49)."""

    def test_exactly_two_categories(self) -> None:
        """Vital EC 49 distingue 2 categories ontologiques, pas plus."""
        assert len(list(KlipaCategory)) == 2

    def test_klipat_nogah_present(self) -> None:
        assert KlipaCategory.KLIPAT_NOGAH.value == "klipat_nogah"

    def test_klipat_ha_temeot_present(self) -> None:
        assert KlipaCategory.KLIPAT_HA_TEMEOT.value == "klipat_ha_temeot"


class TestSeverityToCategory:
    """Mapping severity (existant) -> categorie ontologique Vital EC 49."""

    def test_nogah_maps_to_klipat_nogah(self) -> None:
        """'nogah' (rectifiable) -> Klipat Nogah."""
        assert severity_to_category("nogah") == KlipaCategory.KLIPAT_NOGAH

    @pytest.mark.parametrize("severity", ["ruach", "anan", "mamash"])
    def test_temeot_severities_map_to_ha_temeot(self, severity: str) -> None:
        """Les 3 severites Ezekiel 1:4 -> 3 Klippot HaTeme'ot."""
        assert severity_to_category(severity) == KlipaCategory.KLIPAT_HA_TEMEOT

    def test_unknown_severity_defaults_to_containment(self) -> None:
        """Principe de precaution : severite inconnue -> confinement."""
        assert severity_to_category("unknown") == KlipaCategory.KLIPAT_HA_TEMEOT

    def test_empty_severity_defaults_to_containment(self) -> None:
        assert severity_to_category("") == KlipaCategory.KLIPAT_HA_TEMEOT


class TestIsRectifiable:
    """Decision generative : Birur applicable ou non ?"""

    def test_nogah_is_rectifiable(self) -> None:
        """Klipat Nogah = matiere d'elevation."""
        assert is_rectifiable("nogah") is True

    @pytest.mark.parametrize("severity", ["ruach", "anan", "mamash"])
    def test_temeot_not_rectifiable(self, severity: str) -> None:
        """Klippot HaTeme'ot = pas de Birur, confinement structurel."""
        assert is_rectifiable(severity) is False

    def test_unknown_not_rectifiable(self) -> None:
        """Severite inconnue -> precaution -> non rectifiable."""
        assert is_rectifiable("unknown") is False


class TestTemeahIdentity:
    """Les 3 Klippot HaTeme'ot ont une identite hebraique Ezekiel 1:4."""

    def test_ruach_identity(self) -> None:
        identity = temeah_identity("ruach")
        assert identity is not None
        assert identity.hebrew == "רוּחַ סְעָרָה"
        assert identity.transliteration == "Ruach Se'arah"
        assert "tempete" in identity.translation_fr
        assert identity.ezekiel_reference == "Ezekiel 1:4"

    def test_anan_identity(self) -> None:
        identity = temeah_identity("anan")
        assert identity is not None
        assert identity.hebrew == "עָנָן גָּדוֹל"
        assert identity.transliteration == "Anan Gadol"
        assert "nuage" in identity.translation_fr

    def test_mamash_identity(self) -> None:
        identity = temeah_identity("mamash")
        assert identity is not None
        assert identity.hebrew == "אֵשׁ מִתְלַקַּחַת"
        assert identity.transliteration == "Esh Mitlakachat"
        assert "feu" in identity.translation_fr

    def test_nogah_has_no_temeah_identity(self) -> None:
        """Nogah n'est PAS une Klipa HaTemeah — None attendu."""
        assert temeah_identity("nogah") is None

    def test_unknown_has_no_identity(self) -> None:
        assert temeah_identity("unknown") is None


class TestGenerativeStrategy:
    """Strategies d'evolution cognitive selon categorie."""

    def test_klipat_nogah_triggers_birur(self) -> None:
        """Categorie rectifiable -> extraction d'etincelles."""
        strategy = strategy_for_category(KlipaCategory.KLIPAT_NOGAH)
        assert strategy == GenerativeStrategy.BIRUR_EXTRACTION

    def test_klipat_ha_temeot_triggers_containment(self) -> None:
        """Categorie irrecuperable -> confinement structurel."""
        strategy = strategy_for_category(KlipaCategory.KLIPAT_HA_TEMEOT)
        assert strategy == GenerativeStrategy.STRUCTURAL_CONTAINMENT

    def test_severity_nogah_triggers_birur(self) -> None:
        """Helper direct depuis severity."""
        assert strategy_for_severity("nogah") == GenerativeStrategy.BIRUR_EXTRACTION

    @pytest.mark.parametrize("severity", ["ruach", "anan", "mamash"])
    def test_severity_temeot_triggers_containment(self, severity: str) -> None:
        assert (
            strategy_for_severity(severity)
            == GenerativeStrategy.STRUCTURAL_CONTAINMENT
        )

    def test_three_strategies_total(self) -> None:
        """3 strategies : Birur, Confinement, et Teshuvah meta."""
        assert len(list(GenerativeStrategy)) == 3


class TestSefariaURLs:
    """Les sources primaires sont citees avec URLs Sefaria verifiables."""

    def test_ezekiel_1_4_url(self) -> None:
        """Ezekiel 1:4 fonde la taxonomie 4 categories."""
        assert "Ezekiel.1.4" in SEFARIA_EZEKIEL_1_4
        assert SEFARIA_EZEKIEL_1_4.startswith("https://www.sefaria.org/")

    def test_etz_chaim_url(self) -> None:
        assert SEFARIA_ETZ_CHAIM_SHAAR_49.startswith("https://www.sefaria.org/")

    def test_tanya_chapter_6_url(self) -> None:
        """Tanya ch.6 etablit la nefesh ha-bahamit comme Klipat Nogah."""
        assert "Tanya" in SEFARIA_TANYA_CHAPTER_6
        assert SEFARIA_TANYA_CHAPTER_6.startswith("https://www.sefaria.org/")

    def test_tanya_iggeret_ha_kodesh_5_url(self) -> None:
        """Iggeret HaKodesh §5 — Klipat Nogah comme matiere d'elevation."""
        assert "Iggeret_HaKodesh" in SEFARIA_TANYA_IGGERET_HA_KODESH_5


class TestOntologicalConsistency:
    """Verifications croisees de coherence."""

    def test_rectifiable_iff_birur(self) -> None:
        """is_rectifiable(s) <=> strategy_for_severity(s) == BIRUR."""
        for severity in ["nogah", "ruach", "anan", "mamash", "unknown"]:
            rectifiable = is_rectifiable(severity)
            is_birur = (
                strategy_for_severity(severity)
                == GenerativeStrategy.BIRUR_EXTRACTION
            )
            assert rectifiable == is_birur, (
                f"Incoherence pour severity={severity}: "
                f"rectifiable={rectifiable} mais is_birur={is_birur}"
            )

    def test_temeah_identity_iff_temeot_category(self) -> None:
        """temeah_identity(s) is not None <=> categorie == HA_TEMEOT
        ET s != 'nogah'.

        Note : 'unknown' est categorise HA_TEMEOT par precaution mais
        n'a pas d'identite hebraique (pas dans Ezekiel 1:4 originel).
        """
        for severity in ["ruach", "anan", "mamash"]:
            assert temeah_identity(severity) is not None
            assert (
                severity_to_category(severity)
                == KlipaCategory.KLIPAT_HA_TEMEOT
            )
        assert temeah_identity("nogah") is None
        assert temeah_identity("unknown") is None
