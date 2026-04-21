"""Birur (בירור) — pre-filter for dream candidates.

The Birur separates Nitzotzot (sparks of insight) from Klipot (shells of noise).
Only Klipat Nogah (mixed signal/noise) is worth processing — the 3 impure Klipot
(pure noise) are eliminated immediately.

This module handles the deterministic pre-filter:
1. Duplication check — already explored?
2. Bisociation zone — in [0.2, 0.8]?
3. Fertility — has a testable prediction?

The adversarial filter (@adversaire) is handled by the skill, not here.
"""
from __future__ import annotations

import enum
from typing import Any

from halom.models import DreamCandidate

_STERILE_PREDICTIONS = {"", "none", "n/a", "aucune", "todo", "tbd"}


class RejectionReason(str, enum.Enum):
    """Why a candidate was rejected."""

    DUPLICATE = "duplicate"
    TRIVIAL = "trivial"       # B < 0.2
    ABSURD = "absurd"         # B > 0.8
    STERILE = "sterile"       # No testable prediction


class Birur:
    """Pre-filter for dream candidates.

    Berakhot 57b: the dream is 1/60 of prophecy.
    This filter handles the deterministic part of the 59/60 rejection.
    """

    def __init__(
        self,
        history: list[dict[str, Any]] | None = None,
        bisociation_min: float = 0.2,
        bisociation_max: float = 0.8,
    ):
        self._history_keys: set[tuple[str, str]] = set()
        if history:
            for entry in history:
                self._history_keys.add(
                    (entry["concept_k"].lower(), entry["concept_ia"].lower())
                )
        self._b_min = bisociation_min
        self._b_max = bisociation_max

    def pre_filter(self, candidate: DreamCandidate) -> RejectionReason | None:
        """Apply all pre-filters. Returns None if passed, RejectionReason if rejected."""
        key = (candidate.concept_k.lower(), candidate.concept_ia.lower())
        if key in self._history_keys:
            return RejectionReason.DUPLICATE

        if candidate.bisociation < self._b_min:
            return RejectionReason.TRIVIAL
        if candidate.bisociation > self._b_max:
            return RejectionReason.ABSURD

        pred = candidate.prediction.strip().lower()
        if pred in _STERILE_PREDICTIONS:
            return RejectionReason.STERILE

        return None

    def filter_batch(self, candidates: list[DreamCandidate]) -> list[DreamCandidate]:
        """Filter a batch, return only survivors."""
        return [c for c in candidates if self.pre_filter(c) is None]
