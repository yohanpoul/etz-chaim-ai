# Phase 3B supervision disabled report

Date: 2026-06-04
Branch: `codex/phase-3b-supervision-disabled`
Initial HEAD: `5b5f7ff feat: add manual Phase 3A loop once`
Initial status: clean on `codex/phase-3a-loop-once`

## Preflight

Required preflight was rerun before edits:

- `git status --short --branch`: `## codex/phase-3a-loop-once`
- `git log --oneline -3`: `5b5f7ff`, `54c523e`, `6cd53d8`
- `git branch --show-current`: `codex/phase-3a-loop-once`
- `git branch --list codex/phase-3b-supervision-disabled`: no output

Created branch:

- `git checkout -b codex/phase-3b-supervision-disabled`

No commit, push, or PR was created.

## Contract delivered

`etzchaim supervision` is a read-only/dry-run Phase 3B macOS supervision
surface. It prepares a dormant LaunchAgent template for a future bounded loop
cycle but refuses real installation in this phase.

Supported:

- `etzchaim supervision --help`
- `etzchaim supervision --preflight --json`
- `etzchaim supervision --install --dry-run --json`

Refused:

- `etzchaim supervision --install --json`
- `etzchaim supervision --preflight --install --json`

The real-install refusal message is:

`Phase 3B refuses real LaunchAgent installation. Use --dry-run only.`

## LaunchAgent template contract

Rendered with `plistlib.dumps(..., fmt=plistlib.FMT_XML)`.

Payload:

- `Label`: `com.etzchaim.loop-once`
- `ProgramArguments`: `["etzchaim", "loop", "--once", "--json"]`
- `RunAtLoad`: `false`
- `KeepAlive`: `false`
- `Disabled`: `true`

Absent in Phase 3B:

- `StartInterval`
- `StartCalendarInterval`
- `WatchPaths`
- `QueueDirectories`

The renderer is pure: it imports no launchd activation helper and performs no
subprocess, shell, file write, scheduler, daemon, or service operation.

## Files modified or created

Modified:

- `etzchaim/cli/app.py`
- `tests/test_install/test_cli_version_info.py`

Created:

- `etzchaim/cli/commands/supervision.py`
- `etzchaim/supervision/__init__.py`
- `etzchaim/supervision/launchagent.py`
- `tests/test_install/test_cli_supervision.py`
- `tests/test_supervision_launchagent.py`
- `strategy/codex-prompt/codex-plan/etzchaim-phase3b-supervision-disabled-report.md`

No target-repo files were deleted.

## TDD evidence

Red test command:

```bash
export PYTHONDONTWRITEBYTECODE=1
export PYTEST_ADDOPTS="${PYTEST_ADDOPTS:-} -p no:cacheprovider"
.venv/bin/python -m pytest tests/test_supervision_launchagent.py tests/test_install/test_cli_supervision.py -q
```

Red result:

- `7 failed in 0.14s`
- Expected failure modes:
  - `ModuleNotFoundError: No module named 'etzchaim.supervision'`
  - `etzchaim supervision` command missing, Typer exit `2`

Green result after implementation:

- `7 passed in 0.12s`

## Final validation

All final pytest commands used:

- `PYTHONDONTWRITEBYTECODE=1`
- `PYTEST_ADDOPTS="${PYTEST_ADDOPTS:-} -p no:cacheprovider"`

Results:

- `tests/test_supervision_launchagent.py tests/test_install/test_cli_supervision.py`: `7 passed in 0.12s`
- `tests/test_metacognition_loop_once.py tests/test_install/test_cli_loop.py tests/test_install/test_cli_supervision.py tests/test_install/test_cli_version_info.py`: `17 passed in 0.12s`
- `tests/test_install/test_psql_helper.py sifrei_yesod/tests/test_folio_map.py`: `17 passed in 0.36s`
- `git diff --check`: exit `0`

## Isolated HOME smokes

Preflight:

- Command: `HOME="$PREFLIGHT_HOME" .venv/bin/etzchaim supervision --preflight --json`
- Exit: `0`
- HOME: `/var/folders/6x/7kkcg3j57c5_zplrqbmsv2xw0000gp/T/tmp.p1ewoDDAUJ`
- Files under HOME: `0`
- JSON: `status=ok`, `mode=preflight`, `read_only=true`, `activation_allowed=false`

Install dry-run:

- Command: `HOME="$DRY_HOME" .venv/bin/etzchaim supervision --install --dry-run --json`
- Exit: `0`
- HOME: `/var/folders/6x/7kkcg3j57c5_zplrqbmsv2xw0000gp/T/tmp.zBnh3C9Ytt`
- Files under HOME: `0`
- JSON: `status=dry-run`, `mode=install-dry-run`, `would_write.bytes=493`

Real install refusal:

- Command: `HOME="$BLOCK_HOME" .venv/bin/etzchaim supervision --install --json`
- Exit: `1`
- HOME: `/var/folders/6x/7kkcg3j57c5_zplrqbmsv2xw0000gp/T/tmp.WV4bjycudR`
- Files under HOME: `0`
- JSON: `status=refused`, `mode=install-refused`
- Message: `Phase 3B refuses real LaunchAgent installation. Use --dry-run only.`

## Launchd and permanence proof

No activation command was executed:

- Renderer and CLI tests monkeypatched `subprocess.run`, `subprocess.Popen`,
  `os.system`, and `os.popen`; calls remained `[]`.
- The new renderer/CLI code contains no launchctl activation path.
- `launchctl list | grep etzchaim || true`: no output.

No continuous or permanent mode was added:

- The only planned invocation is bounded: `etzchaim loop --once --json`.
- `RunAtLoad=false`.
- `KeepAlive=false`.
- `Disabled=true`.
- No active interval or calendar trigger exists in the template.
- Real installation is refused in Phase 3B.

## Guarded areas

Final restricted diff check:

```bash
git diff --name-only -- daemon.py 'etzchaim/autopilot/**' 'autopilot/git_integration/pr.py' 'sifrei_yesod/**'
```

Result: no output.

Confirmed:

- `daemon.py` was not modified.
- `etzchaim/autopilot/**` was not modified.
- `etzchaim/autopilot/git_integration/pr.py` was not modified.
- `sifrei_yesod/**` was not modified; only the requested bounded test was run.
- No Docker, PostgreSQL, compose, migration, daemon, worker, cron, LaunchAgent,
  or service was started.
- No `launchctl load`, `launchctl bootstrap`, `launchctl kickstart`,
  `launchctl start`, or equivalent activation command was run.
- No full `make test` was run.
- No commit, push, or PR was created.

Obsidian mirror note:

- Final check in `/Users/fffff/Documents/mon-cerveau/projets/etz-chaim-ai`
  confirms no Phase 3B test artifacts remain at
  `tests/test_supervision_launchagent.py` or
  `tests/test_install/test_cli_supervision.py`.
- All delivered Phase 3B artifacts are in
  `/Users/fffff/Desktop/developper/claude/etz-chaim-ai`.

## Final git state

`git status --short --branch`:

```text
## codex/phase-3b-supervision-disabled
 M etzchaim/cli/app.py
 M tests/test_install/test_cli_version_info.py
?? etzchaim/cli/commands/supervision.py
?? etzchaim/supervision/
?? tests/test_install/test_cli_supervision.py
?? tests/test_supervision_launchagent.py
```

Additional required report file is now also untracked.

## Remaining debt and next step

Remaining debt:

- Real LaunchAgent installation and activation are intentionally not implemented.
- No schedule or recurring trigger exists in Phase 3B.

Next step:

- Hermès/Yohan validation.
- Then local Phase 3B checkpoint if approved.
- Real activation only in a later phase with explicit GO.
