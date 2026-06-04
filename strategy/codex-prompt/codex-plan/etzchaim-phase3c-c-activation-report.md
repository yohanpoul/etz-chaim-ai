# Phase 3C-C real activation report

Date: 2026-06-04
Branch: `codex/phase-3c-controlled-activation`
Base verified commit before activation: `d5ef15d`

## User authorization

Yohan gave voice authorization for Phase 3C-C real activation.

## Preflight

Read-only checks before mutation:

- Branch: `codex/phase-3c-controlled-activation`
- HEAD: `d5ef15d`
- Real plist before activation: absent
- `launchctl list | grep -i etzchaim`: no output
- `uv run --frozen etzchaim supervision --preflight --json`: status `ok`
- Enabled install dry-run: status `dry-run`, target `/Users/fffff/Library/LaunchAgents/com.etzchaim.loop-once.plist`
- Bootstrap/kickstart/rollback dry-runs returned JSON plans.

## First real activation attempt

Real plist write:

- Command: `uv run --frozen etzchaim supervision --install --write --plist-state enabled --allow-real-write --ack "WRITE PHASE 3C ENABLED PLIST FOR BOOTSTRAP" --json`
- Exit: `0`
- Plist written: `/Users/fffff/Library/LaunchAgents/com.etzchaim.loop-once.plist`
- `plutil -lint`: OK
- Plist was enabled and dormant: `Disabled=false`, `RunAtLoad=false`, `KeepAlive=false`.

Real bootstrap:

- Command: `uv run --frozen etzchaim supervision --bootstrap --allow-real-launchctl --ack "BOOTSTRAP PHASE 3C LAUNCHAGENT" --json`
- Exit: `0`
- `launchctl print gui/502/com.etzchaim.loop-once`: service registered, not running, runs `0`.

Real kickstart:

- Command: `uv run --frozen etzchaim supervision --kickstart --allow-real-launchctl --ack "KICKSTART PHASE 3C LOOP ONCE" --json`
- CLI exit: `0` for the `kickstart` command itself.
- Launchd state after 3s: `runs = 1`, `last exit code = 78: EX_CONFIG`.

Root cause evidence from unified log:

```text
Service could not initialize: posix_spawn(etzchaim), error 0x2 - No such file or directory
```

`launchctl print` also showed launchd's default PATH:

```text
PATH => /usr/bin:/bin:/usr/sbin:/sbin
program = etzchaim
```

The shell can resolve `etzchaim` from `/Users/fffff/.local/bin/etzchaim`, and `uv run` resolves it to the project venv:

```text
/Users/fffff/Desktop/developper/claude/etz-chaim-ai/.venv/bin/etzchaim
```

But launchd cannot resolve bare `etzchaim` from its minimal PATH.

## Rollback performed

Because the one-shot run failed with `EX_CONFIG`, rollback was executed immediately:

- `disable`: exit `0`
- `bootout`: exit `0`
- write disabled plist: exit `0`
- `launchctl list | grep -i etzchaim`: no output
- Plist left in place but disabled for inspection (`Disabled=true`).

No deletion was performed.

## Fix implemented after rollback

TDD regression added first:

- Default rendered plist must use an absolute executable path.
- `validate_launchagent_payload` must reject relative `ProgramArguments[0]`.
- Existing CLI/test assertions were updated to accept absolute executable + fixed tail `loop --once --json`.

Production fix:

- Added `resolve_executable()` in `etzchaim/supervision/launchagent.py`.
- LaunchAgent `ProgramArguments[0]` now resolves to an absolute path at render/write time.
- Under `uv run --frozen`, the resolved path is:
  `/Users/fffff/Desktop/developper/claude/etz-chaim-ai/.venv/bin/etzchaim`.
- Validation now checks:
  - executable path is absolute;
  - executable exists;
  - executable is executable;
  - arguments end with `loop --once --json`.

## Validation after fix

- Phase 3C targeted tests: `30 passed`
- loop/CLI subset: `24 passed`
- psql + folio subset: `17 passed`
- Ruff touched files: `All checks passed!`
- `git diff --check`: OK
- Isolated HOME smokes: `POST_ABSOLUTE_EXEC_SMOKES_OK`
  - preflight/dry-run/writes now show absolute venv executable under `uv run --frozen`.

## Second fix: guarded enable for rollback override

The first rollback used `launchctl disable`, which created a disabled override visible via:

```text
launchctl print-disabled gui/502 | grep -i etzchaim
"com.etzchaim.loop-once" => disabled
```

To make retry possible without manual unguarded launchctl commands, a guarded `--enable`
mode was added:

- `launchctl.enable_command()` builds `launchctl enable gui/502/com.etzchaim.loop-once`.
- `etzchaim supervision --enable --dry-run --json` returns a JSON command plan.
- Real enable requires `--allow-real-launchctl --ack "ENABLE PHASE 3C LAUNCHAGENT"`.
- `enable` is included in the internal launchctl allowlist but remains mutation-guarded.
- `load` and `start` remain unsupported/refused.

Validation after guarded-enable fix:

- Phase 3C targeted tests: `30 passed`
- loop/CLI subset: `24 passed`
- psql + folio subset: `17 passed`
- Ruff touched files: `All checks passed!`
- Isolated HOME smokes: `POST_ENABLE_SMOKES_OK`

## Third fix: explicit WorkingDirectory for relative project commands

The retry with an absolute executable spawned successfully and exited `0`, but the run evidence
showed a collector warning:

```text
_collect_pytest raised FileNotFoundError: [Errno 2] No such file or directory: '.venv/bin/python'
```

Root cause: launchd started the absolute executable without the project repository as current
working directory, while the metacognition collector intentionally uses project-relative
commands such as `.venv/bin/python`.

Fix:

- Added `WorkingDirectory` to the LaunchAgent payload.
- `WorkingDirectory` resolves to the current repository path at plist render/write time.
- The Phase 3C allowlist includes only this additional launchd key.
- Validation now requires `WorkingDirectory` to be an absolute existing directory.
- Regression tests cover absolute working directory rendering and relative working directory rejection.

Validation after WorkingDirectory fix:

- Phase 3C targeted tests: `32 passed`
- loop/CLI subset: `24 passed`
- psql + folio subset: `17 passed`
- Ruff touched files: `All checks passed!`
- Isolated HOME smokes: `POST_WORKING_DIRECTORY_SMOKES_OK`

## Current safe state before retry

- Real LaunchAgent service: not loaded (`launchctl list | grep -i etzchaim` empty).
- Real plist exists but is disabled from rollback.
- No push or PR.

## Final Phase 3C-C activation result

Final retry after the absolute executable, guarded enable, and WorkingDirectory fixes:

- HEAD used for final retry: `b9d4c0e`.
- Real plist write enabled: exit `0`, `plutil -lint` OK.
- Final plist payload:
  - `ProgramArguments[0] = /Users/fffff/Desktop/developper/claude/etz-chaim-ai/.venv/bin/etzchaim`
  - `WorkingDirectory = /Users/fffff/Desktop/developper/claude/etz-chaim-ai`
  - `RunAtLoad=false`
  - `KeepAlive=false`
  - `Disabled=false`
- Guarded `launchctl enable`: exit `0`; disabled override became enabled.
- Guarded `launchctl bootstrap`: exit `0`; service registered.
- Guarded `launchctl kickstart -k`: exit `0`.
- Status after 12 seconds:
  - `runs = 1`
  - `last exit code = 0`
  - `state = not running`
  - working directory printed by launchd as the repo root.
- Heartbeat appended to `~/.etz-chaim/state/loop_heartbeat.jsonl`:

```json
{"action_count": 7, "applies_patch": false, "cycle_id": "loop-20260604T193534Z", "guardian_verdict": "unavailable", "improve_status": "written", "status": "written", "timestamp": "2026-06-04T19:35:34.610489Z", "top_issue_id": "known-p0-psql-helper-pollution"}
```

Latest state artifacts:

- `~/.etz-chaim/state/last_loop_run.json`
- `~/.etz-chaim/state/last_improve_run.json`
- `~/.etz-chaim/runs/improve-20260604T193534Z.md`

The previous `posix_spawn(etzchaim)` failure and the subsequent `.venv/bin/python`
relative-cwd failure are both resolved for this controlled one-shot LaunchAgent run.
The loop now reaches the actual project health queue; current top issue is the known
P0 psql helper pollution / local Postgres environment issue, not LaunchAgent activation.

## Current operational state

- LaunchAgent label: `com.etzchaim.loop-once`
- LaunchAgent is bootstrapped and enabled.
- It is dormant after the one-shot run (`RunAtLoad=false`, `KeepAlive=false`, no interval/path trigger).
- It can be kicked manually through the guarded Phase 3C CLI.

## Next action

Proceed to the next operational hardening step: address the loop's top issue
`known-p0-psql-helper-pollution` and/or the local Postgres/Docker observer failures,
without changing external services unless explicitly authorized.
