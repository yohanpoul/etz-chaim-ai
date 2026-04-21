"""Tests du Cube de l'Espace — Sefer Yetzirah, Gra.

Couvre : 22 positions, 6 sceaux, 3 classes de lettres enrichies,
navigation, profils complets, lookups.
"""

import math
import pytest

from kabbalah.cube_of_space import CubeOfSpace, Triad


@pytest.fixture
def cube():
    return CubeOfSpace()


# ═══════════════════════════════════════════════════════════════
# COMPLÉTUDE
# ═══════════════════════════════════════════════════════════════

class TestCompleteness:
    def test_22_positions(self, cube):
        assert len(cube.get_all_positions()) == 22

    def test_3_mothers(self, cube):
        mothers = [p for p in cube.get_all_positions().values() if p.letter_type == "mother"]
        assert len(mothers) == 3

    def test_7_doubles(self, cube):
        doubles = [p for p in cube.get_all_positions().values() if p.letter_type == "double"]
        assert len(doubles) == 7

    def test_12_simples(self, cube):
        simples = [p for p in cube.get_all_positions().values() if p.letter_type == "simple"]
        assert len(simples) == 12

    def test_3_axes(self, cube):
        assert len([p for p in cube.get_all_positions().values() if p.cube_role == "axis"]) == 3

    def test_6_faces(self, cube):
        assert len([p for p in cube.get_all_positions().values() if p.cube_role == "face"]) == 6

    def test_1_center(self, cube):
        assert len([p for p in cube.get_all_positions().values() if p.cube_role == "center"]) == 1

    def test_12_edges(self, cube):
        assert len([p for p in cube.get_all_positions().values() if p.cube_role == "edge"]) == 12

    def test_6_seals(self, cube):
        assert len(cube.get_all_seals()) == 6


# ═══════════════════════════════════════════════════════════════
# 6 SCEAUX — SY 1:13
# ═══════════════════════════════════════════════════════════════

class TestSeals:
    SEALS = {
        "haut":  ("YHV", "יהו", ("chokmah", "binah", "tiferet")),
        "bas":   ("YVH", "יוה", ("chokmah", "tiferet", "binah")),
        "est":   ("HYV", "היו", ("binah", "chokmah", "tiferet")),
        "ouest": ("HVY", "הוי", ("binah", "tiferet", "chokmah")),
        "nord":  ("VYH", "ויה", ("tiferet", "chokmah", "binah")),
        "sud":   ("VHY", "והי", ("tiferet", "binah", "chokmah")),
    }

    @pytest.mark.parametrize("direction,expected", list(SEALS.items()))
    def test_seal_definition(self, cube, direction, expected):
        perm, hebrew, seph_order = expected
        seal = cube.get_seal(direction)
        assert seal.permutation == perm
        assert seal.hebrew == hebrew
        assert seal.sephirotic_order == seph_order

    def test_all_seals_are_yhv_permutations(self, cube):
        seen = set()
        for seal in cube.get_all_seals().values():
            assert set(seal.permutation) == {"Y", "H", "V"}
            assert len(seal.permutation) == 3
            seen.add(seal.permutation)
        # 6 permutations uniques de 3 lettres
        assert len(seen) == 6

    def test_seal_has_cognitive_order(self, cube):
        for seal in cube.get_all_seals().values():
            assert len(seal.cognitive_order) == 3
            assert set(seal.cognitive_order) == {"intuition", "analyse", "synthèse"}

    def test_seal_has_sephirotic_order(self, cube):
        for seal in cube.get_all_seals().values():
            assert len(seal.sephirotic_order) == 3
            assert set(seal.sephirotic_order) == {"chokmah", "binah", "tiferet"}

    def test_get_routing_priority(self, cube):
        # Haut = YHV = intuition d'abord
        assert cube.get_routing_priority("haut") == ["chokmah", "binah", "tiferet"]
        # Est = HYV = analyse d'abord
        assert cube.get_routing_priority("est") == ["binah", "chokmah", "tiferet"]

    def test_seal_unknown_direction(self, cube):
        with pytest.raises(KeyError):
            cube.get_seal("diagonal")

    def test_seal_to_sephirotic_static(self, cube):
        assert CubeOfSpace.seal_to_sephirotic_order("YHV") == ["chokmah", "binah", "tiferet"]
        assert CubeOfSpace.seal_to_sephirotic_order("VHY") == ["tiferet", "binah", "chokmah"]

    def test_seal_to_sephirotic_invalid(self, cube):
        with pytest.raises(ValueError):
            CubeOfSpace.seal_to_sephirotic_order("ABC")
        with pytest.raises(ValueError):
            CubeOfSpace.seal_to_sephirotic_order("YHVV")

    def test_seal_to_dict(self, cube):
        seal = cube.get_seal("haut")
        d = seal.to_dict()
        assert d["permutation"] == "YHV"
        assert d["direction"] == "haut"
        assert d["sephirotic_order"] == ["chokmah", "binah", "tiferet"]


# ═══════════════════════════════════════════════════════════════
# 3 MÈRES — éléments, axes, saisons
# ═══════════════════════════════════════════════════════════════

class TestMothers:
    def test_aleph_air(self, cube):
        p = cube.get_position("aleph")
        assert p.element == "air"
        assert p.axis == "haut-bas"
        assert p.season == "inter-saison"

    def test_mem_water(self, cube):
        p = cube.get_position("mem")
        assert p.element == "eau"
        assert p.axis == "est-ouest"
        assert p.season == "hiver"

    def test_shin_fire(self, cube):
        p = cube.get_position("shin")
        assert p.element == "feu"
        assert p.axis == "nord-sud"
        assert p.season == "été"

    def test_all_mothers_have_element_axis_season(self, cube):
        for name in ("aleph", "mem", "shin"):
            p = cube.get_position(name)
            assert p.element is not None
            assert p.axis is not None
            assert p.season is not None

    def test_get_by_element(self, cube):
        assert cube.get_by_element("feu") == "shin"
        assert cube.get_by_element("eau") == "mem"
        assert cube.get_by_element("air") == "aleph"

    def test_get_by_element_unknown(self, cube):
        with pytest.raises(KeyError):
            cube.get_by_element("terre")

    def test_axis_endpoints_aleph(self, cube):
        assert set(cube.get_axis_endpoints("aleph")) == {"beth", "gimel"}

    def test_axis_endpoints_mem(self, cube):
        assert set(cube.get_axis_endpoints("mem")) == {"daleth", "kaph"}

    def test_axis_endpoints_shin(self, cube):
        assert set(cube.get_axis_endpoints("shin")) == {"peh", "resh"}


# ═══════════════════════════════════════════════════════════════
# 7 DOUBLES — planètes, opposés, jours, portes
# ═══════════════════════════════════════════════════════════════

class TestDoubles:
    DOUBLES = {
        "beth":  ("saturne",  "haut",   ("sagesse", "folie"),      "dimanche", "oeil_droit"),
        "gimel": ("jupiter",  "bas",    ("richesse", "pauvreté"),   "lundi",    "oeil_gauche"),
        "daleth": ("mars",    "est",    ("fertilité", "désolation"), "mardi",   "oreille_droite"),
        "kaph":  ("soleil",   "ouest",  ("vie", "mort"),            "mercredi", "oreille_gauche"),
        "peh":   ("vénus",    "nord",   ("domination", "servitude"), "jeudi",   "narine_droite"),
        "resh":  ("mercure",  "sud",    ("paix", "guerre"),          "vendredi", "narine_gauche"),
        "tav":   ("lune",     "centre", ("grâce", "laideur"),        "shabbat",  "bouche"),
    }

    @pytest.mark.parametrize("name,expected", list(DOUBLES.items()))
    def test_double_full_attributes(self, cube, name, expected):
        planet, direction, opposites, day, gate = expected
        p = cube.get_position(name)
        assert p.planet == planet
        assert p.direction == direction
        assert p.opposites == opposites
        assert p.day == day
        assert p.gate == gate

    def test_all_doubles_have_opposites(self, cube):
        for name in self.DOUBLES:
            opps = cube.get_opposites(name)
            assert opps is not None
            assert len(opps) == 2

    def test_all_doubles_have_day(self, cube):
        for name in self.DOUBLES:
            p = cube.get_position(name)
            assert p.day is not None

    def test_all_doubles_have_gate(self, cube):
        for name in self.DOUBLES:
            p = cube.get_position(name)
            assert p.gate is not None

    def test_7_unique_days(self, cube):
        days = {cube.get_position(n).day for n in self.DOUBLES}
        assert len(days) == 7

    def test_7_unique_gates(self, cube):
        gates = {cube.get_position(n).gate for n in self.DOUBLES}
        assert len(gates) == 7

    def test_mothers_have_no_opposites(self, cube):
        for name in ("aleph", "mem", "shin"):
            assert cube.get_opposites(name) is None

    def test_simples_have_no_opposites(self, cube):
        for name in ("heh", "vav", "zayin"):
            assert cube.get_opposites(name) is None

    def test_get_by_planet(self, cube):
        assert cube.get_by_planet("saturne") == "beth"
        assert cube.get_by_planet("lune") == "tav"

    def test_get_by_planet_unknown(self, cube):
        with pytest.raises(KeyError):
            cube.get_by_planet("pluton")

    def test_get_letter_by_day(self, cube):
        assert cube.get_letter_by_day("dimanche") == "beth"
        assert cube.get_letter_by_day("shabbat") == "tav"
        assert cube.get_letter_by_day("mercredi") == "kaph"

    def test_get_letter_by_day_unknown(self, cube):
        with pytest.raises(KeyError):
            cube.get_letter_by_day("octodi")

    def test_get_letter_by_gate(self, cube):
        assert cube.get_letter_by_gate("oeil_droit") == "beth"
        assert cube.get_letter_by_gate("bouche") == "tav"
        assert cube.get_letter_by_gate("narine_droite") == "peh"

    def test_get_letter_by_gate_unknown(self, cube):
        with pytest.raises(KeyError):
            cube.get_letter_by_gate("troisieme_oeil")

    def test_tav_is_center(self, cube):
        p = cube.get_position("tav")
        assert p.cube_role == "center"
        assert p.coordinates == (0.0, 0.0, 0.0)


# ═══════════════════════════════════════════════════════════════
# 12 SIMPLES — zodiaque, mois, sens, tribus, organes
# ═══════════════════════════════════════════════════════════════

class TestSimples:
    SIMPLES = {
        "heh":    ("bélier",      "nisan",    "vue",        "yehudah",  "main_droite"),
        "vav":    ("taureau",     "iyyar",    "ouïe",       "yissachar", "rein_droit"),
        "zayin":  ("gémeaux",     "sivan",    "odorat",     "zevulun",  "pied_droit"),
        "cheth":  ("cancer",      "tammouz",  "parole",     "reuven",   "main_gauche"),
        "teth":   ("lion",        "av",       "goût",       "shimon",   "oesophage"),
        "yod":    ("vierge",      "elul",     "action",     "gad",      "pied_gauche"),
        "lamed":  ("balance",     "tishrei",  "mouvement",  "ephraim",  "vesicule"),
        "nun":    ("scorpion",    "cheshvan", "marche",     "menashe",  "intestins"),
        "samekh": ("sagittaire",  "kislev",   "sommeil",    "binyamin", "estomac"),
        "ayin":   ("capricorne",  "tevet",    "colère",     "dan",      "foie"),
        "tsadi":  ("verseau",     "shevat",   "pensée",     "asher",    "rein_gauche"),
        "qoph":   ("poissons",    "adar",     "méditation", "naftali",  "rate"),
    }

    @pytest.mark.parametrize("name,expected", list(SIMPLES.items()))
    def test_simple_full_attributes(self, cube, name, expected):
        zodiac, month, sense, tribe, organ = expected
        p = cube.get_position(name)
        assert p.zodiac == zodiac
        assert p.month == month
        assert p.sense == sense
        assert p.tribe == tribe
        assert p.organ == organ

    def test_all_simples_have_complete_data(self, cube):
        for name in self.SIMPLES:
            p = cube.get_position(name)
            assert p.sense is not None
            assert p.zodiac is not None
            assert p.month is not None
            assert p.tribe is not None
            assert p.organ is not None

    def test_12_unique_zodiac(self, cube):
        signs = {cube.get_position(n).zodiac for n in self.SIMPLES}
        assert len(signs) == 12

    def test_12_unique_months(self, cube):
        months = {cube.get_position(n).month for n in self.SIMPLES}
        assert len(months) == 12

    def test_12_unique_tribes(self, cube):
        tribes = {cube.get_position(n).tribe for n in self.SIMPLES}
        assert len(tribes) == 12

    def test_12_unique_organs(self, cube):
        organs = {cube.get_position(n).organ for n in self.SIMPLES}
        assert len(organs) == 12

    def test_get_by_zodiac(self, cube):
        assert cube.get_by_zodiac("bélier") == "heh"
        assert cube.get_by_zodiac("poissons") == "qoph"

    def test_get_by_zodiac_unknown(self, cube):
        with pytest.raises(KeyError):
            cube.get_by_zodiac("ophiuchus")

    def test_get_by_sense(self, cube):
        assert cube.get_by_sense("vue") == "heh"
        assert cube.get_by_sense("méditation") == "qoph"

    def test_get_by_sense_unknown(self, cube):
        with pytest.raises(KeyError):
            cube.get_by_sense("télépathie")

    def test_get_letter_by_month(self, cube):
        assert cube.get_letter_by_month("nisan") == "heh"
        assert cube.get_letter_by_month("adar") == "qoph"
        assert cube.get_letter_by_month("tishrei") == "lamed"

    def test_get_letter_by_month_unknown(self, cube):
        with pytest.raises(KeyError):
            cube.get_letter_by_month("janvier")

    def test_get_letter_by_tribe(self, cube):
        assert cube.get_letter_by_tribe("yehudah") == "heh"
        assert cube.get_letter_by_tribe("binyamin") == "samekh"
        assert cube.get_letter_by_tribe("naftali") == "qoph"

    def test_get_letter_by_tribe_unknown(self, cube):
        with pytest.raises(KeyError):
            cube.get_letter_by_tribe("romain")

    def test_get_letter_by_organ(self, cube):
        assert cube.get_letter_by_organ("main_droite") == "heh"
        assert cube.get_letter_by_organ("foie") == "ayin"
        assert cube.get_letter_by_organ("rate") == "qoph"

    def test_get_letter_by_organ_unknown(self, cube):
        with pytest.raises(KeyError):
            cube.get_letter_by_organ("cerveau")


# ═══════════════════════════════════════════════════════════════
# get_letters_by_class
# ═══════════════════════════════════════════════════════════════

class TestLettersByClass:
    def test_mothers(self, cube):
        assert set(cube.get_letters_by_class("mother")) == {"aleph", "mem", "shin"}

    def test_doubles(self, cube):
        assert set(cube.get_letters_by_class("double")) == {
            "beth", "gimel", "daleth", "kaph", "peh", "resh", "tav"
        }

    def test_simples(self, cube):
        assert len(cube.get_letters_by_class("simple")) == 12

    def test_unknown_class(self, cube):
        assert cube.get_letters_by_class("quadruple") == []


# ═══════════════════════════════════════════════════════════════
# PROFIL COMPLET
# ═══════════════════════════════════════════════════════════════

class TestFullProfile:
    def test_mother_profile(self, cube):
        prof = cube.get_full_profile("aleph")
        assert prof["element"] == "air"
        assert prof["season"] == "inter-saison"
        assert prof["cognitive_mode"] == "axis:air"
        assert "axis_endpoints" in prof
        assert set(prof["axis_endpoints"]) == {"beth", "gimel"}

    def test_double_face_profile_has_seal(self, cube):
        prof = cube.get_full_profile("beth")
        assert prof["planet"] == "saturne"
        assert prof["day"] == "dimanche"
        assert prof["gate"] == "oeil_droit"
        assert "seal" in prof
        assert prof["seal"]["permutation"] == "YHV"
        assert "adjacent_edges" in prof
        assert len(prof["adjacent_edges"]) == 4

    def test_double_center_profile(self, cube):
        prof = cube.get_full_profile("tav")
        assert prof["day"] == "shabbat"
        assert prof["gate"] == "bouche"
        assert "seal" not in prof  # centre n'a pas de sceau
        assert "adjacent_edges" in prof
        assert len(prof["adjacent_edges"]) == 12

    def test_simple_profile(self, cube):
        prof = cube.get_full_profile("heh")
        assert prof["zodiac"] == "bélier"
        assert prof["month"] == "nisan"
        assert prof["sense"] == "vue"
        assert prof["tribe"] == "yehudah"
        assert prof["organ"] == "main_droite"
        assert prof["cognitive_mode"] == "edge:vue"
        assert "seal" not in prof
        assert "adjacent_edges" not in prof

    def test_every_letter_has_profile(self, cube):
        for name in cube.get_all_positions():
            prof = cube.get_full_profile(name)
            assert "cognitive_mode" in prof
            assert "name" in prof


# ═══════════════════════════════════════════════════════════════
# NAVIGATION
# ═══════════════════════════════════════════════════════════════

class TestNavigation:
    def test_distance_symmetric(self, cube):
        d1 = cube.spatial_distance("beth", "resh")
        d2 = cube.spatial_distance("resh", "beth")
        assert d1 == pytest.approx(d2)

    def test_distance_self_zero(self, cube):
        assert cube.spatial_distance("tav", "tav") == 0.0

    def test_distance_opposite_faces(self, cube):
        assert cube.spatial_distance("beth", "gimel") == pytest.approx(2.0)

    def test_distance_adjacent_faces(self, cube):
        assert cube.spatial_distance("beth", "daleth") == pytest.approx(math.sqrt(2))

    def test_distance_center_to_face(self, cube):
        assert cube.spatial_distance("tav", "beth") == pytest.approx(1.0)

    def test_distance_center_to_edge(self, cube):
        assert cube.spatial_distance("tav", "heh") == pytest.approx(math.sqrt(2))

    def test_navigate_returns_path(self, cube):
        path = cube.navigate("beth", "resh")
        assert path.origin == "beth"
        assert path.destination == "resh"
        assert path.distance > 0

    def test_navigate_roundtrip(self, cube):
        p1 = cube.navigate("beth", "resh")
        p2 = cube.navigate("resh", "beth")
        assert p1.distance == pytest.approx(p2.distance)

    def test_navigate_cognitive_modes(self, cube):
        path = cube.navigate("heh", "vav")
        assert path.cognitive_mode_from == "edge:vue"
        assert path.cognitive_mode_to == "edge:ouïe"


# ═══════════════════════════════════════════════════════════════
# COORDONNÉES 3D
# ═══════════════════════════════════════════════════════════════

class TestCoordinates:
    def test_faces_at_unit_distance(self, cube):
        for name in ("beth", "gimel", "daleth", "kaph", "peh", "resh"):
            p = cube.get_position(name)
            dist = math.sqrt(sum(c**2 for c in p.coordinates))
            assert dist == pytest.approx(1.0), f"{name} n'est pas à distance 1"

    def test_edges_at_sqrt2_distance(self, cube):
        for name, p in cube.get_all_positions().items():
            if p.cube_role == "edge":
                dist = math.sqrt(sum(c**2 for c in p.coordinates))
                assert dist == pytest.approx(math.sqrt(2)), f"{name} n'est pas à sqrt(2)"

    def test_mothers_at_origin(self, cube):
        for name in ("aleph", "mem", "shin"):
            assert cube.get_position(name).coordinates == (0.0, 0.0, 0.0)

    def test_opposite_faces_are_antipodal(self, cube):
        for a, b in [("beth", "gimel"), ("daleth", "kaph"), ("peh", "resh")]:
            ca = cube.get_position(a).coordinates
            cb = cube.get_position(b).coordinates
            assert all(x == -y for x, y in zip(ca, cb))


# ═══════════════════════════════════════════════════════════════
# MODES COGNITIFS
# ═══════════════════════════════════════════════════════════════

class TestCognitiveModes:
    def test_mother_mode(self, cube):
        assert cube.get_cognitive_mode("shin") == "axis:feu"
        assert cube.get_cognitive_mode("mem") == "axis:eau"
        assert cube.get_cognitive_mode("aleph") == "axis:air"

    def test_face_mode(self, cube):
        assert cube.get_cognitive_mode("beth") == "face:haut:sagesse/folie"

    def test_center_mode(self, cube):
        assert cube.get_cognitive_mode("tav") == "center:grâce/laideur"

    def test_edge_mode(self, cube):
        assert cube.get_cognitive_mode("heh") == "edge:vue"


# ═══════════════════════════════════════════════════════════════
# get_letter_at
# ═══════════════════════════════════════════════════════════════

class TestGetLetterAt:
    def test_face_direction(self, cube):
        assert cube.get_letter_at("haut") == "beth"
        assert cube.get_letter_at("sud") == "resh"

    def test_edge_direction(self, cube):
        assert cube.get_letter_at("nord-est") == "heh"
        assert cube.get_letter_at("sud-bas") == "qoph"

    def test_center(self, cube):
        assert cube.get_letter_at("centre") == "tav"

    def test_axis(self, cube):
        assert cube.get_letter_at("haut-bas") == "aleph"
        assert cube.get_letter_at("est-ouest") == "mem"
        assert cube.get_letter_at("nord-sud") == "shin"

    def test_unknown_direction(self, cube):
        with pytest.raises(KeyError):
            cube.get_letter_at("diagonal-supreme")


# ═══════════════════════════════════════════════════════════════
# ADJACENCE
# ═══════════════════════════════════════════════════════════════

class TestAdjacent:
    def test_tav_center_adjacent_to_all_edges(self, cube):
        assert len(cube.get_adjacent_edges("tav")) == 12

    def test_face_has_4_adjacent_edges(self, cube):
        for name in ("beth", "gimel", "daleth", "kaph", "peh", "resh"):
            adj = cube.get_adjacent_edges(name)
            assert len(adj) == 4, f"{name} a {len(adj)} arêtes adjacentes, attendu 4"

    def test_beth_haut_adjacent(self, cube):
        assert set(cube.get_adjacent_edges("beth")) == {"zayin", "teth", "samekh", "tsadi"}

    def test_non_face_raises(self, cube):
        with pytest.raises(ValueError):
            cube.get_adjacent_edges("heh")


# ═══════════════════════════════════════════════════════════════
# SÉRIALISATION
# ═══════════════════════════════════════════════════════════════

class TestSerialization:
    def test_position_to_dict(self, cube):
        d = cube.get_position("beth").to_dict()
        assert d["name"] == "beth"
        assert d["planet"] == "saturne"
        assert d["opposites"] == ["sagesse", "folie"]
        assert d["day"] == "dimanche"
        assert d["gate"] == "oeil_droit"

    def test_simple_to_dict(self, cube):
        d = cube.get_position("heh").to_dict()
        assert d["tribe"] == "yehudah"
        assert d["organ"] == "main_droite"

    def test_mother_to_dict(self, cube):
        d = cube.get_position("aleph").to_dict()
        assert d["season"] == "inter-saison"

    def test_navigate_to_dict(self, cube):
        d = cube.navigate("beth", "resh").to_dict()
        assert "distance" in d
        assert "axes_traversed" in d

    def test_format_report(self, cube):
        lines = cube.format_report()
        assert len(lines) > 10
        assert any("Cube" in l for l in lines)
        assert any("Sceau" in l or "YHV" in l for l in lines)


# ═══════════════════════════════════════════════════════════════
# ERREURS
# ═══════════════════════════════════════════════════════════════

class TestErrors:
    def test_unknown_letter(self, cube):
        with pytest.raises(KeyError):
            cube.get_position("omega")

    def test_axis_endpoints_non_mother(self, cube):
        with pytest.raises(ValueError):
            cube.get_axis_endpoints("beth")

    def test_seal_invalid_permutation(self):
        with pytest.raises(ValueError):
            CubeOfSpace.seal_to_sephirotic_order("XYZ")

    def test_get_axis(self, cube):
        from_c, to_c, direction = cube.get_axis("aleph")
        assert from_c == (0.0, 0.0, -1.0)
        assert to_c == (0.0, 0.0, 1.0)
        assert direction == (0.0, 0.0, 2.0)

    def test_get_axis_non_mother_raises(self, cube):
        with pytest.raises(ValueError):
            cube.get_axis("beth")


# ═══════════════════════════════════════════════════════════════
# DISTANCES AXES-MÈRES
# ═══════════════════════════════════════════════════════════════

class TestAxisDistances:
    """Mothers are segments — distance uses point-to-segment."""

    def test_mother_to_own_face_zero(self, cube):
        """Each mother has distance 0 to its own face endpoints."""
        assert cube.spatial_distance("aleph", "beth") == pytest.approx(0.0, abs=1e-10)
        assert cube.spatial_distance("aleph", "gimel") == pytest.approx(0.0, abs=1e-10)
        assert cube.spatial_distance("mem", "daleth") == pytest.approx(0.0, abs=1e-10)
        assert cube.spatial_distance("mem", "kaph") == pytest.approx(0.0, abs=1e-10)
        assert cube.spatial_distance("shin", "peh") == pytest.approx(0.0, abs=1e-10)
        assert cube.spatial_distance("shin", "resh") == pytest.approx(0.0, abs=1e-10)

    def test_mother_to_perpendicular_face(self, cube):
        """Mother to face on perpendicular axis = 1.0."""
        assert cube.spatial_distance("aleph", "daleth") == pytest.approx(1.0)
        assert cube.spatial_distance("aleph", "peh") == pytest.approx(1.0)
        assert cube.spatial_distance("mem", "beth") == pytest.approx(1.0)
        assert cube.spatial_distance("shin", "beth") == pytest.approx(1.0)

    def test_mother_to_center_zero(self, cube):
        """All mothers pass through origin — distance to Tav = 0."""
        assert cube.spatial_distance("aleph", "tav") == pytest.approx(0.0, abs=1e-10)
        assert cube.spatial_distance("mem", "tav") == pytest.approx(0.0, abs=1e-10)
        assert cube.spatial_distance("shin", "tav") == pytest.approx(0.0, abs=1e-10)

    def test_mother_to_mother_zero(self, cube):
        """All 3 axes intersect at origin."""
        assert cube.spatial_distance("aleph", "mem") == pytest.approx(0.0, abs=1e-10)
        assert cube.spatial_distance("aleph", "shin") == pytest.approx(0.0, abs=1e-10)
        assert cube.spatial_distance("mem", "shin") == pytest.approx(0.0, abs=1e-10)

    def test_231_gates_still_work(self, cube):
        """All 22 letters produce valid distances (no exceptions)."""
        names = list(cube.get_all_positions().keys())
        for i, a in enumerate(names):
            for b in names[i+1:]:
                d = cube.spatial_distance(a, b)
                assert d >= 0


# ═══════════════════════════════════════════════════════════════
# ROUTING PAR LE CUBE
# ═══════════════════════════════════════════════════════════════

class TestRouteByCube:
    def test_face_uses_own_seal(self, cube):
        """Une face utilise directement son propre sceau."""
        assert cube.route_by_cube("beth") == ["chokmah", "binah", "tiferet"]  # haut = YHV
        assert cube.route_by_cube("daleth") == ["binah", "chokmah", "tiferet"]  # est = HYV

    def test_domain_by_sense(self, cube):
        """Un sens (simple) route via la face la plus proche."""
        route = cube.route_by_cube("vue")
        assert len(route) == 3
        assert set(route) == {"chokmah", "binah", "tiferet"}

    def test_domain_by_planet(self, cube):
        """Une planète (double) route via son sceau."""
        assert cube.route_by_cube("saturne") == cube.route_by_cube("beth")

    def test_domain_by_element(self, cube):
        """Un élément (mère) route via la face la plus proche."""
        route = cube.route_by_cube("feu")
        assert len(route) == 3
        assert set(route) == {"chokmah", "binah", "tiferet"}

    def test_domain_by_direction(self, cube):
        """Une direction route via le sceau correspondant."""
        assert cube.route_by_cube("haut") == ["chokmah", "binah", "tiferet"]
        assert cube.route_by_cube("nord") == ["tiferet", "chokmah", "binah"]

    def test_letter_name_direct(self, cube):
        """Accès direct par nom de lettre."""
        route = cube.route_by_cube("heh")
        assert len(route) == 3
        assert set(route) == {"chokmah", "binah", "tiferet"}

    def test_all_routes_valid(self, cube):
        """Toutes les 22 lettres retournent une séquence valide."""
        for name in cube.get_all_positions():
            route = cube.route_by_cube(name)
            assert len(route) == 3
            assert set(route) == {"chokmah", "binah", "tiferet"}

    def test_unknown_domain_raises(self, cube):
        with pytest.raises(KeyError):
            cube.route_by_cube("télépathie_quantique")


# ═══════════════════════════════════════════════════════════════
# FACTORIELLES CRÉATRICES (SY 4:12)
# ═══════════════════════════════════════════════════════════════

class TestFactorielles:
    def test_sy_412_examples(self):
        """SY 4:12 : 2→2, 3→6, 4→24, 5→120, 6→720, 7→5040."""
        from sefer_yetzirah_cosmo import SYCosmology
        assert SYCosmology.calculate_houses(2) == 2
        assert SYCosmology.calculate_houses(3) == 6
        assert SYCosmology.calculate_houses(4) == 24
        assert SYCosmology.calculate_houses(5) == 120
        assert SYCosmology.calculate_houses(6) == 720
        assert SYCosmology.calculate_houses(7) == 5040

    def test_zero_and_one(self):
        from sefer_yetzirah_cosmo import SYCosmology
        assert SYCosmology.calculate_houses(0) == 1
        assert SYCosmology.calculate_houses(1) == 1

    def test_negative_raises(self):
        from sefer_yetzirah_cosmo import SYCosmology
        with pytest.raises(ValueError):
            SYCosmology.calculate_houses(-1)

    def test_domain_complexity(self):
        from sefer_yetzirah_cosmo import SYCosmology
        assert SYCosmology.domain_complexity(["gematria", "tzeruf", "sentiers"]) == 6
        assert SYCosmology.domain_complexity(["a", "b", "c", "d", "e"]) == 120
        assert SYCosmology.domain_complexity([]) == 1
        assert SYCosmology.domain_complexity(["single"]) == 1


# ═══════════════════════════════════════════════════════════════
# 3 REGISTRES — Olam, Shanah, Nefesh (SY 3-5)
# ═══════════════════════════════════════════════════════════════

class TestTriadMothers:
    """SY 3:4 — Les 3 mères dans les 3 registres."""

    def test_shin_triad(self, cube):
        assert cube.get_olam("shin") == "feu"
        assert cube.get_shanah("shin") == "été"
        assert cube.get_nefesh("shin") == "tête"

    def test_aleph_triad(self, cube):
        assert cube.get_olam("aleph") == "air"
        assert cube.get_shanah("aleph") == "inter-saison"
        assert cube.get_nefesh("aleph") == "poitrine"

    def test_mem_triad(self, cube):
        assert cube.get_olam("mem") == "eau"
        assert cube.get_shanah("mem") == "hiver"
        assert cube.get_nefesh("mem") == "ventre"

    def test_mothers_have_body_part(self, cube):
        for name in ("aleph", "mem", "shin"):
            pos = cube.get_position(name)
            assert pos.body_part is not None

    def test_mothers_3_distinct_body_parts(self, cube):
        parts = {cube.get_nefesh(n) for n in ("aleph", "mem", "shin")}
        assert parts == {"tête", "poitrine", "ventre"}


class TestTriadDoubles:
    """SY 4:1-4 — Les 7 doubles dans les 3 registres."""

    EXPECTED = {
        "beth":  ("saturne",  "dimanche", "oeil_droit"),
        "gimel": ("jupiter",  "lundi",    "oeil_gauche"),
        "daleth": ("mars",    "mardi",    "oreille_droite"),
        "kaph":  ("soleil",   "mercredi", "oreille_gauche"),
        "peh":   ("vénus",    "jeudi",    "narine_droite"),
        "resh":  ("mercure",  "vendredi", "narine_gauche"),
        "tav":   ("lune",     "shabbat",  "bouche"),
    }

    @pytest.mark.parametrize("name,expected", list(EXPECTED.items()))
    def test_double_triad(self, cube, name, expected):
        olam, shanah, nefesh = expected
        assert cube.get_olam(name) == olam
        assert cube.get_shanah(name) == shanah
        assert cube.get_nefesh(name) == nefesh


class TestTriadSimples:
    """SY 5:1-4 — Les 12 simples dans les 3 registres."""

    EXPECTED = {
        "heh":    ("bélier",     "nisan",    "main_droite"),
        "vav":    ("taureau",    "iyyar",    "rein_droit"),
        "zayin":  ("gémeaux",    "sivan",    "pied_droit"),
        "cheth":  ("cancer",     "tammouz",  "main_gauche"),
        "teth":   ("lion",       "av",       "oesophage"),
        "yod":    ("vierge",     "elul",     "pied_gauche"),
        "lamed":  ("balance",    "tishrei",  "vesicule"),
        "nun":    ("scorpion",   "cheshvan", "intestins"),
        "samekh": ("sagittaire", "kislev",   "estomac"),
        "ayin":   ("capricorne", "tevet",    "foie"),
        "tsadi":  ("verseau",    "shevat",   "rein_gauche"),
        "qoph":   ("poissons",   "adar",     "rate"),
    }

    @pytest.mark.parametrize("name,expected", list(EXPECTED.items()))
    def test_simple_triad(self, cube, name, expected):
        olam, shanah, nefesh = expected
        assert cube.get_olam(name) == olam
        assert cube.get_shanah(name) == shanah
        assert cube.get_nefesh(name) == nefesh


class TestTriadInterface:
    """get_full_triad et Triad dataclass."""

    def test_full_triad_returns_triad(self, cube):
        t = cube.get_full_triad("beth")
        assert isinstance(t, Triad)
        assert t.olam == "saturne"
        assert t.shanah == "dimanche"
        assert t.nefesh == "oeil_droit"

    def test_every_letter_has_triad(self, cube):
        for name in cube.get_all_positions():
            t = cube.get_full_triad(name)
            assert t.olam is not None
            assert t.shanah is not None
            assert t.nefesh is not None

    def test_triad_to_dict(self, cube):
        d = cube.get_full_triad("shin").to_dict()
        assert d == {"olam": "feu", "shanah": "été", "nefesh": "tête"}

    def test_profile_includes_triad(self, cube):
        prof = cube.get_full_profile("beth")
        assert "triad" in prof
        assert prof["triad"]["olam"] == "saturne"
        assert prof["triad"]["shanah"] == "dimanche"
        assert prof["triad"]["nefesh"] == "oeil_droit"

    def test_22_unique_nefesh(self, cube):
        """Chaque lettre a un nefesh distinct."""
        nefesh_set = {cube.get_nefesh(n) for n in cube.get_all_positions()}
        assert len(nefesh_set) == 22
