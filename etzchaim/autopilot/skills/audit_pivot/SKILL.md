---
name: audit-pivot
description: Weekly check that autopilot work still aligns with MISSION.md and edge claim. Reviews recent PRs, runs adversarial questions, recommends halt or pivot if drift detected. Does not modify code.
version: 0.1.0
license: MIT
metadata:
  etzchaim:
    tags: [audit, pivot, governance]
    related_skills: [validate-edge, paper-writer]
---

# Audit Pivot

## Overview

Weekly governance skill. Walks the last week of autopilot PRs, evaluates
whether the work still advances the MISSION.md edge claim, and either
green-lights continuation or recommends a halt + pivot proposal.

This skill **does not write code**. It produces an audit report.

## When to use

Invoked by `daemon_tasks/pivot_audit.py` weekly (default 7d interval).
Can also be invoked on demand if a release gate failed unexpectedly.

## Inputs

- The current `MISSION.md`.
- Last week of autopilot trajectories (`~/.etz-chaim/autopilot/trajectories.jsonl`).
- Last week of merged PRs from the autopilot.
- Optional : last edge validation report.

## Steps

1. Read MISSION.md and the edge claim section.
2. Fetch the last week's autopilot PRs (merged and open) via `gh pr list`.
3. For each PR, classify : `advances-edge` / `plumbing` / `tangent` /
   `regression`.
4. Run four adversarial check questions, one per agent persona reachable
   via Claude Code skill subprocess :
   - **Adversaire** : "Did the last week of work reduce or amplify the
     gap between this codebase and a generic agent framework ?"
   - **Formalisateur** : "Are the new modules' invariants still distinct
     from common ML primitives ? Cite a specific theorem or property."
   - **Synthesiste** : "What would a stronger edge claim, derivable from
     the current code surface, look like ?"
   - **Edge metric** : "Is the latest measurement above or below threshold
     for ≥ 3 consecutive weeks ?"
5. Compute drift score `(plumbing + tangent + regression) / total`.
6. Render an audit report at
   `~/.etz-chaim/autopilot/audits/pivot_<YYYY-MM-DD>.md`.
7. If drift score > 0.5 OR three weeks below edge threshold OR adversaire
   raises a "collapsed to generic framework" verdict :
   - Write `PIVOT_PROPOSAL_<YYYY-MM-DD>.md` at repo root.
   - Open a GitHub issue tagged `pivot-required`.
   - Set `autopilot.enabled: false` in config (halt loop).
8. Otherwise emit `audit_ok` event and return.

## Guardrails

- The skill never touches code or specs.
- The skill never writes inside `etzchaim/`, `partzufim/`, `mazalengine/`,
  or any path that influences runtime behavior.
- Audit reports are written outside the repo root (in `~/.etz-chaim/`).
- A pivot proposal requires three persona consensus; a single adversarial
  flag is not enough to halt.

## Verification checklist

- [ ] Audit report written
- [ ] PRs classified with rationale
- [ ] Drift score computed
- [ ] If pivot triggered : issue opened + autopilot halted
- [ ] No code modifications
