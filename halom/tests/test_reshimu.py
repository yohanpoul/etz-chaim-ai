"""Tests for Reshimu persistence layer.

Reshimu (רשימו) = the trace left behind after the vessel shatters.
Manages all I/O to the HALOM/ directory.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from halom.models import (
    CycleReport,
    DreamCandidate,
    DreamResult,
    Mechanism,
)
from halom.reshimu import Reshimu


def _make_result(concept_k: str = "Reshimu", accepted: bool = True) -> DreamResult:
    return DreamResult(
        candidate=DreamCandidate(
            concept_k=concept_k,
            concept_ia="Residual connections",
            mechanism=Mechanism.TZERUF,
            structure_commune="Trace through contraction",
            prediction="Skip ∝ compression",
            score_brut=0.73,
        ),
        accepted=accepted,
        adversaire_verdict="tient" if accepted else "ne tient pas",
    )


def _make_report(cycle: int = 1) -> CycleReport:
    return CycleReport(
        cycle_number=cycle,
        date="2026-04-10",
        candidates_generated=50,
        pre_filter_survivors=8,
        adversaire_survivors=2,
        results=[_make_result(), _make_result("Tsimtsum")],
        thompson_state={"tzeruf": {"alpha": 3, "beta": 11}},
    )


class TestReshimuInit:
    """Reshimu creates the HALOM/ directory structure."""

    def test_creates_directory_structure(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "HALOM"
            reshimu = Reshimu(base)
            reshimu.init_structure()
            assert (base / "cycles").is_dir()
            assert (base / "trouvailles").is_dir()
            assert (base / "rejets").is_dir()
            assert (base / "etat").is_dir()

    def test_init_is_idempotent(self):
        """Calling init twice doesn't break anything."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "HALOM"
            reshimu = Reshimu(base)
            reshimu.init_structure()
            reshimu.init_structure()
            assert (base / "etat").is_dir()


class TestReshimuCycles:
    """Persisting and reading cycle reports."""

    def test_save_cycle(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "HALOM"
            reshimu = Reshimu(base)
            reshimu.init_structure()
            report = _make_report(cycle=1)
            reshimu.save_cycle(report)
            cycle_dir = base / "cycles" / "2026-04-10_cycle_001"
            assert cycle_dir.is_dir()
            assert (cycle_dir / "meta.json").exists()
            assert (cycle_dir / "rapport.md").exists()

    def test_get_next_cycle_number(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "HALOM"
            reshimu = Reshimu(base)
            reshimu.init_structure()
            assert reshimu.get_next_cycle_number() == 1
            reshimu.save_cycle(_make_report(cycle=1))
            assert reshimu.get_next_cycle_number() == 2


class TestReshimuHistory:
    """History tracking for duplication check."""

    def test_add_and_check_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "HALOM"
            reshimu = Reshimu(base)
            reshimu.init_structure()
            reshimu.add_to_history("Reshimu", "Residual connections")
            history = reshimu.load_history()
            assert len(history) == 1
            assert history[0]["concept_k"] == "Reshimu"

    def test_history_persists(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "HALOM"
            reshimu = Reshimu(base)
            reshimu.init_structure()
            reshimu.add_to_history("X", "Y")
            # Reload from scratch
            reshimu2 = Reshimu(base)
            history = reshimu2.load_history()
            assert len(history) == 1


class TestReshimuThompson:
    """Thompson state persistence."""

    def test_save_and_load_thompson(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "HALOM"
            reshimu = Reshimu(base)
            reshimu.init_structure()
            state = {"tzeruf": {"alpha": 5, "beta": 20}}
            reshimu.save_thompson(state)
            loaded = reshimu.load_thompson()
            assert loaded == state
