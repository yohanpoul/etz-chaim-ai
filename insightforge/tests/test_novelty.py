"""Tests de nouveauté — le filtre de Chokmah."""

import pytest

from insightforge.models import CandidateInsight, NoveltyAssessment
from insightforge.novelty_assessor import NoveltyAssessor


# ════════════════════════════════════════════════
# 1. Already known
# ════════════════════════════════════════════════

class TestAlreadyKnown:
    def test_exact_match_is_known(self, novelty_with_history):
        candidate = CandidateInsight(
            description="The universe is expanding",
            confidence=0.8,
        )
        result = novelty_with_history.assess(candidate)
        assert result.already_known
        assert not result.is_genuinely_new

    def test_near_match_is_known(self, novelty_with_history):
        candidate = CandidateInsight(
            description="The universe is expanding rapidly",
            confidence=0.8,
        )
        result = novelty_with_history.assess(candidate)
        assert result.already_known

    def test_different_topic_not_known(self, novelty_with_history):
        candidate = CandidateInsight(
            description="Quantum entanglement enables faster than light communication between particles in different states",
            confidence=0.8,
            connects_domains=["quantum", "communication"],
        )
        result = novelty_with_history.assess(candidate)
        assert not result.already_known

    def test_empty_knowledge_nothing_known(self, novelty):
        candidate = CandidateInsight(
            description="Anything at all is brand new here",
            confidence=0.8,
            connects_domains=["domain_a", "domain_b"],
        )
        result = novelty.assess(candidate)
        assert not result.already_known


# ════════════════════════════════════════════════
# 2. Reformulation
# ════════════════════════════════════════════════

class TestReformulation:
    def test_past_insight_detected(self, novelty_with_history):
        candidate = CandidateInsight(
            description="Astrocyte computation mirrors attention mechanisms in transformers",
            confidence=0.9,
        )
        result = novelty_with_history.assess(candidate)
        assert result.is_reformulation
        assert not result.is_genuinely_new

    def test_similar_past_insight_detected(self, novelty_with_history):
        candidate = CandidateInsight(
            description="Astrocyte computation mirrors attention mechanisms in transformers architectures",
            confidence=0.9,
        )
        result = novelty_with_history.assess(candidate)
        assert result.is_reformulation

    def test_different_insight_not_reformulation(self, novelty_with_history):
        candidate = CandidateInsight(
            description="Causal discovery algorithms can identify confounders in observational studies of neural plasticity",
            confidence=0.7,
            connects_domains=["causality", "neuroscience"],
        )
        result = novelty_with_history.assess(candidate)
        assert not result.is_reformulation


# ════════════════════════════════════════════════
# 3. Trivialité
# ════════════════════════════════════════════════

class TestTrivial:
    def test_short_description_trivial(self, novelty):
        candidate = CandidateInsight(
            description="A is B",
            confidence=0.8,
        )
        result = novelty.assess(candidate)
        assert result.is_trivial

    def test_low_confidence_trivial(self, novelty):
        candidate = CandidateInsight(
            description="This is a sufficiently long description for testing",
            confidence=0.1,
        )
        result = novelty.assess(candidate)
        assert result.is_trivial

    def test_good_candidate_not_trivial(self, novelty):
        candidate = CandidateInsight(
            description="Cross-domain connection between causal inference and neural attention that reveals structural isomorphism",
            confidence=0.7,
            connects_domains=["causality", "attention"],
        )
        result = novelty.assess(candidate)
        assert not result.is_trivial

    def test_exactly_at_threshold(self, novelty):
        candidate = CandidateInsight(
            description="Exactly twenty chars!",  # 20 chars
            confidence=0.3,  # At threshold
        )
        result = novelty.assess(candidate)
        # At threshold = not trivial (< 20 and < 0.3 are trivial)
        assert not result.is_trivial


# ════════════════════════════════════════════════
# 4. Cross-domain
# ════════════════════════════════════════════════

class TestCrossDomain:
    def test_two_domains_is_cross(self, novelty):
        candidate = CandidateInsight(
            description="Connection between physics and biology reveals deep structural similarity in feedback mechanisms",
            confidence=0.7,
            connects_domains=["physics", "biology"],
        )
        result = novelty.assess(candidate)
        assert result.is_cross_domain

    def test_three_domains_is_cross(self, novelty):
        candidate = CandidateInsight(
            description="Triple connection across physics biology and computer science in pattern recognition mechanisms",
            confidence=0.7,
            connects_domains=["physics", "biology", "cs"],
        )
        result = novelty.assess(candidate)
        assert result.is_cross_domain

    def test_single_domain_not_cross(self, novelty):
        candidate = CandidateInsight(
            description="Pure physics insight about quantum mechanics and energy conservation principles",
            confidence=0.7,
            connects_domains=["physics"],
        )
        result = novelty.assess(candidate)
        assert not result.is_cross_domain

    def test_duplicate_domains_not_cross(self, novelty):
        candidate = CandidateInsight(
            description="Same domain connection physics to physics subfield without crossing boundaries",
            confidence=0.7,
            connects_domains=["physics", "physics"],
        )
        result = novelty.assess(candidate)
        assert not result.is_cross_domain

    def test_empty_domains_not_cross(self, novelty):
        candidate = CandidateInsight(
            description="No domains specified for this particular candidate insight",
            confidence=0.7,
            connects_domains=[],
        )
        result = novelty.assess(candidate)
        assert not result.is_cross_domain

    def test_empty_string_domains_filtered(self, novelty):
        candidate = CandidateInsight(
            description="Domains with empty strings should be filtered out properly",
            confidence=0.7,
            connects_domains=["physics", ""],
        )
        result = novelty.assess(candidate)
        assert not result.is_cross_domain


# ════════════════════════════════════════════════
# 5. Score de nouveauté
# ════════════════════════════════════════════════

class TestNoveltyScore:
    def test_already_known_score_zero(self, novelty_with_history):
        candidate = CandidateInsight(
            description="The universe is expanding",
            confidence=0.8,
        )
        result = novelty_with_history.assess(candidate)
        assert result.novelty_score == 0.0

    def test_reformulation_score_low(self, novelty_with_history):
        candidate = CandidateInsight(
            description="Information bottleneck formalizes the Tzimtzum concept",
            confidence=0.8,
        )
        result = novelty_with_history.assess(candidate)
        assert result.novelty_score == 0.1

    def test_trivial_score_low(self, novelty):
        candidate = CandidateInsight(
            description="Short",
            confidence=0.1,
        )
        result = novelty.assess(candidate)
        assert result.novelty_score == 0.2

    def test_cross_domain_bonus(self, novelty):
        single = CandidateInsight(
            description="A sufficiently detailed insight description for testing purposes with enough words",
            confidence=0.7,
            connects_domains=["physics"],
        )
        cross = CandidateInsight(
            description="A sufficiently detailed insight description for testing purposes with enough words",
            confidence=0.7,
            connects_domains=["physics", "biology"],
        )
        score_single = novelty.assess(single).novelty_score
        score_cross = novelty.assess(cross).novelty_score
        assert score_cross > score_single

    def test_high_confidence_bonus(self, novelty):
        low = CandidateInsight(
            description="A sufficiently detailed insight description for testing purposes with enough words across domains",
            confidence=0.3,
            connects_domains=["physics", "biology"],
        )
        high = CandidateInsight(
            description="A sufficiently detailed insight description for testing purposes with enough words across domains",
            confidence=0.9,
            connects_domains=["physics", "biology"],
        )
        score_low = novelty.assess(low).novelty_score
        score_high = novelty.assess(high).novelty_score
        assert score_high > score_low

    def test_long_description_bonus(self, novelty):
        short_desc = "A short but valid description for testing with domains"
        long_desc = (
            "A very long and detailed description that provides extensive "
            "context about the cross-domain connection between quantum "
            "mechanics and evolutionary biology through the lens of "
            "information theory and computational complexity"
        )
        short_c = CandidateInsight(
            description=short_desc,
            confidence=0.7,
            connects_domains=["a", "b"],
        )
        long_c = CandidateInsight(
            description=long_desc,
            confidence=0.7,
            connects_domains=["a", "b"],
        )
        score_short = novelty.assess(short_c).novelty_score
        score_long = novelty.assess(long_c).novelty_score
        assert score_long > score_short

    def test_validation_bonus(self, novelty):
        unvalidated = CandidateInsight(
            description="Unvalidated candidate with sufficient detail for testing novelty scoring mechanism",
            confidence=0.7,
            connects_domains=["a", "b"],
        )
        validated = CandidateInsight(
            description="Validated candidate with sufficient detail for testing novelty scoring mechanism",
            confidence=0.7,
            connects_domains=["a", "b"],
            binah_validated=True,
            gevurah_validated=True,
            daat_validated=True,
        )
        score_unval = novelty.assess(unvalidated).novelty_score
        score_val = novelty.assess(validated).novelty_score
        assert score_val > score_unval

    def test_score_capped_at_1(self, novelty):
        candidate = CandidateInsight(
            description="A" * 200,  # Very long
            confidence=1.0,
            connects_domains=["a", "b", "c"],
            binah_validated=True,
            gevurah_validated=True,
            daat_validated=True,
        )
        result = novelty.assess(candidate)
        assert result.novelty_score <= 1.0


# ════════════════════════════════════════════════
# 6. Genuinely new — le verdict final
# ════════════════════════════════════════════════

class TestGenuinelyNew:
    def test_new_cross_domain_high_conf(self, novelty):
        candidate = CandidateInsight(
            description="Novel cross-domain connection between quantum computing error correction and immune system adaptation mechanisms",
            confidence=0.8,
            connects_domains=["quantum", "biology"],
        )
        result = novelty.assess(candidate)
        assert result.is_genuinely_new

    def test_known_not_new(self, novelty_with_history):
        candidate = CandidateInsight(
            description="The universe is expanding",
            confidence=0.9,
        )
        result = novelty_with_history.assess(candidate)
        assert not result.is_genuinely_new

    def test_reformulated_not_new(self, novelty_with_history):
        candidate = CandidateInsight(
            description="Information bottleneck formalizes the Tzimtzum concept",
            confidence=0.9,
        )
        result = novelty_with_history.assess(candidate)
        assert not result.is_genuinely_new

    def test_trivial_not_new(self, novelty):
        candidate = CandidateInsight(
            description="Too short",
            confidence=0.1,
        )
        result = novelty.assess(candidate)
        assert not result.is_genuinely_new

    def test_below_threshold_not_new(self):
        assessor = NoveltyAssessor(min_novelty=0.99)
        candidate = CandidateInsight(
            description="Good candidate but threshold is impossibly high for passing novelty assessment",
            confidence=0.7,
            connects_domains=["a", "b"],
        )
        result = assessor.assess(candidate)
        assert not result.is_genuinely_new


# ════════════════════════════════════════════════
# 7. Batch assessment avec dédup
# ════════════════════════════════════════════════

class TestBatchAssessment:
    def test_batch_dedup(self, novelty):
        candidates = [
            CandidateInsight(
                description="Novel insight about quantum biology connections in photosynthesis mechanisms across domains",
                confidence=0.8,
                connects_domains=["quantum", "biology"],
            ),
            CandidateInsight(
                description="Novel insight about quantum biology connections in photosynthesis mechanisms across domains",
                confidence=0.8,
                connects_domains=["quantum", "biology"],
            ),
        ]
        results = novelty.assess_batch(candidates)
        assert results[0].is_genuinely_new
        assert not results[1].is_genuinely_new
        assert results[1].is_reformulation

    def test_batch_different_candidates(self, novelty):
        candidates = [
            CandidateInsight(
                description="First novel connection between thermodynamics and information theory via entropy concepts",
                confidence=0.8,
                connects_domains=["thermo", "info"],
            ),
            CandidateInsight(
                description="Second novel connection between topology and neural network weight space geometry representations",
                confidence=0.8,
                connects_domains=["topology", "ml"],
            ),
        ]
        results = novelty.assess_batch(candidates)
        assert results[0].is_genuinely_new
        assert results[1].is_genuinely_new

    def test_batch_empty(self, novelty):
        results = novelty.assess_batch([])
        assert results == []

    def test_batch_preserves_order(self, novelty):
        candidates = [
            CandidateInsight(
                description="Quantum entanglement reveals surprising connections between particle physics and cryptography",
                confidence=0.8,
                connects_domains=["a", "b"],
            ),
            CandidateInsight(
                description="Short",  # Trivial
                confidence=0.1,
            ),
            CandidateInsight(
                description="Evolutionary algorithms mimic natural selection pressure in protein folding optimization landscape",
                confidence=0.8,
                connects_domains=["c", "d"],
            ),
        ]
        results = novelty.assess_batch(candidates)
        assert len(results) == 3
        assert results[0].is_genuinely_new
        assert not results[1].is_genuinely_new  # Trivial
        assert results[2].is_genuinely_new


# ════════════════════════════════════════════════
# 8. Reasoning
# ════════════════════════════════════════════════

class TestReasoning:
    def test_reasoning_contains_score(self, novelty):
        candidate = CandidateInsight(
            description="Test candidate with adequate detail for reasoning verification",
            confidence=0.7,
            connects_domains=["a", "b"],
        )
        result = novelty.assess(candidate)
        assert "Novelty score" in result.reasoning

    def test_known_reasoning(self, novelty_with_history):
        candidate = CandidateInsight(
            description="The universe is expanding",
            confidence=0.8,
        )
        result = novelty_with_history.assess(candidate)
        assert "existing knowledge" in result.reasoning.lower()

    def test_cross_domain_reasoning(self, novelty):
        candidate = CandidateInsight(
            description="Cross-domain candidate linking different fields for reasoning test purposes",
            confidence=0.7,
            connects_domains=["physics", "biology"],
        )
        result = novelty.assess(candidate)
        assert "cross-domain" in result.reasoning.lower()

    def test_new_reasoning(self, novelty):
        candidate = CandidateInsight(
            description="Genuinely new cross-domain insight connecting very different scientific domains",
            confidence=0.8,
            connects_domains=["a", "b"],
        )
        result = novelty.assess(candidate)
        assert "GENUINELY NEW" in result.reasoning
