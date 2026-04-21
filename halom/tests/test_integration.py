"""Integration test — full Halom pipeline (Python layer only).

Tests the deterministic parts of a dream cycle:
Thompson selects → candidates are created → Birur filters →
Reshimu persists. The creative generation (Opus) and adversarial
filtering (@adversaire) are handled by the skill, not tested here.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from halom.birur import Birur, RejectionReason
from halom.models import CycleReport, DreamCandidate, DreamResult, Mechanism
from halom.reshimu import Reshimu
from halom.thompson import ThompsonBandit


class TestFullPipeline:
    """End-to-end test of the Python computation layer."""

    def test_full_cycle(self):
        """Simulate a complete cycle: select → generate → filter → persist."""
        with tempfile.TemporaryDirectory() as tmp:
            halom_dir = Path(tmp) / "HALOM"

            # 1. Init persistence
            reshimu = Reshimu(halom_dir)
            reshimu.init_structure()

            # 2. Init Thompson
            bandit = ThompsonBandit(seed=42)

            # 3. Generate 20 candidates (simulated)
            candidates = []
            for i in range(20):
                mechanism = bandit.select(turn=i, total_turns=20)
                candidates.append(
                    DreamCandidate(
                        concept_k=f"Concept_K_{i}",
                        concept_ia=f"Concept_IA_{i}",
                        mechanism=mechanism,
                        structure_commune=f"Structure {i}",
                        prediction=f"Prediction {i}" if i % 3 != 0 else "",
                        score_brut=0.5,
                        bisociation=0.1 if i % 5 == 0 else 0.5,
                    )
                )

            # 4. Birur pre-filter
            birur = Birur(history=reshimu.load_history())
            survivors = birur.filter_batch(candidates)

            # Some should be filtered (empty prediction, low bisociation)
            assert len(survivors) < len(candidates)
            assert len(survivors) > 0

            # 5. Simulate adversaire (accept first 2 survivors)
            results = []
            for i, s in enumerate(survivors[:2]):
                results.append(
                    DreamResult(
                        candidate=s,
                        accepted=True,
                        adversaire_verdict="tient",
                    )
                )
                bandit.update(s.mechanism, success=True)

            # Mark the rest as failures
            for s in survivors[2:]:
                bandit.update(s.mechanism, success=False)

            # 6. Create report
            report = CycleReport(
                cycle_number=reshimu.get_next_cycle_number(),
                date="2026-04-10",
                candidates_generated=len(candidates),
                pre_filter_survivors=len(survivors),
                adversaire_survivors=len(results),
                results=results,
                thompson_state=bandit.get_state(),
            )

            # 7. Persist
            cycle_dir = reshimu.save_cycle(report)
            reshimu.save_thompson(bandit.get_state())

            # 8. Verify persistence
            assert cycle_dir.is_dir()
            assert (cycle_dir / "meta.json").exists()
            assert (cycle_dir / "rapport.md").exists()

            # History should have entries
            history = reshimu.load_history()
            assert len(history) == len(results)

            # Thompson state should be updated
            loaded_thompson = reshimu.load_thompson()
            assert loaded_thompson["tzeruf"]["alpha"] >= 1

            # Next cycle number should increment
            assert reshimu.get_next_cycle_number() == 2

    def test_multi_cycle_memory(self):
        """Cycle 2 knows what cycle 1 explored."""
        with tempfile.TemporaryDirectory() as tmp:
            halom_dir = Path(tmp) / "HALOM"
            reshimu = Reshimu(halom_dir)
            reshimu.init_structure()

            # Cycle 1: explore "Reshimu" <-> "Residual"
            reshimu.add_to_history("Reshimu", "Residual connections")
            reshimu.save_cycle(
                CycleReport(
                    cycle_number=1,
                    date="2026-04-10",
                    candidates_generated=50,
                    pre_filter_survivors=8,
                    adversaire_survivors=1,
                    results=[],
                    thompson_state={},
                )
            )

            # Cycle 2: same pair should be detected as duplicate
            history = reshimu.load_history()
            birur = Birur(history=history)
            candidate = DreamCandidate(
                concept_k="Reshimu",
                concept_ia="Residual connections",
                mechanism=Mechanism.TZERUF,
                structure_commune="Same thing",
                prediction="Same prediction",
                bisociation=0.5,
            )
            assert birur.pre_filter(candidate) == RejectionReason.DUPLICATE


class TestGilgulPipeline:
    """End-to-end test of the Gilgul (Ouroboros) Python layer."""

    def test_gilgul_cycle(self):
        """Simulate: create genome → mutate → save gilgul → load."""
        with tempfile.TemporaryDirectory() as tmp:
            halom_dir = Path(tmp) / "HALOM"
            reshimu = Reshimu(halom_dir)
            reshimu.init_structure()

            from halom.gilgul import Genome, GilgulReport, Mutation

            # 1. Create and save baseline genome
            baseline_data = {
                "version": 1,
                "ancestor": None,
                "mutations_applied": [],
                "thompson": {"epsilon": 0.05, "phase_boundaries": [0.3, 0.7]},
                "birur": {"bisociation_min": 0.2, "bisociation_max": 0.8},
                "cycle": {"candidates_per_cycle": 50},
                "mechanisms": {"active": ["tzeruf", "structural", "abduction", "samael"]},
                "meta": {},
            }
            baseline = Genome.from_dict(baseline_data)
            reshimu.save_baseline_genome(baseline)
            reshimu.save_genome(baseline)

            # 2. Create mutations
            mutations = [
                Mutation(
                    mutation_id="gilgul_001_001",
                    mechanism=Mechanism.SAMAEL,
                    target="birur.bisociation_max",
                    old_value=0.8,
                    new_value=0.95,
                    mutation_type="modify",
                    rationale="Widen creative range",
                    prediction="More E3+ discoveries",
                    testable=True,
                ),
                Mutation(
                    mutation_id="gilgul_001_002",
                    mechanism=Mechanism.ABDUCTION,
                    target="thompson.epsilon",
                    old_value=0.05,
                    new_value=0.12,
                    mutation_type="modify",
                    rationale="More exploration needed",
                    prediction="More diverse mechanism usage",
                    testable=True,
                ),
            ]

            # 3. Assemble mutant genome
            mutant_data = dict(baseline_data)
            mutant_data["version"] = 2
            mutant_data["ancestor"] = 1
            mutant_data["mutations_applied"] = [
                "bisociation_max→0.95",
                "epsilon→0.12",
            ]
            mutant_data["birur"] = {"bisociation_min": 0.2, "bisociation_max": 0.95}
            mutant_data["thompson"] = {"epsilon": 0.12, "phase_boundaries": [0.3, 0.7]}
            mutant = Genome.from_dict(mutant_data)

            # 4. Verify mutant actually changes behavior
            birur_baseline = Birur(
                bisociation_min=baseline.birur["bisociation_min"],
                bisociation_max=baseline.birur["bisociation_max"],
            )
            birur_mutant = Birur(
                bisociation_min=mutant.birur["bisociation_min"],
                bisociation_max=mutant.birur["bisociation_max"],
            )
            edge_candidate = DreamCandidate(
                concept_k="Test_K",
                concept_ia="Test_IA",
                mechanism=Mechanism.TZERUF,
                structure_commune="Test",
                prediction="Test prediction",
                bisociation=0.85,
            )
            # Baseline rejects, mutant accepts
            assert birur_baseline.pre_filter(edge_candidate) is not None
            assert birur_mutant.pre_filter(edge_candidate) is None

            # 5. Save gilgul report
            report = GilgulReport(
                gilgul_number=1,
                date="2026-04-11",
                genome_current=baseline,
                genome_mutant=mutant,
                mutations_generated=50,
                mutations_survivors=2,
                test_cycle_report=None,
                verdict="ADOPTE",
                verdict_rationale="Mutant accepted candidates baseline missed",
            )
            gilgul_dir = reshimu.save_gilgul(report)
            assert gilgul_dir.is_dir()

            # 6. Adopt mutant as active genome
            reshimu.save_genome(mutant)
            loaded = reshimu.load_genome()
            assert loaded.version == 2
            assert loaded.birur["bisociation_max"] == 0.95

            # 7. Baseline still intact
            loaded_baseline = reshimu.load_baseline_genome()
            assert loaded_baseline.version == 1
            assert loaded_baseline.birur["bisociation_max"] == 0.8

            # 8. Save and verify lignee
            lignee = {
                "v1": {"parent": None, "gilgul": None, "discovery_rate": 0.04},
                "v2": {"parent": "v1", "gilgul": "001", "discovery_rate": 0.08},
            }
            reshimu.save_lignee(lignee)
            loaded_lignee = reshimu.load_lignee()
            assert loaded_lignee["v2"]["parent"] == "v1"

            # 9. Next gilgul number increments
            assert reshimu.get_next_gilgul_number() == 2
