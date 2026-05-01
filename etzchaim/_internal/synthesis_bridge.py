"""Cross-faculty synthesis bridge for the Cognitive OS.

The bridge composes the outputs of two upstream faculties — an insight
faculty and a reason faculty — into a single coherent claim that carries the
provenance of both inputs. It performs no inference of its own and never
writes to the source faculties' state; it is a read-only composition layer.

Internal: SPEC-002 — see ``specs/02_synthesis_bridge.md``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class InsightOutput:
    """Output produced by an insight faculty for a single query."""

    text: str
    refs: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ReasonOutput:
    """Output produced by a reason faculty for a single query."""

    text: str
    refs: tuple[str, ...] = field(default_factory=tuple)
    confidence: float = 0.0


@runtime_checkable
class InsightSource(Protocol):
    """Protocol for the upstream insight faculty.

    Implementations must return an ``InsightOutput`` for any well-formed
    query string. They own their own state — the bridge never writes to it.
    """

    def insight(self, query: str) -> InsightOutput:  # pragma: no cover - protocol
        ...


@runtime_checkable
class ReasonSource(Protocol):
    """Protocol for the upstream reason faculty."""

    def reason(self, query: str) -> ReasonOutput:  # pragma: no cover - protocol
        ...


@dataclass(frozen=True)
class SynthesisResult:
    """Single coherent claim produced by the bridge.

    ``insight_refs`` and ``reason_refs`` are preserved verbatim from the
    upstream outputs so any consumer can audit which inputs produced this
    claim. ``confidence`` is bounded to ``[0.0, 1.0]``.
    """

    claim: str
    insight_refs: tuple[str, ...]
    reason_refs: tuple[str, ...]
    confidence: float


class SynthesisError(ValueError):
    """Base class for synthesis failures."""


class MissingInputError(SynthesisError):
    """Raised when the insight or reason source returns no usable output."""


def _validate_query(query: str) -> str:
    if not isinstance(query, str):
        raise TypeError(f"query must be str, got {type(query).__name__}")
    stripped = query.strip()
    if not stripped:
        raise ValueError("query must be non-empty")
    return stripped


def _validate_insight(output: InsightOutput | None) -> InsightOutput:
    if output is None:
        raise MissingInputError("insight source returned no output")
    if not isinstance(output, InsightOutput):
        raise MissingInputError(
            "insight source returned an unexpected type: "
            f"{type(output).__name__}"
        )
    if not output.text.strip():
        raise MissingInputError("insight output has empty text")
    if not output.refs:
        raise MissingInputError("insight output has no refs")
    return output


def _validate_reason(output: ReasonOutput | None) -> ReasonOutput:
    if output is None:
        raise MissingInputError("reason source returned no output")
    if not isinstance(output, ReasonOutput):
        raise MissingInputError(
            "reason source returned an unexpected type: "
            f"{type(output).__name__}"
        )
    if not output.text.strip():
        raise MissingInputError("reason output has empty text")
    if not output.refs:
        raise MissingInputError("reason output has no refs")
    return output


def _compose_claim(insight: InsightOutput, reason: ReasonOutput) -> str:
    """Deterministically combine an insight and a reason into one claim."""
    return f"{insight.text.strip()} | {reason.text.strip()}"


def _bounded_confidence(reason: ReasonOutput, insight: InsightOutput) -> float:
    """Combine the reason confidence with input richness, clamped to [0, 1].

    The reason faculty supplies a base confidence; the bridge attenuates it
    by a saturating factor that grows with the number of supporting refs.
    No randomness — same inputs always yield the same value.
    """
    base = max(0.0, min(1.0, float(reason.confidence)))
    support = len(insight.refs) + len(reason.refs)
    saturation = support / (support + 2)
    return round(base * saturation, 6)


class SynthesisBridge:
    """Compose insight + reason outputs into a single coherent claim.

    The bridge holds references to two source faculties but never mutates
    their state. Each ``synthesize`` call performs a fresh read from both
    sources, validates that both returned a usable output, and emits a
    ``SynthesisResult`` carrying the combined claim and full provenance.
    """

    def __init__(
        self,
        insight_source: InsightSource,
        reason_source: ReasonSource,
    ) -> None:
        if insight_source is None:
            raise MissingInputError("insight_source is required")
        if reason_source is None:
            raise MissingInputError("reason_source is required")
        if not hasattr(insight_source, "insight"):
            raise TypeError(
                "insight_source must implement InsightSource.insight()"
            )
        if not hasattr(reason_source, "reason"):
            raise TypeError(
                "reason_source must implement ReasonSource.reason()"
            )
        self._insight_source = insight_source
        self._reason_source = reason_source

    def synthesize(self, query: str) -> SynthesisResult:
        """Combine insight + causal reasoning into one claim with provenance."""
        normalized = _validate_query(query)
        insight = _validate_insight(self._insight_source.insight(normalized))
        reason = _validate_reason(self._reason_source.reason(normalized))

        return SynthesisResult(
            claim=_compose_claim(insight, reason),
            insight_refs=tuple(insight.refs),
            reason_refs=tuple(reason.refs),
            confidence=_bounded_confidence(reason, insight),
        )
