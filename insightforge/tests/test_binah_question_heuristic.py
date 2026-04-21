"""Tests heuristique question Binah — Sprint 8b fix 1.

Les descriptions en forme de question ouverte (hitbonenut) ne sont pas
des claims falsifiables. Elles doivent être déferrées, pas envoyées à
`binah.check_claim()` qui tombe systématiquement en correlation_only.
"""

from __future__ import annotations

from insightforge.models import CandidateInsight
from insightforge.insight_validator import InsightValidator, _is_question

from .conftest import StubCausal


class _ProbeCausal(StubCausal):
    """Stub Binah qui enregistre s'il a été appelé."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.called = False

    def check_claim(self, cause, effect, domain=""):
        self.called = True
        return super().check_claim(cause=cause, effect=effect, domain=domain)


def test_is_question_ends_with_mark():
    assert _is_question("Quelle est la relation entre X et Y ?")
    assert _is_question("How does this work?")


def test_is_question_prefix_detection():
    assert _is_question("Comment les seuils de passage se formalisent")
    assert _is_question("Pourquoi X cause Y")
    assert _is_question("Why we reject this")


def test_is_question_skips_prefix_label():
    # Format réel produit par hitbonenut.
    assert _is_question(
        "Hitbonenut insight: Quelle est la relation entre A et B ?",
    )


def test_is_question_false_for_claims():
    assert not _is_question(
        "X causes Y because of mechanism Z in the domain",
    )
    assert not _is_question(
        "The mechanism: A leads to B through feedback",
    )
    assert not _is_question("")


def test_question_description_is_deferred_not_called():
    """Description en forme de question → Binah n'est pas appelé."""
    probe = _ProbeCausal()
    v = InsightValidator(binah=probe)
    candidate = CandidateInsight(
        description="Quelle est la relation entre Hishtalshelut et Information Bottleneck ?",
        confidence=0.7,
        connects_domains=["kabbalah", "ml"],
    )
    result = v.validate(candidate)
    assert not result.binah_ok
    assert "question_deferred" in result.binah_detail
    assert probe.called is False


def test_claim_description_still_calls_binah():
    """Description claim légitime → Binah est bien appelé."""
    probe = _ProbeCausal()
    v = InsightValidator(binah=probe)
    candidate = CandidateInsight(
        description="X causes Y because Z mediates the interaction in the domain",
        confidence=0.7,
        connects_domains=["a", "b"],
    )
    v.validate(candidate)
    assert probe.called is True


def test_empty_description_not_question():
    """Description vide/trop courte : fallback standard, pas question."""
    probe = _ProbeCausal()
    v = InsightValidator(binah=probe)
    candidate = CandidateInsight(
        description="",
        confidence=0.5,
        connects_domains=["a", "b"],
    )
    v.validate(candidate)
    # Binah appelé avec description vide — comportement existant préservé.
    assert probe.called is True
