"""NogahMiner — extract Nitzotzot (sparks) from errors before correction.

Kabbalistic foundation (Tanya, ch. 6):
    Qlipat Nogah is the only intermediate shell — neither purely impure
    (Shalosh Klipot Tmeot) nor holy. It contains recoverable sparks.
    Mamash-severity errors belong to the three impure shells: no Nogah,
    no extraction possible. All other errors pass through Nogah and MUST
    be mined before correction, because the fix destroys the information.

Three insight types:
    anti_pattern — what pattern produced this failure (always extracted)
    threshold    — a numerical boundary violated or approached
    invariant    — a structural contract broken (type, shape, ordering)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class NogahInsight:
    content: str
    insight_type: str          # "anti_pattern" | "threshold" | "invariant"
    confidence: float          # 0.0 – 1.0
    source_error: str
    source_module: str | None = None


# ---------------------------------------------------------------------------
# Regex patterns for threshold signals
# ---------------------------------------------------------------------------
_THRESHOLD_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"threshold\s+(?:is|=|was)\s+[\d.]+", re.IGNORECASE),
    re.compile(r"[\d.]+\s+was\s+(?:rejected|refused|below|above)", re.IGNORECASE),
    re.compile(r"(?:limit|max|min|boundary)\s+(?:is|=|was)\s+[\d.]+", re.IGNORECASE),
    re.compile(r"confidence\s+[\d.]+", re.IGNORECASE),
]

# ---------------------------------------------------------------------------
# Regex patterns for invariant violations
# ---------------------------------------------------------------------------
_INVARIANT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"expected\s+\w+\s+but\s+got\s+\w+", re.IGNORECASE),
    re.compile(r"type\s+error", re.IGNORECASE),
    re.compile(r"invalid\s+type", re.IGNORECASE),
    re.compile(r"must\s+be\s+\w+", re.IGNORECASE),
]


class NogahMiner:
    """Mine recoverable insights from non-mamash errors."""

    def __init__(self) -> None:
        self._total_extracted: int = 0

    @property
    def total_insights_extracted(self) -> int:
        return self._total_extracted

    def extract(
        self,
        error_description: str,
        severity: str,
        context: dict,
    ) -> list[NogahInsight]:
        """Extract Nitzotzot from an error.

        Args:
            error_description: Human-readable error text.
            severity: Error severity label. "mamash" → no extraction.
            context: Structured metadata about the error.

        Returns:
            List of NogahInsight objects (empty for mamash).
        """
        # Rule 1: mamash = Shalosh Klipot Tmeot, no recoverable spark.
        if severity == "mamash":
            return []

        insights: list[NogahInsight] = []

        # Rule 2: always extract an anti_pattern.
        anti_confidence = 0.6 if severity == "nogah" else 0.4
        insights.append(
            NogahInsight(
                content=(
                    f"Anti-pattern detected in '{severity}' error: {error_description}"
                ),
                insight_type="anti_pattern",
                confidence=anti_confidence,
                source_error=error_description,
            )
        )

        # Rule 3: threshold signals in error text.
        if any(pat.search(error_description) for pat in _THRESHOLD_PATTERNS):
            insights.append(
                NogahInsight(
                    content=(
                        f"Threshold boundary identified in error: {error_description}"
                    ),
                    insight_type="threshold",
                    confidence=0.7,
                    source_error=error_description,
                )
            )

        # Rule 4: invariant violations in error text.
        if any(pat.search(error_description) for pat in _INVARIANT_PATTERNS):
            insights.append(
                NogahInsight(
                    content=(
                        f"Invariant violation detected: {error_description}"
                    ),
                    insight_type="invariant",
                    confidence=0.8,
                    source_error=error_description,
                )
            )

        # Rule 5a: context threshold/limit key.
        if "threshold" in context or "limit" in context:
            insights.append(
                NogahInsight(
                    content=(
                        "Context confirms threshold boundary: "
                        + str(context.get("threshold", context.get("limit")))
                    ),
                    insight_type="threshold",
                    confidence=0.8,
                    source_error=error_description,
                )
            )

        # Rule 5b: context field + got keys.
        if "field" in context and "got" in context:
            insights.append(
                NogahInsight(
                    content=(
                        f"Context invariant: field '{context['field']}' "
                        f"received unexpected type '{context['got']}'"
                    ),
                    insight_type="invariant",
                    confidence=0.9,
                    source_error=error_description,
                )
            )

        # Rule 6: accumulate counter.
        self._total_extracted += len(insights)

        return insights
