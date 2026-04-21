"""Tests for Reshimu genome/gilgul persistence."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from halom.gilgul import Genome, GilgulReport
from halom.reshimu import Reshimu

_BASELINE_GENOME = {
    "version": 1,
    "ancestor": None,
    "mutations_applied": [],
    "thompson": {"epsilon": 0.05},
    "birur": {"bisociation_min": 0.2, "bisociation_max": 0.8},
    "cycle": {"candidates_per_cycle": 50},
    "mechanisms": {"active": ["tzeruf", "structural", "abduction", "samael"]},
    "meta": {"creativity_model": "bisociation_koestler"},
}


class TestGenomePersistence:
    def test_save_and_load_genome(self):
        with tempfile.TemporaryDirectory() as tmp:
            reshimu = Reshimu(Path(tmp) / "HALOM")
            reshimu.init_structure()
            genome = Genome.from_dict(_BASELINE_GENOME)
            reshimu.save_genome(genome)
            loaded = reshimu.load_genome()
            assert loaded is not None
            assert loaded.version == 1
            assert loaded.thompson["epsilon"] == 0.05

    def test_load_genome_returns_none_when_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            reshimu = Reshimu(Path(tmp) / "HALOM")
            reshimu.init_structure()
            assert reshimu.load_genome() is None

    def test_save_baseline_genome(self):
        with tempfile.TemporaryDirectory() as tmp:
            reshimu = Reshimu(Path(tmp) / "HALOM")
            reshimu.init_structure()
            genome = Genome.from_dict(_BASELINE_GENOME)
            reshimu.save_baseline_genome(genome)
            loaded = reshimu.load_baseline_genome()
            assert loaded is not None
            assert loaded.version == 1

    def test_baseline_immutable_after_active_update(self):
        with tempfile.TemporaryDirectory() as tmp:
            reshimu = Reshimu(Path(tmp) / "HALOM")
            reshimu.init_structure()
            baseline = Genome.from_dict(_BASELINE_GENOME)
            reshimu.save_baseline_genome(baseline)
            mutant_data = dict(_BASELINE_GENOME)
            mutant_data["version"] = 2
            mutant_data["thompson"] = {"epsilon": 0.20}
            mutant = Genome.from_dict(mutant_data)
            reshimu.save_genome(mutant)
            loaded_baseline = reshimu.load_baseline_genome()
            assert loaded_baseline.version == 1
            assert loaded_baseline.thompson["epsilon"] == 0.05


class TestGilgulPersistence:
    def test_get_next_gilgul_number_starts_at_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            reshimu = Reshimu(Path(tmp) / "HALOM")
            reshimu.init_structure()
            assert reshimu.get_next_gilgul_number() == 1

    def test_save_gilgul_creates_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            reshimu = Reshimu(Path(tmp) / "HALOM")
            reshimu.init_structure()
            current = Genome.from_dict(_BASELINE_GENOME)
            mutant_data = dict(_BASELINE_GENOME)
            mutant_data["version"] = 2
            mutant = Genome.from_dict(mutant_data)
            report = GilgulReport(
                gilgul_number=1, date="2026-04-11",
                genome_current=current, genome_mutant=mutant,
                mutations_generated=50, mutations_survivors=7,
                test_cycle_report=None, verdict="ADOPTE",
                verdict_rationale="Discovery rate doubled",
            )
            gilgul_dir = reshimu.save_gilgul(report)
            assert gilgul_dir.is_dir()
            assert (gilgul_dir / "genome_mutant.json").exists()
            assert (gilgul_dir / "verdict.md").exists()

    def test_next_gilgul_increments(self):
        with tempfile.TemporaryDirectory() as tmp:
            reshimu = Reshimu(Path(tmp) / "HALOM")
            reshimu.init_structure()
            current = Genome.from_dict(_BASELINE_GENOME)
            mutant = Genome.from_dict(_BASELINE_GENOME)
            report = GilgulReport(
                gilgul_number=1, date="2026-04-11",
                genome_current=current, genome_mutant=mutant,
                mutations_generated=50, mutations_survivors=5,
                test_cycle_report=None, verdict="REVERT",
                verdict_rationale="Worse results",
            )
            reshimu.save_gilgul(report)
            assert reshimu.get_next_gilgul_number() == 2


class TestLigneePersistence:
    def test_save_and_load_lignee(self):
        with tempfile.TemporaryDirectory() as tmp:
            reshimu = Reshimu(Path(tmp) / "HALOM")
            reshimu.init_structure()
            lignee = {
                "v1": {"parent": None, "gilgul": None, "date": "2026-04-11",
                       "discovery_rate": 0.04, "description": "Baseline"},
            }
            reshimu.save_lignee(lignee)
            loaded = reshimu.load_lignee()
            assert loaded["v1"]["discovery_rate"] == 0.04

    def test_load_lignee_returns_empty_when_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            reshimu = Reshimu(Path(tmp) / "HALOM")
            reshimu.init_structure()
            assert reshimu.load_lignee() == {}
