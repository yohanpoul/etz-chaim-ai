---
name: implement-spec
description: Use when implementing a specification module from `specs/`. Reads the spec frontmatter, generates the public module + tests with neutral naming, runs the public surface guard and pytest, and opens a PR with a neutral title and body. Never merges.
version: 0.1.0
license: MIT
metadata:
  etzchaim:
    tags: [implementation, code, spec]
    related_skills: [implement-rectifier, implement-metric]
---

# Implement Spec

## Overview

This skill implements one specification file under `specs/` into runnable
Python with tests, opens a pull request, and stops. A human reviewer then
labels the PR `human-approved` if it passes review, and the PR is merged.

## When to use

When `autopilot.loop.run_one_cycle()` selects an unimplemented spec from
`specs/*.md` and dispatches `implement-spec` to do the work.

## Inputs

- Path to the spec file (e.g. `specs/synthesis_bridge.md`).
- The frozen context snapshot (mission, autopilot context, operator
  preferences).

## Steps

1. Read the spec file.
2. Parse frontmatter; note `internal_name`, `internal_source`,
   `internal_e_label` (these stay in code only as docstring footnotes).
3. Identify target public class name from frontmatter `public_name` field
   (e.g. `MetaOrchestrator`, `SynthesisBridge`). Public class names must
   pass `scripts/check_public_surface.sh`.
4. Implement the module in the path indicated by frontmatter `module_path`.
   Public API uses neutral naming throughout.
5. Write tests in `<module>/tests/test_<public_name>.py` with neutral test
   names (`test_construction`, `test_invariant_holds`, etc.).
6. Run `bash scripts/check_public_surface.sh`. If it fails, undo and abort.
7. Run `pytest <module>/tests/ -x`. If tests fail, fix them up to a small
   bounded number of attempts, otherwise abort.
8. Create a feature branch `feat/spec-<spec-name>-<timestamp>`.
9. Stage files, write a neutral commit message, commit, push.
10. Open a PR via `gh pr create` with a neutral title and body. Do not add
    the `human-approved` label.

## Guardrails

- Never modify `sifrei_yesod/`, `.claude/`, `paper/`, `specs/`,
  `partzufim/internal/`, or any path listed in `autopilot.config.excluded_paths`.
- Never push to `main`. Always work on a fresh feature branch.
- Never include hebraic terms in public-facing strings (PR title, body,
  module docstrings, test names). Internal docstring footnotes may reference
  `internal_name` from the spec frontmatter for traceability.

## Verification checklist

- [ ] `bash scripts/check_public_surface.sh` exit 0
- [ ] `pytest <module>/tests/ -x` green
- [ ] PR title matches `feat\(<module>\): implement <neutral-name>`
- [ ] PR body free of forbidden terms (re-scanned via the same script)
- [ ] Branch name matches `feat/spec-<spec-name>-*`
- [ ] No commits land on `main`
