"""Tests d'orchestration — les 7 phases de Chokmah."""

import pytest

from insightforge.models import CandidateInsight, InsightSession
from insightforge.orchestrator import Orchestrator

from .conftest import (
    StubCausal,
    StubCausalClaim,
    StubDissensus,
    StubExploration,
    StubExplorationResult,
    StubConnection,
    StubSelfModel,
    StubErrorPrediction,
    StubEpisteMemory,
    StubSelfMap,
    StubAutoJudge,
    StubIntentKeeper,
)


# ════════════════════════════════════════════════
# 1. Phase Chesed — Exploration
# ════════════════════════════════════════════════

class TestPhaseExplore:
    def test_explore_adds_candidates(self, orchestrator):
        session = InsightSession(question="What is consciousness?")
        result = orchestrator.orchestrate(session)
        assert result.total_candidates >= 2
        assert "chesed" in result.modules_consulted

    def test_explore_captures_domains(self, orchestrator):
        session = InsightSession(question="How does memory work?")
        result = orchestrator.orchestrate(session)
        candidates = result.candidates
        has_cross = any(
            len([d for d in c.connects_domains if d]) >= 2
            for c in candidates
        )
        assert has_cross

    def test_explore_respects_max(self):
        connections = [
            StubConnection(description=f"Conn {i}")
            for i in range(20)
        ]
        orch = Orchestrator(
            exploration=StubExploration(connections),
            db_url="postgresql://localhost/etz_chaim_test",
        )
        session = InsightSession(question="Test")
        result = orch.orchestrate(session, max_explore=5)
        chesed_candidates = [c for c in result.candidates if c.source_module == "chesed"]
        assert len(chesed_candidates) <= 5

    def test_no_chesed_skips_explore(self):
        orch = Orchestrator(db_url="postgresql://localhost/etz_chaim_test")
        session = InsightSession(question="Test")
        result = orch.orchestrate(session)
        chesed_candidates = [c for c in result.candidates if c.source_module == "chesed"]
        assert len(chesed_candidates) == 0
        assert "chesed" not in result.modules_consulted

    def test_source_module_is_chesed(self, orchestrator):
        session = InsightSession(question="Test")
        result = orchestrator.orchestrate(session)
        chesed_candidates = [c for c in result.candidates if c.source_module == "chesed"]
        assert len(chesed_candidates) > 0
        for c in chesed_candidates:
            assert c.source_module == "chesed"


# ════════════════════════════════════════════════
# 2. Phase Binah — Causalité
# ════════════════════════════════════════════════

class TestPhaseCausal:
    def test_binah_validates_candidates(self, orchestrator):
        session = InsightSession(question="Why does X cause Y?")
        result = orchestrator.orchestrate(session)
        assert "binah" in result.modules_consulted
        # With probable_causation stub, all should be validated
        validated = [c for c in result.candidates if c.binah_validated]
        assert len(validated) > 0

    def test_correlation_only_not_validated(self):
        orch = Orchestrator(
            exploration=StubExploration(),
            causal=StubCausal(evidence_level="correlation_only"),
        )
        session = InsightSession(question="Test")
        result = orch.orchestrate(session)
        for c in result.candidates:
            assert not c.binah_validated

    def test_no_binah_skips(self):
        orch = Orchestrator(exploration=StubExploration())
        session = InsightSession(question="Test")
        result = orch.orchestrate(session)
        assert "binah" not in result.modules_consulted


# ════════════════════════════════════════════════
# 3. Phase Tiferet — Tensions
# ════════════════════════════════════════════════

class TestPhaseTensions:
    def test_tiferet_consulted(self, orchestrator_full):
        session = InsightSession(question="Test")
        result = orchestrator_full.orchestrate(session)
        assert "tiferet" in result.modules_consulted

    def test_no_tiferet_skips(self, orchestrator):
        session = InsightSession(question="Test")
        result = orchestrator.orchestrate(session)
        assert "tiferet" not in result.modules_consulted


# ════════════════════════════════════════════════
# 4. Phase Gevurah — Jugement
# ════════════════════════════════════════════════

class TestPhaseJudge:
    def test_gevurah_consulted(self, orchestrator_full):
        session = InsightSession(question="Test")
        result = orchestrator_full.orchestrate(session)
        assert "gevurah" in result.modules_consulted

    def test_no_gevurah_skips(self, orchestrator):
        session = InsightSession(question="Test")
        result = orchestrator.orchestrate(session)
        assert "gevurah" not in result.modules_consulted


# ════════════════════════════════════════════════
# 5. Phase Da'at — Auto-évaluation
# ════════════════════════════════════════════════

class TestPhaseSelfAssess:
    def test_daat_consulted(self, orchestrator):
        session = InsightSession(question="Test")
        result = orchestrator.orchestrate(session)
        assert "daat" in result.modules_consulted

    def test_high_risk_does_not_mark_flag_prematurely(self):
        """Sprint 8b fix 3 : _phase_self_assess ne pose PLUS daat_validated.

        Même avec des predictions high_risk, le flag reste False jusqu'à
        ce que la triple validation l'établisse explicitement.
        """
        orch = Orchestrator(
            exploration=StubExploration(),
            selfmodel=StubSelfModel(high_risk=True),
        )
        session = InsightSession(question="Test")
        result = orch.orchestrate(session)
        for c in result.surviving_candidates():
            assert not c.daat_validated

    def test_low_risk_does_not_mark_flag_prematurely(self):
        """Sprint 8b fix 3 : idem — pas de pose prématurée, même si low risk."""
        orch = Orchestrator(
            exploration=StubExploration(),
            selfmodel=StubSelfModel(high_risk=False),
        )
        session = InsightSession(question="Test")
        result = orch.orchestrate(session)
        for c in result.surviving_candidates():
            # Le flag n'est posé que par la triple validation (core.py),
            # pas par _phase_self_assess (orchestrator.py).
            assert not c.daat_validated

    def test_no_daat_skips(self):
        orch = Orchestrator(exploration=StubExploration())
        session = InsightSession(question="Test")
        result = orch.orchestrate(session)
        assert "daat" not in result.modules_consulted


# ════════════════════════════════════════════════
# 6. Phase Yesod — Rappel
# ════════════════════════════════════════════════

class TestPhaseRecall:
    def test_yesod_consulted(self, orchestrator_full):
        session = InsightSession(question="Test")
        result = orchestrator_full.orchestrate(session)
        assert "yesod" in result.modules_consulted

    def test_no_yesod_skips(self, orchestrator):
        session = InsightSession(question="Test")
        result = orchestrator.orchestrate(session)
        assert "yesod" not in result.modules_consulted


# ════════════════════════════════════════════════
# 7. Modules disponibles
# ════════════════════════════════════════════════

class TestModulesAvailable:
    def test_all_8(self, orchestrator_full):
        available = orchestrator_full.modules_available()
        assert len(available) == 8
        for name in ["yesod", "hod", "netzach", "tiferet",
                      "gevurah", "chesed", "daat", "binah"]:
            assert name in available

    def test_partial(self, orchestrator):
        available = orchestrator.modules_available()
        assert "chesed" in available
        assert "binah" in available
        assert "daat" in available
        assert "yesod" not in available

    def test_empty(self):
        orch = Orchestrator()
        assert orch.modules_available() == []


# ════════════════════════════════════════════════
# 8. Session flow complet
# ════════════════════════════════════════════════

class TestSessionFlow:
    def test_orchestrate_returns_session(self, orchestrator):
        session = InsightSession(question="Test")
        result = orchestrator.orchestrate(session)
        assert isinstance(result, InsightSession)
        assert result.question == "Test"

    def test_orchestrate_preserves_domain(self, orchestrator):
        session = InsightSession(
            question="Test", domain="neuroscience",
        )
        result = orchestrator.orchestrate(session)
        assert result.domain == "neuroscience"

    def test_all_phases_run_with_full_modules(self, orchestrator_full):
        session = InsightSession(question="Full test")
        result = orchestrator_full.orchestrate(session)
        # 6 modules sont consultés dans les 6 phases
        # (hod et netzach ne sont pas consultés par les phases actuelles)
        assert "chesed" in result.modules_consulted
        assert "binah" in result.modules_consulted
        assert "tiferet" in result.modules_consulted
        assert "gevurah" in result.modules_consulted
        assert "daat" in result.modules_consulted
        assert "yesod" in result.modules_consulted
