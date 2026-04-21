"""Tests des Partzufim — configurations matures de l'Arbre.

Couvre :
  - Instanciation de chaque Partzuf
  - PartzufBase (facultés, overall, mochin, orientation)
  - assess() → PartzufState
  - interact() → ZivugResult (panim/akhor, résonance)
  - update_from_modules() (avec mocks)
  - Registre et helpers (__init__)
"""

from unittest.mock import patch

import pytest

from partzufim.base import PartzufBase, PartzufState, ZivugResult, FACULTY_NAMES
from partzufim.atik_yomin import AtikYomin
from partzufim.arikh_anpin import ArikhAnpin
from partzufim.abba import Abba
from partzufim.imma import Imma
from partzufim.zeir_anpin import ZeirAnpin
from partzufim.nukva import Nukva
from partzufim import (
    REGISTRY, get_partzuf, list_partzufim,
    init_partzufim, update_all_partzufim, feedback_from_malkuth,
)
from partzufim.zivvug import ZivvugEngine


# ── Helpers ──────────────────────────────────────────────────

class StubPartzuf(PartzufBase):
    """Partzuf minimal pour tests isolés."""
    name = "Stub"
    hebrew = "סטאב"
    source_sephirah = "tiferet"

    def _compute_faculties(self, modules: dict) -> None:
        for fac in FACULTY_NAMES:
            self.set_faculty(fac, 0.5)

    def _assess_specific(self) -> dict:
        return {"message": "stub assessment"}

    def _interact_specific(self, other, resonance):
        return {"stub": True}


# ── PartzufBase ──────────────────────────────────────────────

class TestPartzufBase:

    def test_faculty_names_count(self):
        assert len(FACULTY_NAMES) == 10

    def test_init_all_zero(self):
        p = StubPartzuf()
        for fac in FACULTY_NAMES:
            assert p.get_faculty(fac) == 0.0

    def test_set_get_faculty(self):
        p = StubPartzuf()
        p.set_faculty("keter", 0.75)
        assert p.get_faculty("keter") == 0.75

    def test_set_faculty_clamps(self):
        p = StubPartzuf()
        p.set_faculty("chesed", 1.5)
        assert p.get_faculty("chesed") == 1.0
        p.set_faculty("chesed", -0.3)
        assert p.get_faculty("chesed") == 0.0

    def test_invalid_faculty_raises(self):
        p = StubPartzuf()
        with pytest.raises(ValueError):
            p.get_faculty("daat")
        with pytest.raises(ValueError):
            p.set_faculty("daat", 0.5)

    def test_faculties_property(self):
        p = StubPartzuf()
        p.set_faculty("tiferet", 0.7)
        facs = p.faculties
        assert isinstance(facs, dict)
        assert len(facs) == 10
        assert facs["tiferet"] == 0.7

    def test_overall_tiferet_weighted(self):
        """Tiferet compte double dans le score global."""
        p = StubPartzuf()
        # Tout à 0 sauf Tiferet à 1.0
        p.set_faculty("tiferet", 1.0)
        overall = p.overall
        # 10 facultés : 9 à 0.0 * 1.0 + 1 à 1.0 * 2.0 = 2.0 / 11.0
        assert abs(overall - 2.0 / 11.0) < 0.01

    def test_mochin_katnut(self):
        """Facultés supérieures < 0.3 → katnut."""
        p = StubPartzuf()
        p.set_faculty("keter", 0.1)
        p.set_faculty("chokhmah", 0.1)
        p.set_faculty("binah", 0.1)
        assert p.mochin_state == "katnut"

    def test_mochin_gadlut(self):
        """Supérieures > 0.6 et inférieures > 0.4 → gadlut."""
        p = StubPartzuf()
        for fac in FACULTY_NAMES:
            p.set_faculty(fac, 0.7)
        assert p.mochin_state == "gadlut"

    def test_mochin_transitional(self):
        """Entre les deux → transitional."""
        p = StubPartzuf()
        p.set_faculty("keter", 0.5)
        p.set_faculty("chokhmah", 0.5)
        p.set_faculty("binah", 0.5)
        p.set_faculty("netzach", 0.3)
        p.set_faculty("hod", 0.3)
        p.set_faculty("yesod", 0.3)
        p.set_faculty("malkuth", 0.3)
        assert p.mochin_state == "transitional"

    def test_orientation_default_panim(self):
        p = StubPartzuf()
        assert p.orientation == "panim"

    def test_orientation_akhor_when_tiferet_low(self):
        p = StubPartzuf()
        p.internal_tiferet = 0.1
        p.internal_malkuth = 0.1
        p.update_from_modules({})
        # _update_orientation est appelé dans update_from_modules
        # mais _compute_faculties remet tout à 0.5 pour StubPartzuf
        # Testons directement
        p2 = PartzufBase()
        p2.internal_tiferet = 0.1
        p2.internal_malkuth = 0.1
        p2._update_orientation()
        assert p2.orientation == "akhor"


class TestAssess:

    def test_assess_returns_partzuf_state(self):
        p = StubPartzuf()
        p.update_from_modules({})
        state = p.assess()
        assert isinstance(state, PartzufState)
        assert state.name == "Stub"
        assert state.hebrew == "סטאב"
        assert state.source_sephirah == "tiferet"
        assert isinstance(state.faculties, dict)
        assert 0.0 <= state.overall <= 1.0
        assert state.mochin_state in ("katnut", "gadlut", "transitional")
        assert state.orientation in ("panim", "akhor")

    def test_assess_message_from_subclass(self):
        p = StubPartzuf()
        p.update_from_modules({})
        state = p.assess()
        assert state.message == "stub assessment"


class TestInteract:

    def test_interact_panim_be_panim(self):
        a = StubPartzuf()
        b = StubPartzuf()
        a.update_from_modules({})
        b.update_from_modules({})
        result = a.interact(b)
        assert isinstance(result, ZivugResult)
        assert result.partzuf_a == "Stub"
        assert result.partzuf_b == "Stub"
        assert result.orientation == "panim_be_panim"
        assert result.resonance > 0.0
        assert result.success is True

    def test_interact_akhor_degrades_resonance(self):
        a = StubPartzuf()
        b = StubPartzuf()
        a.update_from_modules({})
        b.update_from_modules({})
        r_panim = a.interact(b).resonance

        # Forcer akhor
        a._orientation = "akhor"
        r_akhor = a.interact(b).resonance

        assert r_akhor < r_panim
        assert a.interact(b).orientation == "akhor_be_akhor"

    def test_resonance_complementary(self):
        """Chesed↔Gevurah complémentarité augmente la résonance."""
        a = StubPartzuf()
        b = StubPartzuf()
        # A fort en Chesed, B fort en Gevurah → complémentarité
        a.set_faculty("chesed", 0.9)
        a.set_faculty("gevurah", 0.1)
        b.set_faculty("chesed", 0.1)
        b.set_faculty("gevurah", 0.9)
        res = a._compute_resonance(b)
        assert res > 0.0

    def test_interact_offspring_from_subclass(self):
        a = StubPartzuf()
        b = StubPartzuf()
        a.update_from_modules({})
        b.update_from_modules({})
        result = a.interact(b)
        assert result.offspring == {"stub": True}


# ── Les 6 Partzufim concrets ────────────────────────────────

class TestAtikYomin:

    def test_instanciation(self):
        p = AtikYomin()
        assert p.name == "Atik Yomin"
        assert p.source_sephirah == "keter"

    def test_assess_without_modules(self):
        p = AtikYomin()
        state = p.assess()
        assert isinstance(state, PartzufState)
        assert "Atik Yomin" in state.message

    def test_ethical_rules_loaded(self):
        p = AtikYomin()
        assert len(p._ethical_rules) >= 5

    def test_interact_blocks_non_arikh(self):
        """Atik ne communique qu'avec Arikh Anpin."""
        atik = AtikYomin()
        nukva = Nukva()
        result = atik.interact(nukva)
        assert result.offspring.get("blocked") is True

    def test_interact_allows_arikh(self):
        atik = AtikYomin()
        arikh = ArikhAnpin()
        result = atik.interact(arikh)
        assert result.offspring.get("blocked") is not True
        assert "ethical_rules" in result.offspring


class TestArikhAnpin:

    def test_instanciation(self):
        p = ArikhAnpin()
        assert p.name == "Arikh Anpin"
        assert p.source_sephirah == "keter"

    def test_tikkunei_dikna_count(self):
        from partzufim.arikh_anpin import TIKKUNEI_DIKNA
        assert len(TIKKUNEI_DIKNA) == 13

    def test_assess_without_modules(self):
        p = ArikhAnpin()
        p.update_from_modules({})
        state = p.assess()
        assert isinstance(state, PartzufState)
        assert state.data.get("n_active_intents") == 0


class TestAbba:

    def test_instanciation(self):
        p = Abba()
        assert p.name == "Abba"
        assert p.source_sephirah == "chokmah"

    def test_assess_without_modules(self):
        p = Abba()
        p.update_from_modules({})
        state = p.assess()
        assert isinstance(state, PartzufState)
        assert "Abba" in state.message
        assert state.data["wisdom_sources"]["insights"] == 0

    def test_interact_provides_wisdom(self):
        a = Abba()
        i = Imma()
        a.update_from_modules({})
        i.update_from_modules({})
        result = a.interact(i)
        assert "wisdom_volume" in result.offspring
        assert "quality" in result.offspring


class TestImma:

    def test_instanciation(self):
        p = Imma()
        assert p.name == "Imma"
        assert p.source_sephirah == "binah"

    def test_assess_without_modules(self):
        p = Imma()
        p.update_from_modules({})
        state = p.assess()
        assert isinstance(state, PartzufState)
        assert "Imma" in state.message

    def test_gestation_ready(self):
        """Malkuth-d'Imma > 0.4 → gestation prête."""
        p = Imma()
        p.update_from_modules({})
        # Sans modules, Binah et Tiferet sont basses → gestation pas prête
        assert p.assess().data.get("gestation_ready") is False

    def test_interact_provides_structure(self):
        a = Abba()
        i = Imma()
        a.update_from_modules({})
        i.update_from_modules({})
        result = i.interact(a)
        assert "causal_structure" in result.offspring
        assert "structural_rigor" in result.offspring


class TestZeirAnpin:

    def test_instanciation(self):
        p = ZeirAnpin()
        assert p.name == "Zeir Anpin"
        assert p.source_sephirah == "tiferet"

    @patch("pool.get_pool", side_effect=RuntimeError("pool not init"))
    def test_assess_without_modules(self, _mock_pool):
        p = ZeirAnpin()
        p.update_from_modules({})
        state = p.assess()
        assert isinstance(state, PartzufState)
        assert state.data.get("n_active") == 0
        assert state.data.get("operational") is False

    @patch("pool.get_pool", side_effect=RuntimeError("pool not init"))
    def test_operational_detection(self, _mock_pool):
        """ZA opérationnel si >= 4 Midot actives (DB-driven).

        Sans DB, aucune Midah n'est active — le test vérifie
        que le mécanisme de détection fonctionne structurellement.
        """
        p = ZeirAnpin()
        p.update_from_modules({})
        state = p.assess()
        # Sans DB, n_active = 0, pas opérationnel
        assert state.data.get("n_active") == 0
        assert state.data.get("operational") is False
        # Vérification structurelle : les 6 midot sont rapportées
        assert state.data.get("n_total") == 6
        assert len(state.data.get("midot_status", {})) == 6


class TestNukva:

    def test_instanciation(self):
        p = Nukva()
        assert p.name == "Nukva"
        assert p.source_sephirah == "malkuth"

    def test_assess_without_modules(self):
        p = Nukva()
        p.update_from_modules({})
        state = p.assess()
        assert isinstance(state, PartzufState)
        assert "Nukva" in state.message
        assert state.data.get("response_count") == 0

    def test_zivug_za_nukva(self):
        """Zivug ZA×Nukva produit transparence et mode."""
        za = ZeirAnpin()
        n = Nukva()
        za.update_from_modules({})
        n.update_from_modules({})
        result = za.interact(n)
        assert isinstance(result, ZivugResult)
        # ZA a des infos midot dans offspring
        assert "n_midot_active" in result.offspring

    def test_nukva_interact_gives_transparency(self):
        za = ZeirAnpin()
        n = Nukva()
        za.update_from_modules({})
        n.update_from_modules({})
        result = n.interact(za)
        assert "transparency" in result.offspring
        assert "mode" in result.offspring

    def test_receive_response_panim(self):
        n = Nukva()
        n.update_from_modules({})
        ctx = {}
        check = n.receive_response("Tout va bien", ctx)
        assert "mode" in check
        # Pas de tensions → pas d'issues → panim
        assert check["mode"] == "panim_be_panim"

    def test_receive_response_akhor(self):
        """Tensions non reflétées → akhor."""
        n = Nukva()
        n.update_from_modules({})
        ctx = {"tiferet_diag": {"open_tensions": 3}}
        check = n.receive_response("Tout est parfait", ctx)
        assert check["mode"] == "akhor_be_akhor"
        assert len(check["issues"]) > 0

    def test_receive_response_reflects_tensions(self):
        n = Nukva()
        n.update_from_modules({})
        ctx = {"tiferet_diag": {"open_tensions": 2}}
        check = n.receive_response(
            "Cependant il y a une tension entre ces approches", ctx
        )
        assert check["mode"] == "panim_be_panim"
        assert len(check["checks"]) > 0


# ── Registre et helpers ──────────────────────────────────────

class TestRegistry:

    def test_registry_has_6_entries(self):
        assert len(REGISTRY) == 6

    def test_registry_keys(self):
        expected = {"atik_yomin", "arikh_anpin", "abba", "imma",
                    "zeir_anpin", "nukva"}
        assert set(REGISTRY.keys()) == expected

    def test_get_partzuf(self):
        p = get_partzuf("abba")
        assert isinstance(p, Abba)

    def test_get_partzuf_case_insensitive(self):
        p = get_partzuf("ZEIR_ANPIN")
        assert isinstance(p, ZeirAnpin)

    def test_get_partzuf_unknown(self):
        assert get_partzuf("unknown") is None

    def test_list_partzufim_ordered(self):
        items = list_partzufim()
        assert len(items) == 6
        assert items[0]["name"] == "atik_yomin"
        assert items[-1]["name"] == "nukva"

    def test_init_partzufim(self):
        ps = init_partzufim()
        assert len(ps) == 6
        assert isinstance(ps["abba"], Abba)
        assert isinstance(ps["nukva"], Nukva)

    def test_update_all_partzufim(self):
        ps = init_partzufim()
        modules = {"chesed": object(), "gevurah": object()}
        update_all_partzufim(ps, modules)
        # Sans DB, ZA lit 0 données — mais le mécanisme fonctionne
        za_state = ps["zeir_anpin"].assess()
        assert "n_active" in za_state.data
        assert za_state.data.get("n_total") == 6


# ── Feedback bidirectionnel (Hitkalelut) ──────────────────

class TestFeedbackFromMalkuth:
    """Or Chozer : la qualité de la réponse remonte l'arbre."""

    def test_low_quality_degrades_za_malkuth(self):
        ps = init_partzufim()
        za = ps["zeir_anpin"]
        za.set_faculty("malkuth", 0.6)
        old = za.get_faculty("malkuth")
        feedback_from_malkuth(ps, quality_score=0.2)
        assert za.get_faculty("malkuth") < old

    def test_high_quality_boosts_za_malkuth(self):
        ps = init_partzufim()
        za = ps["zeir_anpin"]
        old = za.get_faculty("malkuth")
        feedback_from_malkuth(ps, quality_score=0.9)
        assert za.get_faculty("malkuth") > old

    def test_medium_quality_no_za_change(self):
        ps = init_partzufim()
        za = ps["zeir_anpin"]
        old = za.get_faculty("malkuth")
        feedback_from_malkuth(ps, quality_score=0.6)
        assert za.get_faculty("malkuth") == old

    def test_insight_boosts_imma_via_zivvug(self):
        ps = init_partzufim()
        engine = ZivvugEngine()
        result = feedback_from_malkuth(
            ps, quality_score=0.7,
            zivvug_engine=engine,
            insight_produced=True,
        )
        assert result["reinforcement"] is not None
        assert result["reinforcement"]["imma_boosted"] is True
        assert engine.get_boosts()["imma"] > 0

    def test_causal_boosts_abba_via_zivvug(self):
        ps = init_partzufim()
        engine = ZivvugEngine()
        result = feedback_from_malkuth(
            ps, quality_score=0.7,
            zivvug_engine=engine,
            causal_validated=True,
        )
        assert result["reinforcement"]["abba_boosted"] is True
        assert engine.get_boosts()["abba"] > 0

    def test_no_zivvug_no_reinforcement(self):
        ps = init_partzufim()
        result = feedback_from_malkuth(
            ps, quality_score=0.5,
            insight_produced=True,
        )
        assert result["reinforcement"] is None
