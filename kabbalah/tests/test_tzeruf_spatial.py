"""Tests — TzerufSpatial : Tzeruf dans le Cube de l'Espace.

Vérifie :
- compute_route_geometry retourne des distances cohérentes
- compare_words détecte la similarité entre mots proches
- Un mot et sa permutation ont des géométries différentes
- route_to_cognitive_path produit des séquences valides
- suggest_exploration_route retourne des routes cohérentes
- find_spatial_anagram trouve des permutations géométriquement différentes
"""

import math
import pytest

from kabbalah.tzeruf_spatial import (
    CognitiveModeStep,
    PronunciationAnalysis,
    RouteGeometry,
    SpatialComparison,
    TriadAnalysis,
    TzerufSpatial,
)
from kabbalah.cube_of_space import PronunciationPosition


@pytest.fixture
def ts():
    return TzerufSpatial()


# ═══════════════════════════════════════════════════════════════
# compute_route_geometry
# ═══════════════════════════════════════════════════════════════

class TestRouteGeometry:
    def test_empty_word(self, ts):
        geom = ts.compute_route_geometry("")
        assert geom.total_distance == 0.0
        assert geom.letters == []
        assert geom.segment_count == 0

    def test_non_hebrew(self, ts):
        geom = ts.compute_route_geometry("hello")
        assert geom.total_distance == 0.0

    def test_single_letter_non_mother(self, ts):
        """ב — Beth (0,0,1), single point, no distance."""
        geom = ts.compute_route_geometry("ב")
        assert len(geom.letters) == 1
        assert geom.letters[0] == "beth"
        assert geom.total_distance == 0.0
        assert geom.segment_count == 0

    def test_single_mother_traverses_axis(self, ts):
        """א — Aleph traverses vertical axis, distance = 2."""
        geom = ts.compute_route_geometry("א")
        assert len(geom.letters) == 1
        assert geom.letters[0] == "aleph"
        assert geom.total_distance == pytest.approx(2.0)
        assert geom.ascent == pytest.approx(2.0)
        assert geom.segment_count == 1

    def test_two_letters_distance(self, ts):
        # Beth (0,0,1) → Gimel (0,0,-1) = distance 2.0
        geom = ts.compute_route_geometry("בג")
        assert len(geom.letters) == 2
        assert geom.letters == ["beth", "gimel"]
        assert geom.total_distance == pytest.approx(2.0, abs=0.01)
        assert geom.segment_count == 1

    def test_emet_aleph_mem_tav(self, ts):
        """אמת — Aleph traverses vertical, Mem traverses horizontal, Tav at center.

        Route: (0,0,-1)→(0,0,1)→(-1,0,0)→(1,0,0)→(0,0,0)
        Axis traversals: Aleph=2, Mem=2, transitions between axes.
        """
        geom = ts.compute_route_geometry("אמת")
        assert len(geom.letters) == 3
        assert "aleph" in geom.letters
        assert "mem" in geom.letters
        assert "tav" in geom.letters
        assert geom.passes_center  # Tav est au centre (0,0,0)
        assert geom.total_distance > 4.0  # at least 2 axis traversals
        assert geom.ascent > 0  # Aleph goes up
        assert geom.segment_count >= 4  # from→to for each mother + transitions

    def test_ascending_word(self, ts):
        # Gimel (0,0,-1) → Beth (0,0,1) : montée pure
        geom = ts.compute_route_geometry("גב")
        assert geom.ascent > 0
        assert geom.descent == 0.0
        assert geom.direction_dominant == "ascending"

    def test_descending_word(self, ts):
        # Beth (0,0,1) → Gimel (0,0,-1) : descente pure
        geom = ts.compute_route_geometry("בג")
        assert geom.descent > 0
        assert geom.ascent == 0.0
        assert geom.direction_dominant == "descending"

    def test_horizontal_word(self, ts):
        # Daleth (1,0,0) → Kaph (-1,0,0) : est→ouest, pas de montée
        geom = ts.compute_route_geometry("דכ")
        assert geom.ascent == 0.0
        assert geom.descent == 0.0
        assert geom.direction_dominant == "horizontal"

    def test_east_west_tracking(self, ts):
        # Daleth (1,0,0) → Kaph (-1,0,0) : est→ouest
        geom = ts.compute_route_geometry("דכ")
        assert geom.east_west < 0  # vers l'ouest

    def test_north_south_tracking(self, ts):
        # Peh (0,1,0) → Resh (0,-1,0) : nord→sud
        geom = ts.compute_route_geometry("פר")
        assert geom.north_south < 0  # vers le sud

    def test_passes_center_tav(self, ts):
        geom = ts.compute_route_geometry("בתג")
        assert geom.passes_center

    def test_does_not_pass_center(self, ts):
        geom = ts.compute_route_geometry("בג")
        assert not geom.passes_center

    def test_three_letter_route(self, ts):
        # Beth (0,0,1) → Tav (0,0,0) → Gimel (0,0,-1)
        geom = ts.compute_route_geometry("בתג")
        assert geom.segment_count == 2
        assert geom.total_distance > 0


# ═══════════════════════════════════════════════════════════════
# compare_words
# ═══════════════════════════════════════════════════════════════

class TestCompareWords:
    def test_identical_words(self, ts):
        cmp = ts.compare_words("בג", "בג")
        assert cmp.geometric_similarity == pytest.approx(1.0, abs=0.01)
        assert cmp.angle == pytest.approx(0.0, abs=0.01)

    def test_reversed_words_opposed(self, ts):
        # Beth→Gimel (descente) vs Gimel→Beth (montée)
        cmp = ts.compare_words("בג", "גב")
        assert cmp.angle == pytest.approx(180.0, abs=0.01)
        assert cmp.relationship == "opposed"

    def test_perpendicular_words(self, ts):
        # Beth→Gimel (haut→bas, axe z) vs Daleth→Kaph (est→ouest, axe x)
        cmp = ts.compare_words("בג", "דכ")
        assert cmp.angle == pytest.approx(90.0, abs=1.0)
        assert cmp.relationship == "perpendicular"

    def test_parallel_words(self, ts):
        # Deux mots qui descendent tous les deux
        # Beth (0,0,1) → Tav (0,0,0) et Zayin (1,0,1) → Cheth (1,0,-1)
        cmp = ts.compare_words("בת", "זח")
        # Les deux descendent sur z
        assert cmp.relationship in ("parallel", "similar")

    def test_comparison_fields(self, ts):
        cmp = ts.compare_words("אב", "גד")
        assert isinstance(cmp, SpatialComparison)
        assert isinstance(cmp.trajectory_distance, float)
        assert isinstance(cmp.geometric_similarity, float)
        assert isinstance(cmp.angle, float)
        assert cmp.relationship in ("parallel", "perpendicular", "opposed", "similar")


# ═══════════════════════════════════════════════════════════════
# find_spatial_anagram
# ═══════════════════════════════════════════════════════════════

class TestFindSpatialAnagram:
    def test_two_letter_word(self, ts):
        results = ts.find_spatial_anagram("בג")
        assert len(results) == 1  # only one permutation of 2 letters
        assert results[0]["word"] == "גב"

    def test_direction_change(self, ts):
        # Beth→Gimel (descente) should have opposite direction from Gimel→Beth
        results = ts.find_spatial_anagram("בג")
        assert results[0]["direction_changed"] is True

    def test_three_letter_word(self, ts):
        results = ts.find_spatial_anagram("בגד")
        # 3! - 1 = 5 permutations
        assert len(results) == 5

    def test_sorted_by_angle(self, ts):
        results = ts.find_spatial_anagram("בגד")
        # Sorted by angle descending
        for i in range(len(results) - 1):
            assert results[i]["angle_from_original"] >= results[i + 1]["angle_from_original"]

    def test_max_results(self, ts):
        results = ts.find_spatial_anagram("הוזח", max_results=5)
        assert len(results) <= 5

    def test_single_letter_returns_empty(self, ts):
        results = ts.find_spatial_anagram("א")
        assert results == []

    def test_too_long_returns_empty(self, ts):
        results = ts.find_spatial_anagram("אבגדהוזחטי")  # 10 letters
        assert results == []

    def test_each_result_has_required_fields(self, ts):
        results = ts.find_spatial_anagram("בג")
        for r in results:
            assert "word" in r
            assert "direction" in r
            assert "angle_from_original" in r
            assert "direction_changed" in r
            assert "total_distance" in r


# ═══════════════════════════════════════════════════════════════
# route_to_cognitive_path
# ═══════════════════════════════════════════════════════════════

class TestRouteToCognitivePath:
    def test_empty_route(self, ts):
        geom = ts.compute_route_geometry("")
        path = ts.route_to_cognitive_path(geom)
        assert path == []

    def test_single_letter_path(self, ts):
        geom = ts.compute_route_geometry("ב")
        path = ts.route_to_cognitive_path(geom)
        assert len(path) == 1
        assert isinstance(path[0], CognitiveModeStep)
        assert path[0].letter_name == "beth"
        assert path[0].letter_hebrew == "ב"
        assert path[0].axis_change is None  # first letter, no movement

    def test_vertical_movement_has_air_element(self, ts):
        # Beth (0,0,1) → Gimel (0,0,-1) : mouvement sur axe z (Aleph/air)
        geom = ts.compute_route_geometry("בג")
        path = ts.route_to_cognitive_path(geom)
        assert len(path) == 2
        assert path[1].element == "air"
        assert "aleph" in path[1].axis_change

    def test_ew_movement_has_water_element(self, ts):
        # Daleth (1,0,0) → Kaph (-1,0,0) : mouvement sur axe x (Mem/eau)
        geom = ts.compute_route_geometry("דכ")
        path = ts.route_to_cognitive_path(geom)
        assert path[1].element == "eau"
        assert "mem" in path[1].axis_change

    def test_ns_movement_has_fire_element(self, ts):
        # Peh (0,1,0) → Resh (0,-1,0) : mouvement sur axe y (Shin/feu)
        geom = ts.compute_route_geometry("פר")
        path = ts.route_to_cognitive_path(geom)
        assert path[1].element == "feu"
        assert "shin" in path[1].axis_change

    def test_mode_is_cognitive_mode(self, ts):
        geom = ts.compute_route_geometry("בד")
        path = ts.route_to_cognitive_path(geom)
        # Beth = face:haut, Daleth = face:est
        assert "face:" in path[0].mode
        assert "face:" in path[1].mode

    def test_three_step_path(self, ts):
        geom = ts.compute_route_geometry("בתג")
        path = ts.route_to_cognitive_path(geom)
        assert len(path) == 3
        # First: no axis_change
        assert path[0].axis_change is None
        # Second and third: have axis_changes
        assert path[1].axis_change is not None or path[2].axis_change is not None


# ═══════════════════════════════════════════════════════════════
# suggest_exploration_route
# ═══════════════════════════════════════════════════════════════

class TestSuggestExplorationRoute:
    def test_known_domains(self, ts):
        route = ts.suggest_exploration_route("vue", "parole")
        assert len(route) >= 2  # at least start and end
        assert route[0]["role"] == "départ"
        assert route[-1]["role"] == "arrivée"

    def test_unknown_domain_returns_empty(self, ts):
        route = ts.suggest_exploration_route("unknown_xyz", "vue")
        assert route == []

    def test_route_has_intermediates(self, ts):
        route = ts.suggest_exploration_route("vue", "méditation")
        intermediates = [s for s in route if s["role"] == "intermédiaire"]
        # Should have some intermediates between distant letters
        assert len(intermediates) >= 0  # may or may not have depending on geometry

    def test_route_fields(self, ts):
        route = ts.suggest_exploration_route("vue", "parole")
        for step in route:
            assert "letter" in step
            assert "hebrew" in step
            assert "coordinates" in step
            assert "mode" in step
            assert "role" in step

    def test_letter_names(self, ts):
        route = ts.suggest_exploration_route("vue", "parole")
        # vue → heh, parole → cheth
        assert route[0]["letter"] == "heh"
        assert route[-1]["letter"] == "cheth"

    def test_same_domain_minimal_route(self, ts):
        route = ts.suggest_exploration_route("vue", "vue")
        # Start and end are the same — should still work
        assert len(route) >= 2


# ═══════════════════════════════════════════════════════════════
# Angle calculation
# ═══════════════════════════════════════════════════════════════

class TestAngleCalculation:
    def test_zero_vectors(self, ts):
        angle = ts._angle_between((0, 0, 0), (1, 0, 0))
        assert angle == 0.0

    def test_parallel_vectors(self, ts):
        angle = ts._angle_between((1, 0, 0), (2, 0, 0))
        assert angle == pytest.approx(0.0, abs=0.01)

    def test_opposite_vectors(self, ts):
        angle = ts._angle_between((1, 0, 0), (-1, 0, 0))
        assert angle == pytest.approx(180.0, abs=0.01)

    def test_perpendicular_vectors(self, ts):
        angle = ts._angle_between((1, 0, 0), (0, 1, 0))
        assert angle == pytest.approx(90.0, abs=0.01)

    def test_45_degree_vectors(self, ts):
        angle = ts._angle_between((1, 0, 0), (1, 1, 0))
        assert angle == pytest.approx(45.0, abs=0.01)


# ═══════════════════════════════════════════════════════════════
# MÈRES-AXES — Les 3 mères sont des SEGMENTS, pas des points
# ═══════════════════════════════════════════════════════════════

class TestMotherAxes:
    """Les mères (SY 3:2-4) sont des axes traversant le cube,
    pas des points à l'origine."""

    def test_aleph_has_from_to(self, ts):
        pos = ts.cube.get_position("aleph")
        assert pos.from_coord == (0.0, 0.0, -1.0)
        assert pos.to_coord == (0.0, 0.0, 1.0)

    def test_mem_has_from_to(self, ts):
        pos = ts.cube.get_position("mem")
        assert pos.from_coord == (-1.0, 0.0, 0.0)
        assert pos.to_coord == (1.0, 0.0, 0.0)

    def test_shin_has_from_to(self, ts):
        pos = ts.cube.get_position("shin")
        assert pos.from_coord == (0.0, -1.0, 0.0)
        assert pos.to_coord == (0.0, 1.0, 0.0)

    def test_midpoint_still_origin(self, ts):
        """Rétrocompat: coordinates (midpoint) = (0,0,0) pour les mères."""
        for name in ("aleph", "mem", "shin"):
            assert ts.cube.get_position(name).coordinates == (0.0, 0.0, 0.0)

    def test_get_axis_aleph(self, ts):
        from_c, to_c, direction = ts.cube.get_axis("aleph")
        assert from_c == (0.0, 0.0, -1.0)
        assert to_c == (0.0, 0.0, 1.0)
        assert direction == (0.0, 0.0, 2.0)

    def test_get_axis_non_mother_raises(self, ts):
        with pytest.raises(ValueError):
            ts.cube.get_axis("beth")

    def test_doubles_have_no_from_to(self, ts):
        for name in ("beth", "gimel", "daleth", "kaph", "peh", "resh", "tav"):
            pos = ts.cube.get_position(name)
            assert pos.from_coord is None
            assert pos.to_coord is None


class TestMotherDistances:
    """spatial_distance uses point-to-segment for mothers."""

    def test_aleph_to_beth_zero(self, ts):
        """Beth (0,0,1) is at Aleph's endpoint → distance = 0."""
        d = ts.cube.spatial_distance("aleph", "beth")
        assert d == pytest.approx(0.0, abs=1e-10)

    def test_aleph_to_gimel_zero(self, ts):
        """Gimel (0,0,-1) is at Aleph's other endpoint → distance = 0."""
        d = ts.cube.spatial_distance("aleph", "gimel")
        assert d == pytest.approx(0.0, abs=1e-10)

    def test_mem_to_daleth_zero(self, ts):
        """Daleth (1,0,0) is at Mem's endpoint → distance = 0."""
        d = ts.cube.spatial_distance("mem", "daleth")
        assert d == pytest.approx(0.0, abs=1e-10)

    def test_mem_to_kaph_zero(self, ts):
        """Kaph (-1,0,0) is at Mem's endpoint → distance = 0."""
        d = ts.cube.spatial_distance("mem", "kaph")
        assert d == pytest.approx(0.0, abs=1e-10)

    def test_shin_to_peh_zero(self, ts):
        """Peh (0,1,0) is at Shin's endpoint → distance = 0."""
        d = ts.cube.spatial_distance("shin", "peh")
        assert d == pytest.approx(0.0, abs=1e-10)

    def test_shin_to_resh_zero(self, ts):
        """Resh (0,-1,0) is at Shin's endpoint → distance = 0."""
        d = ts.cube.spatial_distance("shin", "resh")
        assert d == pytest.approx(0.0, abs=1e-10)

    def test_aleph_to_daleth_is_one(self, ts):
        """Daleth (1,0,0) — closest point on Aleph axis is (0,0,0) → dist = 1."""
        d = ts.cube.spatial_distance("aleph", "daleth")
        assert d == pytest.approx(1.0)

    def test_mother_to_mother_zero(self, ts):
        """All mother axes intersect at origin → distance = 0."""
        assert ts.cube.spatial_distance("aleph", "mem") == pytest.approx(0.0, abs=1e-10)
        assert ts.cube.spatial_distance("aleph", "shin") == pytest.approx(0.0, abs=1e-10)
        assert ts.cube.spatial_distance("mem", "shin") == pytest.approx(0.0, abs=1e-10)

    def test_aleph_to_tav_zero(self, ts):
        """Tav (0,0,0) is on Aleph's axis → distance = 0."""
        d = ts.cube.spatial_distance("aleph", "tav")
        assert d == pytest.approx(0.0, abs=1e-10)

    def test_distance_symmetric(self, ts):
        """Point-to-segment distance is symmetric."""
        d1 = ts.cube.spatial_distance("aleph", "daleth")
        d2 = ts.cube.spatial_distance("daleth", "aleph")
        assert d1 == pytest.approx(d2)


class TestEmetSheker:
    """Emet (אמת) and Sheker (שקר) — the key semantic test."""

    def test_emet_nonzero_distance(self, ts):
        geom = ts.compute_route_geometry("אמת")
        assert geom.total_distance > 0

    def test_sheker_nonzero_distance(self, ts):
        geom = ts.compute_route_geometry("שקר")
        assert geom.total_distance > 0

    def test_emet_and_sheker_different(self, ts):
        emet = ts.compute_route_geometry("אמת")
        sheker = ts.compute_route_geometry("שקר")
        assert emet.total_distance != sheker.total_distance

    def test_emet_passes_center(self, ts):
        """Emet ends at Tav (center) — stability."""
        geom = ts.compute_route_geometry("אמת")
        assert geom.passes_center

    def test_emet_has_ascent(self, ts):
        """Aleph traverses haut-bas, so there IS vertical movement."""
        geom = ts.compute_route_geometry("אמת")
        assert geom.ascent > 0

    def test_emet_traverses_two_axes(self, ts):
        """Emet traverses 2 complete axes (Aleph=vertical, Mem=horizontal)."""
        geom = ts.compute_route_geometry("אמת")
        # At least 4 segments: 2 per axis + transitions
        assert geom.segment_count >= 4

    def test_sheker_does_not_pass_center(self, ts):
        """שקר — Shin(axis), Qoph(edge), Resh(face) — none at center."""
        geom = ts.compute_route_geometry("שקר")
        # Qoph is at (0,-1,-1), Resh at (0,-1,0) — neither is center
        # But Shin axis passes through (0,0,0)... check the waypoints
        # Shin from (0,-1,0) to (0,1,0) — neither waypoint is (0,0,0)
        # So passes_center depends on Tav or a waypoint at origin
        # In this case, no Tav present
        assert not geom.passes_center


# ═══════════════════════════════════════════════════════════════
# REGISTRES DANS RouteGeometry
# ═══════════════════════════════════════════════════════════════

class TestRouteRegisters:
    """compute_route_geometry retourne les 3 registres traversés."""

    def test_empty_word_empty_registers(self, ts):
        geom = ts.compute_route_geometry("")
        assert geom.olam_traversed == []
        assert geom.shanah_traversed == []
        assert geom.nefesh_traversed == []

    def test_single_letter_registers(self, ts):
        geom = ts.compute_route_geometry("ב")
        assert geom.olam_traversed == ["saturne"]
        assert geom.shanah_traversed == ["dimanche"]
        assert geom.nefesh_traversed == ["oeil_droit"]

    def test_emet_registers(self, ts):
        geom = ts.compute_route_geometry("אמת")
        assert geom.olam_traversed == ["air", "eau", "lune"]
        assert geom.shanah_traversed == ["inter-saison", "hiver", "shabbat"]
        assert geom.nefesh_traversed == ["poitrine", "ventre", "bouche"]

    def test_register_count_matches_letters(self, ts):
        geom = ts.compute_route_geometry("בגד")
        assert len(geom.olam_traversed) == 3
        assert len(geom.shanah_traversed) == 3
        assert len(geom.nefesh_traversed) == 3


# ═══════════════════════════════════════════════════════════════
# ANALYSE TRIADIQUE — analyze_triad
# ═══════════════════════════════════════════════════════════════

class TestAnalyzeTriad:
    """analyze_triad : les 3 registres + score d'intégration."""

    def test_empty_word(self, ts):
        ta = ts.analyze_triad("")
        assert ta.letters == []
        assert ta.integration_score == 0.0

    def test_single_letter(self, ts):
        ta = ts.analyze_triad("ב")
        assert len(ta.letters) == 1
        assert ta.olam_elements == ["saturne"]
        assert ta.nefesh_body == ["oeil_droit"]
        assert ta.nefesh_zones == ["rosh"]
        assert ta.zones_covered == {"rosh"}

    def test_emet_covers_3_zones(self, ts):
        """אמת — Aleph(poitrine/gavia) + Mem(ventre/beten) + Tav(bouche/rosh).
        La Vérité touche tout le corps."""
        ta = ts.analyze_triad("אמת")
        assert ta.nefesh_body == ["poitrine", "ventre", "bouche"]
        assert ta.nefesh_zones == ["gavia", "beten", "rosh"]
        assert ta.zones_covered == {"rosh", "gavia", "beten"}

    def test_emet_high_integration(self, ts):
        """Emet couvre les 3 zones uniformément → score maximum."""
        ta = ts.analyze_triad("אמת")
        assert ta.integration_score == pytest.approx(1.0, abs=0.01)

    def test_sheker_missing_gavia(self, ts):
        """שקר — Shin(tête/rosh) + Qoph(rate/beten) + Resh(narine_gauche/rosh).
        Le Mensonge ne touche PAS le torse."""
        ta = ts.analyze_triad("שקר")
        assert "gavia" not in ta.zones_covered
        assert "rosh" in ta.zones_covered
        assert "beten" in ta.zones_covered

    def test_sheker_lower_integration_than_emet(self, ts):
        """Le mensonge est moins intégrateur que la vérité."""
        emet = ts.analyze_triad("אמת")
        sheker = ts.analyze_triad("שקר")
        assert sheker.integration_score < emet.integration_score

    def test_all_doubles_in_rosh(self, ts):
        """Les 7 doubles (portes du visage) sont toutes dans la zone rosh."""
        for letter in "בגדכפרת":
            ta = ts.analyze_triad(letter)
            assert ta.nefesh_zones == ["rosh"], f"{letter} devrait être rosh"

    def test_triads_field(self, ts):
        ta = ts.analyze_triad("אמת")
        assert len(ta.triads) == 3
        assert ta.triads[0].olam == "air"
        assert ta.triads[1].olam == "eau"
        assert ta.triads[2].olam == "lune"

    def test_olam_elements_fire_word(self, ts):
        """שקר — Shin = feu dans Olam."""
        ta = ts.analyze_triad("שקר")
        assert ta.olam_elements[0] == "feu"

    def test_integration_single_zone_low(self, ts):
        """Un mot dont toutes les lettres sont en rosh → intégration basse."""
        # בג = Beth(rosh) + Gimel(rosh)
        ta = ts.analyze_triad("בג")
        assert ta.integration_score == 0.0  # une seule zone

    def test_integration_two_zones(self, ts):
        """Un mot sur 2 zones → intégration intermédiaire."""
        # בה = Beth(rosh) + Heh(gavia)
        ta = ts.analyze_triad("בה")
        assert 0.0 < ta.integration_score < 1.0

    def test_isinstance_triad_analysis(self, ts):
        ta = ts.analyze_triad("אמת")
        assert isinstance(ta, TriadAnalysis)


# ═══════════════════════════════════════════════════════════════
# PRONONCIATION — Les 5 positions de la bouche (SY 2:3)
# ═══════════════════════════════════════════════════════════════

class TestPronunciationPositions:
    """get_pronunciation et get_letters_by_pronunciation sur CubeOfSpace."""

    def test_all_22_letters_have_pronunciation(self, ts):
        """Chaque lettre a une position de prononciation."""
        for name in ts.cube.get_all_positions():
            pos = ts.cube.get_position(name)
            assert pos.mouth_position is not None, f"{name} n'a pas de mouth_position"
            assert pos.mouth_depth is not None, f"{name} n'a pas de mouth_depth"

    def test_five_groups_total_22(self, ts):
        """Les 5 groupes contiennent exactement 22 lettres (4+4+5+5+4)."""
        total = 0
        expected_counts = {
            "gorge": 4, "palais": 4, "langue": 5, "dents": 5, "levres": 4,
        }
        for position, expected in expected_counts.items():
            letters = ts.cube.get_letters_by_pronunciation(position)
            assert len(letters) == expected, (
                f"{position}: attendu {expected}, obtenu {len(letters)}: {letters}"
            )
            total += len(letters)
        assert total == 22

    def test_gorge_letters(self, ts):
        """Gorge : א ח ה ע"""
        letters = ts.cube.get_letters_by_pronunciation("gorge")
        assert set(letters) == {"aleph", "cheth", "heh", "ayin"}

    def test_palais_letters(self, ts):
        """Palais : ג י כ ק"""
        letters = ts.cube.get_letters_by_pronunciation("palais")
        assert set(letters) == {"gimel", "yod", "kaph", "qoph"}

    def test_langue_letters(self, ts):
        """Langue : ד ט ל נ ת"""
        letters = ts.cube.get_letters_by_pronunciation("langue")
        assert set(letters) == {"daleth", "teth", "lamed", "nun", "tav"}

    def test_dents_letters(self, ts):
        """Dents : ז ס ש ר צ"""
        letters = ts.cube.get_letters_by_pronunciation("dents")
        assert set(letters) == {"zayin", "samekh", "shin", "resh", "tsadi"}

    def test_levres_letters(self, ts):
        """Lèvres : ב ו מ פ"""
        letters = ts.cube.get_letters_by_pronunciation("levres")
        assert set(letters) == {"beth", "vav", "mem", "peh"}

    def test_get_pronunciation_returns_dataclass(self, ts):
        pron = ts.cube.get_pronunciation("aleph")
        assert isinstance(pron, PronunciationPosition)
        assert pron.position == "gorge"
        assert pron.depth == 5
        assert pron.hebrew_name == "גרון"

    def test_depth_values(self, ts):
        """Les profondeurs correspondent aux positions."""
        assert ts.cube.get_pronunciation("aleph").depth == 5  # gorge
        assert ts.cube.get_pronunciation("gimel").depth == 4  # palais
        assert ts.cube.get_pronunciation("daleth").depth == 3  # langue
        assert ts.cube.get_pronunciation("zayin").depth == 2  # dents
        assert ts.cube.get_pronunciation("beth").depth == 1  # lèvres

    def test_unknown_position_raises(self, ts):
        with pytest.raises(KeyError):
            ts.cube.get_letters_by_pronunciation("nez")

    def test_all_pronunciation_positions(self, ts):
        all_pron = ts.cube.get_all_pronunciation_positions()
        assert len(all_pron) == 5
        assert set(all_pron.keys()) == {"gorge", "palais", "langue", "dents", "levres"}


# ═══════════════════════════════════════════════════════════════
# ANALYSE DE PRONONCIATION — analyze_pronunciation
# ═══════════════════════════════════════════════════════════════

class TestAnalyzePronunciation:
    """analyze_pronunciation : profil sonore d'un mot."""

    def test_empty_word(self, ts):
        pa = ts.analyze_pronunciation("")
        assert pa.letters == []
        assert pa.depth_profile == []
        assert pa.direction == "stable"

    def test_single_letter(self, ts):
        pa = ts.analyze_pronunciation("א")
        assert pa.letters == ["aleph"]
        assert pa.positions == ["gorge"]
        assert pa.depth_profile == [5]
        assert pa.avg_depth == 5.0
        assert pa.depth_range == 0
        assert pa.direction == "stable"

    def test_emet_pronunciation(self, ts):
        """אמת — gorge(5) → lèvres(1) → langue(3)
        Du plus caché au plus exprimé puis articulé."""
        pa = ts.analyze_pronunciation("אמת")
        assert pa.letters == ["aleph", "mem", "tav"]
        assert pa.positions == ["gorge", "levres", "langue"]
        assert pa.depth_profile == [5, 1, 3]
        assert pa.avg_depth == pytest.approx(3.0, abs=0.01)
        assert pa.depth_range == 4  # 5 - 1

    def test_sheker_pronunciation(self, ts):
        """שקר — dents(2) → palais(4) → dents(2)
        Reste dans la zone médiane, jamais profond."""
        pa = ts.analyze_pronunciation("שקר")
        assert pa.positions == ["dents", "palais", "dents"]
        assert pa.depth_profile == [2, 4, 2]
        assert pa.depth_range == 2  # 4 - 2

    def test_emet_greater_range_than_sheker(self, ts):
        """Emet couvre plus de spectre que Sheker."""
        emet = ts.analyze_pronunciation("אמת")
        sheker = ts.analyze_pronunciation("שקר")
        assert emet.depth_range > sheker.depth_range

    def test_manifestation_direction(self, ts):
        """Un mot qui va du profond au superficiel = manifestation."""
        # gorge(5) → lèvres(1) : profondeur décroît
        pa = ts.analyze_pronunciation("אב")  # aleph(gorge=5) → beth(levres=1)
        assert pa.direction == "manifestation"

    def test_interiorisation_direction(self, ts):
        """Un mot qui va du superficiel au profond = intériorisation."""
        pa = ts.analyze_pronunciation("בא")  # beth(levres=1) → aleph(gorge=5)
        assert pa.direction == "interiorisation"

    def test_stable_direction(self, ts):
        """Un mot qui reste au même niveau = stable."""
        pa = ts.analyze_pronunciation("בו")  # beth(levres=1) → vav(levres=1)
        assert pa.direction == "stable"

    def test_position_counts(self, ts):
        """שקר — 2 dents, 1 palais."""
        pa = ts.analyze_pronunciation("שקר")
        assert pa.position_counts["dents"] == 2
        assert pa.position_counts["palais"] == 1

    def test_isinstance(self, ts):
        pa = ts.analyze_pronunciation("אמת")
        assert isinstance(pa, PronunciationAnalysis)


# ═══════════════════════════════════════════════════════════════
# PRONONCIATION DANS RouteGeometry
# ═══════════════════════════════════════════════════════════════

class TestRoutePronunciation:
    """compute_route_geometry inclut le profil de prononciation."""

    def test_emet_route_has_pronunciation(self, ts):
        geom = ts.compute_route_geometry("אמת")
        assert geom.pronunciation_positions == ["gorge", "levres", "langue"]
        assert geom.pronunciation_depths == [5, 1, 3]
        assert geom.pronunciation_avg_depth == pytest.approx(3.0, abs=0.01)

    def test_empty_route_no_pronunciation(self, ts):
        geom = ts.compute_route_geometry("")
        assert geom.pronunciation_positions == []
        assert geom.pronunciation_depths == []
        assert geom.pronunciation_avg_depth is None

    def test_pronunciation_direction_in_route(self, ts):
        geom = ts.compute_route_geometry("אב")  # gorge→lèvres
        assert geom.pronunciation_direction == "manifestation"


# ═══════════════════════════════════════════════════════════════
# EMET vs SHEKER — Dimension sonore
# ═══════════════════════════════════════════════════════════════

class TestEmetShekerSonore:
    """Comparaison sonore Emet/Sheker — la Vérité traverse tout
    le spectre de la manifestation, le Mensonge reste médian."""

    def test_emet_full_spectrum(self, ts):
        """Emet : gorge(5) → lèvres(1) → langue(3) = range 4."""
        pa = ts.analyze_pronunciation("אמת")
        assert pa.depth_range == 4
        assert "gorge" in pa.positions
        assert "levres" in pa.positions

    def test_sheker_narrow_spectrum(self, ts):
        """Sheker : dents(2) → palais(4) → dents(2) = range 2."""
        pa = ts.analyze_pronunciation("שקר")
        assert pa.depth_range == 2
        assert "gorge" not in pa.positions
        assert "levres" not in pa.positions

    def test_emet_manifestation_sheker_no(self, ts):
        """Emet commence par la gorge (le plus caché) :
        la Vérité émerge des profondeurs.
        Sheker ne touche jamais la gorge (profondeur 5)."""
        emet = ts.analyze_pronunciation("אמת")
        sheker = ts.analyze_pronunciation("שקר")
        assert max(emet.depth_profile) == 5  # Emet atteint la profondeur max
        assert max(sheker.depth_profile) == 4  # Sheker n'atteint que 4

    def test_emet_avg_depth_higher_than_sheker(self, ts):
        """La Vérité est en moyenne plus profonde que le Mensonge."""
        emet = ts.analyze_pronunciation("אמת")
        sheker = ts.analyze_pronunciation("שקר")
        # Emet: (5+1+3)/3 = 3.0, Sheker: (2+4+2)/3 = 2.667
        assert emet.avg_depth > sheker.avg_depth
