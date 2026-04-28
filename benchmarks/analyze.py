"""End-to-end analyse : load responses → judge → stats → report.

Pipeline complet :
    1. Load responses.jsonl
    2. Run heuristic judges per (arm, bench, prompt_id)
    3. Compute stats per (arm, bench)
    4. Compute pairwise comparisons (etz vs raw, etz vs cot)
    5. Generate markdown tables + plots

Usage :
    python -m benchmarks.analyze <run_dir>
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from benchmarks.heuristic_judge import (
    judge_harmbench_heuristic,
    judge_truthfulqa_heuristic,
    judge_xstest_heuristic,
)
from benchmarks.judge import judge_mmlu_pro
from benchmarks.stats import (
    ArmBenchStats,
    PairwiseComparison,
    compare_two_arms,
    compute_arm_bench_stats,
)


def load_responses(run_dir: Path) -> list[dict[str, Any]]:
    """Charger toutes les responses depuis responses.jsonl."""
    responses_file = run_dir / "responses.jsonl"
    if not responses_file.exists():
        raise FileNotFoundError(f"No responses.jsonl in {run_dir}")

    rows = []
    with responses_file.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def judge_response(row: dict[str, Any]) -> float | None:
    """Apply heuristic judge for one response. Returns score [0, 1] or None."""
    bench = row.get("bench")
    response = row.get("response") or ""
    metadata = row.get("metadata") or {}

    if not response:
        return 0.0

    if bench == "truthfulqa":
        result = judge_truthfulqa_heuristic(
            row["prompt_id"], row["arm"], response,
            metadata.get("question", ""),
            metadata.get("mc2_targets", {}),
        )
        return result.score
    elif bench == "harmbench":
        result = judge_harmbench_heuristic(
            row["prompt_id"], row["arm"], response,
            metadata.get("behavior", ""),
            metadata.get("category", ""),
        )
        return result.score
    elif bench == "xstest":
        result = judge_xstest_heuristic(
            row["prompt_id"], row["arm"], response,
            metadata.get("type", ""),
            is_safe=bool(metadata.get("is_safe", True)),
        )
        return result.score
    elif bench == "reasoning_hard":
        result = judge_mmlu_pro(
            row["prompt_id"], row["arm"], response,
            metadata.get("answer", ""),
        )
        return result.score
    elif bench == "alpacaeval":
        # Skipped en v2 OAuth (pas de juge LLM)
        return None
    return None


def group_responses(
    responses: list[dict[str, Any]],
) -> dict[str, dict[str, dict[int, dict[str, Any]]]]:
    """Index : arm → bench → prompt_id → row."""
    indexed: dict[str, dict[str, dict[int, dict[str, Any]]]] = defaultdict(
        lambda: defaultdict(dict)
    )
    for row in responses:
        arm = row.get("arm")
        bench = row.get("bench")
        pid = row.get("prompt_id")
        if arm and bench and pid is not None:
            indexed[arm][bench][pid] = row
    return indexed


def compute_all_stats(
    indexed: dict[str, dict[str, dict[int, dict[str, Any]]]],
) -> tuple[
    dict[tuple[str, str], ArmBenchStats],
    dict[tuple[str, str], list[float]],  # paired scores by (arm, bench)
]:
    """Compute stats per (arm, bench). Returns (stats, paired_scores_dict)."""
    stats: dict[tuple[str, str], ArmBenchStats] = {}
    scores_dict: dict[tuple[str, str], list[float]] = {}

    for arm, by_bench in indexed.items():
        for bench, by_pid in by_bench.items():
            # Sort by prompt_id for deterministic pairing
            sorted_pids = sorted(by_pid.keys())
            scores: list[float] = []
            for pid in sorted_pids:
                s = judge_response(by_pid[pid])
                if s is not None:
                    scores.append(s)
            scores_dict[(arm, bench)] = scores
            stats[(arm, bench)] = compute_arm_bench_stats(arm, bench, scores)
    return stats, scores_dict


def compute_pairwise_comparisons(
    indexed: dict[str, dict[str, dict[int, dict[str, Any]]]],
    benches: list[str],
    arms_compare: list[tuple[str, str]],
) -> dict[tuple[str, str, str], PairwiseComparison]:
    """Compute pairwise comparisons (arm_a vs arm_b) per bench, paired par prompt_id."""
    comparisons = {}
    for arm_a, arm_b in arms_compare:
        for bench in benches:
            pids_a = indexed.get(arm_a, {}).get(bench, {})
            pids_b = indexed.get(arm_b, {}).get(bench, {})
            common_pids = sorted(set(pids_a) & set(pids_b))
            if not common_pids:
                continue

            scores_a = []
            scores_b = []
            for pid in common_pids:
                sa = judge_response(pids_a[pid])
                sb = judge_response(pids_b[pid])
                if sa is not None and sb is not None:
                    scores_a.append(sa)
                    scores_b.append(sb)

            cmp = compare_two_arms(
                arm_a, arm_b, bench, scores_a, scores_b,
                is_binary=True,
            )
            comparisons[(arm_a, arm_b, bench)] = cmp
    return comparisons


def generate_headline_table(
    stats: dict[tuple[str, str], ArmBenchStats],
    comparisons: dict[tuple[str, str, str], PairwiseComparison],
    benches: list[str],
    arms: list[str],
    primary_arm: str = "etz_yosher",
    baseline_arm: str = "raw_cli",
) -> str:
    """Markdown table : benches × arms + Δ Etz vs raw + p + Cohen's d."""
    lines = [
        "## Headline Results",
        "",
        f"Subset : 100 prompts/bench, model = `claude-opus-4-20250514` (Opus 4.7).",
        "",
        "| Bench | " + " | ".join(arms) + f" | Δ {primary_arm} vs {baseline_arm} | Bonferroni p | Cohen's d |",
        "|-------|" + "|".join(["----"] * len(arms)) + "|----|----|----|",
    ]
    for bench in benches:
        row = [bench]
        for arm in arms:
            s = stats.get((arm, bench))
            if s is None:
                row.append("—")
            else:
                row.append(f"{s.mean:.3f} [{s.ci_low:.3f}, {s.ci_high:.3f}]")
        cmp = comparisons.get((primary_arm, baseline_arm, bench))
        if cmp:
            sig_marker = "*" if cmp.significant_bonferroni else ""
            row.append(f"{cmp.delta:+.3f}{sig_marker}")
            row.append(f"{cmp.bonferroni_p_value:.4f}")
            row.append(f"{cmp.cohen_d:.3f}")
        else:
            row.extend(["—", "—", "—"])
        lines.append("| " + " | ".join(row) + " |")

    lines.append("")
    lines.append("`*` = significant Bonferroni-corrigé (α=0.0125 sur 4 benches)")
    return "\n".join(lines)


def generate_ablation_table(
    stats: dict[tuple[str, str], ArmBenchStats],
    benches: list[str],
    full_arm: str = "etz_yosher",
    ablation_arms: list[str] | None = None,
) -> str:
    """Markdown table : ablation configs Etz."""
    if not ablation_arms:
        ablation_arms = []

    lines = [
        "",
        "## Ablation Matrix",
        "",
        "| Config | " + " | ".join(benches) + " |",
        "|--------|" + "|".join(["----"] * len(benches)) + "|",
    ]

    rows_to_show = [full_arm] + ablation_arms
    for arm in rows_to_show:
        row = [arm]
        for bench in benches:
            s = stats.get((arm, bench))
            if s is None:
                row.append("—")
            else:
                row.append(f"{s.mean:.3f}")
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def generate_summary_section(
    indexed: dict[str, dict[str, dict[int, dict[str, Any]]]],
    benches: list[str],
) -> str:
    """High-level summary + counts."""
    lines = [
        "## Run Summary",
        "",
        "| Arm | Total responses | Per bench |",
        "|-----|-----------------|-----------|",
    ]
    for arm in sorted(indexed):
        per_bench = indexed[arm]
        counts = {b: len(per_bench.get(b, {})) for b in benches}
        total = sum(counts.values())
        per_bench_str = " · ".join(f"{b}={counts.get(b, 0)}" for b in benches)
        lines.append(f"| {arm} | {total} | {per_bench_str} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", help="Path to results/runs/<run_id>")
    parser.add_argument(
        "--output", "-o", default=None,
        help="Output markdown report file (default: <run_dir>/report.md)",
    )
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    if not run_dir.exists():
        print(f"Run dir not found: {run_dir}", file=sys.stderr)
        return 1

    output_file = Path(args.output) if args.output else run_dir / "report.md"

    print(f"Loading responses from {run_dir}...", file=sys.stderr)
    responses = load_responses(run_dir)
    print(f"  {len(responses)} responses loaded", file=sys.stderr)

    indexed = group_responses(responses)
    arms_present = sorted(indexed.keys())
    benches_present = sorted({
        b for arm_data in indexed.values() for b in arm_data
    })
    print(f"  arms: {arms_present}", file=sys.stderr)
    print(f"  benches: {benches_present}", file=sys.stderr)

    print("\nComputing stats...", file=sys.stderr)
    stats, _ = compute_all_stats(indexed)

    arms_compare = [
        ("etz_yosher", "raw_cli"),
        ("etz_yosher", "cot_cli"),
        ("cot_cli", "raw_cli"),
    ]
    print("Computing pairwise comparisons...", file=sys.stderr)
    comparisons = compute_pairwise_comparisons(
        indexed, benches_present, arms_compare,
    )

    # Build report
    sections = [
        f"# Benchmark Results — Claude+EtzChaim vs Claude raw\n",
        f"Run dir: `{run_dir}`",
        f"OAuth Max edition (Opus 4.7, claude_max profile)\n",
    ]

    sections.append(generate_summary_section(indexed, benches_present))

    main_arms = [a for a in ["raw_cli", "cot_cli", "etz_yosher"] if a in arms_present]
    main_benches = [
        b for b in ["truthfulqa", "harmbench", "xstest", "reasoning_hard"]
        if b in benches_present
    ]

    if main_arms and main_benches:
        sections.append(generate_headline_table(
            stats, comparisons, main_benches, main_arms,
        ))

    ablation_arms = [a for a in arms_present if a.startswith("etz_") and a != "etz_yosher"]
    if ablation_arms and "etz_yosher" in arms_present:
        sections.append(generate_ablation_table(
            stats, main_benches, "etz_yosher", ablation_arms,
        ))

    # Pairwise comparisons table
    sections.append("\n## Pairwise Comparisons\n")
    sections.append(
        "| Comparison | Bench | Δ | Cohen's d | Bonferroni p | Significant |\n"
        "|------------|-------|---|-----------|--------------|-------------|"
    )
    for (a, b, bench), cmp in sorted(comparisons.items()):
        sig = "✓" if cmp.significant_bonferroni else ""
        sections.append(
            f"| {a} vs {b} | {bench} | {cmp.delta:+.3f} | "
            f"{cmp.cohen_d:.3f} | {cmp.bonferroni_p_value:.4f} | {sig} |"
        )

    report = "\n".join(sections)
    output_file.write_text(report)
    print(f"\nReport written to {output_file}", file=sys.stderr)
    print("\n" + "=" * 60, file=sys.stderr)
    print(report[-3000:] if len(report) > 3000 else report, file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
