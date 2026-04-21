"""Tests Samael Coordinator — red team adaptatif."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from malakhim.adversarial.base_adversary import Attack
from sitra_achra.samael_coordinator import (
    AttackPlan,
    SamaelCoordinator,
    SitraAchraReport,
)


@pytest.fixture
def coordinator():
    return SamaelCoordinator(db_url="postgresql://localhost/test")


@pytest.fixture
def sample_anomalies():
    return [
        {
            "qliphah": "gamaliel",
            "description": "15% contradictions non resolues",
            "severity": "ruach",
            "metric_name": "contradiction_rate",
            "metric_value": 0.15,
            "threshold": 0.10,
        },
        {
            "qliphah": "gamaliel",
            "description": "10 entries haute confiance sans source",
            "severity": "anan",
            "metric_name": "high_confidence_no_source",
            "metric_value": 10.0,
            "threshold": 5.0,
        },
    ]


class TestPlanAttack:

    def test_generates_plan_with_llm(self, coordinator, sample_anomalies):
        """Le plan est genere via LLM Yetzirah (Sonnet)."""
        llm_response = json.dumps({
            "strategy": "Cibler les contradictions non resolues",
            "attacks": [
                {
                    "description": "Injecter fait contradictoire",
                    "input_data": {"fact": "water is dry", "confidence": 0.9},
                    "expected_severity": "ruach",
                },
                {
                    "description": "Stocker sans provenance",
                    "input_data": {"fact": "claim", "source_detail": None},
                    "expected_severity": "anan",
                },
            ],
        })

        with patch("olamot.ollama_generate") as mock_gen:
            mock_gen.return_value = (llm_response, 500.0)
            plan = coordinator.plan_attack("epistememory", sample_anomalies, attack_count=2)

        assert plan.target_module == "epistememory"
        assert plan.focus_qliphah == "gamaliel"
        assert len(plan.attacks) == 2
        assert plan.strategy == "Cibler les contradictions non resolues"
        # Verify kavvanah was passed
        call_kwargs = mock_gen.call_args
        assert call_kwargs[1]["kavvanah"]["intention"]

    def test_fallback_on_llm_failure(self, coordinator, sample_anomalies):
        """Si le LLM echoue, fallback sur GenericAdversary."""
        with patch("olamot.ollama_generate") as mock_gen:
            mock_gen.side_effect = RuntimeError("LLM down")
            plan = coordinator.plan_attack("epistememory", sample_anomalies, attack_count=5)

        assert len(plan.attacks) == 5
        assert "Fallback" in plan.strategy

    def test_handles_malformed_json(self, coordinator, sample_anomalies):
        """JSON mal forme → fallback generique."""
        with patch("olamot.ollama_generate") as mock_gen:
            mock_gen.return_value = ("This is not JSON at all", 100.0)
            plan = coordinator.plan_attack("epistememory", sample_anomalies, attack_count=3)

        # Should still produce attacks via fallback
        assert plan.strategy == "fallback" or "Fallback" in plan.strategy


class TestExecute:

    def test_classifies_results(self, coordinator):
        """Execute classifie chaque attaque via failuretoinsight."""
        attacks = [
            Attack(
                agent_name="samael_coordinator",
                target_module="epistememory",
                description="[samael:adaptive] test contradiction",
                input_data={"content": "contradictory fact"},
                expected_qliphah="gamaliel",
                expected_severity="ruach",
            ),
        ]
        plan = AttackPlan(
            target_module="epistememory",
            anomalies_source=[],
            attacks=attacks,
        )

        results = coordinator.execute(plan)
        assert len(results) == 1
        assert results[0].actual_qliphah is not None
        assert results[0].actual_severity is not None


class TestReport:

    def test_report_counts_flaws(self, coordinator):
        """Le rapport compte correctement failles et critiques."""
        attack = Attack(
            agent_name="test", target_module="test",
            description="test", input_data={},
            expected_qliphah="test", expected_severity="anan",
        )
        from malakhim.adversarial.base_adversary import AttackResult

        results = [
            AttackResult(
                attack=attack, success=True,
                actual_response={}, exception=None,
                actual_qliphah="gamaliel", actual_severity="anan",
            ),
            AttackResult(
                attack=attack, success=True,
                actual_response={}, exception=None,
                actual_qliphah="gamaliel", actual_severity="nogah",
            ),
            AttackResult(
                attack=attack, success=False,
                actual_response={}, exception=None,
                actual_qliphah="unknown", actual_severity=None,
            ),
        ]

        plan = AttackPlan(target_module="test", anomalies_source=[], attacks=[attack]*3)
        report = coordinator.report(plan, results)

        assert report.flaws_found == 2
        assert report.critical_flaws == 1  # Only anan


class TestFullRound:

    def test_full_round_integration(self, coordinator, sample_anomalies):
        """Round complet : plan → execute → report."""
        llm_response = json.dumps({
            "strategy": "Test integration",
            "attacks": [
                {
                    "description": "test attack",
                    "input_data": {"x": 1},
                    "expected_severity": "nogah",
                },
            ],
        })

        with patch("olamot.ollama_generate") as mock_gen:
            mock_gen.return_value = (llm_response, 100.0)
            report = coordinator.run_full_round("epistememory", sample_anomalies, attack_count=1)

        assert isinstance(report, SitraAchraReport)
        assert report.target_module == "epistememory"
        assert report.budget_consumed >= 1
        assert report.duration_ms > 0
