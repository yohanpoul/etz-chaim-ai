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

## Current safe state before retry

- Real LaunchAgent service: not loaded (`launchctl list | grep -i etzchaim` empty).
- Real plist exists but is disabled from rollback.
- No push or PR.

## Next action

Commit the absolute-executable fix locally, then rerun Phase 3C-C real activation with the corrected plist.
