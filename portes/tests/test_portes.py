"""Tests pour les 231 Portes et leur enrichissement SY."""

import pytest

from portes import (
    Porte, ALEPH_BET,
    get_porte, list_portes, portes_stats,
)
from portes.sy_enrichment import enrich_porte, interaction_class_stats


# ── Constantes ────────────────────────────────────────────────

TOTAL_GATES = 231  # C(22, 2)
TOTAL_LETTERS = 22


class TestBasics:
    """Vérifications structurelles des 231 portes."""

    def test_total_count(self):
        assert len(list_portes()) == TOTAL_GATES

    def test_all_numbered(self):
        numbers = {g.number for g in list_portes()}
        assert numbers == set(range(1, TOTAL_GATES + 1))

    def test_no_duplicate_ids(self):
        ids = [g.gate_id for g in list_portes()]
        assert len(ids) == len(set(ids))

    def test_alphabet_size(self):
        assert len(ALEPH_BET) == TOTAL_LETTERS

    def test_all_hebrew_present(self):
        """Chaque porte a deux lettres hébraïques distinctes."""
        for g in list_portes():
            assert g.letter_a != g.letter_b
            assert len(g.letter_a) == 1
            assert len(g.letter_b) == 1


class TestLookup:
    """Lookup par identifiant (latin, hébreu, inversé)."""

    def test_latin_lookup(self):
        g = get_porte("aleph-beth")
        assert g is not None
        assert g.name_a == "aleph"
        assert g.name_b == "beth"

    def test_case_insensitive(self):
        g = get_porte("ALEPH-BETH")
        assert g is not None
        assert g.gate_id == "aleph-beth"

    def test_reversed_order(self):
        g = get_porte("beth-aleph")
        assert g is not None
        assert g.gate_id == "aleph-beth"

    def test_hebrew_lookup(self):
        g = get_porte("\u05d0-\u05d1")  # א-ב
        assert g is not None
        assert g.gate_id == "aleph-beth"

    def test_invalid_returns_none(self):
        assert get_porte("foo-bar") is None
        assert get_porte("aleph") is None
        assert get_porte("") is None


class TestSYEnrichment:
    """Enrichissement par le Sefer Yetzirah."""

    def test_all_enriched(self):
        """Toutes les portes ont une gematria > 0."""
        for g in list_portes():
            assert g.gematria_sum > 0, f"{g.gate_id} manque de gematria"

    def test_gematria_sum_correct(self):
        """Vérification manuelle : aleph(1) + beth(2) = 3."""
        g = get_porte("aleph-beth")
        assert g.gematria_sum == 3

    def test_gematria_product_correct(self):
        """aleph(1) × beth(2) = 2."""
        g = get_porte("aleph-beth")
        assert g.gematria_product == 2

    def test_shin_tav_gematria(self):
        """shin(300) + tav(400) = 700 — la somme max."""
        g = get_porte("shin-tav")
        assert g.gematria_sum == 700

    def test_aleph_beth_gematria_min(self):
        """aleph(1) + beth(2) = 3 — la somme min."""
        g = get_porte("aleph-beth")
        assert g.gematria_sum == 3

    def test_types_assigned(self):
        """Chaque porte a des types de lettres."""
        for g in list_portes():
            assert g.type_a in ("mother", "double", "simple"), f"{g.gate_id}: type_a={g.type_a}"
            assert g.type_b in ("mother", "double", "simple"), f"{g.gate_id}: type_b={g.type_b}"

    def test_interaction_class_assigned(self):
        for g in list_portes():
            assert g.interaction_class in (
                "mother-mother", "mother-double", "mother-simple",
                "double-double", "double-simple", "simple-simple",
            ), f"{g.gate_id}: {g.interaction_class}"

    def test_sy_correspondences_present(self):
        """Chaque porte a des correspondances SY pour les deux lettres."""
        for g in list_portes():
            assert isinstance(g.sy_a, dict) and len(g.sy_a) > 0, f"{g.gate_id}: sy_a vide"
            assert isinstance(g.sy_b, dict) and len(g.sy_b) > 0, f"{g.gate_id}: sy_b vide"


class TestInteractionClasses:
    """Vérification des classes d'interaction.

    3 mères, 7 doubles, 12 simples →
      mère×mère = C(3,2) = 3
      mère×double = 3×7 = 21
      mère×simple = 3×12 = 36
      double×double = C(7,2) = 21
      double×simple = 7×12 = 84
      simple×simple = C(12,2) = 66
      Total = 231 ✓
    """

    def test_mother_mother_count(self):
        gates = [g for g in list_portes() if g.interaction_class == "mother-mother"]
        assert len(gates) == 3

    def test_mother_double_count(self):
        gates = [g for g in list_portes() if g.interaction_class == "mother-double"]
        assert len(gates) == 21

    def test_mother_simple_count(self):
        gates = [g for g in list_portes() if g.interaction_class == "mother-simple"]
        assert len(gates) == 36

    def test_double_double_count(self):
        gates = [g for g in list_portes() if g.interaction_class == "double-double"]
        assert len(gates) == 21

    def test_double_simple_count(self):
        gates = [g for g in list_portes() if g.interaction_class == "double-simple"]
        assert len(gates) == 84

    def test_simple_simple_count(self):
        gates = [g for g in list_portes() if g.interaction_class == "simple-simple"]
        assert len(gates) == 66

    def test_total_interaction_classes(self):
        stats = interaction_class_stats(list_portes())
        assert sum(stats.values()) == TOTAL_GATES


class TestMothers:
    """Les 3 Mères : Shin(feu), Mem(eau), Aleph(air)."""

    @pytest.mark.parametrize("gate_id,elements", [
        ("aleph-shin", {"air", "feu"}),
        ("aleph-mem", {"air", "eau"}),
        ("mem-shin", {"eau", "feu"}),
    ])
    def test_mother_elements(self, gate_id, elements):
        g = get_porte(gate_id)
        found = set()
        if "element" in g.sy_a:
            found.add(g.sy_a["element"])
        if "element" in g.sy_b:
            found.add(g.sy_b["element"])
        assert found == elements

    def test_shin_mem_fire_water(self):
        """Shin×Mem = feu×eau — l'opposition primordiale."""
        g = get_porte("shin-mem")
        assert "feu" in g.sy_description
        assert "eau" in g.sy_description


class TestDoubles:
    """Les 7 Doubles et leurs planètes."""

    @pytest.mark.parametrize("name,planet", [
        ("beth", "saturne"), ("gimel", "jupiter"), ("daleth", "mars"),
        ("kaph", "soleil"), ("peh", "vénus"), ("resh", "mercure"), ("tav", "lune"),
    ])
    def test_double_planet_in_sy(self, name, planet):
        """Chaque double porte sa planète dans sy_a ou sy_b."""
        # Trouver une porte qui contient cette lettre
        g = get_porte(f"{name}-tav") if name != "tav" else get_porte("beth-tav")
        sy = g.sy_a if g.name_a == name else g.sy_b
        assert sy.get("planet") == planet


class TestSimples:
    """Les 12 Simples et leurs sens/zodiaques."""

    @pytest.mark.parametrize("name,sense,zodiac", [
        ("heh", "vue", "bélier"),
        ("vav", "ouïe", "taureau"),
        ("zayin", "odorat", "gémeaux"),
        ("lamed", "mouvement", "balance"),
        ("qoph", "méditation", "poissons"),
    ])
    def test_simple_correspondences(self, name, sense, zodiac):
        g = get_porte(f"aleph-{name}")
        sy = g.sy_a if g.name_a == name else g.sy_b
        assert sy.get("sense") == sense
        assert sy.get("zodiac") == zodiac


class TestGematria:
    """Propriétés gematriques des portes."""

    def test_sum_always_positive(self):
        for g in list_portes():
            assert g.gematria_sum > 0

    def test_product_always_positive(self):
        for g in list_portes():
            assert g.gematria_product > 0

    def test_sum_equals_letter_values(self):
        """Vérification par calcul indépendant pour quelques portes."""
        checks = {
            "shin-tav": 300 + 400,     # 700
            "aleph-beth": 1 + 2,       # 3
            "yod-kaph": 10 + 20,       # 30
            "qoph-resh": 100 + 200,    # 300
            "mem-nun": 40 + 50,        # 90
        }
        for gate_id, expected_sum in checks.items():
            g = get_porte(gate_id)
            assert g.gematria_sum == expected_sum, f"{gate_id}: {g.gematria_sum} != {expected_sum}"

    def test_gematria_range(self):
        stats = portes_stats()
        assert stats["gematria_range"] == (3, 700)


class TestStats:
    """Statistiques globales."""

    def test_stats_keys(self):
        stats = portes_stats()
        expected_keys = {
            "total", "defined", "partial", "undefined",
            "communicating", "silent", "protocols",
            "sephiroth_connectivity", "interaction_classes",
            "gematria_range", "sy_enriched",
        }
        assert set(stats.keys()) == expected_keys

    def test_all_enriched_count(self):
        stats = portes_stats()
        assert stats["sy_enriched"] == TOTAL_GATES

    def test_interaction_classes_sum(self):
        stats = portes_stats()
        assert sum(stats["interaction_classes"].values()) == TOTAL_GATES


class TestEnrichPorteStandalone:
    """Test de la fonction enrich_porte indépendamment."""

    def test_returns_all_keys(self):
        result = enrich_porte("aleph", "beth")
        expected_keys = {
            "gematria_sum", "gematria_product",
            "type_a", "type_b", "interaction_class",
            "sy_a", "sy_b", "sy_description",
        }
        assert set(result.keys()) == expected_keys

    def test_mother_double_interaction(self):
        result = enrich_porte("aleph", "beth")
        assert result["type_a"] == "mother"
        assert result["type_b"] == "double"
        assert result["interaction_class"] == "mother-double"

    def test_simple_simple_interaction(self):
        result = enrich_porte("heh", "vav")
        assert result["interaction_class"] == "simple-simple"


# ═══════════════════════════════════════════════════════════════
# CUBE DISTANCE — distance 3D du Cube de l'Espace
# ═══════════════════════════════════════════════════════════════

class TestCubeDistance:
    """Chaque porte a une distance 3D calculée par le Cube."""

    def test_all_portes_have_cube_distance(self):
        """Les 231 portes ont toutes une cube_distance non-None."""
        for g in list_portes():
            assert g.cube_distance is not None, f"{g.gate_id} manque cube_distance"
            assert g.cube_distance >= 0.0

    def test_cube_distance_range(self):
        """Les distances sont dans [0, 2*sqrt(3)] (diagonale max du cube)."""
        import math
        max_diag = 2 * math.sqrt(3)  # ~3.464
        for g in list_portes():
            assert g.cube_distance <= max_diag + 0.01, (
                f"{g.gate_id}: distance {g.cube_distance} > diagonale {max_diag}"
            )

    def test_opposite_faces_distance_2(self):
        """Faces opposées (beth-gimel) ont distance 2.0."""
        import math
        g = get_porte("beth-gimel")
        assert g is not None
        assert g.cube_distance == pytest.approx(2.0)

    def test_adjacent_faces_distance_sqrt2(self):
        """Faces adjacentes (beth-daleth) ont distance sqrt(2)."""
        import math
        g = get_porte("beth-daleth")
        assert g is not None
        assert g.cube_distance == pytest.approx(math.sqrt(2), abs=0.001)

    def test_mothers_distance_zero(self):
        """Les 3 mères sont toutes à l'origine → distance 0."""
        for pair in ("aleph-mem", "aleph-shin", "mem-shin"):
            g = get_porte(pair)
            assert g is not None
            assert g.cube_distance == pytest.approx(0.0)
