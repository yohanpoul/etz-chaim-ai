"""Tests for Thompson Sampling meta-bandit.

The meta-bandit selects which creative mechanism to use.
Thompson Sampling maintains Beta(α, β) priors per mechanism
and samples to balance exploration vs exploitation.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np

from halom.models import Mechanism
from halom.thompson import ThompsonBandit


class TestThompsonBandit:
    """Thompson Sampling over the 4 creative mechanisms."""

    def test_initial_state_uniform(self):
        """Fresh bandit starts with Beta(1,1) for all mechanisms."""
        bandit = ThompsonBandit()
        state = bandit.get_state()
        for m in Mechanism:
            assert state[m.value]["alpha"] == 1
            assert state[m.value]["beta"] == 1

    def test_select_returns_valid_mechanism(self):
        """Selection always returns one of the 4 mechanisms."""
        bandit = ThompsonBandit(seed=42)
        for _ in range(100):
            m = bandit.select()
            assert m in Mechanism

    def test_update_success_increases_alpha(self):
        """Reporting success increments α for that mechanism."""
        bandit = ThompsonBandit()
        bandit.update(Mechanism.TZERUF, success=True)
        state = bandit.get_state()
        assert state["tzeruf"]["alpha"] == 2
        assert state["tzeruf"]["beta"] == 1

    def test_update_failure_increases_beta(self):
        """Reporting failure increments β for that mechanism."""
        bandit = ThompsonBandit()
        bandit.update(Mechanism.SAMAEL, success=False)
        state = bandit.get_state()
        assert state["samael"]["alpha"] == 1
        assert state["samael"]["beta"] == 2

    def test_convergence_toward_best_arm(self):
        """After many successes on one arm, it gets selected more often."""
        bandit = ThompsonBandit(seed=42)
        for _ in range(50):
            bandit.update(Mechanism.STRUCTURAL, success=True)
        counts = {m: 0 for m in Mechanism}
        for _ in range(200):
            counts[bandit.select()] += 1
        assert counts[Mechanism.STRUCTURAL] > 100

    def test_never_zero_probability(self):
        """Thompson Sampling never completely abandons a mechanism."""
        bandit = ThompsonBandit(seed=42)
        for _ in range(100):
            bandit.update(Mechanism.SAMAEL, success=False)
        selections = [bandit.select() for _ in range(1000)]
        assert Mechanism.SAMAEL in selections

    def test_phased_bias_early(self):
        """In early phase (turn < 15), Tzeruf gets a boost."""
        bandit = ThompsonBandit(seed=42)
        counts = {m: 0 for m in Mechanism}
        for _ in range(200):
            counts[bandit.select(turn=5, total_turns=50)] += 1
        assert counts[Mechanism.TZERUF] / 200 > 0.30

    def test_phased_bias_late(self):
        """In late phase (turn > 35), Abduction+Samael get a boost."""
        bandit = ThompsonBandit(seed=42)
        counts = {m: 0 for m in Mechanism}
        for _ in range(200):
            counts[bandit.select(turn=45, total_turns=50)] += 1
        late_count = counts[Mechanism.ABDUCTION] + counts[Mechanism.SAMAEL]
        assert late_count / 200 > 0.40

    def test_save_and_load(self):
        """State persists to JSON and reloads identically."""
        bandit = ThompsonBandit()
        bandit.update(Mechanism.TZERUF, success=True)
        bandit.update(Mechanism.TZERUF, success=True)
        bandit.update(Mechanism.SAMAEL, success=False)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = Path(f.name)

        bandit.save(path)
        loaded = ThompsonBandit.load(path)
        assert loaded.get_state() == bandit.get_state()
        path.unlink()

    def test_get_probabilities(self):
        """Probabilities sum to 1.0."""
        bandit = ThompsonBandit(seed=42)
        probs = bandit.get_probabilities()
        assert abs(sum(probs.values()) - 1.0) < 0.01
        for m in Mechanism:
            assert m.value in probs


class TestThompsonParameterized:
    """ThompsonBandit accepts genome-driven parameters."""

    def test_custom_epsilon(self):
        """Custom epsilon changes exploration rate."""
        bandit = ThompsonBandit(seed=42, epsilon=0.50)
        counts = {m: 0 for m in Mechanism}
        for _ in range(100):
            bandit.update(Mechanism.TZERUF, success=True)
        for _ in range(1000):
            counts[bandit.select()] += 1
        for m in Mechanism:
            assert counts[m] / 1000 > 0.08

    def test_custom_phase_bias(self):
        """Custom phase bias overrides defaults."""
        custom_bias = {
            "none": {"tzeruf": 1.0, "structural": 1.0, "abduction": 1.0, "samael": 1.0},
            "early": {"tzeruf": 0.1, "structural": 0.1, "abduction": 0.1, "samael": 5.0},
            "mid": {"tzeruf": 1.0, "structural": 1.0, "abduction": 1.0, "samael": 1.0},
            "late": {"tzeruf": 1.0, "structural": 1.0, "abduction": 1.0, "samael": 1.0},
        }
        bandit = ThompsonBandit(seed=42, phase_bias=custom_bias)
        counts = {m: 0 for m in Mechanism}
        for _ in range(200):
            counts[bandit.select(turn=5, total_turns=50)] += 1
        assert counts[Mechanism.SAMAEL] / 200 > 0.40

    def test_custom_phase_boundaries(self):
        """Custom phase boundaries change when phases switch."""
        bandit = ThompsonBandit(seed=42, phase_boundaries=[0.1, 0.2])
        counts = {m: 0 for m in Mechanism}
        for _ in range(200):
            counts[bandit.select(turn=6, total_turns=50)] += 1
        assert counts[Mechanism.STRUCTURAL] / 200 > 0.30

    def test_default_epsilon_unchanged(self):
        """Without explicit epsilon, default 0.05 is used."""
        bandit = ThompsonBandit(seed=42)
        for _ in range(200):
            bandit.update(Mechanism.TZERUF, success=True)
        counts = {m: 0 for m in Mechanism}
        for _ in range(1000):
            counts[bandit.select()] += 1
        assert counts[Mechanism.TZERUF] / 1000 > 0.70
