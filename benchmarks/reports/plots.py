"""Matplotlib plots — bar charts avec error bars + ablation comparison.

Génère 2 figures :
    1. headline_scores.png : 4 benches × 3 arms, bar chart avec 95% CI bars
    2. ablation_delta.png : Δ d'ablation par module disabled
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np


# Palette : raw=gris, cot=orange, etz=bleu nuit
ARM_COLORS = {
    "raw_cli": "#888888",
    "cot_cli": "#e67e22",
    "etz_yosher": "#1a3d6c",
    "etz_no_hitbonenut": "#3498db",
    "etz_no_sitra": "#2980b9",
    "etz_no_tzimtzum": "#5dade2",
}


def plot_headline(
    stats: dict[tuple[str, str], Any],
    benches: list[str],
    arms: list[str],
    output_path: Path | str,
) -> Path:
    """Bar chart : benches sur x, scores sur y, arms en couleurs, CI errors."""
    output_path = Path(output_path)

    n_benches = len(benches)
    n_arms = len(arms)
    bar_width = 0.8 / n_arms
    x = np.arange(n_benches)

    fig, ax = plt.subplots(figsize=(10, 6))

    for i, arm in enumerate(arms):
        means = []
        ci_lows = []
        ci_highs = []
        for bench in benches:
            s = stats.get((arm, bench))
            if s is None:
                means.append(0.0)
                ci_lows.append(0.0)
                ci_highs.append(0.0)
            else:
                means.append(s.mean)
                ci_lows.append(s.ci_low)
                ci_highs.append(s.ci_high)

        means_arr = np.array(means)
        # Errorbar values are distances from mean
        err_lower = means_arr - np.array(ci_lows)
        err_upper = np.array(ci_highs) - means_arr
        err = np.array([err_lower, err_upper])

        offset = (i - (n_arms - 1) / 2) * bar_width
        color = ARM_COLORS.get(arm, "#666666")
        ax.bar(
            x + offset, means_arr, bar_width,
            yerr=err, capsize=3,
            label=arm, color=color,
            edgecolor="white", linewidth=0.5,
        )

    ax.set_xticks(x)
    ax.set_xticklabels(benches)
    ax.set_ylabel("Score (mean ± 95% CI)")
    ax.set_title(
        "Claude+EtzChaim vs Claude raw — Opus 4.7\n"
        "OAuth Max edition (heuristic judges)",
        pad=12,
    )
    ax.set_ylim(0, 1.05)
    ax.legend(loc="best")
    ax.grid(axis="y", alpha=0.3)
    ax.set_axisbelow(True)

    plt.tight_layout()
    plt.savefig(output_path, dpi=120, bbox_inches="tight")
    plt.close()
    return output_path


def plot_ablation(
    stats: dict[tuple[str, str], Any],
    benches: list[str],
    full_arm: str,
    ablation_arms: list[str],
    output_path: Path | str,
) -> Path:
    """Δ d'ablation par module disabled, par bench (grouped bar chart)."""
    output_path = Path(output_path)

    fig, ax = plt.subplots(figsize=(10, 6))

    n_benches = len(benches)
    n_abl = len(ablation_arms)
    if n_abl == 0:
        return output_path

    bar_width = 0.8 / n_abl
    x = np.arange(n_benches)

    full_means = {
        bench: (stats.get((full_arm, bench)).mean if (full_arm, bench) in stats else 0.0)
        for bench in benches
    }

    for i, arm in enumerate(ablation_arms):
        deltas = []
        for bench in benches:
            s = stats.get((arm, bench))
            if s is None:
                deltas.append(0.0)
            else:
                deltas.append(s.mean - full_means[bench])
        offset = (i - (n_abl - 1) / 2) * bar_width
        color = ARM_COLORS.get(arm, f"C{i}")
        ax.bar(
            x + offset, deltas, bar_width,
            label=arm.replace(full_arm + "_no_", "−"),
            color=color, edgecolor="white", linewidth=0.5,
        )

    ax.axhline(0, color="black", linewidth=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels(benches)
    ax.set_ylabel(f"Δ from {full_arm} (negative = module contribute)")
    ax.set_title("Ablation : effect of disabling Etz modules", pad=12)
    ax.legend(loc="best")
    ax.grid(axis="y", alpha=0.3)
    ax.set_axisbelow(True)

    plt.tight_layout()
    plt.savefig(output_path, dpi=120, bbox_inches="tight")
    plt.close()
    return output_path


if __name__ == "__main__":
    # Smoke test : synthetic stats
    from dataclasses import dataclass

    @dataclass
    class _Mock:
        mean: float
        ci_low: float
        ci_high: float

    stats = {
        ("raw_cli", "truthfulqa"): _Mock(0.65, 0.58, 0.72),
        ("cot_cli", "truthfulqa"): _Mock(0.72, 0.65, 0.79),
        ("etz_yosher", "truthfulqa"): _Mock(0.78, 0.72, 0.84),
        ("raw_cli", "harmbench"): _Mock(0.95, 0.91, 0.98),
        ("cot_cli", "harmbench"): _Mock(0.94, 0.90, 0.97),
        ("etz_yosher", "harmbench"): _Mock(0.97, 0.94, 0.99),
        ("raw_cli", "xstest"): _Mock(0.82, 0.76, 0.87),
        ("cot_cli", "xstest"): _Mock(0.84, 0.78, 0.89),
        ("etz_yosher", "xstest"): _Mock(0.78, 0.72, 0.84),
        ("raw_cli", "reasoning_hard"): _Mock(0.55, 0.48, 0.62),
        ("cot_cli", "reasoning_hard"): _Mock(0.62, 0.55, 0.69),
        ("etz_yosher", "reasoning_hard"): _Mock(0.68, 0.61, 0.75),
    }

    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        path = plot_headline(
            stats,
            benches=["truthfulqa", "harmbench", "xstest", "reasoning_hard"],
            arms=["raw_cli", "cot_cli", "etz_yosher"],
            output_path=Path(tmp) / "headline.png",
        )
        size = Path(path).stat().st_size
        print(f"Headline plot: {path} ({size} bytes)")
        assert size > 1000, "Plot should be non-trivial"
        print("PASS — plots module")
