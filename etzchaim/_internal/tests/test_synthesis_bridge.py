"""Tests for ``etzchaim._internal.synthesis_bridge``.

The tests use minimal fake source implementations so the bridge contract is
exercised in isolation from any real upstream faculty.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

from etzchaim._internal.synthesis_bridge import (
    InsightOutput,
    InsightSource,
    MissingInputError,
    ReasonOutput,
    ReasonSource,
    SynthesisBridge,
    SynthesisError,
    SynthesisResult,
)


class FakeInsightSource:
    def __init__(
        self,
        text: str = "pattern observed",
        refs: tuple[str, ...] = ("note-1", "note-2"),
    ) -> None:
        self._text = text
        self._refs = refs
        self.calls: list[str] = []

    def insight(self, query: str) -> InsightOutput:
        self.calls.append(query)
        return InsightOutput(text=self._text, refs=self._refs)


class FakeReasonSource:
    def __init__(
        self,
        text: str = "cause inferred",
        refs: tuple[str, ...] = ("trace-a",),
        confidence: float = 0.6,
    ) -> None:
        self._text = text
        self._refs = refs
        self._confidence = confidence
        self.calls: list[str] = []

    def reason(self, query: str) -> ReasonOutput:
        self.calls.append(query)
        return ReasonOutput(
            text=self._text, refs=self._refs, confidence=self._confidence
        )


class EmptyInsightSource:
    def insight(self, query: str) -> InsightOutput:
        return InsightOutput(text="", refs=())


class NoneInsightSource:
    def insight(self, query: str):
        return None


class EmptyReasonSource:
    def reason(self, query: str) -> ReasonOutput:
        return ReasonOutput(text="", refs=(), confidence=0.0)


class NoneReasonSource:
    def reason(self, query: str):
        return None


class StatefulReasonSource:
    """Records mutations attempted by a hypothetical bypass."""

    def __init__(self) -> None:
        self.state = {"writes": 0}
        self._refs = ("trace-1",)

    def reason(self, query: str) -> ReasonOutput:
        return ReasonOutput(text="ok", refs=self._refs, confidence=0.5)


def test_construction_with_two_valid_sources() -> None:
    bridge = SynthesisBridge(FakeInsightSource(), FakeReasonSource())
    assert isinstance(bridge, SynthesisBridge)


def test_construction_rejects_missing_sources() -> None:
    with pytest.raises(MissingInputError):
        SynthesisBridge(None, FakeReasonSource())  # type: ignore[arg-type]
    with pytest.raises(MissingInputError):
        SynthesisBridge(FakeInsightSource(), None)  # type: ignore[arg-type]


def test_construction_rejects_wrong_protocol() -> None:
    class NotASource:
        pass

    with pytest.raises(TypeError):
        SynthesisBridge(NotASource(), FakeReasonSource())  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        SynthesisBridge(FakeInsightSource(), NotASource())  # type: ignore[arg-type]


def test_synthesize_returns_result_with_non_empty_refs() -> None:
    bridge = SynthesisBridge(FakeInsightSource(), FakeReasonSource())
    result = bridge.synthesize("why did X fail?")
    assert isinstance(result, SynthesisResult)
    assert result.claim
    assert result.insight_refs == ("note-1", "note-2")
    assert result.reason_refs == ("trace-a",)
    assert 0.0 <= result.confidence <= 1.0


def test_synthesize_preserves_provenance_verbatim() -> None:
    insight = FakeInsightSource(refs=("alpha", "beta", "gamma"))
    reason = FakeReasonSource(refs=("x", "y"))
    result = SynthesisBridge(insight, reason).synthesize("q")
    assert result.insight_refs == ("alpha", "beta", "gamma")
    assert result.reason_refs == ("x", "y")


def test_synthesize_is_deterministic_for_equal_inputs() -> None:
    def fresh() -> SynthesisBridge:
        return SynthesisBridge(FakeInsightSource(), FakeReasonSource())

    a = fresh().synthesize("same query")
    b = fresh().synthesize("same query")
    assert a == b


def test_synthesize_differs_when_inputs_differ() -> None:
    base = SynthesisBridge(FakeInsightSource(), FakeReasonSource()).synthesize("q")
    other = SynthesisBridge(
        FakeInsightSource(text="different pattern"), FakeReasonSource()
    ).synthesize("q")
    assert base != other


def test_synthesize_rejects_empty_query() -> None:
    bridge = SynthesisBridge(FakeInsightSource(), FakeReasonSource())
    with pytest.raises(ValueError):
        bridge.synthesize("")
    with pytest.raises(ValueError):
        bridge.synthesize("   ")


def test_synthesize_rejects_non_string_query() -> None:
    bridge = SynthesisBridge(FakeInsightSource(), FakeReasonSource())
    with pytest.raises(TypeError):
        bridge.synthesize(123)  # type: ignore[arg-type]


def test_synthesize_raises_when_insight_missing() -> None:
    bridge = SynthesisBridge(EmptyInsightSource(), FakeReasonSource())
    with pytest.raises(ValueError):
        bridge.synthesize("q")


def test_synthesize_raises_when_insight_returns_none() -> None:
    bridge = SynthesisBridge(NoneInsightSource(), FakeReasonSource())
    with pytest.raises(ValueError):
        bridge.synthesize("q")


def test_synthesize_raises_when_reason_missing() -> None:
    bridge = SynthesisBridge(FakeInsightSource(), EmptyReasonSource())
    with pytest.raises(ValueError):
        bridge.synthesize("q")


def test_synthesize_raises_when_reason_returns_none() -> None:
    bridge = SynthesisBridge(FakeInsightSource(), NoneReasonSource())
    with pytest.raises(ValueError):
        bridge.synthesize("q")


def test_missing_input_error_is_synthesis_error() -> None:
    assert issubclass(MissingInputError, SynthesisError)
    assert issubclass(SynthesisError, ValueError)


def test_protocols_runtime_checkable() -> None:
    assert isinstance(FakeInsightSource(), InsightSource)
    assert isinstance(FakeReasonSource(), ReasonSource)


def test_bridge_does_not_mutate_source_state() -> None:
    reason = StatefulReasonSource()
    snapshot = dict(reason.state)
    SynthesisBridge(FakeInsightSource(), reason).synthesize("q")
    assert reason.state == snapshot


def test_bridge_source_contains_no_state_assignment() -> None:
    """Static check: the bridge source contains no assignment to attributes
    of its source faculties (``state``, ``refs``, etc.). This guards the
    no-bypass invariant at the source level, not just at runtime."""
    src_path = (
        pathlib.Path(__file__).resolve().parents[1] / "synthesis_bridge.py"
    )
    tree = ast.parse(src_path.read_text())
    forbidden = {"state", "refs", "text", "confidence"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Attribute):
                    if isinstance(target.value, ast.Attribute):
                        chain = target.value.attr
                        if chain in {"_insight_source", "_reason_source"}:
                            assert target.attr not in forbidden, (
                                f"forbidden write to source.{target.attr}"
                            )


def test_confidence_is_zero_when_reason_confidence_is_zero() -> None:
    reason = FakeReasonSource(confidence=0.0)
    result = SynthesisBridge(FakeInsightSource(), reason).synthesize("q")
    assert result.confidence == 0.0


def test_confidence_clamped_when_reason_returns_out_of_range() -> None:
    reason = FakeReasonSource(confidence=2.5)
    result = SynthesisBridge(FakeInsightSource(), reason).synthesize("q")
    assert 0.0 <= result.confidence <= 1.0
    reason_neg = FakeReasonSource(confidence=-1.0)
    result_neg = SynthesisBridge(FakeInsightSource(), reason_neg).synthesize("q")
    assert result_neg.confidence == 0.0


def test_query_is_normalized_before_dispatch() -> None:
    insight = FakeInsightSource()
    reason = FakeReasonSource()
    SynthesisBridge(insight, reason).synthesize("  trim me  ")
    assert insight.calls == ["trim me"]
    assert reason.calls == ["trim me"]
