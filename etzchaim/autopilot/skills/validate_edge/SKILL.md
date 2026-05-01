---
name: validate-edge
description: Weekly run of the Cognitive OS Evaluation Suite. Runs all 8 metrics against current Etz Chaim build + 4 baselines (LLM alone, LangChain, AutoGen, generic self-evolution). Generates an edge report with statistical significance verdict. Does not modify code.
version: 0.1.0
license: MIT
metadata:
  etzchaim:
    tags: [evaluation, edge, benchmark]
    related_skills: [audit-pivot]
---

# Validate Edge

## Overview

Weekly benchmark skill. Runs the Cognitive OS Evaluation Suite (8 metrics)
against the four named baselines, computes statistical significance, and
writes an edge report. Halts the autopilot loop if the edge metric falls
below threshold for three consecutive weeks.

## When to use

Invoked by `daemon_tasks/edge_validation.py` weekly (default 7d interval).
Can also run on demand to verify before merging a major refactor.

## Inputs

- The current build of `etzchaim/`.
- Baseline configurations : LLM alone, LLM + LangChain, LLM + AutoGen,
  LLM + generic self-evolution loop.
- The Cognitive OS Evaluation Suite implementation under `etzchaim/eval/`.

## Steps

1. Verify all 8 metrics in the suite are implemented (else abort with
   `incomplete_suite` status).
2. For each baseline + Etz Chaim, run 3 independent passes.
3. Compute per-metric statistical comparison (paired t-test or Mann-Whitney,
   per metric type).
4. Determine `overall_significant = (significant_metrics >= 6/8 with p<0.05)`.
5. Render edge report to
   `~/.etz-chaim/autopilot/edge/edge_<YYYY-MM-DD>.md` with :
   - per-metric values + p-values
   - delta vs each baseline
   - reproducibility check (multi-LLM consistency, when 4-LLM data is available)
6. Append a row to `~/.etz-chaim/autopilot/edge/history.jsonl`.
7. If three consecutive weekly reports show `overall_significant = false`,
   trigger pivot-audit (write a flag file `EDGE_DEGRADATION` for the
   pivot-audit skill to pick up).

## Guardrails

- The skill never modifies `etzchaim/` source.
- Edge reports written to `~/.etz-chaim/autopilot/edge/` (outside the repo).
- Baseline runs use isolated processes; cross-contamination guarded by
  separate venvs.
- Historical edge data is append-only; no rewriting past reports.

## Verification checklist

- [ ] Edge report written to expected path
- [ ] All 8 metrics executed; missing ones reported as `not_implemented`
- [ ] Statistical comparison computed per metric
- [ ] History file appended
- [ ] If 3 consecutive failures : `EDGE_DEGRADATION` flag emitted
