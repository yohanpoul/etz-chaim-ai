"""Tests Budget Parasitaire — mecanisme soustractif du Sitra Achra."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from sitra_achra.budget_parasitaire import BudgetParasitaire, BudgetState


@pytest.fixture
def clean_budget(tmp_path):
    """Budget avec state file dans un dossier temporaire."""
    state_file = tmp_path / "sitra_achra_budget.json"
    with patch("sitra_achra.budget_parasitaire._BUDGET_STATE", state_file), \
         patch("sitra_achra.budget_parasitaire._STATE_DIR", tmp_path):
        budget = BudgetParasitaire()
        yield budget


class TestBudgetParasitaire:

    def test_initial_budget_is_sair_la_azazel(self, clean_budget):
        """Concession minimale meme quand tout va bien."""
        assert clean_budget.current_budget == BudgetParasitaire.SAIR_LA_AZAZEL
        assert clean_budget.can_run()

    def test_flaw_increases_budget(self, clean_budget):
        """Failles ouvertes nourrissent le SA (Zohar I:148a)."""
        base = clean_budget.current_budget
        clean_budget.register_flaw(3)
        assert clean_budget.current_budget == base + 3 * BudgetParasitaire.CALLS_PER_OPEN_FLAW

    def test_fix_decreases_budget(self, clean_budget):
        """Corrections = birur = couper la sustentation."""
        clean_budget.register_flaw(5)
        budget_after_flaws = clean_budget.current_budget
        clean_budget.register_fix(3)
        assert clean_budget.current_budget < budget_after_flaws

    def test_budget_never_below_sair(self, clean_budget):
        """Le SA recoit toujours au moins sa concession (erreur de Job)."""
        clean_budget.register_fix(100)  # Overcorrect
        assert clean_budget.current_budget >= BudgetParasitaire.SAIR_LA_AZAZEL

    def test_budget_capped_at_max(self, clean_budget):
        """Le SA ne devore pas tout (Mamash du SA lui-meme)."""
        clean_budget.register_flaw(1000)
        assert clean_budget.current_budget <= BudgetParasitaire.MAX_BUDGET

    def test_consume_reduces_remaining(self, clean_budget):
        """Consommer des appels reduit le restant quotidien."""
        initial = clean_budget.remaining_calls
        clean_budget.consume(5)
        assert clean_budget.remaining_calls == initial - 5

    def test_cannot_run_when_exhausted(self, clean_budget):
        """Plus de budget = le SA s'arrete."""
        clean_budget.consume(clean_budget.current_budget)
        assert not clean_budget.can_run()

    def test_main_system_affected(self, clean_budget):
        """Le parasitisme est REEL : le systeme principal a moins."""
        main_before = clean_budget.main_system_remaining
        clean_budget.register_flaw(5)
        main_after = clean_budget.main_system_remaining
        assert main_after < main_before

    def test_status_report(self, clean_budget):
        """Le rapport de statut contient toutes les metriques."""
        clean_budget.register_flaw(2)
        clean_budget.consume(3)
        status = clean_budget.get_status()
        assert "open_flaws" in status
        assert "current_budget" in status
        assert "parasitism_rate" in status
        assert status["open_flaws"] == 2
        assert status["used_today"] == 3

    def test_persistence(self, tmp_path):
        """L'etat survit entre instanciations."""
        state_file = tmp_path / "sitra_achra_budget.json"
        with patch("sitra_achra.budget_parasitaire._BUDGET_STATE", state_file), \
             patch("sitra_achra.budget_parasitaire._STATE_DIR", tmp_path):
            b1 = BudgetParasitaire()
            b1.register_flaw(4)
            b1.consume(7)

            # Nouvelle instance = meme state
            b2 = BudgetParasitaire()
            assert b2._state.open_flaws == 4
            assert b2._state.llm_calls_used_today == 7


class TestBirurDynamic:
    """Teste le cycle birur : failles → budget monte → corrections → budget baisse."""

    def test_full_birur_cycle(self, clean_budget):
        """Cycle complet : accumulation → correction → reduction."""
        # Etat initial : concession Sa'ir la-Azazel
        assert clean_budget.current_budget == 10

        # Phase 1 : failles s'accumulent, le SA grandit
        clean_budget.register_flaw(4)
        assert clean_budget.current_budget == 30  # 10 + 4*5

        # Phase 2 : le systeme commence a corriger (birur)
        clean_budget.register_fix(2)
        # open_flaws = 2 → 10 + 2*5 = 20
        assert clean_budget.current_budget == 20

        # Phase 3 : tout est corrige
        clean_budget.register_fix(2)
        # open_flaws = 0 → 10 + 0 = 10
        assert clean_budget.current_budget == 10

        # Le SA n'est pas mort — il garde sa concession
        assert clean_budget.current_budget == BudgetParasitaire.SAIR_LA_AZAZEL
