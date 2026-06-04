# Phase 3A loop once report

Date: 2026-06-04
Branch: `codex/phase-3a-loop-once`
Initial HEAD: `54c523e feat: add explicit P2D faculty adapters`
Initial status: clean on `codex/phase-2d-explicit-faculty-adapters`

## Contract delivered

`etzchaim loop` is a manual, non-permanent runtime surface.

Supported:

- `etzchaim loop --once --dry-run --json`
- `etzchaim loop --once --json`
- `etzchaim loop --once --dry-run`
- `etzchaim loop --once`

Refused:

- Any invocation without `--once`.

The refusal message is:

`Phase 3A loop only supports explicit --once.`

The loop runs exactly one bounded cycle by calling the existing
`report.run_improve_once(...)` path. It does not schedule, supervise, retry,
spawn workers, open PRs, start services, or apply patches.

## Payload contract

The loop payload contains:

- `status`
- `dry_run`
- `generated_at`
- `cycle_id`
- `heartbeat`
- `improve`
- `would_write` in dry-run mode
- `written` in write mode

`cycle_id` uses the format `loop-YYYYMMDDTHHMMSSZ`.

## Files modified or created

Modified:

- `etzchaim/cli/app.py`
- `tests/test_install/test_cli_version_info.py`

Created:

- `etzchaim/cli/commands/loop.py`
- `etzchaim/metacognition/runtime_loop.py`
- `tests/test_install/test_cli_loop.py`
- `tests/test_metacognition_loop_once.py`
- `strategy/codex-prompt/codex-plan/etzchaim-phase3a-loop-once-report.md`

No files were deleted.

## Write-mode files

Write-mode adds the existing improve files plus two loop files.

Expected improve files:

- `.etz-chaim/runs/improve-YYYYMMDDTHHMMSSZ.md`
- `.etz-chaim/state/last_improve_run.json`
- `.etz-chaim/state/improve_ledger.jsonl`

Expected loop files:

- `.etz-chaim/state/last_loop_run.json`
- `.etz-chaim/state/loop_heartbeat.jsonl`

Observed isolated HOME write smoke created exactly:

- `.etz-chaim/runs/improve-20260604T150122Z.md`
- `.etz-chaim/state/improve_ledger.jsonl`
- `.etz-chaim/state/last_improve_run.json`
- `.etz-chaim/state/last_loop_run.json`
- `.etz-chaim/state/loop_heartbeat.jsonl`

## TDD evidence

Red test command:

`PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS="${PYTEST_ADDOPTS:-} -p no:cacheprovider" .venv/bin/python -m pytest tests/test_metacognition_loop_once.py tests/test_install/test_cli_loop.py -q`

Red result:

- `7 failed`
- Expected failure mode:
  - `ImportError: cannot import name 'runtime_loop'`
  - `etzchaim loop` command not registered

Green targeted result after implementation:

- `7 passed in 0.12s`

## Final validation

All final pytest commands were run with:

- `PYTHONDONTWRITEBYTECODE=1`
- `PYTEST_ADDOPTS="${PYTEST_ADDOPTS:-} -p no:cacheprovider"`

Results:

- `tests/test_metacognition_loop_once.py tests/test_install/test_cli_loop.py`: `7 passed in 0.10s`
- metacognition plus CLI subset: `43 passed in 0.18s`
- PSQL helper plus folio map subset: `17 passed in 0.63s`
- `git diff --check`: exit 0

## Dry-run proof

Isolated HOME dry-run smoke:

- Command: `HOME="$DRY_HOME" .venv/bin/etzchaim loop --once --dry-run --json`
- JSON validation: `dry-loop-json-ok`
- HOME: `/var/folders/6x/7kkcg3j57c5_zplrqbmsv2xw0000gp/T/tmp.rf0NjGma5v`
- Files under HOME: `0`

This proves dry-run did not write loop files, improve files, state files, or
heartbeat files.

## Write-mode smoke proof

Isolated HOME write smoke:

- Command: `HOME="$WRITE_HOME" .venv/bin/etzchaim loop --once --json`
- JSON validation: `write-loop-json-ok`
- HOME: `/var/folders/6x/7kkcg3j57c5_zplrqbmsv2xw0000gp/T/tmp.HhyX48Hvmz`
- Files under HOME: exactly the five expected files listed above.

## Safety invariants

Verified:

- `applies_patch=False` for all actions in runtime tests.
- `applies_patch=False` for all actions in CLI dry-run and write-mode smokes.
- Guardian default remains `unavailable`.
- No DB adapter is configured by the CLI.
- No action is applied by loop.
- `launchctl list | grep etzchaim || true` produced no active etzchaim entry.
- No daemon, LaunchAgent, cron, Docker, PostgreSQL, compose, migration, worker,
  PR flow, or permanent service was started.
- `daemon.py` was not modified.
- `etzchaim/autopilot/**` was not modified.
- `autopilot/git_integration/pr.py` was not modified.
- `sifrei_yesod` was only used by the bounded pytest command.

## Git and repository constraints

Confirmed:

- No commit was created.
- No push was run.
- No PR was opened.
- No destructive command was run.
- No deletion was performed.
- No full `make test` was run.
- The Obsidian mirror at
  `/Users/fffff/Documents/mon-cerveau/projets/etz-chaim-ai` was not modified by
  this Phase 3A work.

Final tracked changes before writing this report:

- `etzchaim/cli/app.py`
- `tests/test_install/test_cli_version_info.py`

Final untracked Phase 3A files before writing this report:

- `etzchaim/cli/commands/loop.py`
- `etzchaim/metacognition/runtime_loop.py`
- `tests/test_install/test_cli_loop.py`
- `tests/test_metacognition_loop_once.py`

This report is the final additional untracked file required by the phase.
