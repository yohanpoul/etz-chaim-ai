"""Thompson Sampling meta-bandit for creative mechanism selection.

Selects which of the 4 mechanisms (Tzeruf, Structural, Abduction, Samael)
to use at each step of the Chalom phase. Maintains Beta(α, β) priors
per mechanism, updated after each evaluation.

Thompson Sampling never abandons a mechanism completely — it always
gives a non-zero chance, preventing convergence to local optima.
This mirrors the kabbalistic principle that every Sephirah, even in
excess (Samael), has a legitimate function.

Phased regime (within a cycle):
  - Turns 1-15:  bias toward Tzeruf (exploration)
  - Turns 16-35: bias toward Structural (structuration)
  - Turns 36-50: bias toward Abduction + Samael (deepening)
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from halom.models import Mechanism

# Phase bias multipliers: multiply the sampled θ by this factor
_PHASE_BIAS: dict[str, dict[str, float]] = {
    "none": {
        Mechanism.TZERUF.value: 1.0,
        Mechanism.STRUCTURAL.value: 1.0,
        Mechanism.ABDUCTION.value: 1.0,
        Mechanism.SAMAEL.value: 1.0,
    },
    "early": {
        Mechanism.TZERUF.value: 2.0,
        Mechanism.STRUCTURAL.value: 1.0,
        Mechanism.ABDUCTION.value: 0.5,
        Mechanism.SAMAEL.value: 0.5,
    },
    "mid": {
        Mechanism.TZERUF.value: 0.8,
        Mechanism.STRUCTURAL.value: 2.0,
        Mechanism.ABDUCTION.value: 1.2,
        Mechanism.SAMAEL.value: 0.8,
    },
    "late": {
        Mechanism.TZERUF.value: 0.5,
        Mechanism.STRUCTURAL.value: 0.8,
        Mechanism.ABDUCTION.value: 2.0,
        Mechanism.SAMAEL.value: 1.5,
    },
}


class ThompsonBandit:
    """Thompson Sampling meta-bandit over 4 creative mechanisms.

    Includes a small exploration floor (epsilon=0.05) to guarantee
    that no mechanism is ever fully abandoned — even with extreme
    posterior skew. This mirrors the kabbalistic intuition: even
    Samael (the adversary) must always retain a voice.
    """

    _DEFAULT_EPSILON: float = 0.05
    _DEFAULT_PHASE_BOUNDARIES: list[float] = [0.3, 0.7]

    def __init__(
        self,
        seed: int | None = None,
        epsilon: float | None = None,
        phase_bias: dict[str, dict[str, float]] | None = None,
        phase_boundaries: list[float] | None = None,
    ):
        self._rng = np.random.default_rng(seed)
        self._arms: dict[str, dict[str, int]] = {
            m.value: {"alpha": 1, "beta": 1} for m in Mechanism
        }
        self._epsilon = epsilon if epsilon is not None else self._DEFAULT_EPSILON
        self._phase_bias = phase_bias if phase_bias is not None else _PHASE_BIAS
        self._phase_boundaries = (
            phase_boundaries if phase_boundaries is not None
            else self._DEFAULT_PHASE_BOUNDARIES
        )

    def select(
        self,
        turn: int | None = None,
        total_turns: int = 50,
    ) -> Mechanism:
        """Sample from Beta posteriors and select the best mechanism.

        When turn is None, no phase bias is applied (pure Thompson Sampling).
        When turn is provided, a phased bias steers mechanism selection.

        With probability epsilon, selects uniformly at random to ensure
        no mechanism is ever completely abandoned.
        """
        mechanisms = list(Mechanism)

        # Epsilon-greedy exploration floor
        if self._rng.random() < self._epsilon:
            return mechanisms[self._rng.integers(len(mechanisms))]

        if turn is None:
            phase = "none"
        else:
            ratio = turn / max(total_turns, 1)
            if ratio < self._phase_boundaries[0]:
                phase = "early"
            elif ratio < self._phase_boundaries[1]:
                phase = "mid"
            else:
                phase = "late"

        bias = self._phase_bias[phase]

        samples = {}
        for m in Mechanism:
            arm = self._arms[m.value]
            theta = self._rng.beta(arm["alpha"], arm["beta"])
            samples[m] = theta * bias[m.value]

        return max(samples, key=samples.get)

    def update(self, mechanism: Mechanism, success: bool) -> None:
        """Update the posterior after observing a result."""
        arm = self._arms[mechanism.value]
        if success:
            arm["alpha"] += 1
        else:
            arm["beta"] += 1

    def get_state(self) -> dict[str, dict[str, int]]:
        """Return the current state of all arms."""
        return {k: dict(v) for k, v in self._arms.items()}

    def get_probabilities(self, n_samples: int = 10000) -> dict[str, float]:
        """Estimate selection probabilities via Monte Carlo."""
        counts: dict[str, int] = {m.value: 0 for m in Mechanism}
        for _ in range(n_samples):
            m = self.select()
            counts[m.value] += 1
        total = sum(counts.values())
        return {k: v / total for k, v in counts.items()}

    def save(self, path: Path) -> None:
        """Persist state to JSON."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self._arms, indent=2))

    @classmethod
    def load(cls, path: Path) -> ThompsonBandit:
        """Load state from JSON."""
        bandit = cls()
        data = json.loads(path.read_text())
        bandit._arms = data
        return bandit
