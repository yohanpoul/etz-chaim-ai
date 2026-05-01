---
name: implement-metric
description: Use when implementing one metric of the Cognitive OS Evaluation Suite (`specs/cognitive_os_eval_suite.md`). Generates the metric class + dataset loader + per-metric test, opens a PR. Does not run benchmarks against baselines (that is the job of `task_edge_validation`).
version: 0.1.0
license: MIT
metadata:
  etzchaim:
    tags: [implementation, code, evaluation]
    related_skills: [implement-spec, implement-rectifier]
---

# Implement Metric

## Overview

Implements one of the 8 metrics from the Cognitive OS Evaluation Suite as
a self-contained module with deterministic scoring and a test that exercises
it against a stub agent.

## When to use

When the autopilot loop selects an unimplemented metric (`metric_<id>` in
the suite spec with no companion implementation marker).

## Inputs

- Metric id (e.g. `self_model_coherence`).
- The suite spec at `specs/cognitive_os_eval_suite.md` for context.

## Steps

1. Read the suite spec to identify the metric's test description and
   dataset path.
2. Create `etzchaim/eval/metrics/<metric_id>.py` implementing :
   - `class <PublicName>Metric` with `evaluate(agent: AgentUnderTest) -> MetricResult`.
   - Deterministic scoring : same inputs → same output.
3. Add dataset stub at `datasets/<metric_id>/sample.jsonl` (small fixture
   for the test). Full datasets are versioned separately and not committed
   here.
4. Add `tests/test_metric_<metric_id>.py` :
   - Stub agent with predictable behavior → expected score.
   - Two evaluations with same agent → equal `MetricResult`.
5. Surface gates : `bash scripts/check_public_surface.sh`, `pytest`.
6. Branch + commit + push + PR.

## Guardrails

- No live LLM calls in tests; use a stub agent.
- Datasets larger than 100 KB go to `datasets/<metric_id>/full.jsonl` and
  are referenced by hash in the metric module's `EXPECTED_HASH` constant.
- Metric public name must be neutral; internal mapping (if any) goes in a
  module-level `# Internal:` docstring footnote.

## Verification checklist

- [ ] `bash scripts/check_public_surface.sh` exit 0
- [ ] `pytest tests/test_metric_<metric_id>.py -x` green
- [ ] PR title : `feat(eval): implement <metric_id> metric`
- [ ] Determinism test present
- [ ] Dataset sample committed (full versioned by hash)
