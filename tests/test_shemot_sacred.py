"""Tests pour les attributs sacrés des 72 Shemot.

Vérifie le chargement du YAML, l'enrichissement des Shem,
la cohérence des données, et la commande CLI shem info.
"""

import unittest
from pathlib import Path
from unittest.mock import patch

import yaml


# ── Chargement YAML brut ────────────────────────────────────


YAML_PATH = Path(__file__).parent.parent / "shemot" / "shemot_72.yaml"


def _load_yaml() -> list[dict]:
    with open(YAML_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data["shemot"]


class TestYamlFile(unittest.TestCase):
    """Le fichier YAML existe et contient 72 entrées bien formées."""

    def test_yaml_exists(self):
        self.assertTrue(YAML_PATH.exists())

    def test_yaml_has_72_entries(self):
        entries = _load_yaml()
        self.assertEqual(len(entries), 72)

    def test_yaml_numbers_1_to_72(self):
        entries = _load_yaml()
        numbers = [e["number"] for e in entries]
        self.assertEqual(numbers, list(range(1, 73)))

    def test_yaml_required_fields(self):
        required = {
            "number", "trigram", "transliteration", "suffix",
            "angel_name", "choir", "sephirah", "zodiac_sign",
            "zodiac_degrees", "element", "calendar_start",
            "calendar_end", "psalm_verse",
        }
        entries = _load_yaml()
        for entry in entries:
            for field in required:
                self.assertIn(
                    field, entry,
                    f"Shem #{entry.get('number', '?')} manque le champ '{field}'"
                )
                self.assertIsNotNone(
                    entry[field],
                    f"Shem #{entry['number']} a '{field}' = None"
                )


class TestYamlCoherence(unittest.TestCase):
    """Cohérence interne des données YAML."""

    @classmethod
    def setUpClass(cls):
        cls.entries = _load_yaml()

    def test_suffixes_are_el_or_yah(self):
        for e in self.entries:
            self.assertIn(
                e["suffix"], ("El", "Yah"),
                f"Shem #{e['number']} a suffix={e['suffix']}"
            )

    def test_elements_valid(self):
        valid = {"Feu", "Terre", "Air", "Eau"}
        for e in self.entries:
            self.assertIn(
                e["element"], valid,
                f"Shem #{e['number']} a element={e['element']}"
            )

    def test_zodiac_signs_valid(self):
        valid = {
            "Bélier", "Taureau", "Gémeaux", "Cancer",
            "Lion", "Vierge", "Balance", "Scorpion",
            "Sagittaire", "Capricorne", "Verseau", "Poissons",
        }
        for e in self.entries:
            self.assertIn(
                e["zodiac_sign"], valid,
                f"Shem #{e['number']} a zodiac_sign={e['zodiac_sign']}"
            )

    def test_choirs_valid(self):
        valid = {
            "Seraphim", "Cherubim", "Trones", "Dominations",
            "Puissances", "Vertus", "Principautes", "Archanges", "Anges",
        }
        for e in self.entries:
            self.assertIn(
                e["choir"], valid,
                f"Shem #{e['number']} a choir={e['choir']}"
            )

    def test_sephirot_valid(self):
        valid = {
            "Keter", "Hokhmah", "Binah", "Hesed",
            "Gevurah", "Tiferet", "Netzah", "Hod", "Yesod",
        }
        for e in self.entries:
            self.assertIn(
                e["sephirah"], valid,
                f"Shem #{e['number']} a sephirah={e['sephirah']}"
            )

    def test_8_angels_per_choir(self):
        """9 chœurs × 8 anges = 72."""
        from collections import Counter
        choir_counts = Counter(e["choir"] for e in self.entries)
        for choir, count in choir_counts.items():
            self.assertEqual(
                count, 8,
                f"Chœur {choir} a {count} anges (attendu 8)"
            )

    def test_zodiac_covers_360_degrees(self):
        """72 quinaires × 5° = 360°."""
        self.assertEqual(len(self.entries), 72)
        for e in self.entries:
            deg = e["zodiac_degrees"]
            start, end = deg.split("-")
            self.assertEqual(
                int(end) - int(start), 5,
                f"Shem #{e['number']} a quinaire {deg} (attendu 5°)"
            )

    def test_element_matches_zodiac(self):
        """L'élément est déterminé par le signe zodiacal."""
        sign_to_element = {
            "Bélier": "Feu", "Lion": "Feu", "Sagittaire": "Feu",
            "Taureau": "Terre", "Vierge": "Terre", "Capricorne": "Terre",
            "Gémeaux": "Air", "Balance": "Air", "Verseau": "Air",
            "Cancer": "Eau", "Scorpion": "Eau", "Poissons": "Eau",
        }
        for e in self.entries:
            expected = sign_to_element[e["zodiac_sign"]]
            self.assertEqual(
                e["element"], expected,
                f"Shem #{e['number']} : {e['zodiac_sign']}→{e['element']} "
                f"(attendu {expected})"
            )

    def test_choir_sephirah_mapping(self):
        """Chaque chœur correspond à une Sephirah fixe."""
        choir_sephirah = {
            "Seraphim": "Keter", "Cherubim": "Hokhmah",
            "Trones": "Binah", "Dominations": "Hesed",
            "Puissances": "Gevurah", "Vertus": "Tiferet",
            "Principautes": "Netzah", "Archanges": "Hod",
            "Anges": "Yesod",
        }
        for e in self.entries:
            expected = choir_sephirah[e["choir"]]
            self.assertEqual(
                e["sephirah"], expected,
                f"Shem #{e['number']} : chœur {e['choir']}→{e['sephirah']} "
                f"(attendu {expected})"
            )

    def test_yabamiah_is_genesis(self):
        """Le 70e nom est le seul associé à la Genèse, pas à un psaume."""
        entry_70 = self.entries[69]
        self.assertEqual(entry_70["number"], 70)
        self.assertTrue(entry_70["psalm_verse"].startswith("Gen"))


# ── Enrichissement des instances Shem ────────────────────────


class TestShemEnrichment(unittest.TestCase):
    """Les attributs sacrés sont bien chargés sur les instances Shem."""

    def test_all_72_have_angel_name(self):
        from shemot import list_shemot
        items = list_shemot()
        for item in items:
            self.assertIsNotNone(
                item["angel_name"],
                f"Shem #{item['number']} n'a pas d'angel_name"
            )

    def test_all_72_have_suffix(self):
        from shemot import list_shemot
        items = list_shemot()
        for item in items:
            self.assertIn(
                item["suffix"], ("El", "Yah"),
                f"Shem #{item['number']} a suffix={item['suffix']}"
            )

    def test_all_72_have_choir(self):
        from shemot import list_shemot
        items = list_shemot()
        for item in items:
            self.assertIsNotNone(
                item["choir"],
                f"Shem #{item['number']} n'a pas de choir"
            )

    def test_all_72_have_psalm(self):
        from shemot import list_shemot
        items = list_shemot()
        for item in items:
            self.assertIsNotNone(
                item["psalm_verse"],
                f"Shem #{item['number']} n'a pas de psalm_verse"
            )

    def test_get_shem_by_number(self):
        from shemot import get_shem_by_number
        shem = get_shem_by_number(1)
        self.assertIsNotNone(shem)
        self.assertEqual(shem.number, 1)
        self.assertEqual(shem.angel_name, "Vehuiah")
        self.assertEqual(shem.suffix, "Yah")
        self.assertEqual(shem.choir, "Seraphim")
        self.assertEqual(shem.sacred_sephirah, "Keter")

    def test_get_shem_by_number_72(self):
        from shemot import get_shem_by_number
        shem = get_shem_by_number(72)
        self.assertIsNotNone(shem)
        self.assertEqual(shem.angel_name, "Mumiah")
        self.assertEqual(shem.suffix, "Yah")
        self.assertEqual(shem.choir, "Anges")
        self.assertEqual(shem.sacred_sephirah, "Yesod")
        self.assertEqual(shem.psalm_verse, "Ps 116:7")

    def test_get_shem_by_number_invalid(self):
        from shemot import get_shem_by_number
        self.assertIsNone(get_shem_by_number(0))
        self.assertIsNone(get_shem_by_number(73))
        self.assertIsNone(get_shem_by_number(999))

    def test_shem_attributes_accessible(self):
        """Tous les attributs sacrés sont accessibles via l'instance."""
        from shemot import get_shem_by_number
        shem = get_shem_by_number(26)  # Haaiah / GematriaCalc
        self.assertEqual(shem.suffix, "Yah")
        self.assertEqual(shem.angel_name, "Haaiah")
        self.assertEqual(shem.choir, "Dominations")
        self.assertEqual(shem.sacred_sephirah, "Hesed")
        self.assertEqual(shem.zodiac_sign, "Lion")
        self.assertEqual(shem.zodiac_degrees, "5-10")
        self.assertEqual(shem.element, "Feu")
        self.assertEqual(shem.calendar_start, "28 juillet")
        self.assertEqual(shem.calendar_end, "1 août")
        self.assertEqual(shem.psalm_verse, "Ps 119:145")

    def test_mikael_is_42(self):
        """Mikael (מיכ) est le 42e — vérification croisée."""
        from shemot import get_shem_by_number
        shem = get_shem_by_number(42)
        self.assertEqual(shem.angel_name, "Mikael")
        self.assertEqual(shem.trigram, "מיכ")
        self.assertEqual(shem.element, "Air")


# ── CLI shem info ────────────────────────────────────────────


class TestCliShemInfo(unittest.TestCase):
    """La commande CLI etz shem info fonctionne."""

    def _run_cli(self, identifier: str) -> str:
        """Capturer la sortie de cmd_shem_info."""
        import io
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from main import cmd_shem_info
        captured = io.StringIO()
        sys.stdout = captured
        try:
            cmd_shem_info(identifier)
        finally:
            sys.stdout = sys.__stdout__
        return captured.getvalue()

    def test_info_by_number(self):
        output = self._run_cli("1")
        self.assertIn("Vehuiah", output)
        self.assertIn("Seraphim", output)
        self.assertIn("Keter", output)
        self.assertIn("Ps 3:3", output)

    def test_info_by_skill_id(self):
        output = self._run_cli("gematria_calc")
        self.assertIn("Haaiah", output)
        self.assertIn("Dominations", output)
        self.assertIn("Lion", output)

    def test_info_unknown(self):
        output = self._run_cli("999")
        self.assertIn("inconnu", output)

    def test_info_shows_zodiac(self):
        output = self._run_cli("42")
        self.assertIn("Balance", output)
        self.assertIn("25-30", output)
        self.assertIn("Air", output)

    def test_info_shows_calendar(self):
        output = self._run_cli("72")
        self.assertIn("16 mars", output)
        self.assertIn("20 mars", output)


if __name__ == "__main__":
    unittest.main()
