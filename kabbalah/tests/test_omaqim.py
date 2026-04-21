"""Tests des 6 Omaqim — Position 5D (SY 1:5).

Couvre : 5 dimensions, distance 5D, position système, 32 sentiers,
analyse de profondeur, Tzeruf 5D.
"""

import math
import pytest

from kabbalah.omaqim import (
    OMAQIM_PAIRS,
    DIRECTIONS,
    FiveDimensionalPosition,
    SixOmaqim,
    SystemMetrics,
)


@pytest.fixture
def omaqim():
    return SixOmaqim()


# ═══════════════════════════════════════════════════════════════
# STRUCTURE DES OMAQIM
# ═══════════════════════════════════════════════════════════════

class TestOmaqimStructure:
    def test_5_pairs(self):
        """6 paires de profondeurs = 5 dimensions."""
        assert len(OMAQIM_PAIRS) == 5

    def test_10_directions(self):
        """10 directions = 10 Sefirot du néant."""
        assert len(DIRECTIONS) == 10

    def test_3_spatial_dimensions(self):
        spatial = [p for p in OMAQIM_PAIRS.values() if p["dimension"].startswith("spatial")]
        assert len(spatial) == 3

    def test_1_temporal_dimension(self):
        temporal = [p for p in OMAQIM_PAIRS.values() if p["dimension"] == "temporal"]
        assert len(temporal) == 1

    def test_1_moral_dimension(self):
        moral = [p for p in OMAQIM_PAIRS.values() if p["dimension"] == "moral"]
        assert len(moral) == 1

    def test_each_pair_has_hebrew(self):
        for pair in OMAQIM_PAIRS.values():
            assert len(pair["hebrew"]) == 2
            for h in pair["hebrew"]:
                assert len(h) > 0

    def test_spatial_axes_match_cube(self):
        """Les axes spatiaux correspondent aux 3 mères."""
        mothers = {p["mother"] for p in OMAQIM_PAIRS.values() if p["mother"]}
        assert mothers == {"aleph", "mem", "shin"}


# ═══════════════════════════════════════════════════════════════
# POSITION 5D
# ═══════════════════════════════════════════════════════════════

class TestFiveDimensionalPosition:
    def test_creation(self, omaqim):
        pos = omaqim.get_5d_position(0.5, -0.3, 0.8, 0.4, 0.7)
        assert pos.x == 0.5
        assert pos.y == -0.3
        assert pos.z == 0.8
        assert pos.t == 0.4
        assert pos.m == 0.7

    def test_clamping(self, omaqim):
        """Les valeurs sont clampées dans les bornes."""
        pos = omaqim.get_5d_position(2.0, -3.0, 0.0, -0.5, 1.5)
        assert pos.x == 1.0
        assert pos.y == -1.0
        assert pos.t == 0.0
        assert pos.m == 1.0

    def test_spatial_property(self, omaqim):
        pos = omaqim.get_5d_position(0.5, -0.3, 0.8)
        assert pos.spatial == (0.5, -0.3, 0.8)

    def test_to_tuple(self, omaqim):
        pos = omaqim.get_5d_position(0.1, 0.2, 0.3, 0.4, 0.5)
        assert pos.to_tuple() == (0.1, 0.2, 0.3, 0.4, 0.5)

    def test_to_dict(self, omaqim):
        pos = omaqim.get_5d_position(0.1, 0.2, 0.3, 0.4, 0.5)
        d = pos.to_dict()
        assert d == {"x": 0.1, "y": 0.2, "z": 0.3, "t": 0.4, "m": 0.5}

    def test_magnitude(self, omaqim):
        pos = omaqim.get_5d_position(1.0, 0.0, 0.0, 0.0, 0.0)
        assert pos.magnitude == pytest.approx(1.0)
        pos2 = omaqim.get_5d_position(1.0, 1.0, 1.0, 1.0, 1.0)
        assert pos2.magnitude == pytest.approx(math.sqrt(5))

    def test_frozen(self, omaqim):
        pos = omaqim.get_5d_position(0.5, 0.5, 0.5, 0.5, 0.5)
        with pytest.raises(AttributeError):
            pos.x = 0.9  # type: ignore


# ═══════════════════════════════════════════════════════════════
# DISTANCE 5D
# ═══════════════════════════════════════════════════════════════

class TestDistance5D:
    def test_same_point_zero_distance(self, omaqim):
        a = omaqim.get_5d_position(0.5, 0.5, 0.5, 0.5, 0.5)
        assert omaqim.distance_5d(a, a) == 0.0

    def test_known_distance(self, omaqim):
        a = omaqim.get_5d_position(0.0, 0.0, 0.0, 0.0, 0.0)
        b = omaqim.get_5d_position(1.0, 0.0, 0.0, 0.0, 0.0)
        assert omaqim.distance_5d(a, b) == pytest.approx(1.0)

    def test_diagonal_distance(self, omaqim):
        a = omaqim.get_5d_position(-1.0, -1.0, -1.0, 0.0, 0.0)
        b = omaqim.get_5d_position(1.0, 1.0, 1.0, 1.0, 1.0)
        assert omaqim.distance_5d(a, b) == pytest.approx(math.sqrt(14))

    def test_symmetry(self, omaqim):
        a = omaqim.get_5d_position(0.3, -0.7, 0.1, 0.8, 0.2)
        b = omaqim.get_5d_position(-0.5, 0.4, 0.9, 0.1, 0.9)
        assert omaqim.distance_5d(a, b) == pytest.approx(omaqim.distance_5d(b, a))

    def test_triangle_inequality(self, omaqim):
        a = omaqim.get_5d_position(0.0, 0.0, 0.0, 0.0, 0.0)
        b = omaqim.get_5d_position(0.5, 0.5, 0.5, 0.5, 0.5)
        c = omaqim.get_5d_position(1.0, 1.0, 1.0, 1.0, 1.0)
        d_ab = omaqim.distance_5d(a, b)
        d_bc = omaqim.distance_5d(b, c)
        d_ac = omaqim.distance_5d(a, c)
        assert d_ac <= d_ab + d_bc + 1e-10


# ═══════════════════════════════════════════════════════════════
# SEPHIROT 5D
# ═══════════════════════════════════════════════════════════════

class TestSephirot5D:
    def test_10_sephirot(self, omaqim):
        positions = omaqim.get_all_sephirot_positions()
        assert len(positions) == 10

    def test_keter_highest(self, omaqim):
        """Keter est au sommet vertical."""
        keter = omaqim.get_sephirah_position("keter")
        assert keter.z == 1.0

    def test_malkuth_lowest(self, omaqim):
        """Malkuth est en bas."""
        malkuth = omaqim.get_sephirah_position("malkuth")
        assert malkuth.z == -1.0

    def test_tiferet_center(self, omaqim):
        """Tiferet est au centre spatial."""
        tif = omaqim.get_sephirah_position("tiferet")
        assert tif.x == 0.0
        assert tif.y == 0.0
        assert tif.z == 0.0

    def test_chesed_east(self, omaqim):
        """Chesed est à l'est (expansion)."""
        chesed = omaqim.get_sephirah_position("chesed")
        assert chesed.x > 0

    def test_gevurah_west(self, omaqim):
        """Gevurah est à l'ouest (contraction)."""
        gevurah = omaqim.get_sephirah_position("gevurah")
        assert gevurah.x < 0

    def test_unknown_sephirah(self, omaqim):
        with pytest.raises(KeyError):
            omaqim.get_sephirah_position("daat")  # pas dans les 10


# ═══════════════════════════════════════════════════════════════
# POSITION SYSTÈME
# ═══════════════════════════════════════════════════════════════

class TestSystemPosition:
    def test_default_metrics_neutral(self, omaqim):
        """Métriques par défaut → position neutre."""
        metrics = SystemMetrics()
        result = omaqim.assess_system_position(metrics)
        assert result.position.t == 0.0
        assert result.temporal_phase == "reshit"

    def test_full_metrics_advanced(self, omaqim):
        """Métriques maximales → position avancée."""
        metrics = SystemMetrics(
            omer_progress=1.0,
            nitzotzot_progress=1.0,
            partzufim_gadlut_ratio=1.0,
            soul_level_index=1.0,
            intentions_avg=1.0,
            ratio_elokit=1.0,
            ratio_behamit=0.0,
            qliphoth_active=0,
            qliphoth_total=10,
            facts_ratio=1.0,
            accepted_ratio=1.0,
            hitbonenut_avg=1.0,
        )
        result = omaqim.assess_system_position(metrics)
        assert result.position.t == pytest.approx(1.0)
        assert result.position.m == pytest.approx(1.0)
        assert result.temporal_phase == "acharit"
        assert result.moral_phase == "tov"

    def test_mid_metrics(self, omaqim):
        """Métriques moyennes → position intermédiaire."""
        metrics = SystemMetrics(
            omer_progress=0.5,
            nitzotzot_progress=0.5,
            partzufim_gadlut_ratio=0.5,
            soul_level_index=0.5,
            intentions_avg=0.5,
            ratio_elokit=0.5,
            ratio_behamit=0.5,
            qliphoth_active=5,
            qliphoth_total=10,
            facts_ratio=0.5,
            accepted_ratio=0.5,
            hitbonenut_avg=0.5,
        )
        result = omaqim.assess_system_position(metrics)
        assert 0.3 < result.position.t < 0.7
        assert 0.3 < result.position.m < 0.7
        assert result.temporal_phase == "olam"
        assert result.moral_phase == "nogah"

    def test_5_depths_returned(self, omaqim):
        """5 dimensions = 5 analyses de profondeur."""
        result = omaqim.assess_system_position(SystemMetrics())
        assert len(result.depths) == 5

    def test_spatial_depths_balanced(self, omaqim):
        """Les axes spatiaux du système sont toujours équilibrés."""
        result = omaqim.assess_system_position(SystemMetrics())
        spatial_depths = [d for d in result.depths if d.dimension.startswith("spatial")]
        assert len(spatial_depths) == 3
        for d in spatial_depths:
            assert d.balance == 1.0

    def test_to_dict(self, omaqim):
        result = omaqim.assess_system_position(SystemMetrics())
        d = result.to_dict()
        assert "position" in d
        assert "depths" in d
        assert "temporal_phase" in d
        assert "moral_phase" in d

    def test_warning_ra_extreme(self, omaqim):
        """Warning si dominance Ra."""
        metrics = SystemMetrics(
            ratio_elokit=0.0,
            ratio_behamit=1.0,
            qliphoth_active=10,
            qliphoth_total=10,
        )
        result = omaqim.assess_system_position(metrics)
        moral_depth = next(d for d in result.depths if d.dimension == "moral")
        assert moral_depth.warning is not None
        assert "Ra" in moral_depth.warning


# ═══════════════════════════════════════════════════════════════
# ANALYSE DE PROFONDEUR
# ═══════════════════════════════════════════════════════════════

class TestDepthAnalysis:
    def test_spatial_depth(self, omaqim):
        d = omaqim.assess_depth("spatial_x")
        assert d.dimension == "spatial_x"
        assert d.pair_name == "mizrach_maarav"

    def test_temporal_depth(self, omaqim):
        d = omaqim.assess_depth("temporal")
        assert d.dimension == "temporal"

    def test_moral_depth(self, omaqim):
        d = omaqim.assess_depth("moral")
        assert d.dimension == "moral"

    def test_unknown_dimension(self, omaqim):
        with pytest.raises(KeyError):
            omaqim.assess_depth("quantum")

    def test_all_5_dimensions(self, omaqim):
        dims = ["spatial_x", "spatial_y", "spatial_z", "temporal", "moral"]
        for dim in dims:
            d = omaqim.assess_depth(dim)
            assert d.dimension == dim


# ═══════════════════════════════════════════════════════════════
# 32 SENTIERS (5-HYPERCUBE)
# ═══════════════════════════════════════════════════════════════

class TestHypercube:
    def test_32_vertices(self, omaqim):
        """2^5 = 32 sommets."""
        vertices = omaqim.hypercube_vertices()
        assert len(vertices) == 32

    def test_vertices_binary(self, omaqim):
        """Chaque composante est ±1."""
        for vertex in omaqim.hypercube_vertices():
            assert len(vertex) == 5
            for v in vertex:
                assert v in (-1, 1)

    def test_vertices_unique(self, omaqim):
        vertices = omaqim.hypercube_vertices()
        assert len(set(vertices)) == 32

    def test_32_paths(self, omaqim):
        """32 sentiers mappés."""
        paths = omaqim.map_32_paths()
        assert len(paths) == 32

    def test_10_sephirot_in_paths(self, omaqim):
        paths = omaqim.map_32_paths()
        sephirot = [p for p in paths if p["type"] == "sephirah"]
        assert len(sephirot) == 10

    def test_22_letters_in_paths(self, omaqim):
        paths = omaqim.map_32_paths()
        letters = [p for p in paths if p["type"] == "letter"]
        assert len(letters) == 22

    def test_each_path_has_5d(self, omaqim):
        paths = omaqim.map_32_paths()
        for p in paths:
            assert len(p["position_5d"]) == 5


# ═══════════════════════════════════════════════════════════════
# TZERUF 5D
# ═══════════════════════════════════════════════════════════════

class TestTzeruf5D:
    def test_compute_route_5d(self):
        from kabbalah.tzeruf_spatial import TzerufSpatial
        ts = TzerufSpatial()
        geom = ts.compute_route_5d("אמת")  # Aleph-Mem-Tav
        assert geom.temporal_span is not None
        assert geom.moral_span is not None
        assert geom.temporal_span > 0  # Aleph (0.0) → Tav (1.0) = span 1.0

    def test_temporal_span_aleph_tav(self):
        """Aleph (début) → Tav (fin) = span temporel maximal."""
        from kabbalah.tzeruf_spatial import TzerufSpatial
        ts = TzerufSpatial()
        geom = ts.compute_route_5d("את")  # Aleph + Tav
        assert geom.temporal_span == pytest.approx(1.0)

    def test_single_letter_zero_span(self):
        """Un seul caractère → span 0."""
        from kabbalah.tzeruf_spatial import TzerufSpatial
        ts = TzerufSpatial()
        geom = ts.compute_route_5d("א")
        assert geom.temporal_span == 0.0
        assert geom.moral_span == 0.0

    def test_empty_word(self):
        from kabbalah.tzeruf_spatial import TzerufSpatial
        ts = TzerufSpatial()
        geom = ts.compute_route_5d("")
        assert geom.temporal_span is None
        assert geom.moral_span is None

    def test_standard_geometry_preserved(self):
        """compute_route_5d préserve la géométrie 3D standard."""
        from kabbalah.tzeruf_spatial import TzerufSpatial
        ts = TzerufSpatial()
        geom_3d = ts.compute_route_geometry("אמת")
        geom_5d = ts.compute_route_5d("אמת")
        assert geom_3d.total_distance == geom_5d.total_distance
        assert geom_3d.ascent == geom_5d.ascent
        assert geom_3d.passes_center == geom_5d.passes_center


# ═══════════════════════════════════════════════════════════════
# TEMPORAL / MORAL POSITION COMPUTATION
# ═══════════════════════════════════════════════════════════════

class TestPositionComputation:
    def test_temporal_zero_metrics(self, omaqim):
        t = omaqim.compute_temporal_position(SystemMetrics())
        assert t == 0.0

    def test_temporal_full_metrics(self, omaqim):
        m = SystemMetrics(
            omer_progress=1.0, nitzotzot_progress=1.0,
            partzufim_gadlut_ratio=1.0, soul_level_index=1.0,
            intentions_avg=1.0,
        )
        t = omaqim.compute_temporal_position(m)
        assert t == pytest.approx(1.0)

    def test_moral_zero_metrics(self, omaqim):
        m = omaqim.compute_moral_position(SystemMetrics())
        # Avec tout à 0 sauf elokit_dominance = 0.5 (default)
        assert 0.0 <= m <= 0.5

    def test_moral_full_tov(self, omaqim):
        m_metrics = SystemMetrics(
            ratio_elokit=1.0, ratio_behamit=0.0,
            qliphoth_active=0, qliphoth_total=10,
            facts_ratio=1.0, accepted_ratio=1.0,
            hitbonenut_avg=1.0,
        )
        m = omaqim.compute_moral_position(m_metrics)
        assert m == 1.0

    def test_moral_bounded(self, omaqim):
        for _ in range(10):
            import random
            m = SystemMetrics(
                ratio_elokit=random.random(),
                ratio_behamit=random.random(),
                qliphoth_active=random.randint(0, 10),
                facts_ratio=random.random(),
                accepted_ratio=random.random(),
                hitbonenut_avg=random.random(),
            )
            result = omaqim.compute_moral_position(m)
            assert 0.0 <= result <= 1.0
