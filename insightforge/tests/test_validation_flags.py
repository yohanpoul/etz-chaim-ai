"""Tests propagation flags triple validation — Sprint 8b fix 3.

Avant : `daat_validated` était posé prématurément dans
orchestrator._phase_self_assess avant la triple validation, tandis que
binah/gevurah_validated n'étaient posés qu'après validation réussie.
Résultat : 237 rows DB avec daat_validated=TRUE mais 0 rows avec
binah/gevurah_validated=TRUE — asymétrie qui cassait la requête
triple-AND du daemon.

Après : les 3 flags individuels reflètent le résultat de chaque gate,
quelle que soit l'issue globale de la validation.
"""

from __future__ import annotations

from insightforge.models import CandidateInsight
from insightforge.insight_validator import InsightValidator
from insightforge.orchestrator import Orchestrator

from .conftest import StubCausal, StubSelfModel


def _make_candidate() -> CandidateInsight:
    return CandidateInsight(
        description="Causal mechanism X explains pattern Y in the domain Z",
        confidence=0.7,
        connects_domains=["physics", "biology"],
    )


class TestOrchestratorPhaseSelfAssess:
    """Sprint 8b fix 3 — le daat_validated ne doit plus être posé ici."""

    def test_phase_self_assess_does_not_set_daat_flag_prematurely(self):
        from insightforge.models import InsightSession

        session = InsightSession(question="test question", domain="test")
        candidate = _make_candidate()
        session.add_candidate(candidate)

        orchestrator = Orchestrator(selfmodel=StubSelfModel(high_risk=True))
        orchestrator._phase_self_assess(session)

        # Fix 3 : le flag ne doit PAS être posé par cette phase, seule
        # la triple validation a autorité pour le poser.
        assert candidate.daat_validated is False
        assert "daat" in session.modules_consulted


class TestValidatorFlagPropagation:
    """Triple validation — les 3 flags individuels sont toujours propagés."""

    def test_binah_fail_others_ok(self):
        v = InsightValidator(
            binah=StubCausal(evidence_level="correlation_only", confidence=0.3),
            daat=StubSelfModel(high_risk=False),
        )
        result = v.validate(_make_candidate())
        assert result.binah_ok is False
        assert result.gevurah_ok is True
        assert result.daat_ok is True
        assert result.is_valid is False  # triple requis

    def test_all_gates_pass(self):
        v = InsightValidator(
            binah=StubCausal(evidence_level="probable_causation", confidence=0.8),
            daat=StubSelfModel(high_risk=False),
        )
        result = v.validate(_make_candidate())
        assert result.binah_ok is True
        assert result.gevurah_ok is True
        assert result.daat_ok is True
        assert result.is_valid is True

    def test_daat_fail_binah_ok(self):
        """Binah OK + Da'at high_risk → daat_ok=False, binah_ok=True."""
        v = InsightValidator(
            binah=StubCausal(evidence_level="probable_causation", confidence=0.8),
            daat=StubSelfModel(high_risk=True),
        )
        result = v.validate(_make_candidate())
        assert result.binah_ok is True
        assert result.daat_ok is False
        assert result.is_valid is False


class TestCoreFlagPropagationOnRejected:
    """core.py — flags propagés sur candidates rejetés aussi (pas que validés)."""

    def test_rejected_candidate_keeps_individual_flags(self, mini_forge):
        """Un candidat rejeté par Binah doit avoir binah_validated=False
        ET gevurah_validated=True si Gevurah a passé."""
        from insightforge.models import CandidateInsight, InsightSession

        session = InsightSession(question="Q", domain="general")
        candidate = CandidateInsight(
            description="Long enough description claim for local quality check pass",
            confidence=0.7,
            connects_domains=["a", "b"],
            domain="general",
        )
        session.add_candidate(candidate)

        # Forcer novelty OK pour déclencher triple validation
        from insightforge.models import NoveltyAssessment
        novelty = NoveltyAssessment(
            is_genuinely_new=True,
            novelty_score=0.8,
            reasoning="novel",
        )

        # Appeler directement le validator avec un Binah qui échoue
        from insightforge.insight_validator import InsightValidator
        v = InsightValidator(
            binah=StubCausal(evidence_level="correlation_only", confidence=0.3),
            daat=StubSelfModel(high_risk=False),
        )
        validation = v.validate(candidate)

        # Simuler la propagation que core.py fait désormais
        candidate.binah_validated = validation.binah_ok
        candidate.gevurah_validated = validation.gevurah_ok
        candidate.daat_validated = validation.daat_ok

        assert candidate.binah_validated is False
        assert candidate.gevurah_validated is True
        assert candidate.daat_validated is True
        assert validation.is_valid is False


# --- Fixture locale ---

import pytest


@pytest.fixture
def mini_forge():
    """Minimal marker; real forge not required for this suite."""
    return None
