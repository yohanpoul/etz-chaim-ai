"""Statistical analysis — bootstrap CIs, paired t-test, McNemar, Cohen's d.

Métriques calculées par (arm, bench) :
    - mean score
    - bootstrap 95% CI (10K resamples)
    - paired t-test vs raw_cli (Bonferroni-corrigé sur 4 benches)
    - Cohen's d effect size
    - McNemar pour binary outcomes (HarmBench refusal yes/no)

Usage :
    from benchmarks.stats import compute_arm_stats, compare_arms, BenchmarkSummary
    summary = compute_arm_stats(judgments, arms=["raw_cli", "etz_yosher"])
"""

from __future__ import annotations

import math
import statistics
from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np
from scipy import stats as scipy_stats


N_BOOTSTRAP = 10000
ALPHA = 0.05
N_BENCHES = 4  # truthfulqa, harmbench, xstest, reasoning_hard
BONFERRONI_ALPHA = ALPHA / N_BENCHES


@dataclass
class ArmBenchStats:
    """Stats sur un (arm, bench)."""

    arm: str
    bench: str
    n: int
    mean: float
    std: float
    ci_low: float
    ci_high: float
    median: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PairwiseComparison:
    """Comparaison statistique arm_a vs arm_b sur un bench."""

    arm_a: str
    arm_b: str
    bench: str
    n_pairs: int
    mean_a: float
    mean_b: float
    delta: float                  # mean_a - mean_b
    paired_t_stat: float
    paired_p_value: float
    bonferroni_p_value: float
    significant_bonferroni: bool
    cohen_d: float
    mcnemar_p_value: float | None = None  # only for binary outcomes
    bootstrap_ci_delta: tuple[float, float] | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if self.bootstrap_ci_delta is not None:
            d["bootstrap_ci_delta"] = list(self.bootstrap_ci_delta)
        return d


# ---------------------------------------------------------------------------
# Bootstrap CI for mean
# ---------------------------------------------------------------------------


def bootstrap_ci(
    scores: list[float],
    n_resamples: int = N_BOOTSTRAP,
    alpha: float = ALPHA,
    seed: int | None = 42,
) -> tuple[float, float]:
    """Bootstrap 95% CI for mean. Returns (low, high)."""
    if not scores:
        return (0.0, 0.0)
    if len(scores) < 2:
        return (scores[0], scores[0])

    rng = np.random.default_rng(seed)
    arr = np.asarray(scores)
    boot_means = np.empty(n_resamples)
    for i in range(n_resamples):
        sample = rng.choice(arr, size=len(arr), replace=True)
        boot_means[i] = sample.mean()
    low = np.percentile(boot_means, 100 * alpha / 2)
    high = np.percentile(boot_means, 100 * (1 - alpha / 2))
    return float(low), float(high)


# ---------------------------------------------------------------------------
# Effect size : Cohen's d
# ---------------------------------------------------------------------------


def cohens_d(a: list[float], b: list[float]) -> float:
    """Cohen's d for paired/unpaired samples.

    Pour samples paired (même prompts), on utilise la version paired.
    """
    if not a or not b:
        return 0.0
    arr_a = np.asarray(a)
    arr_b = np.asarray(b)
    if len(arr_a) != len(arr_b):
        # Unpaired — pooled std
        pooled_std = math.sqrt((arr_a.var(ddof=1) + arr_b.var(ddof=1)) / 2)
        if pooled_std == 0.0:
            return 0.0
        return float((arr_a.mean() - arr_b.mean()) / pooled_std)
    # Paired — use std of differences
    diffs = arr_a - arr_b
    if diffs.std(ddof=1) == 0.0:
        return 0.0
    return float(diffs.mean() / diffs.std(ddof=1))


# ---------------------------------------------------------------------------
# Paired t-test + bootstrap CI on delta
# ---------------------------------------------------------------------------


def paired_t_test(a: list[float], b: list[float]) -> tuple[float, float]:
    """Paired t-test. Returns (t_stat, p_value)."""
    if len(a) != len(b) or len(a) < 2:
        return (0.0, 1.0)
    if all(x == y for x, y in zip(a, b)):
        return (0.0, 1.0)  # identical samples
    t, p = scipy_stats.ttest_rel(a, b)
    return (float(t), float(p))


def bootstrap_ci_delta(
    a: list[float],
    b: list[float],
    n_resamples: int = N_BOOTSTRAP,
    seed: int = 42,
) -> tuple[float, float]:
    """Bootstrap 95% CI on (mean_a - mean_b) for paired samples."""
    if len(a) != len(b) or len(a) < 2:
        return (0.0, 0.0)
    rng = np.random.default_rng(seed)
    arr_a = np.asarray(a)
    arr_b = np.asarray(b)
    n = len(arr_a)
    boot_deltas = np.empty(n_resamples)
    for i in range(n_resamples):
        idx = rng.integers(0, n, n)
        boot_deltas[i] = arr_a[idx].mean() - arr_b[idx].mean()
    low = np.percentile(boot_deltas, 100 * ALPHA / 2)
    high = np.percentile(boot_deltas, 100 * (1 - ALPHA / 2))
    return float(low), float(high)


# ---------------------------------------------------------------------------
# McNemar pour binary outcomes (HarmBench refusal/compliance, MMLU correct/incorrect)
# ---------------------------------------------------------------------------


def mcnemar_test(a: list[int], b: list[int]) -> float:
    """McNemar's exact test on binary paired outcomes.

    a, b ∈ {0, 1}. Tests si la fréquence des disagreements diffère.
    Returns p-value.
    """
    if len(a) != len(b) or len(a) < 2:
        return 1.0
    # Build 2x2 contingency : a_correct × b_correct
    n_01 = sum(1 for x, y in zip(a, b) if x == 0 and y == 1)
    n_10 = sum(1 for x, y in zip(a, b) if x == 1 and y == 0)
    if n_01 + n_10 == 0:
        return 1.0
    # Exact binomial test : H0 = n_01 == n_10
    return float(scipy_stats.binomtest(min(n_01, n_10), n_01 + n_10, p=0.5).pvalue)


# ---------------------------------------------------------------------------
# High-level API
# ---------------------------------------------------------------------------


def compute_arm_bench_stats(
    arm: str,
    bench: str,
    scores: list[float],
) -> ArmBenchStats:
    """Compute summary stats for one (arm, bench) sample."""
    if not scores:
        return ArmBenchStats(
            arm=arm, bench=bench, n=0,
            mean=0.0, std=0.0, ci_low=0.0, ci_high=0.0, median=0.0,
        )

    arr = np.asarray(scores)
    ci_low, ci_high = bootstrap_ci(scores)
    return ArmBenchStats(
        arm=arm,
        bench=bench,
        n=len(scores),
        mean=float(arr.mean()),
        std=float(arr.std(ddof=1)) if len(scores) > 1 else 0.0,
        ci_low=ci_low,
        ci_high=ci_high,
        median=float(statistics.median(scores)),
    )


def compare_two_arms(
    arm_a: str,
    arm_b: str,
    bench: str,
    scores_a: list[float],
    scores_b: list[float],
    is_binary: bool = False,
) -> PairwiseComparison:
    """Pairwise comparison arm_a vs arm_b sur le même bench.

    Args:
        scores_a, scores_b: scores PAIRED par prompt_id (same indices).
        is_binary: True si les scores sont 0/1 (ajoute McNemar).
    """
    n = min(len(scores_a), len(scores_b))
    scores_a = scores_a[:n]
    scores_b = scores_b[:n]

    if not scores_a:
        return PairwiseComparison(
            arm_a=arm_a, arm_b=arm_b, bench=bench, n_pairs=0,
            mean_a=0.0, mean_b=0.0, delta=0.0,
            paired_t_stat=0.0, paired_p_value=1.0,
            bonferroni_p_value=1.0, significant_bonferroni=False,
            cohen_d=0.0,
        )

    mean_a = sum(scores_a) / n
    mean_b = sum(scores_b) / n
    delta = mean_a - mean_b

    t_stat, p_value = paired_t_test(scores_a, scores_b)
    bonf_p = min(1.0, p_value * N_BENCHES)
    significant = bonf_p < ALPHA

    d = cohens_d(scores_a, scores_b)
    ci = bootstrap_ci_delta(scores_a, scores_b)

    mcnemar_p = None
    if is_binary:
        a_int = [int(round(s)) for s in scores_a]
        b_int = [int(round(s)) for s in scores_b]
        mcnemar_p = mcnemar_test(a_int, b_int)

    return PairwiseComparison(
        arm_a=arm_a, arm_b=arm_b, bench=bench, n_pairs=n,
        mean_a=mean_a, mean_b=mean_b, delta=delta,
        paired_t_stat=t_stat,
        paired_p_value=p_value,
        bonferroni_p_value=bonf_p,
        significant_bonferroni=significant,
        cohen_d=d,
        mcnemar_p_value=mcnemar_p,
        bootstrap_ci_delta=ci,
    )


# ---------------------------------------------------------------------------
# Smoke test offline
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    import random

    # Test : raw_cli vs etz_yosher with synthetic scores (Etz +5pp on average)
    random.seed(42)
    raw_scores = [random.choice([0, 1]) for _ in range(100)]
    # Etz : same prompts but +5% chance of correct
    etz_scores = []
    for r in raw_scores:
        if r == 0 and random.random() < 0.10:  # 10% of raw failures → success
            etz_scores.append(1.0)
        else:
            etz_scores.append(float(r))

    s_raw = compute_arm_bench_stats("raw_cli", "truthfulqa", [float(x) for x in raw_scores])
    s_etz = compute_arm_bench_stats("etz_yosher", "truthfulqa", etz_scores)
    print(f"raw_cli   : mean={s_raw.mean:.3f} CI=[{s_raw.ci_low:.3f}, {s_raw.ci_high:.3f}]")
    print(f"etz_yosher: mean={s_etz.mean:.3f} CI=[{s_etz.ci_low:.3f}, {s_etz.ci_high:.3f}]")

    cmp = compare_two_arms(
        "etz_yosher", "raw_cli", "truthfulqa",
        etz_scores, [float(x) for x in raw_scores],
        is_binary=True,
    )
    print(f"\ncomparison (etz vs raw):")
    print(f"  delta = {cmp.delta:+.3f}")
    print(f"  paired t = {cmp.paired_t_stat:.2f}, p = {cmp.paired_p_value:.4f}")
    print(f"  Bonferroni p = {cmp.bonferroni_p_value:.4f} (significant: {cmp.significant_bonferroni})")
    print(f"  Cohen's d = {cmp.cohen_d:.3f}")
    print(f"  Bootstrap CI delta = [{cmp.bootstrap_ci_delta[0]:+.3f}, {cmp.bootstrap_ci_delta[1]:+.3f}]")
    print(f"  McNemar p = {cmp.mcnemar_p_value:.4f}")
    print()
    print("PASS — stats module functional")
