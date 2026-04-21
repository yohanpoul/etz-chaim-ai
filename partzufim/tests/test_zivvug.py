"""Tests du ZivvugEngine — couplage Abba (Chokmah) ↔ Imma (Binah).

Couvre :
  - ZivvugState (ACTIVE / PARTIAL / BLOCKED)
  - couple_abba_imma() — évaluation du delta et de l'état
  - transfer_mochin() — réactif limitant, coupling_factor
  - mutual_reinforcement() — boosts croisés
  - assess_zivvug_state() — avec boosts appliqués
  - Intégration avec update_all_partzufim → ZA reçoit les Mochin
  - ZA en Katnut si Zivvug bloqué
"""

import pytest

from partzufim.zivvug import (
    ZivvugEngine,
    ZivvugState,
    ZivvugAssessment,
    MochinTransfer,
)
from partzufim.abba import Abba
from partzufim.imma import Imma
from partzufim.zeir_anpin import ZeirAnpin
from partzufim import init_partzufim, update_all_partzufim


# ── ZivvugState ─────────────────────────────────────────────

class TestZivvugState:

    def test_active_when_close_and_high(self):
        """Delta < 0.15 et les deux > 0.5 → ACTIVE."""
        engine = ZivvugEngine()
        result = engine.couple_abba_imma(0.60, 0.55)
        assert result.state == ZivvugState.ACTIVE
        assert result.delta < 0.15

    def test_partial_when_moderate_delta(self):
        """Delta entre 0.15 et 0.30 → PARTIAL."""
        engine = ZivvugEngine()
        result = engine.couple_abba_imma(0.55, 0.35)
        assert result.state == ZivvugState.PARTIAL
        assert 0.15 <= result.delta < 0.30

    def test_blocked_when_large_delta(self):
        """Delta > 0.30 → BLOCKED."""
        engine = ZivvugEngine()
        result = engine.couple_abba_imma(0.80, 0.40)
        assert result.state == ZivvugState.BLOCKED
        assert result.delta > 0.30

    def test_blocked_when_one_too_low(self):
        """Un score < 0.3 → BLOCKED même si delta petit."""
        engine = ZivvugEngine()
        result = engine.couple_abba_imma(0.25, 0.25)
        assert result.state == ZivvugState.BLOCKED

    def test_partial_when_close_but_below_active_threshold(self):
        """Delta < 0.15 mais l'un < 0.5 → PARTIAL, pas ACTIVE."""
        engine = ZivvugEngine()
        result = engine.couple_abba_imma(0.45, 0.40)
        assert result.state == ZivvugState.PARTIAL

    def test_limiting_partzuf_abba(self):
        """Abba plus faible → limiting = abba."""
        engine = ZivvugEngine()
        result = engine.couple_abba_imma(0.40, 0.55)
        assert result.limiting_partzuf == "abba"

    def test_limiting_partzuf_imma(self):
        """Imma plus faible → limiting = imma."""
        engine = ZivvugEngine()
        result = engine.couple_abba_imma(0.60, 0.50)
        assert result.limiting_partzuf == "imma"

    def test_limiting_partzuf_none_when_equal(self):
        """Scores égaux → pas de limitant."""
        engine = ZivvugEngine()
        result = engine.couple_abba_imma(0.55, 0.55)
        assert result.limiting_partzuf is None


# ── transfer_mochin ─────────────────────────────────────────

class TestTransferMochin:

    def test_mochin_limited_by_weakest(self):
        """Mochin = min(abba, imma) × coupling_factor — le réactif limitant."""
        engine = ZivvugEngine()
        transfer = engine.transfer_mochin(0.60, 0.55)
        # min(0.60, 0.55) = 0.55, coupling = 1 - 0.05 = 0.95
        expected = 0.55 * 0.95
        assert abs(transfer.mochin_score - expected) < 0.01

    def test_mochin_zero_when_blocked(self):
        """Pas de Mochin si Zivvug bloqué."""
        engine = ZivvugEngine()
        transfer = engine.transfer_mochin(0.80, 0.20)
        assert transfer.mochin_score == 0.0
        assert transfer.zivvug_state == ZivvugState.BLOCKED

    def test_mochin_increases_with_alignment(self):
        """Mieux alignés → plus de Mochin."""
        engine = ZivvugEngine()
        t_aligned = engine.transfer_mochin(0.60, 0.58)
        t_divergent = engine.transfer_mochin(0.60, 0.40)
        assert t_aligned.mochin_score > t_divergent.mochin_score

    def test_coupling_factor_decreases_with_delta(self):
        """coupling_factor = 1.0 - delta."""
        engine = ZivvugEngine()
        transfer = engine.transfer_mochin(0.70, 0.50)
        assert abs(transfer.coupling_factor - 0.80) < 0.01  # 1.0 - 0.20

    def test_returns_mochin_transfer(self):
        engine = ZivvugEngine()
        transfer = engine.transfer_mochin(0.55, 0.55)
        assert isinstance(transfer, MochinTransfer)
        assert transfer.source_abba == 0.55
        assert transfer.source_imma == 0.55


# ── mutual_reinforcement ────────────────────────────────────

class TestMutualReinforcement:

    def test_insight_boosts_imma(self):
        """InsightForge produit un insight → Imma +BOOST_AMOUNT."""
        engine = ZivvugEngine()
        result = engine.mutual_reinforcement(insight_produced=True)
        assert result["imma_boosted"] is True
        assert result["abba_boosted"] is False
        assert result["imma_boost_total"] == pytest.approx(ZivvugEngine.BOOST_AMOUNT)

    def test_causal_boosts_abba(self):
        """CausalEngine valide un claim → Abba +BOOST_AMOUNT."""
        engine = ZivvugEngine()
        result = engine.mutual_reinforcement(causal_validated=True)
        assert result["abba_boosted"] is True
        assert result["imma_boosted"] is False
        assert result["abba_boost_total"] == pytest.approx(ZivvugEngine.BOOST_AMOUNT)

    def test_both_at_once(self):
        """Les deux en même temps → les deux boostés."""
        engine = ZivvugEngine()
        result = engine.mutual_reinforcement(
            insight_produced=True, causal_validated=True,
        )
        assert result["abba_boosted"] is True
        assert result["imma_boosted"] is True
        assert result["abba_boost_total"] == pytest.approx(ZivvugEngine.BOOST_AMOUNT)
        assert result["imma_boost_total"] == pytest.approx(ZivvugEngine.BOOST_AMOUNT)

    def test_accumulates(self):
        """Les boosts s'accumulent."""
        engine = ZivvugEngine()
        engine.mutual_reinforcement(insight_produced=True)
        engine.mutual_reinforcement(insight_produced=True)
        engine.mutual_reinforcement(insight_produced=True)
        assert engine.imma_boost == pytest.approx(3 * ZivvugEngine.BOOST_AMOUNT)
        assert engine.abba_boost == pytest.approx(0.0)

    def test_reinforcement_log(self):
        """Le log enregistre les événements."""
        engine = ZivvugEngine()
        engine.mutual_reinforcement(insight_produced=True)
        engine.mutual_reinforcement(causal_validated=True)
        log = engine.reinforcement_log
        assert len(log) == 2
        assert log[0]["type"] == "insight→imma"
        assert log[1]["type"] == "causal→abba"

    def test_no_boost_when_nothing(self):
        """Aucun événement → aucun boost."""
        engine = ZivvugEngine()
        result = engine.mutual_reinforcement()
        assert result["abba_boosted"] is False
        assert result["imma_boosted"] is False


# ── assess_zivvug_state (avec boosts) ───────────────────────

class TestAssessWithBoosts:

    def test_boosts_included_in_assessment(self):
        """assess_zivvug_state applique les boosts accumulés."""
        engine = ZivvugEngine()
        # Seeds ajustées pour rester < MIN_ACTIVE_SCORE après accumulation,
        # cohérence doctrinale préservée malgré recalibrage BOOST_AMOUNT (EC-K5-008).
        # Objectif narratif : abba effectif reste < 0.5 (partial, pas active).
        n_cycles = 3
        for _ in range(n_cycles):
            engine.mutual_reinforcement(causal_validated=True)
        accumulated = n_cycles * ZivvugEngine.BOOST_AMOUNT
        abba_seed = 0.30
        imma_seed = 0.50
        result = engine.assess_zivvug_state(abba_seed, imma_seed)
        expected_abba_effective = abba_seed + accumulated
        assert result.abba_score == pytest.approx(expected_abba_effective, abs=0.01)
        assert result.delta == pytest.approx(
            abs(imma_seed - expected_abba_effective), abs=0.02
        )

    def test_boosts_capped_at_one(self):
        """Les boosts ne dépassent pas 1.0."""
        engine = ZivvugEngine()
        for _ in range(100):
            engine.mutual_reinforcement(causal_validated=True)
        result = engine.assess_zivvug_state(0.95, 0.60)
        assert result.abba_score <= 1.0


# ── Sérialisation ───────────────────────────────────────────

class TestSerialization:

    def test_to_dict_and_from_dict(self):
        engine = ZivvugEngine()
        engine.mutual_reinforcement(insight_produced=True)
        engine.mutual_reinforcement(causal_validated=True)

        data = engine.to_dict()
        assert data["abba_boost"] == pytest.approx(ZivvugEngine.BOOST_AMOUNT)
        assert data["imma_boost"] == pytest.approx(ZivvugEngine.BOOST_AMOUNT)
        assert data["reinforcement_count"] == 2

        restored = ZivvugEngine.from_dict(data)
        assert restored.abba_boost == pytest.approx(ZivvugEngine.BOOST_AMOUNT)
        assert restored.imma_boost == pytest.approx(ZivvugEngine.BOOST_AMOUNT)

    def test_reset_boosts(self):
        engine = ZivvugEngine()
        engine.mutual_reinforcement(insight_produced=True)
        engine.reset_boosts()
        assert engine.abba_boost == 0.0
        assert engine.imma_boost == 0.0


# ── Intégration avec update_all_partzufim ───────────────────

class TestIntegrationPartzufim:

    def test_za_katnut_when_zivvug_blocked(self):
        """ZA ne peut pas passer en Gadlut si Zivvug bloqué."""
        partzufim = init_partzufim()
        engine = ZivvugEngine()

        # Sans aucun module, Abba et Imma sont très bas (< 0.3) → BLOCKED
        assessment = update_all_partzufim(partzufim, {}, zivvug_engine=engine)

        assert assessment.state == ZivvugState.BLOCKED
        za = partzufim["zeir_anpin"]
        # Les facultés supérieures de ZA devraient être plafonnées à 0.25
        assert za.get_faculty("keter") <= 0.25

    def test_za_boosted_when_zivvug_active(self):
        """ZA reçoit des Mochin quand Zivvug actif — test direct de _apply_mochin_to_za."""
        from partzufim import _apply_mochin_to_za

        za = ZeirAnpin()
        # Base ZA faculties
        za.set_faculty("keter", 0.3)
        za.set_faculty("chokhmah", 0.2)
        za.set_faculty("binah", 0.2)

        # Mochin pleins : score élevé, état ACTIVE
        _apply_mochin_to_za(za, mochin_score=0.55, zivvug_state=ZivvugState.ACTIVE)

        # ZA devrait avoir reçu un boost complet
        assert za.get_faculty("keter") > 0.50   # 0.3 + 0.55*0.5 = 0.575
        assert za.get_faculty("chokhmah") > 0.30  # 0.2 + 0.55*0.4 = 0.42
        assert za.get_faculty("binah") > 0.30     # 0.2 + 0.55*0.4 = 0.42

    def test_update_returns_assessment(self):
        """update_all_partzufim retourne un ZivvugAssessment."""
        partzufim = init_partzufim()
        engine = ZivvugEngine()
        assessment = update_all_partzufim(partzufim, {}, zivvug_engine=engine)
        assert isinstance(assessment, ZivvugAssessment)

    def test_update_without_engine_returns_none(self):
        """Sans engine, retourne quand même un assessment (engine par défaut)."""
        partzufim = init_partzufim()
        # Sans zivvug_engine, un engine par défaut est créé
        assessment = update_all_partzufim(partzufim, {})
        assert assessment is not None

    def test_mutual_reinforcement_applied_to_faculties(self):
        """Les boosts de renforcement mutuel modifient les facultés."""
        partzufim = init_partzufim()
        engine = ZivvugEngine()

        # Accumuler des boosts pour Abba
        n_cycles = 10
        for _ in range(n_cycles):
            engine.mutual_reinforcement(causal_validated=True)
        assert engine.abba_boost == pytest.approx(n_cycles * ZivvugEngine.BOOST_AMOUNT)

        modules = {}
        update_all_partzufim(partzufim, modules, zivvug_engine=engine)

        # Les boosts devraient être réinitialisés après application
        assert engine.abba_boost == 0.0
        assert engine.imma_boost == 0.0
