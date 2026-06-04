# P2D explicit faculty adapters report

Date: 2026-06-04
Branch: `codex/phase-2d-explicit-faculty-adapters`
Base checkpoint: `6cd53d8 feat: harden P2C faculty bridge`

## Summary

P2D adds an explicit adapter injection path for the safe improve loop:

- `etzchaim.metacognition.report.build_run_payload(..., faculty_adapters=None)`
- `etzchaim.metacognition.report.run_improve_once(..., faculty_adapters=None)`

The default remains equivalent to no adapters. The CLI default path was not given
any adapter/config loading and still calls `run_improve_once()` without
`faculty_adapters`.

## Scope confirmation

- No commit was created.
- No push was run.
- No PR was opened.
- No daemon, LaunchAgent, Docker, PostgreSQL, cron, migration, or permanent
  service was started.
- No files were deleted.
- `sifrei_yesod` was only exercised by the required bounded test command.
- `autopilot/git_integration/pr.py` was not modified.
- The Obsidian mirror at
  `/Users/fffff/Documents/mon-cerveau/projets/etz-chaim-ai` was not modified by
  this P2D work.

## Behavior verified

- Explicit `FailureToInsight` adapters are used only when passed to the report
  pipeline, and the read-only path remains `guide_next_hypothesis(domain=...)`.
- A `FailureToInsight` adapter exposing only `analyze_failure()` is not called
  by the report pipeline.
- Explicit `Guardian` adapters can return a real verdict such as `caution`.
- Without an explicit `Guardian` adapter, the verdict remains `unavailable`,
  never `proceed`.
- Explicit `IntentKeeper` adapters can link an intent through
  `summarize_event_intent(...)`.
- Without an explicit `IntentKeeper` adapter, status remains `no_active_intent`.
- Default report execution does not import `failuretoinsight`, `intentkeeper`,
  `selfmodel.guardian`, `psycopg`, or `psycopg2`.
- `applies_patch=False` remains invariant for all proposed actions.

## Validation run

All commands were run from `/Users/fffff/Desktop/developper/claude/etz-chaim-ai`
with `PYTHONDONTWRITEBYTECODE=1` and pytest cache disabled where applicable.

- Red TDD run before implementation:
  `tests/test_metacognition_first_loop.py tests/test_install/test_cli_improve.py`
  failed for the expected reason: `faculty_adapters` was not accepted yet.
- Green targeted run:
  `15 passed in 0.12s`
- Faculty subset:
  `6 passed in 0.02s`
- Metacognition/CLI subset:
  `39 passed in 0.19s`
- PSQL helper plus folio map subset:
  `17 passed in 0.82s`
- `git diff --check`: exit 0.

## Smoke gates

- Dry-run isolated HOME:
  - CLI exit: 0
  - JSON status: `dry-run`
  - Guardian verdict: `unavailable`
  - All proposed actions: `applies_patch == false`
  - Files written under isolated HOME: `0`
- Write-mode isolated HOME:
  - CLI exit: 0
  - JSON status: `written`
  - Files written under isolated HOME were exactly:
    - `.etz-chaim/runs/improve-20260604T130904Z.md`
    - `.etz-chaim/state/improve_ledger.jsonl`
    - `.etz-chaim/state/last_improve_run.json`

## Security check

- `launchctl list | grep etzchaim || true` produced no running etzchaim entry.
- Before writing this report, `git status --short --branch` showed only:
  - `etzchaim/metacognition/report.py`
  - `tests/test_install/test_cli_improve.py`
  - `tests/test_metacognition_first_loop.py`
- Before writing this report, `git ls-files --others --exclude-standard`
  returned no untracked files.
