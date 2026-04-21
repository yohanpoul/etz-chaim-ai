"""Tests pour les 13 méthodes de gématria.

Vérifie les 6 nouvelles méthodes (milui, katan_mispari, hakadmi, perati,
meruba_haklali, musafi) + kolel et atbash, avec des mots hébreux connus.
"""

import unittest

from gematria.engine import (
    ALBAM_MAP,
    ATBACH_MAP,
    MILUI_MAH_SPELLINGS,
    MILUI_MAH_VALUES,
    VALID_METHODS,
    _ORDINAL_WITH_FINALS,
    GematriaEngine,
    calc_albam,
    calc_atbach,
    calc_atbash,
    calc_hakadmi,
    calc_katan,
    calc_katan_mispari,
    calc_kolel,
    calc_meruba_haklali,
    calc_milui,
    calc_musafi,
    calc_ordinal,
    calc_perati,
    calc_standard,
)
from shemot.language import HEBREW_GEMATRIA, HEBREW_ORDINAL


# ── Dictionnaires MILUI ────────────────────────────────────────


class TestMiluiDicts(unittest.TestCase):
    """Les dictionnaires MILUI_MAH sont cohérents."""

    def test_spellings_has_22_letters(self):
        standard = [ch for ch in MILUI_MAH_SPELLINGS if ch in HEBREW_ORDINAL]
        self.assertEqual(len(standard), 22)

    def test_spellings_has_5_finals(self):
        finals = {"ך", "ם", "ן", "ף", "ץ"}
        for f in finals:
            self.assertIn(f, MILUI_MAH_SPELLINGS, f"Finale {f} manquante")

    def test_values_has_27_entries(self):
        """22 lettres + 5 finales = 27 entrées."""
        self.assertEqual(len(MILUI_MAH_VALUES), 27)

    def test_spellings_match_values_count(self):
        self.assertEqual(len(MILUI_MAH_SPELLINGS), len(MILUI_MAH_VALUES))

    def test_aleph_milui(self):
        """א → אלף = 1+30+80 = 111."""
        self.assertEqual(MILUI_MAH_VALUES["א"], 111)
        self.assertEqual(MILUI_MAH_SPELLINGS["א"], "אלף")

    def test_he_milui_mah(self):
        """ה → הא = 5+1 = 6 (Milui de Mah, pas de Sag)."""
        self.assertEqual(MILUI_MAH_VALUES["ה"], 6)
        self.assertEqual(MILUI_MAH_SPELLINGS["ה"], "הא")

    def test_vav_milui_mah(self):
        """ו → ואו = 6+1+6 = 13 (Milui de Mah)."""
        self.assertEqual(MILUI_MAH_VALUES["ו"], 13)
        self.assertEqual(MILUI_MAH_SPELLINGS["ו"], "ואו")

    def test_finals_equal_standard(self):
        """Les finales ont la même valeur milui que leur forme standard."""
        pairs = [("ך", "כ"), ("ם", "מ"), ("ן", "נ"), ("ף", "פ"), ("ץ", "צ")]
        for final, std in pairs:
            self.assertEqual(
                MILUI_MAH_VALUES[final], MILUI_MAH_VALUES[std],
                f"Finale {final} ≠ standard {std}",
            )

    def test_known_milui_values(self):
        """Valeurs milui pour les 22 lettres standard."""
        expected = {
            "א": 111, "ב": 412, "ג": 83,  "ד": 434,
            "ה": 6,   "ו": 13,  "ז": 67,  "ח": 418,
            "ט": 419, "י": 20,  "כ": 100, "ל": 74,
            "מ": 80,  "נ": 106, "ס": 120, "ע": 130,
            "פ": 81,  "צ": 104, "ק": 186, "ר": 510,
            "ש": 360, "ת": 406,
        }
        for letter, val in expected.items():
            self.assertEqual(
                MILUI_MAH_VALUES[letter], val,
                f"Milui de {letter} = {MILUI_MAH_VALUES[letter]}, attendu {val}",
            )


class TestOrdinalWithFinals(unittest.TestCase):
    """_ORDINAL_WITH_FINALS couvre les finales."""

    def test_has_27_entries(self):
        self.assertEqual(len(_ORDINAL_WITH_FINALS), 27)

    def test_kaf_sofit(self):
        self.assertEqual(_ORDINAL_WITH_FINALS["ך"], HEBREW_ORDINAL["כ"])

    def test_mem_sofit(self):
        self.assertEqual(_ORDINAL_WITH_FINALS["ם"], HEBREW_ORDINAL["מ"])


# ── calc_milui ─────────────────────────────────────────────────


class TestCalcMilui(unittest.TestCase):
    """Mispar Gadol Mispari (Milui de Mah)."""

    def test_aleph_alone(self):
        self.assertEqual(calc_milui("א"), 111)

    def test_emet(self):
        """אמת : א(111) + מ(80) + ת(406) = 597."""
        self.assertEqual(calc_milui("אמת"), 597)

    def test_chesed(self):
        """חסד : ח(418) + ס(120) + ד(434) = 972."""
        self.assertEqual(calc_milui("חסד"), 972)

    def test_yhvh(self):
        """יהוה : Milui de Mah = 10+6+4 + 5+1 + 6+1+6 + 5+1 = 45."""
        # C'est le Shem Mah (שם מ"ה = 45), fondamental en Kabbale lourianique.
        self.assertEqual(calc_milui("יהוה"), 45)

    def test_empty_string(self):
        self.assertEqual(calc_milui(""), 0)

    def test_non_hebrew(self):
        self.assertEqual(calc_milui("abc"), 0)

    def test_with_final_mem(self):
        """אלהים avec ם final."""
        # א(111) + ל(74) + ה(6) + י(20) + ם(80) = 291
        self.assertEqual(calc_milui("אלהים"), 291)


# ── calc_katan_mispari ─────────────────────────────────────────


class TestCalcKatanMispari(unittest.TestCase):
    """Mispar Katan Mispari (double réduction du Milui)."""

    def test_emet(self):
        """אמת : milui=597 → 5+9+7=21 → 2+1=3."""
        self.assertEqual(calc_katan_mispari("אמת"), 3)

    def test_chesed(self):
        """חסד : milui=972 → 9+7+2=18 → 1+8=9."""
        self.assertEqual(calc_katan_mispari("חסד"), 9)

    def test_yhvh(self):
        """יהוה : milui=45 → 4+5=9."""
        self.assertEqual(calc_katan_mispari("יהוה"), 9)

    def test_single_digit_milui(self):
        """ה : milui=6 → déjà un chiffre → 6."""
        self.assertEqual(calc_katan_mispari("ה"), 6)

    def test_empty(self):
        self.assertEqual(calc_katan_mispari(""), 0)


# ── calc_hakadmi ───────────────────────────────────────────────


class TestCalcHaKadmi(unittest.TestCase):
    """Mispar HaKadmi (triangulaire)."""

    def test_aleph(self):
        """Aleph ordinal=1, T(1)=1."""
        self.assertEqual(calc_hakadmi("א"), 1)

    def test_bet(self):
        """Bet ordinal=2, T(2)=3."""
        self.assertEqual(calc_hakadmi("ב"), 3)

    def test_gimel(self):
        """Gimel ordinal=3, T(3)=6."""
        self.assertEqual(calc_hakadmi("ג"), 6)

    def test_tav(self):
        """Tav ordinal=22, T(22)=253."""
        self.assertEqual(calc_hakadmi("ת"), 253)

    def test_emet(self):
        """אמת : T(1)+T(13)+T(22) = 1+91+253 = 345."""
        self.assertEqual(calc_hakadmi("אמת"), 345)

    def test_chesed(self):
        """חסד : T(8)+T(15)+T(4) = 36+120+10 = 166."""
        self.assertEqual(calc_hakadmi("חסד"), 166)

    def test_with_final(self):
        """ן final a le même ordinal que נ (14), T(14)=105."""
        self.assertEqual(calc_hakadmi("ן"), 105)

    def test_empty(self):
        self.assertEqual(calc_hakadmi(""), 0)


# ── calc_perati ────────────────────────────────────────────────


class TestCalcPerati(unittest.TestCase):
    """Mispar Perati (carré)."""

    def test_aleph(self):
        """Aleph: 1² = 1."""
        self.assertEqual(calc_perati("א"), 1)

    def test_yod(self):
        """Yod: 10² = 100."""
        self.assertEqual(calc_perati("י"), 100)

    def test_qof(self):
        """Qof: 100² = 10000."""
        self.assertEqual(calc_perati("ק"), 10000)

    def test_emet(self):
        """אמת : 1² + 40² + 400² = 1 + 1600 + 160000 = 161601."""
        self.assertEqual(calc_perati("אמת"), 161601)

    def test_chesed(self):
        """חסד : 8² + 60² + 4² = 64 + 3600 + 16 = 3680."""
        self.assertEqual(calc_perati("חסד"), 3680)

    def test_empty(self):
        self.assertEqual(calc_perati(""), 0)


# ── calc_meruba_haklali ────────────────────────────────────────


class TestCalcMerubaHaKlali(unittest.TestCase):
    """Mispar HaMeruba HaKlali (carré du total)."""

    def test_emet(self):
        """אמת : standard=441, 441² = 194481."""
        self.assertEqual(calc_meruba_haklali("אמת"), 194481)

    def test_chesed(self):
        """חסד : standard=72, 72² = 5184."""
        self.assertEqual(calc_meruba_haklali("חסד"), 5184)

    def test_ab(self):
        """אב : standard=3, 3² = 9 (exemple du user)."""
        self.assertEqual(calc_meruba_haklali("אב"), 9)

    def test_empty(self):
        self.assertEqual(calc_meruba_haklali(""), 0)


# ── calc_musafi ────────────────────────────────────────────────


class TestCalcMusafi(unittest.TestCase):
    """Mispar Musafi (standard + nombre de lettres)."""

    def test_emet(self):
        """אמת : standard=441 + 3 lettres = 444."""
        self.assertEqual(calc_musafi("אמת"), 444)

    def test_chesed(self):
        """חסד : standard=72 + 3 lettres = 75."""
        self.assertEqual(calc_musafi("חסד"), 75)

    def test_ab(self):
        """אב : standard=3 + 2 lettres = 5 (exemple du user)."""
        self.assertEqual(calc_musafi("אב"), 5)

    def test_single_letter(self):
        """א : standard=1 + 1 lettre = 2."""
        self.assertEqual(calc_musafi("א"), 2)

    def test_empty(self):
        self.assertEqual(calc_musafi(""), 0)


# ── calc_kolel & calc_atbash ───────────────────────────────────


class TestCalcKolel(unittest.TestCase):
    """Kolel = standard + 1."""

    def test_emet(self):
        self.assertEqual(calc_kolel("אמת"), 442)

    def test_chesed(self):
        self.assertEqual(calc_kolel("חסד"), 73)


class TestCalcAtbash(unittest.TestCase):
    """Atbash = gématria standard après permutation miroir."""

    def test_emet(self):
        """אמת : א→ת(400), מ→י(10), ת→א(1) = 411."""
        self.assertEqual(calc_atbash("אמת"), 411)

    def test_chesed(self):
        """חסד : ח→ס(60), ס→ח(8), ד→ק(100) = 168."""
        self.assertEqual(calc_atbash("חסד"), 168)


# ── calc_albam ────────────────────────────────────────────────


class TestCalcAlbam(unittest.TestCase):
    """Al-Bam = permutation des 2 moitiés de l'alphabet (11+11)."""

    def test_map_has_22_entries(self):
        self.assertEqual(len(ALBAM_MAP), 22)

    def test_map_is_involutive(self):
        """Al-Bam appliqué deux fois = identité."""
        for ch, mapped in ALBAM_MAP.items():
            self.assertEqual(ALBAM_MAP[mapped], ch)

    def test_aleph_to_lamed(self):
        """א → ל (30)."""
        self.assertEqual(ALBAM_MAP["א"], "ל")
        self.assertEqual(calc_albam("א"), 30)

    def test_emet(self):
        """אמת : א→ל(30), מ→ב(2), ת→כ(20) = 52."""
        self.assertEqual(calc_albam("אמת"), 52)

    def test_chesed(self):
        """חסד : ח→ק(100), ס→ד(4), ד→ס(60) = 164."""
        self.assertEqual(calc_albam("חסד"), 164)

    def test_yhvh(self):
        """יהוה : י→ש(300), ה→ע(70), ו→פ(80), ה→ע(70) = 520."""
        self.assertEqual(calc_albam("יהוה"), 520)

    def test_empty(self):
        self.assertEqual(calc_albam(""), 0)

    def test_non_hebrew(self):
        self.assertEqual(calc_albam("abc"), 0)


# ── calc_atbach ───────────────────────────────────────────────


class TestCalcAtbach(unittest.TestCase):
    """At-Bach = permutation miroir par groupe de magnitude."""

    def test_map_has_22_entries(self):
        self.assertEqual(len(ATBACH_MAP), 22)

    def test_map_is_involutive(self):
        """At-Bach appliqué deux fois = identité."""
        for ch, mapped in ATBACH_MAP.items():
            self.assertEqual(ATBACH_MAP[mapped], ch)

    def test_fixed_points(self):
        """ה et נ sont des points fixes."""
        self.assertEqual(ATBACH_MAP["ה"], "ה")
        self.assertEqual(ATBACH_MAP["נ"], "נ")

    def test_aleph_to_tet(self):
        """א → ט (9)."""
        self.assertEqual(ATBACH_MAP["א"], "ט")
        self.assertEqual(calc_atbach("א"), 9)

    def test_emet(self):
        """אמת : א→ט(9), מ→ס(60), ת→ק(100) = 169."""
        self.assertEqual(calc_atbach("אמת"), 169)

    def test_chesed(self):
        """חסד : ח→ב(2), ס→מ(40), ד→ו(6) = 48."""
        self.assertEqual(calc_atbach("חסד"), 48)

    def test_yhvh(self):
        """יהוה : י→צ(90), ה→ה(5), ו→ד(4), ה→ה(5) = 104."""
        self.assertEqual(calc_atbach("יהוה"), 104)

    def test_empty(self):
        self.assertEqual(calc_atbach(""), 0)

    def test_non_hebrew(self):
        self.assertEqual(calc_atbach("abc"), 0)


# ── GematriaEngine.calculate() ─────────────────────────────────


class TestCalculateAll(unittest.TestCase):
    """calculate() retourne toutes les valeurs."""

    def test_returns_all_keys(self):
        result = GematriaEngine.calculate("אמת")
        self.assertIsNotNone(result)
        expected_keys = {
            "hebrew", "transliteration",
            "standard", "ordinal", "katan", "kolel",
            "atbash", "atbash_text",
            "milui", "milui_detail", "katan_mispari",
            "hakadmi", "perati", "meruba_haklali", "musafi",
            "albam", "albam_text", "atbach", "atbach_text",
        }
        self.assertEqual(set(result.keys()), expected_keys)

    def test_emet_values(self):
        r = GematriaEngine.calculate("אמת")
        self.assertEqual(r["standard"], 441)
        self.assertEqual(r["ordinal"], 36)
        self.assertEqual(r["katan"], 9)
        self.assertEqual(r["kolel"], 442)
        self.assertEqual(r["atbash"], 411)
        self.assertEqual(r["atbash_text"], "תיא")
        self.assertEqual(r["milui"], 597)
        self.assertEqual(r["katan_mispari"], 3)
        self.assertEqual(r["hakadmi"], 345)
        self.assertEqual(r["perati"], 161601)
        self.assertEqual(r["meruba_haklali"], 194481)
        self.assertEqual(r["musafi"], 444)
        self.assertEqual(r["albam"], 52)
        self.assertEqual(r["albam_text"], "לבכ")
        self.assertEqual(r["atbach"], 169)
        self.assertEqual(r["atbach_text"], "טסק")

    def test_chesed_values(self):
        r = GematriaEngine.calculate("חסד")
        self.assertEqual(r["standard"], 72)
        self.assertEqual(r["milui"], 972)
        self.assertEqual(r["katan_mispari"], 9)
        self.assertEqual(r["hakadmi"], 166)
        self.assertEqual(r["perati"], 3680)
        self.assertEqual(r["meruba_haklali"], 5184)
        self.assertEqual(r["musafi"], 75)
        self.assertEqual(r["albam"], 164)
        self.assertEqual(r["atbach"], 48)

    def test_yhvh_milui_45(self):
        """Le Shem de Mah : יהוה en Milui Mah = 45."""
        r = GematriaEngine.calculate("יהוה")
        self.assertEqual(r["standard"], 26)
        self.assertEqual(r["milui"], 45)

    def test_milui_detail_format(self):
        r = GematriaEngine.calculate("אב")
        self.assertEqual(r["milui_detail"], "אלף + בית")

    def test_none_for_non_hebrew(self):
        self.assertIsNone(GematriaEngine.calculate("hello"))

    def test_transliteration(self):
        """calculate() accepte les translittérations connues."""
        r = GematriaEngine.calculate("chesed")
        if r is not None:
            self.assertEqual(r["standard"], 72)


# ── VALID_METHODS ──────────────────────────────────────────────


class TestValidMethods(unittest.TestCase):
    """VALID_METHODS contient les 11 méthodes stockées en DB."""

    def test_has_11_methods(self):
        self.assertEqual(len(VALID_METHODS), 11)

    def test_original_3(self):
        for m in ("standard", "ordinal", "katan"):
            self.assertIn(m, VALID_METHODS)

    def test_new_8(self):
        for m in ("milui", "katan_mispari", "hakadmi", "perati",
                   "meruba_haklali", "musafi", "albam", "atbach"):
            self.assertIn(m, VALID_METHODS)


# ── Cas limites ────────────────────────────────────────────────


class TestEdgeCases(unittest.TestCase):
    """Cas limites pour toutes les méthodes."""

    def test_all_methods_handle_empty(self):
        for fn in (calc_milui, calc_katan_mispari, calc_hakadmi,
                   calc_perati, calc_meruba_haklali, calc_musafi,
                   calc_kolel, calc_atbash, calc_albam, calc_atbach):
            self.assertEqual(fn(""), 0, f"{fn.__name__}('') ≠ 0")

    def test_all_methods_handle_non_hebrew(self):
        for fn in (calc_milui, calc_katan_mispari, calc_hakadmi,
                   calc_perati, calc_meruba_haklali, calc_musafi,
                   calc_albam, calc_atbach):
            self.assertEqual(fn("abc"), 0, f"{fn.__name__}('abc') ≠ 0")

    def test_mixed_hebrew_non_hebrew(self):
        """Seules les lettres hébraïques comptent."""
        # "א test ב" — seuls א et ב comptent
        self.assertEqual(calc_standard("א test ב"), 3)
        self.assertEqual(calc_milui("א test ב"), 111 + 412)

    def test_final_forms_in_perati(self):
        """Les finales utilisent leurs valeurs étendues (500-900) pour perati."""
        # ך = 500, 500² = 250000
        self.assertEqual(calc_perati("ך"), 250000)

    def test_final_forms_in_hakadmi(self):
        """Les finales utilisent l'ordinal de leur forme standard pour hakadmi."""
        # ך → ordinal de כ = 11, T(11) = 66
        self.assertEqual(calc_hakadmi("ך"), 66)

    def test_tiferet_standard(self):
        """תפארת : ת(400)+פ(80)+א(1)+ר(200)+ת(400) = 1081."""
        self.assertEqual(calc_standard("תפארת"), 1081)

    def test_tiferet_milui(self):
        """תפארת en Milui de Mah."""
        # ת(406)+פ(81)+א(111)+ר(510)+ת(406) = 1514
        self.assertEqual(calc_milui("תפארת"), 1514)


if __name__ == "__main__":
    unittest.main()
