# Phase 3C-A/B controlled activation report

Date: 2026-06-04
Branch: `codex/phase-3c-controlled-activation`
Initial HEAD: `a031c7d`
Initial status:

```text
## codex/phase-3b-supervision-disabled
?? strategy/codex-prompt/codex-plan/etzchaim-phase3c-controlled-activation-plan.md
?? uv.lock
```

## Preflight

Required preflight before edits:

- `git rev-parse --short HEAD`: `a031c7d`
- `git diff --name-only -- daemon.py 'etzchaim/autopilot/**' 'autopilot/git_integration/pr.py' 'sifrei_yesod/**'`: no output
- `launchctl list | grep -i etzchaim || true`: no output
- `test ! -e "$HOME/Library/LaunchAgents/com.etzchaim.loop-once.plist" || echo "REAL_PLIST_ALREADY_EXISTS"`: no output
- `git branch --list codex/phase-3c-controlled-activation`: no output

Branch created:

```bash
git checkout -b codex/phase-3c-controlled-activation a031c7d
```

No commit, push, or PR was created.

## Files modified or created

Modified:

- `etzchaim/cli/commands/supervision.py`
- `etzchaim/supervision/launchagent.py`
- `tests/test_install/test_cli_supervision.py`
- `tests/test_supervision_launchagent.py`

Created:

- `etzchaim/supervision/launchctl.py`
- `tests/test_supervision_launchctl.py`
- `strategy/codex-prompt/codex-plan/etzchaim-phase3c-controlled-activation-report.md`

Untracked and intentionally not committed:

- `uv.lock`
- `strategy/codex-prompt/codex-plan/etzchaim-phase3c-controlled-activation-plan.md`

## Contract delivered

`etzchaim supervision` now supports Phase 3C-A/B safe modes:

- `--preflight`
- `--status`
- `--install`
- `--bootstrap`
- `--kickstart`
- `--bootout`
- `--disable`

Guard flags:

- `--dry-run`
- `--write`
- `--allow-real-write`
- `--allow-real-launchctl`
- `--ack TEXT`
- `--plist-state disabled|enabled`
- `--json`

Real plist writes require a double confirmation:

- disabled plist: `--allow-real-write --ack "WRITE PHASE 3C DISABLED PLIST"`
- enabled plist: `--plist-state enabled --allow-real-write --ack "WRITE PHASE 3C ENABLED PLIST FOR BOOTSTRAP"`

Real launchctl actions require `--allow-real-launchctl` plus the exact action
ack. They were implemented but only exercised through tests with mocked
`subprocess.run`; no real mutable launchctl command was run.

LaunchAgent invariants:

- `ProgramArguments = ["etzchaim", "loop", "--once", "--json"]`
- `RunAtLoad = false`
- `KeepAlive = false`
- no `StartInterval`
- no `StartCalendarInterval`
- no `WatchPaths`
- no `QueueDirectories`
- default `Disabled = true`

## TDD evidence

Red test command:

```bash
export PYTHONDONTWRITEBYTECODE=1
export PYTEST_ADDOPTS="${PYTEST_ADDOPTS:-} -p no:cacheprovider"
.venv/bin/python -m pytest tests/test_supervision_launchagent.py tests/test_supervision_launchctl.py tests/test_install/test_cli_supervision.py -q
```

Red result:

- `18 failed, 5 passed in 0.23s`
- Expected failure modes:
  - missing `disabled=` support in plist renderer
  - missing plist parse/validate/write helpers
  - missing `etzchaim.supervision.launchctl`
  - missing new CLI flags and modes

Green result after implementation:

- `23 passed in 0.20s`

## Final validation

All pytest commands used:

- `PYTHONDONTWRITEBYTECODE=1`
- `PYTEST_ADDOPTS="${PYTEST_ADDOPTS:-} -p no:cacheprovider"`

Results:

- `tests/test_supervision_launchagent.py tests/test_supervision_launchctl.py tests/test_install/test_cli_supervision.py`: `23 passed in 0.20s`
- `tests/test_metacognition_loop_once.py tests/test_install/test_cli_loop.py tests/test_install/test_cli_supervision.py tests/test_install/test_cli_version_info.py`: `23 passed in 0.19s`
- `tests/test_install/test_psql_helper.py sifrei_yesod/tests/test_folio_map.py`: `17 passed in 0.25s`
- `git diff --check`: exit `0`

## Isolated HOME smokes

All smokes used `uv run` with `UV_CACHE_DIR="$(mktemp -d)"` outside the isolated
`HOME`.

Preflight:

- Command: `HOME="$TMP_HOME" UV_CACHE_DIR="$UV_CACHE_DIR" uv run etzchaim supervision --preflight --json`
- Exit: `0`
- HOME: `/var/folders/6x/7kkcg3j57c5_zplrqbmsv2xw0000gp/T/tmp.dWvsHpqvjO`
- UV cache: `/var/folders/6x/7kkcg3j57c5_zplrqbmsv2xw0000gp/T/tmp.slvhnaWlBH`
- Files under HOME: `0`

Install dry-run:

- Command: `HOME="$TMP_HOME" UV_CACHE_DIR="$UV_CACHE_DIR" uv run etzchaim supervision --install --dry-run --json`
- Exit: `0`
- HOME: `/var/folders/6x/7kkcg3j57c5_zplrqbmsv2xw0000gp/T/tmp.5r5jtOtjHa`
- UV cache: `/var/folders/6x/7kkcg3j57c5_zplrqbmsv2xw0000gp/T/tmp.ZjQql5NOTI`
- Files under HOME: `0`

Write without acknowledgement:

- Command: `HOME="$TMP_HOME" UV_CACHE_DIR="$UV_CACHE_DIR" uv run etzchaim supervision --install --write --json`
- Exit: `1`
- HOME: `/var/folders/6x/7kkcg3j57c5_zplrqbmsv2xw0000gp/T/tmp.TCNuJ1LYRA`
- UV cache: `/var/folders/6x/7kkcg3j57c5_zplrqbmsv2xw0000gp/T/tmp.hkcrCVbWGd`
- Files under HOME: `0`
- Message: `Real plist write requires --allow-real-write and exact --ack.`

Disabled plist write:

- Command: `HOME="$TMP_HOME" UV_CACHE_DIR="$UV_CACHE_DIR" uv run etzchaim supervision --install --write --allow-real-write --ack "WRITE PHASE 3C DISABLED PLIST" --json`
- Exit: `0`
- HOME: `/var/folders/6x/7kkcg3j57c5_zplrqbmsv2xw0000gp/T/tmp.Qiku8dVuEe`
- UV cache: `/var/folders/6x/7kkcg3j57c5_zplrqbmsv2xw0000gp/T/tmp.efdLW8igBc`
- Files under HOME: `1`
- Validation: `disabled-plist-ok`

Enabled plist write:

- Command: `HOME="$TMP_HOME" UV_CACHE_DIR="$UV_CACHE_DIR" uv run etzchaim supervision --install --write --plist-state enabled --allow-real-write --ack "WRITE PHASE 3C ENABLED PLIST FOR BOOTSTRAP" --json`
- Exit: `0`
- HOME: `/var/folders/6x/7kkcg3j57c5_zplrqbmsv2xw0000gp/T/tmp.GtaS5pKaQ6`
- UV cache: `/var/folders/6x/7kkcg3j57c5_zplrqbmsv2xw0000gp/T/tmp.3EXEEfVLOD`
- Files under HOME: `1`
- Validation: `enabled-plist-ok`

Launchctl dry-run modes:

- Command set:
  - `--bootstrap --dry-run --json`
  - `--kickstart --dry-run --json`
  - `--bootout --dry-run --json`
  - `--disable --dry-run --json`
- Exit: `0` for each mode
- HOME: `/var/folders/6x/7kkcg3j57c5_zplrqbmsv2xw0000gp/T/tmp.UywHK52N6V`
- UV cache: `/var/folders/6x/7kkcg3j57c5_zplrqbmsv2xw0000gp/T/tmp.mMRQJqRRcp`
- Files under HOME: `0`
- `--disable --dry-run --json` explicitly covered and returned a JSON plan:
  `["launchctl", "disable", "gui/502/com.etzchaim.loop-once"]`

## Launchctl safety

No real mutable launchctl command was run:

- Real `bootstrap`, `kickstart`, `bootout`, and `disable` paths were tested only
  with mocked `subprocess.run`.
- Dry-run modes returned JSON command plans and did not invoke subprocess.
- The implementation uses `subprocess.run([...], shell=False)` in the single
  launchctl wrapper.
- No `launchctl load`, `launchctl start`, or `launchctl enable` builder exists.

Read-only final launchd check:

- `launchctl list | grep -i etzchaim || true`: no output

Real plist safety:

- `test ! -e "$HOME/Library/LaunchAgents/com.etzchaim.loop-once.plist" || echo "REAL_PLIST_ALREADY_EXISTS"`: no output
- No write was made to the real `~/Library/LaunchAgents/`.

## Guarded areas and repository constraints

Final restricted diff check:

```bash
git diff --name-only -- daemon.py 'etzchaim/autopilot/**' 'autopilot/git_integration/pr.py' 'sifrei_yesod/**'
```

Result: no output.

Confirmed:

- `daemon.py` not modified.
- `etzchaim/autopilot/**` not modified.
- `autopilot/git_integration/pr.py` not modified.
- `sifrei_yesod/**` not modified.
- No daemon, Docker, PostgreSQL, cron, service, migration, LaunchAgent
  activation, real launchctl mutation, commit, push, or PR.
- `uv.lock` left untracked and uncommitted.

## Hermes post-review hardening

After Hermes independent verification, the Phase 3C-A/B surface was hardened before
local commit:

- Removed two unused imports flagged by Ruff.
- Added a strict LaunchAgent plist key allowlist. The only accepted keys are:
  `Label`, `ProgramArguments`, `RunAtLoad`, `KeepAlive`, and `Disabled`.
- Hardened the low-level plist write primitive so `home` must be explicit; the CLI
  now passes `Path.home()` only after the write double-confirmation guard.
- Hardened the low-level `launchctl` runner so mutating subcommands require an
  explicit `allow_mutation=True`; the CLI passes it only after the launchctl
  double-confirmation guard. Unsupported launchctl subcommands such as `enable`,
  `start`, and `load` are refused even with explicit mutation allow.
- Added regression coverage for:
  - `WatchPaths` and `QueueDirectories` rejection.
  - unknown launchd key rejection, including `StartOnMount`.
  - implicit default-HOME plist writes being refused at the helper level.
  - mutable `launchctl` runner calls being refused without explicit mutation allow.
  - unsupported `launchctl` subcommands being refused even with explicit mutation allow.
  - `--status --dry-run --json` returning a `launchctl print` plan without
    subprocess execution.
  - wrong ACK refusal for all mutable launchctl modes: `bootstrap`, `kickstart`,
    `bootout`, and `disable`.
- Final Hermes validation after hardening:
  - Phase 3C pytest subset: `29 passed`.
  - loop/CLI subset: `24 passed`.
  - psql + folio subset: `17 passed`.
  - Ruff touched files: `All checks passed!`.
  - isolated HOME smokes: `FINAL_FULL_HARDENING_SMOKES_OK`.
  - real launchd check: no Etz Chaim service and no real plist.

No real activation was performed during this hardening pass.

## Final status

Final status before this report was written:

```text
## codex/phase-3c-controlled-activation
 M etzchaim/cli/commands/supervision.py
 M etzchaim/supervision/launchagent.py
 M tests/test_install/test_cli_supervision.py
 M tests/test_supervision_launchagent.py
?? etzchaim/supervision/launchctl.py
?? strategy/codex-prompt/codex-plan/etzchaim-phase3c-controlled-activation-plan.md
?? tests/test_supervision_launchctl.py
?? uv.lock
```

This report is the final additional untracked Phase 3C-A/B artifact.

## Next step

Stop here and wait for Hermes/Yohan review. Phase 3C-C real activation remains
out of scope until a separate explicit GO.
