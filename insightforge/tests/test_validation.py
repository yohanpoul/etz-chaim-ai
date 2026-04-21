"""Tests de validation — triple validation anti-Ghagiel."""

import pytest

from insightforge.models import CandidateInsight, InsightValidation
from insightforge.insight_validator import InsightValidator

from .conftest import (
    StubCausal,
    StubSelfModel,
    StubAutoJudge,
    StubEpisteMemory,
    StubSelfMap,
    StubDissensus,
    StubMemoryItem,
)


# ════════════════════════════════════════════════
# 1. Check Binah — causalité
# ════════════════════════════════════════════════

class TestCheckBinah:
    def test_probable_causation_passes(self, validator):
        candidate = CandidateInsight(
            description="A validated causal relationship between two variables in physics domain",
            confidence=0.7,
            connects_domains=["physics", "biology"],
        )
        result = validator.validate(candidate)
        assert result.binah_ok

    def test_correlation_only_fails(self):
        v = InsightValidator(
            binah=StubCausal(
                evidence_level="correlation_only", confidence=0.3,
            ),
        )
        candidate = CandidateInsight(
            description="Weak correlation without causal evidence for testing purposes",
            confidence=0.7,
            connects_domains=["a", "b"],
        )
        result = v.validate(candidate)
        assert not result.binah_ok

    def test_correlation_high_conf_passes(self):
        v = InsightValidator(
            binah=StubCausal(
                evidence_level="correlation_only", confidence=0.7,
            ),
        )
        candidate = CandidateInsight(
            description="Correlation with high confidence might still pass for testing",
            confidence=0.7,
            connects_domains=["a", "b"],
        )
        result = v.validate(candidate)
        assert result.binah_ok

    def test_no_binah_defaults_ok(self, validator_no_modules):
        candidate = CandidateInsight(
            description="Candidate without Binah available for validation testing purpose",
            confidence=0.7,
            connects_domains=["a", "b"],
        )
        result = validator_no_modules.validate(candidate)
        assert result.binah_ok

    def test_binah_detail_contains_info(self, validator):
        candidate = CandidateInsight(
            description="Candidate for binah detail verification testing purposes",
            confidence=0.7,
            connects_domains=["a", "b"],
        )
        result = validator.validate(candidate)
        assert len(result.binah_detail) > 0


# ════════════════════════════════════════════════
# 2. Check Gevurah — qualité
# ════════════════════════════════════════════════

class TestCheckGevurah:
    def test_good_candidate_passes(self, validator):
        candidate = CandidateInsight(
            description="Well-formed insight with sufficient detail for quality check validation",
            confidence=0.7,
            connects_domains=["physics", "biology"],
        )
        result = validator.validate(candidate)
        assert result.gevurah_ok

    def test_short_description_fails(self, validator):
        candidate = CandidateInsight(
            description="Too short",
            confidence=0.7,
            connects_domains=["a", "b"],
        )
        result = validator.validate(candidate)
        assert not result.gevurah_ok

    def test_low_confidence_fails(self, validator):
        candidate = CandidateInsight(
            description="Sufficiently long description but very low confidence level for testing",
            confidence=0.1,
            connects_domains=["a", "b"],
        )
        result = validator.validate(candidate)
        assert not result.gevurah_ok

    def test_no_domains_fails(self, validator):
        candidate = CandidateInsight(
            description="Good description but no connected domains specified at all",
            confidence=0.7,
            connects_domains=[],
        )
        result = validator.validate(candidate)
        assert not result.gevurah_ok

    def test_empty_string_domains_fail(self, validator):
        candidate = CandidateInsight(
            description="Good description but domains are empty strings not real domains",
            confidence=0.7,
            connects_domains=["", ""],
        )
        result = validator.validate(candidate)
        assert not result.gevurah_ok


# ════════════════════════════════════════════════
# 3. Check Da'at — prédiction d'erreur
# ════════════════════════════════════════════════

class TestCheckDaat:
    def test_low_risk_passes(self, validator):
        candidate = CandidateInsight(
            description="Candidate for daat low risk test with sufficient detail",
            confidence=0.7,
            connects_domains=["a", "b"],
        )
        result = validator.validate(candidate)
        assert result.daat_ok

    def test_high_risk_fails(self):
        v = InsightValidator(daat=StubSelfModel(high_risk=True))
        candidate = CandidateInsight(
            description="Candidate where daat predicts high risk error probability",
            confidence=0.7,
            connects_domains=["a", "b"],
        )
        result = v.validate(candidate)
        assert not result.daat_ok

    def test_no_predictions_passes(self):
        v = InsightValidator(daat=StubSelfModel(predictions=[]))
        candidate = CandidateInsight(
            description="Candidate where daat has no predictions at all for testing",
            confidence=0.7,
            connects_domains=["a", "b"],
        )
        result = v.validate(candidate)
        assert result.daat_ok

    def test_no_daat_defaults_ok(self, validator_no_modules):
        candidate = CandidateInsight(
            description="Candidate without daat available for validation testing",
            confidence=0.7,
            connects_domains=["a", "b"],
        )
        result = validator_no_modules.validate(candidate)
        assert result.daat_ok


# ════════════════════════════════════════════════
# 4. Triple validation
# ════════════════════════════════════════════════

class TestTripleValidation:
    def test_all_three_pass_is_valid(self, validator):
        candidate = CandidateInsight(
            description="Excellent candidate passing all three validation checks easily",
            confidence=0.7,
            connects_domains=["physics", "biology"],
        )
        result = validator.validate(candidate)
        assert result.is_valid
        assert result.triple_validated

    def test_binah_fails_not_valid(self):
        v = InsightValidator(
            binah=StubCausal(
                evidence_level="correlation_only", confidence=0.3,
            ),
            gevurah=StubAutoJudge(),
            daat=StubSelfModel(),
            require_triple=True,
        )
        candidate = CandidateInsight(
            description="Good candidate but Binah fails due to weak causal evidence",
            confidence=0.7,
            connects_domains=["a", "b"],
        )
        result = v.validate(candidate)
        assert not result.is_valid

    def test_daat_fails_not_valid(self):
        v = InsightValidator(
            binah=StubCausal(),
            gevurah=StubAutoJudge(),
            daat=StubSelfModel(high_risk=True),
            require_triple=True,
        )
        candidate = CandidateInsight(
            description="Good candidate but daat predicts high risk errors here",
            confidence=0.7,
            connects_domains=["a", "b"],
        )
        result = v.validate(candidate)
        assert not result.is_valid

    def test_two_of_three_in_relaxed_mode(self):
        v = InsightValidator(
            binah=StubCausal(),
            gevurah=StubAutoJudge(),
            daat=StubSelfModel(high_risk=True),
            require_triple=False,
        )
        candidate = CandidateInsight(
            description="Good candidate where two of three checks pass in relaxed mode",
            confidence=0.7,
            connects_domains=["a", "b"],
        )
        result = v.validate(candidate)
        # Binah OK, Gevurah OK (local check), Da'at FAIL → 2/3 → valid
        assert result.is_valid

    def test_one_of_three_in_relaxed_mode_fails(self):
        v = InsightValidator(
            binah=StubCausal(
                evidence_level="correlation_only", confidence=0.3,
            ),
            gevurah=StubAutoJudge(),
            daat=StubSelfModel(high_risk=True),
            require_triple=False,
        )
        candidate = CandidateInsight(
            description="Good candidate but only one check passes which is insufficient",
            confidence=0.7,
            connects_domains=["a", "b"],
        )
        result = v.validate(candidate)
        # Binah FAIL, Gevurah OK, Da'at FAIL → 1/3 → not valid
        assert not result.is_valid


# ════════════════════════════════════════════════
# 5. Checks supplémentaires
# ════════════════════════════════════════════════

class TestSupplementaryChecks:
    def test_sources_info_in_detail(self, validator):
        candidate = CandidateInsight(
            description="Candidate with sources available in epistemem for checking",
            confidence=0.7,
            connects_domains=["a", "b"],
        )
        result = validator.validate(candidate)
        assert "Sources" in result.binah_detail

    def test_competence_info_in_detail(self, validator):
        candidate = CandidateInsight(
            description="Candidate with competence check available for detail testing",
            confidence=0.7,
            connects_domains=["a", "b"],
        )
        result = validator.validate(candidate, domain="physics")
        assert "Competence" in result.daat_detail

    def test_low_competence_noted(self):
        v = InsightValidator(
            hod=StubSelfMap(competence=0.1),
        )
        candidate = CandidateInsight(
            description="Candidate in domain where system has low competence level",
            confidence=0.7,
            connects_domains=["a", "b"],
        )
        result = v.validate(candidate, domain="exotic")
        assert "low competence" in result.daat_detail.lower()

    def test_no_memories_noted(self):
        v = InsightValidator(
            yesod=StubEpisteMemory(memories=[]),
        )
        candidate = CandidateInsight(
            description="Candidate with no supporting data in the epistememory system",
            confidence=0.7,
            connects_domains=["a", "b"],
        )
        result = v.validate(candidate)
        assert "no supporting" in result.binah_detail.lower()

    def test_contradiction_noted(self):
        v = InsightValidator(
            tiferet=StubDissensus(has_contradiction=True),
        )
        candidate = CandidateInsight(
            description="Candidate that contradicts existing validated claims in system",
            confidence=0.7,
            connects_domains=["a", "b"],
        )
        result = v.validate(candidate)
        assert "contradict" in result.gevurah_detail.lower()


# ════════════════════════════════════════════════
# 6. Confiance composite
# ════════════════════════════════════════════════

class TestConfidence:
    def test_all_checks_pass_high_confidence(self, validator):
        candidate = CandidateInsight(
            description="Perfect candidate with all checks passing for confidence testing",
            confidence=0.8,
            connects_domains=["physics", "biology"],
        )
        result = validator.validate(candidate)
        assert result.confidence >= 0.7

    def test_no_checks_pass_low_confidence(self):
        v = InsightValidator(
            binah=StubCausal(
                evidence_level="correlation_only", confidence=0.3,
            ),
            daat=StubSelfModel(high_risk=True),
            yesod=StubEpisteMemory(memories=[]),
            hod=StubSelfMap(competence=0.1),
            tiferet=StubDissensus(has_contradiction=True),
        )
        candidate = CandidateInsight(
            description="Everything fails",
            confidence=0.1,
            connects_domains=[],
        )
        result = v.validate(candidate)
        assert result.confidence < 0.5

    def test_confidence_below_min_rejects(self):
        v = InsightValidator(
            binah=StubCausal(),
            gevurah=StubAutoJudge(),
            daat=StubSelfModel(),
            min_confidence=0.99,  # Impossible threshold
        )
        candidate = CandidateInsight(
            description="Good candidate but confidence threshold is impossibly high",
            confidence=0.7,
            connects_domains=["a", "b"],
        )
        result = v.validate(candidate)
        assert not result.is_valid

    def test_confidence_capped_at_1(self, validator):
        candidate = CandidateInsight(
            description="Maximum confidence candidate for testing caps on confidence",
            confidence=1.0,
            connects_domains=["a", "b", "c"],
            binah_validated=True,
            gevurah_validated=True,
            daat_validated=True,
        )
        result = validator.validate(candidate)
        assert result.confidence <= 1.0


# ════════════════════════════════════════════════
# 7. Batch validation
# ════════════════════════════════════════════════

class TestBatchValidation:
    def test_batch(self, validator):
        candidates = [
            CandidateInsight(
                description="First candidate for batch validation testing with detail",
                confidence=0.7,
                connects_domains=["a", "b"],
            ),
            CandidateInsight(
                description="Second candidate for batch validation testing with detail",
                confidence=0.7,
                connects_domains=["c", "d"],
            ),
        ]
        results = validator.validate_batch(candidates)
        assert len(results) == 2
        assert all(isinstance(r, InsightValidation) for r in results)

    def test_batch_empty(self, validator):
        results = validator.validate_batch([])
        assert results == []
