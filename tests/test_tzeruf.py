"""Tests pour le module Tzeruf — permutations et combinaisons de lettres.

Vérifie :
  - Les 231 paires du Sefer Yetzirah
  - Les roues et combinaisons d'Abulafia
  - Les tables de permutation (Atbash, Albam, Avgad)
  - Le Tzeruf opératif (calcul gématrique des permutations)
"""

import math
import unittest

from tzeruf.engine import (
    ALBAM_MAP,
    ALEPH_BET,
    AVGAD_MAP,
    PermutationTable,
    TzerufEngine,
    TzerufPair,
    TzerufResult,
    abulafia_circles,
    abulafia_combination,
    abulafia_wheel,
    apply_temura,
    pairs_231,
    rotate_pair,
    table_albam,
    table_atbash,
    table_avgad,
    table_direct,
)
from gematria.engine import calc_standard
from shemot.language import ATBASH_MAP, HEBREW_LETTERS


# ── Tests des 231 paires ──────────────────────────────────────


class TestPairs231(unittest.TestCase):
    """Les 231 paires du Sefer Yetzirah (C(22,2))."""

    def setUp(self):
        self.pairs = pairs_231()

    def test_count_is_231(self):
        """C(22,2) = 22*21/2 = 231."""
        self.assertEqual(len(self.pairs), 231)

    def test_combinatorial_formula(self):
        """Vérifier que C(22,2) = 231."""
        self.assertEqual(math.comb(22, 2), 231)

    def test_all_pairs_are_unique(self):
        """Aucune paire dupliquée."""
        forwards = [p.forward for p in self.pairs]
        self.assertEqual(len(forwards), len(set(forwards)))

    def test_numbering_1_to_231(self):
        """Numérotation continue de 1 à 231."""
        numbers = [p.number for p in self.pairs]
        self.assertEqual(numbers, list(range(1, 232)))

    def test_first_pair_is_aleph_beth(self):
        """Première paire : Aleph-Beth (אב)."""
        p = self.pairs[0]
        self.assertEqual(p.letter_a, "א")
        self.assertEqual(p.letter_b, "ב")
        self.assertEqual(p.forward, "אב")
        self.assertEqual(p.reverse, "בא")
        self.assertEqual(p.number, 1)

    def test_last_pair_is_shin_tav(self):
        """Dernière paire : Shin-Tav (שת)."""
        p = self.pairs[-1]
        self.assertEqual(p.letter_a, "ש")
        self.assertEqual(p.letter_b, "ת")
        self.assertEqual(p.forward, "שת")
        self.assertEqual(p.reverse, "תש")
        self.assertEqual(p.number, 231)

    def test_forward_reverse_different(self):
        """Forward et reverse sont différents (sauf si lettres identiques, impossible ici)."""
        for p in self.pairs:
            self.assertNotEqual(p.forward, p.reverse)

    def test_gematria_forward(self):
        """Gématria du forward d'Aleph-Beth = 1+2 = 3."""
        p = self.pairs[0]
        self.assertEqual(p.gematria_forward, 3)

    def test_every_letter_appears(self):
        """Les 22 lettres apparaissent chacune exactement 21 fois."""
        from collections import Counter
        letter_count = Counter()
        for p in self.pairs:
            letter_count[p.letter_a] += 1
            letter_count[p.letter_b] += 1
        self.assertEqual(len(letter_count), 22)
        for letter, count in letter_count.items():
            self.assertEqual(count, 21, f"Lettre {letter} apparaît {count} fois, attendu 21")


class TestRotatePair(unittest.TestCase):
    """rotate_pair() retourne les 2 permutations."""

    def test_basic(self):
        self.assertEqual(rotate_pair("א", "ב"), ("אב", "בא"))

    def test_same_letters(self):
        a, b = rotate_pair("א", "א")
        self.assertEqual(a, "אא")
        self.assertEqual(b, "אא")


# ── Tests des roues d'Abulafia ────────────────────────────────


class TestAbulafiaCi(unittest.TestCase):
    """abulafia_circles() — roue d'une lettre avec les 22."""

    def test_circle_count(self):
        """22 combinaisons par lettre."""
        circles = abulafia_circles("א")
        self.assertEqual(len(circles), 22)

    def test_includes_self(self):
        """La lettre combinée avec elle-même est incluse."""
        circles = abulafia_circles("א")
        self.assertIn("אא", circles)

    def test_first_is_aleph_aleph(self):
        """Premier élément = lettre + aleph."""
        circles = abulafia_circles("א")
        self.assertEqual(circles[0], "אא")

    def test_last_is_aleph_tav(self):
        """Dernier élément = lettre + tav."""
        circles = abulafia_circles("א")
        self.assertEqual(circles[-1], "את")

    def test_bet_circle(self):
        """Roue de Beth : 22 combinaisons commençant par ב."""
        circles = abulafia_circles("ב")
        self.assertEqual(len(circles), 22)
        for c in circles:
            self.assertTrue(c.startswith("ב"))

    def test_invalid_letter(self):
        """Lettre invalide → liste vide."""
        self.assertEqual(abulafia_circles("X"), [])
        self.assertEqual(abulafia_circles(""), [])


class TestAbulafiaCombination(unittest.TestCase):
    """abulafia_combination() — entrelacement de deux mots."""

    def test_same_length(self):
        """Deux mots de même longueur → alternance parfaite."""
        result = abulafia_combination("אמת", "חסד")
        # א ח מ ס ת ד
        self.assertEqual(result, "אחמסתד")

    def test_different_length_a_longer(self):
        """Mot A plus long → lettres restantes à la fin."""
        result = abulafia_combination("אמתה", "חס")
        # א ח מ ס ת ה
        self.assertEqual(result, "אחמסתה")

    def test_different_length_b_longer(self):
        """Mot B plus long → lettres restantes à la fin."""
        result = abulafia_combination("אמ", "חסדה")
        # א ח מ ס ד ה
        self.assertEqual(result, "אחמסדה")

    def test_single_letters(self):
        """Deux lettres simples → concaténation."""
        self.assertEqual(abulafia_combination("א", "ב"), "אב")

    def test_empty_words(self):
        """Mots vides → chaîne vide."""
        self.assertEqual(abulafia_combination("", ""), "")

    def test_non_hebrew_filtered(self):
        """Caractères non-hébreux ignorés."""
        result = abulafia_combination("אXמ", "חYס")
        self.assertEqual(result, "אחמס")


class TestAbulafiWheel(unittest.TestCase):
    """abulafia_wheel() — toutes les permutations d'un mot."""

    def test_two_letter_word(self):
        """2 lettres → 2 permutations."""
        perms = abulafia_wheel("אב")
        self.assertEqual(len(perms), 2)
        self.assertIn("אב", perms)
        self.assertIn("בא", perms)

    def test_three_letter_word(self):
        """3 lettres distinctes → 6 permutations."""
        perms = abulafia_wheel("אבג")
        self.assertEqual(len(perms), 6)

    def test_repeated_letters(self):
        """Lettres répétées → moins de permutations uniques."""
        perms = abulafia_wheel("אאב")
        # 3!/2! = 3 permutations uniques : אאב, אבא, באא
        self.assertEqual(len(perms), 3)

    def test_single_letter(self):
        """1 lettre → 1 permutation."""
        perms = abulafia_wheel("א")
        self.assertEqual(len(perms), 1)
        self.assertEqual(perms[0], "א")

    def test_empty(self):
        """Mot vide → liste vide."""
        self.assertEqual(abulafia_wheel(""), [])

    def test_cap_at_seven(self):
        """Mots >7 lettres sont tronqués à 7 (cap 5040)."""
        word = "אבגדהוזחט"  # 9 lettres
        perms = abulafia_wheel(word)
        # 7! = 5040, mais les 7 premières lettres ont des perms
        self.assertLessEqual(len(perms), 5040)

    def test_original_included(self):
        """Le mot original est dans les permutations."""
        perms = abulafia_wheel("אמת")
        self.assertIn("אמת", perms)

    def test_four_letters(self):
        """4 lettres distinctes → 24 permutations."""
        perms = abulafia_wheel("אבגד")
        self.assertEqual(len(perms), 24)


# ── Tests des tables de permutation ───────────────────────────


class TestTemuraMaps(unittest.TestCase):
    """Vérifier les tables Albam et Avgad."""

    def test_albam_aleph_to_lamed(self):
        """Albam : א → ל (rotation de 11)."""
        self.assertEqual(ALBAM_MAP["א"], "ל")

    def test_albam_lamed_to_aleph(self):
        """Albam : ל → א (involution)."""
        self.assertEqual(ALBAM_MAP["ל"], "א")

    def test_albam_is_involution(self):
        """Albam appliqué deux fois = identité."""
        for ch in ALEPH_BET:
            self.assertEqual(ALBAM_MAP[ALBAM_MAP[ch]], ch)

    def test_avgad_aleph_to_beth(self):
        """Avgad : א → ב (décalage +1)."""
        self.assertEqual(AVGAD_MAP["א"], "ב")

    def test_avgad_tav_to_aleph(self):
        """Avgad : ת → א (cycle)."""
        self.assertEqual(AVGAD_MAP["ת"], "א")

    def test_atbash_bavel_to_sheshakh(self):
        """Atbash : בבל → ששכ (Jérémie 25:26).

        Traditionnellement écrit ששך avec Kaph final, mais notre
        implémentation opère sur les 22 lettres standard sans
        normalisation positionnelle des finales. ב→ש, ב→ש, ל→כ.
        """
        self.assertEqual(apply_temura("בבל", "atbash"), "ששכ")


class TestApplyTemura(unittest.TestCase):
    """apply_temura() — application des 3 méthodes."""

    def test_atbash_aleph_tav(self):
        """Atbash : א↔ת."""
        self.assertEqual(apply_temura("א", "atbash"), "ת")
        self.assertEqual(apply_temura("ת", "atbash"), "א")

    def test_atbash_is_involution(self):
        """Atbash appliqué deux fois = identité."""
        word = "אמת"
        self.assertEqual(apply_temura(apply_temura(word, "atbash"), "atbash"), word)

    def test_albam_word(self):
        """Albam sur un mot."""
        result = apply_temura("א", "albam")
        self.assertEqual(result, "ל")

    def test_avgad_word(self):
        """Avgad sur un mot."""
        result = apply_temura("אבג", "avgad")
        self.assertEqual(result, "בגד")

    def test_unknown_method_raises(self):
        """Méthode inconnue → ValueError."""
        with self.assertRaises(ValueError):
            apply_temura("א", "unknown")

    def test_non_hebrew_preserved(self):
        """Caractères non-hébreux sont préservés."""
        result = apply_temura("א X ב", "atbash")
        self.assertEqual(result, "ת X ש")


class TestPermutationTables(unittest.TestCase):
    """Tables 22x22 de combinaisons."""

    def test_direct_table_size(self):
        """Table directe : 22 lignes × 22 colonnes."""
        t = table_direct()
        self.assertEqual(len(t.rows), 22)
        self.assertEqual(len(t.cols), 22)
        self.assertEqual(len(t.cells), 22)
        self.assertEqual(len(t.cells[0]), 22)

    def test_direct_table_content(self):
        """Table directe [0][0] = אא, [0][1] = אב."""
        t = table_direct()
        self.assertEqual(t.cells[0][0], "אא")
        self.assertEqual(t.cells[0][1], "אב")
        self.assertEqual(t.cells[1][0], "בא")

    def test_atbash_table_content(self):
        """Table Atbash [0][0] = les Atbash de א et א = תת."""
        t = table_atbash()
        self.assertEqual(t.cells[0][0], "תת")

    def test_albam_table_content(self):
        """Table Albam [0][0] = les Albam de א et א = לל."""
        t = table_albam()
        self.assertEqual(t.cells[0][0], "לל")

    def test_avgad_table_content(self):
        """Table Avgad [0][0] = les Avgad de א et א = בב."""
        t = table_avgad()
        self.assertEqual(t.cells[0][0], "בב")

    def test_total_cells(self):
        """22² = 484 cellules au total."""
        t = table_direct()
        total = sum(len(row) for row in t.cells)
        self.assertEqual(total, 484)


# ── Tests du Tzeruf opératif ──────────────────────────────────


class TestTzerufEngine(unittest.TestCase):
    """TzerufEngine — orchestration des opérations."""

    def setUp(self):
        self.engine = TzerufEngine()

    def test_pairs_via_engine(self):
        """pairs_231() accessible via l'engine."""
        pairs = self.engine.pairs_231()
        self.assertEqual(len(pairs), 231)

    def test_circles_via_engine(self):
        """abulafia_circles() accessible via l'engine."""
        circles = self.engine.abulafia_circles("א")
        self.assertEqual(len(circles), 22)

    def test_temura_via_engine(self):
        """apply_temura() accessible via l'engine."""
        self.assertEqual(self.engine.apply_temura("א", "atbash"), "ת")


class TestTzerufQuery(unittest.TestCase):
    """tzeruf_query() — sans base de données."""

    def setUp(self):
        self.engine = TzerufEngine()  # Sans gematria_engine

    def test_query_returns_result(self):
        """tzeruf_query retourne un TzerufResult."""
        result = self.engine.tzeruf_query("אמת")
        self.assertIsInstance(result, TzerufResult)

    def test_query_original_preserved(self):
        """Le mot original est préservé dans le résultat."""
        result = self.engine.tzeruf_query("אמת")
        self.assertEqual(result.original, "אמת")

    def test_query_has_permutations(self):
        """Des permutations sont générées."""
        result = self.engine.tzeruf_query("אמת")
        self.assertEqual(len(result.permutations), 6)  # 3! = 6

    def test_query_has_gematria(self):
        """Chaque permutation a des valeurs gématriques."""
        result = self.engine.tzeruf_query("אמת")
        for perm in result.permutations:
            self.assertIn(perm, result.gematria_values)
            vals = result.gematria_values[perm]
            self.assertIn("standard", vals)
            self.assertIn("ordinal", vals)
            self.assertIn("katan", vals)

    def test_query_no_db_no_equivalences(self):
        """Sans DB, pas d'équivalences."""
        result = self.engine.tzeruf_query("אמת")
        self.assertEqual(result.equivalences, [])

    def test_query_max_perms(self):
        """max_perms limite le nombre de permutations."""
        result = self.engine.tzeruf_query("אבגד", max_perms=5)
        self.assertEqual(len(result.permutations), 5)

    def test_query_gematria_values_correct(self):
        """Vérifier les valeurs gématriques : אמת standard=441."""
        result = self.engine.tzeruf_query("אמת")
        self.assertEqual(result.gematria_values["אמת"]["standard"], 441)
        # Toutes les permutations de אמת ont la même valeur standard
        for perm, vals in result.gematria_values.items():
            self.assertEqual(vals["standard"], 441)


# ── Tests d'intégration avec portes/ ──────────────────────────


class TestPortesIntegration(unittest.TestCase):
    """Vérifier la cohérence entre tzeruf/pairs_231 et portes/."""

    def test_same_count(self):
        """Même nombre : 231 paires dans les deux modules."""
        from portes import list_portes
        tzeruf_pairs = pairs_231()
        portes = list_portes()
        self.assertEqual(len(tzeruf_pairs), len(portes))

    def test_same_letters(self):
        """Les 22 lettres sont les mêmes dans les deux modules."""
        from portes import ALEPH_BET as PORTES_AB
        portes_letters = [letter for letter, name in PORTES_AB]
        self.assertEqual(ALEPH_BET, portes_letters)


# ── Tests edge cases ──────────────────────────────────────────


class TestEdgeCases(unittest.TestCase):

    def test_empty_string_pairs(self):
        """rotate_pair avec chaînes vides."""
        a, b = rotate_pair("", "")
        self.assertEqual(a, "")
        self.assertEqual(b, "")

    def test_combination_empty_with_word(self):
        """Combinaison d'un mot vide avec un mot."""
        result = abulafia_combination("", "אמת")
        self.assertEqual(result, "אמת")

    def test_all_22_circles(self):
        """Les 22 roues fonctionnent toutes."""
        for letter in ALEPH_BET:
            circles = abulafia_circles(letter)
            self.assertEqual(len(circles), 22, f"Roue de {letter} a {len(circles)} éléments")

    def test_temura_consistency_with_shem(self):
        """Le Shem #28 (Temura) utilise la même logique que TzerufEngine."""
        from shemot.language import Temura
        temura_shem = Temura()
        for method in ("atbash", "albam", "avgad"):
            shem_result = temura_shem.run("אמת", method=method)
            engine_result = apply_temura("אמת", method)
            self.assertEqual(shem_result.data["output"], engine_result,
                             f"Divergence pour méthode {method}")


if __name__ == "__main__":
    unittest.main()
