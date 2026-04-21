"""Tests pour les 462 Portes directionnelles (SY 2:4-5).

Vérifie :
  - 462 portes générées (231 × 2)
  - Chaque paire a des directions opposées
  - Ascendant/descendant cohérents
  - oscillate() retourne la porte inverse
  - Route d'un mot = séquence de portes
  - Exemples Emet (אמת) et Sheker (שקר)
"""

import math

import pytest

from kabbalah.gates_462 import DirectionalGate, Gates462


@pytest.fixture
def gates():
    return Gates462()


# ── Nombre total ──────────────────────────────────────────────

class TestCount:
    def test_462_gates(self, gates):
        """231 paires × 2 directions = 462."""
        assert len(gates) == 462

    def test_all_gates_returns_462(self, gates):
        assert len(gates.all_gates()) == 462

    def test_stats_total(self, gates):
        s = gates.stats()
        assert s["total"] == 462
        assert s["pairs"] == 231

    def test_ascending_plus_descending_plus_horizontal(self, gates):
        """Partition complète : chaque porte est soit montante, descendante, ou horizontale."""
        s = gates.stats()
        assert s["ascending"] + s["descending"] + s["horizontal"] == 462


# ── Paires et oscillation ────────────────────────────────────

class TestPairs:
    def test_gate_pair_exists(self, gates):
        """Chaque paire (A→B, B→A) existe."""
        ab, ba = gates.get_gate_pair("aleph", "beth")
        assert ab.letter_from == "aleph"
        assert ab.letter_to == "beth"
        assert ba.letter_from == "beth"
        assert ba.letter_to == "aleph"

    def test_opposite_direction_vectors(self, gates):
        """A→B et B→A ont des vecteurs opposés."""
        ab, ba = gates.get_gate_pair("aleph", "mem")
        for i in range(3):
            assert abs(ab.direction_vector[i] + ba.direction_vector[i]) < 1e-6

    def test_same_distance(self, gates):
        """A→B et B→A ont la même distance."""
        ab, ba = gates.get_gate_pair("shin", "tav")
        assert abs(ab.distance - ba.distance) < 1e-6

    def test_oscillate_returns_inverse(self, gates):
        """oscillate() retourne la porte inverse."""
        gate = gates.get_gate("aleph", "mem")
        inv = gates.oscillate(gate)
        assert inv.letter_from == "mem"
        assert inv.letter_to == "aleph"
        assert inv.gate_id == "mem→aleph"

    def test_double_oscillate_returns_original(self, gates):
        """Osciller deux fois revient au point de départ."""
        gate = gates.get_gate("beth", "gimel")
        double_osc = gates.oscillate(gates.oscillate(gate))
        assert double_osc.gate_id == gate.gate_id

    def test_all_pairs_have_opposite_vectors(self, gates):
        """Vérification systématique : TOUTES les paires ont des vecteurs opposés."""
        from kabbalah.gates_462 import _ALEPH_BET_NAMES
        for i, a in enumerate(_ALEPH_BET_NAMES):
            for b in _ALEPH_BET_NAMES[i + 1:]:
                ab, ba = gates.get_gate_pair(a, b)
                for dim in range(3):
                    assert abs(ab.direction_vector[dim] + ba.direction_vector[dim]) < 1e-6, \
                        f"Paire {a}-{b} dim {dim}: {ab.direction_vector[dim]} vs {ba.direction_vector[dim]}"


# ── Ascendant / Descendant ───────────────────────────────────

class TestVertical:
    def test_ascending_is_descending_inverse(self, gates):
        """Si A→B monte, B→A descend."""
        ab = gates.get_gate("gimel", "beth")  # bas→haut
        ba = gates.get_gate("beth", "gimel")  # haut→bas
        if ab.is_ascending:
            assert ba.is_descending
        elif ab.is_descending:
            assert ba.is_ascending

    def test_ascending_gates_have_positive_dz(self, gates):
        for g in gates.get_ascending_gates():
            assert g.direction_vector[2] > 0, f"{g.gate_id} dz={g.direction_vector[2]}"

    def test_descending_gates_have_negative_dz(self, gates):
        for g in gates.get_descending_gates():
            assert g.direction_vector[2] < 0, f"{g.gate_id} dz={g.direction_vector[2]}"

    def test_horizontal_gates_near_zero_dz(self, gates):
        for g in gates.get_horizontal_gates():
            assert abs(g.direction_vector[2]) <= 0.01, f"{g.gate_id} dz={g.direction_vector[2]}"

    def test_ascending_descending_symmetry(self, gates):
        """Autant de portes montantes que descendantes (par symétrie des paires)."""
        assert len(gates.get_ascending_gates()) == len(gates.get_descending_gates())


# ── Axes traversés ───────────────────────────────────────────

class TestAxes:
    def test_crossing_aleph_axis(self, gates):
        """Il existe des portes traversant l'axe Aleph (haut-bas)."""
        crossing = gates.get_gates_crossing_axis("aleph")
        assert len(crossing) > 0

    def test_crossing_mem_axis(self, gates):
        crossing = gates.get_gates_crossing_axis("mem")
        assert len(crossing) > 0

    def test_crossing_shin_axis(self, gates):
        crossing = gates.get_gates_crossing_axis("shin")
        assert len(crossing) > 0


# ── Filtres par lettre ────────────────────────────────────────

class TestLetterFilters:
    def test_21_gates_from_each_letter(self, gates):
        """Chaque lettre a 21 portes sortantes (vers les 21 autres)."""
        from kabbalah.gates_462 import _ALEPH_BET_NAMES
        for name in _ALEPH_BET_NAMES:
            from_gates = gates.get_gates_from(name)
            assert len(from_gates) == 21, f"{name}: {len(from_gates)} gates"

    def test_21_gates_to_each_letter(self, gates):
        """Chaque lettre a 21 portes entrantes."""
        from kabbalah.gates_462 import _ALEPH_BET_NAMES
        for name in _ALEPH_BET_NAMES:
            to_gates = gates.get_gates_to(name)
            assert len(to_gates) == 21, f"{name}: {len(to_gates)} gates"


# ── Transitions Olam/Shanah/Nefesh ───────────────────────────

class TestTransitions:
    def test_olam_transition_filled(self, gates):
        """Chaque porte a une transition Olam non vide."""
        for g in gates.all_gates():
            assert g.olam_transition[0] is not None, f"{g.gate_id} olam_from is None"
            assert g.olam_transition[1] is not None, f"{g.gate_id} olam_to is None"

    def test_shanah_transition_filled(self, gates):
        for g in gates.all_gates():
            assert g.shanah_transition[0] is not None, f"{g.gate_id}"
            assert g.shanah_transition[1] is not None, f"{g.gate_id}"

    def test_nefesh_transition_filled(self, gates):
        for g in gates.all_gates():
            assert g.nefesh_transition[0] is not None, f"{g.gate_id}"
            assert g.nefesh_transition[1] is not None, f"{g.gate_id}"


# ── Classes d'interaction ─────────────────────────────────────

class TestInteractionClasses:
    def test_mother_to_mother_count(self, gates):
        """3 mères, paires ordonnées = 3×2 = 6 portes mother→mother."""
        m2m = gates.get_gates_by_interaction("mother→mother")
        # 3 mères : aleph, mem, shin. Paires ordonnées = P(3,2) = 6
        assert len(m2m) == 6

    def test_interaction_class_format(self, gates):
        """Chaque interaction_class a le format 'type→type'."""
        for g in gates.all_gates():
            assert "→" in g.interaction_class
            parts = g.interaction_class.split("→")
            assert parts[0] in ("mother", "double", "simple")
            assert parts[1] in ("mother", "double", "simple")


# ── Routes de mots ────────────────────────────────────────────

class TestWordRoutes:
    def test_emet(self, gates):
        """אמת (Emet = Vérité) : Aleph→Mem + Mem→Tav = 2 portes."""
        route = gates.word_to_gates("אמת")
        assert len(route) == 2
        assert route[0].letter_from == "aleph"
        assert route[0].letter_to == "mem"
        assert route[1].letter_from == "mem"
        assert route[1].letter_to == "tav"

    def test_sheker(self, gates):
        """שקר (Sheker = Mensonge) : Shin→Qoph + Qoph→Resh = 2 portes."""
        route = gates.word_to_gates("שקר")
        assert len(route) == 2
        assert route[0].letter_from == "shin"
        assert route[0].letter_to == "qoph"
        assert route[1].letter_from == "qoph"
        assert route[1].letter_to == "resh"

    def test_single_letter_no_gates(self, gates):
        """Un seul caractère = aucune porte."""
        assert gates.word_to_gates("א") == []

    def test_empty_string_no_gates(self, gates):
        assert gates.word_to_gates("") == []

    def test_word_gate_summary(self, gates):
        summary = gates.word_gate_summary("אמת")
        assert summary["gates_count"] == 2
        # Emet = 2 mères + centre: toutes se rejoignent à l'origine → distance 0
        assert summary["total_distance"] >= 0
        assert isinstance(summary["axes_traversed"], list)

    def test_emet_vs_sheker_geometry(self, gates):
        """Emet et Sheker ont des profils géométriques différents.

        Emet (א-מ-ת) = 2 mères + centre. Toutes se rejoignent à l'origine
        du Cube — la Vérité est l'ossature même de l'espace, distance = 0
        car les axes se croisent au centre (Tav/Shabbat).

        Sheker (ש-ק-ר) passe par une mère et deux lettres périphériques
        (Qoph=arête, Resh=face) — le mensonge s'éloigne du centre.
        """
        emet = gates.word_gate_summary("אמת")
        sheker = gates.word_gate_summary("שקר")
        # Emet: les axes se croisent au centre → distance 0
        assert emet["total_distance"] == 0.0
        # Sheker: mouvement dans l'espace périphérique → distance > 0
        assert sheker["total_distance"] > 0


# ── Contient / lookup ─────────────────────────────────────────

class TestContains:
    def test_contains_gate_id(self, gates):
        assert "aleph→beth" in gates

    def test_does_not_contain_invalid(self, gates):
        assert "aleph→aleph" not in gates

    def test_get_gate_raises_on_invalid(self, gates):
        with pytest.raises(KeyError):
            gates.get_gate("aleph", "aleph")

    def test_get_gate_raises_on_unknown(self, gates):
        with pytest.raises(KeyError):
            gates.get_gate("aleph", "nonexistent")


# ── to_dict sérialisation ────────────────────────────────────

class TestSerialization:
    def test_to_dict_keys(self, gates):
        gate = gates.get_gate("aleph", "beth")
        d = gate.to_dict()
        assert "gate_id" in d
        assert "direction_vector" in d
        assert "distance" in d
        assert "vertical" in d
        assert "olam" in d
        assert "shanah" in d
        assert "nefesh" in d


# ── Intégration avec TzerufSpatial ────────────────────────────

class TestTzerufIntegration:
    def test_route_to_gates(self):
        from kabbalah.tzeruf_spatial import TzerufSpatial
        ts = TzerufSpatial()
        route = ts.route_to_gates("אמת")
        assert len(route) == 2
        assert route[0].letter_from == "aleph"
        assert route[0].letter_to == "mem"

    def test_route_gate_summary(self):
        from kabbalah.tzeruf_spatial import TzerufSpatial
        ts = TzerufSpatial()
        summary = ts.route_gate_summary("שקר")
        assert summary["gates_count"] == 2
        assert summary["word"] == "שקר"
