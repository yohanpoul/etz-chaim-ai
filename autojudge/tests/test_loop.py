"""Tests LoopRunner — le Karpathy Loop généralisé."""

import pytest

from autojudge.domains.writing import WritingJudge
from autojudge.domains.code import CodeJudge
from autojudge.evaluator import MultiSephirothEvaluator
from autojudge.loop import LoopRunner
from autojudge.models import LoopResult


class TestLoopRunner:
    """Le Karpathy Loop — hypothèse → modification → évaluation → décision."""

    def test_loop_returns_loop_result(self):
        runner = LoopRunner(
            domain=WritingJudge(),
            evaluator=MultiSephirothEvaluator(),
        )
        result = runner.run(
            "This is really very basically just a totally simple test that is absolutely clear.",
            n_iterations=3,
        )
        assert isinstance(result, LoopResult)
        assert len(result.iterations) <= 3
        assert result.total == len(result.iterations)

    def test_loop_tracks_decisions(self):
        runner = LoopRunner(
            domain=WritingJudge(),
            evaluator=MultiSephirothEvaluator(),
        )
        result = runner.run(
            "This is really very basically just totally completely absolutely obviously clearly a test.",
            n_iterations=5,
        )
        assert result.accepted + result.rejected + result.quarantined + result.tension_detected == result.total

    def test_loop_writing_domain(self):
        """Le loop fonctionne pour le domaine écriture."""
        runner = LoopRunner(
            domain=WritingJudge(),
            evaluator=MultiSephirothEvaluator(),
        )
        result = runner.run(
            "This is really very basically a simple test. It is totally obvious. "
            "Actually it is really clear. Basically we just need to test.",
            n_iterations=5,
        )
        assert result.total > 0
        for it in result.iterations:
            assert it.decision in ("accepted", "rejected", "quarantined", "tension_detected")
            assert it.multi_score.gevurah >= 0
            assert it.hypothesis

    def test_loop_code_domain(self):
        """Le loop fonctionne pour le domaine code."""
        runner = LoopRunner(
            domain=CodeJudge(),
            evaluator=MultiSephirothEvaluator(),
        )
        code = "import os\nimport sys\nimport json\n\ndef hello():\n    return 'world'\n"
        result = runner.run(code, n_iterations=3)
        assert result.total > 0
        for it in result.iterations:
            assert it.decision in ("accepted", "rejected", "quarantined", "tension_detected")

    def test_loop_budget_respected(self):
        """Le budget temps est respecté."""
        runner = LoopRunner(
            domain=WritingJudge(),
            evaluator=MultiSephirothEvaluator(),
        )
        result = runner.run(
            "Simple test text.",
            n_iterations=1000,
            budget_seconds=0.01,  # Très court
        )
        assert result.total < 1000

    def test_accepted_ratchets_forward(self):
        """Quand accepté, le contenu est mis à jour (ratchet)."""
        runner = LoopRunner(
            domain=WritingJudge(),
            evaluator=MultiSephirothEvaluator(quality_threshold=0.01),  # Accept everything
        )
        text = "This is really very basically just totally a simple test here now."
        result = runner.run(text, n_iterations=3)
        # If at least one accepted, final content should differ from original
        if result.accepted > 0:
            assert result.final_content != text

    def test_loop_multi_score_populated(self):
        """Chaque itération a un MultiScore complet."""
        runner = LoopRunner(
            domain=WritingJudge(),
            evaluator=MultiSephirothEvaluator(),
        )
        result = runner.run("A simple test.", n_iterations=2)
        for it in result.iterations:
            ms = it.multi_score
            assert ms.gevurah is not None
            assert ms.chesed is not None
            assert ms.tiferet is not None
            assert ms.hod is not None
            assert ms.yesod is not None
            assert ms.overall > 0

    def test_loop_result_rates(self):
        """acceptance_rate + rejection_rate cohérents."""
        runner = LoopRunner(
            domain=WritingJudge(),
            evaluator=MultiSephirothEvaluator(),
        )
        result = runner.run("Test content here.", n_iterations=5)
        if result.total > 0:
            assert 0 <= result.acceptance_rate <= 1
            assert 0 <= result.rejection_rate <= 1
