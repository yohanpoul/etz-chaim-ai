"""Tests du Mekhabber — tressage Sandalphon."""

import pytest
from malakhim.mekhabber.aggregator import Mekhabber, Contribution, SynthesisResult


class TestSynthesizeWeighted:
    def test_empty_contributions(self):
        m = Mekhabber()
        result = m.synthesize("query", [], mode="weighted")
        assert result.contributions_used == 0
        assert result.synthesis == ""

    def test_single_contribution(self):
        m = Mekhabber()
        contribs = [Contribution("agent1", "analysis result", score=0.8)]
        result = m.synthesize("query", contribs, mode="weighted")
        assert result.contributions_used == 1
        assert "analysis result" in result.synthesis

    def test_weighted_ordered_by_score(self):
        m = Mekhabber()
        contribs = [
            Contribution("low", "low quality", score=0.3),
            Contribution("high", "high quality", score=0.9),
        ]
        result = m.synthesize("query", contribs, mode="weighted")
        # high score should come first
        high_pos = result.synthesis.index("high quality")
        low_pos = result.synthesis.index("low quality")
        assert high_pos < low_pos


class TestSynthesizeDialectical:
    def test_dialectical_without_llm(self):
        m = Mekhabber()  # pas de generate_fn
        contribs = [
            Contribution("thesis_agent", "The sky is blue because of Rayleigh scattering", score=0.9),
            Contribution("antithesis_agent", "The sky appears blue due to our perception", score=0.6),
        ]
        result = m.synthesize("Why is the sky blue?", contribs, mode="dialectical")
        assert "Thèse" in result.synthesis
        assert "Antithèse" in result.synthesis
        assert result.mode == "dialectical"

    def test_dialectical_with_llm(self):
        m = Mekhabber(generate_fn=lambda p: f"SYNTHESIS: {p[:50]}")
        contribs = [
            Contribution("a", "point A", score=0.8),
            Contribution("b", "point B", score=0.5),
        ]
        result = m.synthesize("question", contribs, mode="dialectical")
        assert "SYNTHESIS" in result.synthesis


class TestSynthesizeHierarchical:
    def test_hierarchical_atziluth_wins(self):
        m = Mekhabber()
        contribs = [
            Contribution("junior", "simple answer", score=0.8, olam="assiah"),
            Contribution("senior", "deep answer", score=0.7, olam="atziluth"),
        ]
        result = m.synthesize("query", contribs, mode="hierarchical")
        # atziluth should be the primary decision
        assert "senior" in result.synthesis.split("\n")[0]


class TestDivergences:
    def test_no_divergence_similar(self):
        m = Mekhabber()
        contribs = [
            Contribution("a", "the analysis shows important results here", score=0.8),
            Contribution("b", "the analysis reveals important findings here", score=0.7),
        ]
        divergences = m.detect_divergences(contribs)
        assert len(divergences) == 0  # similar enough

    def test_divergence_detected(self):
        m = Mekhabber()
        contribs = [
            Contribution("a", "quantum physics explains everything through waves", score=0.8),
            Contribution("b", "classical economics determines market equilibrium", score=0.7),
        ]
        divergences = m.detect_divergences(contribs)
        assert len(divergences) > 0


class TestConvergences:
    def test_convergence_detected(self):
        m = Mekhabber()
        contribs = [
            Contribution("a", "the analysis demonstrates significant results", score=0.8),
            Contribution("b", "our analysis shows significant findings", score=0.7),
        ]
        convergences = m.detect_convergences(contribs)
        assert len(convergences) > 0  # "analysis" and "significant" should be common


class TestSynthesisMetadata:
    def test_confidence_calculated(self):
        m = Mekhabber()
        contribs = [
            Contribution("a", "result", score=0.8),
            Contribution("b", "result", score=0.6),
        ]
        result = m.synthesize("q", contribs, mode="weighted")
        assert result.confidence == pytest.approx(0.7, abs=0.01)

    def test_invalid_mode_raises(self):
        m = Mekhabber()
        contribs = [Contribution("a", "result", score=0.5)]
        with pytest.raises(ValueError, match="Unknown mode"):
            m.synthesize("q", contribs, mode="invalid")
