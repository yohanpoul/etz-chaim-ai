---
name: implement-rectifier
description: Use when implementing one of the 13 rectifier specs from `specs/04_rectifiers/*.md`. Reads the failure pattern, action options, and invariants; produces a rectifier subclass + tests + PR with neutral naming. Never modifies the probe orchestrator's public contract.
version: 0.1.0
license: MIT
metadata:
  etzchaim:
    tags: [implementation, code, rectifier]
    related_skills: [implement-spec, implement-metric]
---

# Implement Rectifier

## Overview

Implements one rectifier specification (`specs/04_rectifiers/<n>.md`) into a
runnable Python class extending `BaseRectifier`, plus tests, opens a PR.

## When to use

When the autopilot loop selects an unimplemented rectifier spec (any file
under `specs/04_rectifiers/` whose name has no companion `.implemented` flag).

## Inputs

- Path to the rectifier spec (e.g. `specs/04_rectifiers/01.md`).
- The frozen context snapshot (mission + autopilot context + operator).

## Steps

1. Read the spec; parse frontmatter for `public_name`, `module_path`,
   `internal_name`, `internal_source`.
2. Confirm `BaseRectifier` exists in `etzchaim/probes/` (or its alias).
3. Create the rectifier class in `module_path` with public neutral name
   from frontmatter `public_name`.
4. Implement `detect(tree)` returning `list[Deviation]` according to the
   spec's failure pattern.
5. Implement `rectify(deviations, mode)` honoring the three modes
   (`observe`, `suggest`, `act`) and the action branches in the spec.
6. Implement undo recipes for `act` mode (one per action branch).
7. Write tests in `tests/test_rectifier_<n>.py` covering :
   - Detection threshold (positive + negative).
   - Each action branch.
   - Idempotency.
   - Undo correctness.
8. Run `bash scripts/check_public_surface.sh` (must exit 0).
9. Run `pytest <module>/tests/test_rectifier_<n>.py -x`.
10. Branch `feat/auto-rectifier-<n>-<timestamp>`; commit with neutral
    message; push; `gh pr create` with neutral title/body.

## Guardrails

- Never modify `BaseRectifier` itself.
- Never write directly to aggregate state; always go through faculty
  channels.
- Public class name must be the spec's `public_name`. Internal Hebrew name
  may appear in a `# Internal: <name>` docstring footnote only.
- `act` mode tests must include the undo recipe verification.

## Verification checklist

- [ ] `bash scripts/check_public_surface.sh` exit 0
- [ ] `pytest tests/test_rectifier_<n>.py -x` green
- [ ] PR title : `feat(probes): implement <public_name>`
- [ ] PR body neutral
- [ ] No direct aggregate state writes
- [ ] Undo recipe present for each `act`-mode action
