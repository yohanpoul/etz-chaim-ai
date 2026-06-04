# Phase 3C controlled LaunchAgent activation plan

> PLAN ONLY. This pass inspected the repo and wrote this plan document only.
> It did not install, load, bootstrap, kickstart, start, enable, bootout, or
> write anything under `~/Library/LaunchAgents/`.

Date: 2026-06-04

## 1. Initial state observed

Repository:

- `/Users/fffff/Desktop/developper/claude/etz-chaim-ai`

Git state before writing this plan:

- `git branch --show-current`: `codex/phase-3b-supervision-disabled`
- `git rev-parse --short HEAD`: `a031c7d`
- `git log --oneline -3`:
  - `a031c7d [verified] feat: add Phase 3B disabled supervision checkpoint`
  - `5b5f7ff feat: add manual Phase 3A loop once`
  - `54c523e feat: add explicit P2D faculty adapters`
- `git status --short --branch`:

```text
## codex/phase-3b-supervision-disabled
?? uv.lock
```

Additional checks:

- `git branch --list codex/phase-3c-controlled-activation`: no output.
- `git diff --name-only -- daemon.py 'etzchaim/autopilot/**' 'autopilot/git_integration/pr.py' 'sifrei_yesod/**'`: no output.

No launchd activation command was run during this planning pass.

## 2. Known `uv.lock` noise

`uv.lock` is present and untracked. Treat it as known test-tool noise from the
validated Phase 3B context:

- Do not delete it.
- Do not commit it.
- Do not include it as a Phase 3C deliverable.
- Future Phase 3C-A work may proceed from `a031c7d` as long as the only dirty
  state before branching is `?? uv.lock`.

If any tracked file is dirty before Phase 3C-A execution, stop and report a
blocking state instead of branching.

## 3. Phase sequence

### Phase 3C-A - code and tests only, no real activation

Start condition:

```bash
cd /Users/fffff/Desktop/developper/claude/etz-chaim-ai
git status --short --branch
git rev-parse --short HEAD
git branch --list codex/phase-3c-controlled-activation
git checkout -b codex/phase-3c-controlled-activation a031c7d
```

Allowed dirty state before branch: `?? uv.lock` only.

Future files to modify:

- `etzchaim/cli/commands/supervision.py`
- `etzchaim/supervision/__init__.py`
- `etzchaim/supervision/launchagent.py`
- `tests/test_install/test_cli_supervision.py`
- `tests/test_supervision_launchagent.py`
- `tests/test_install/test_cli_version_info.py` only if command discovery output changes.

Future files to create:

- `etzchaim/supervision/launchctl.py`
- `tests/test_supervision_launchctl.py`
- `strategy/codex-prompt/codex-plan/etzchaim-phase3c-controlled-activation-report.md`

Do not modify:

- `daemon.py`
- `etzchaim/autopilot/**`
- `autopilot/git_integration/pr.py`
- `sifrei_yesod/**`

### Phase 3C-B - isolated HOME plist write only

Use `TMP_HOME="$(mktemp -d)"`. Permit a real plist write only under:

- `HOME="$TMP_HOME"`
- exact write flag
- exact acknowledgement phrase
- no launchctl call

The write target must be:

```text
$TMP_HOME/Library/LaunchAgents/com.etzchaim.loop-once.plist
```

Expected result: exactly one file under `TMP_HOME`, and that file parses as a
valid plist.

### Phase 3C-C - real HITL activation, future GO only

Do not execute in Phase 3C-A or 3C-B. This phase requires a separate explicit
Hermes/Yohan GO after code/test review.

Activation uses modern `launchctl bootstrap`, not legacy `launchctl load`.
The only program launched by launchd remains:

```text
etzchaim loop --once --json
```

## 4. CLI design

Keep `etzchaim supervision` as a single public command with mutually exclusive
modes. Defaults stay read-only or dry-run.

Modes:

- `--preflight`: pure local read-only status; no subprocess.
- `--status`: read-only launchd status using `launchctl print`; no mutation.
- `--install`: plist render/write mode.
- `--bootstrap`: load the LaunchAgent into the user launchd domain.
- `--kickstart`: manually run one loaded job.
- `--bootout`: unload the job from the user launchd domain.
- `--disable`: disable the job in the launchd override database.

Shared flags:

- `--json`: structured JSON output.
- `--dry-run`: show planned action and command list without writing or running.
- `--ack TEXT`: exact human acknowledgement phrase.

Write-only flags:

- `--write`: permit a real plist write if paired with `--allow-real-write`.
- `--allow-real-write`: first confirmation flag for plist writes.
- `--plist-state disabled|enabled`: default `disabled`.

Launchctl-only flags:

- `--allow-real-launchctl`: first confirmation flag for real launchctl calls.

Mutual exclusion:

- Exactly one mode must be selected.
- `--dry-run` must not combine with `--write`, `--allow-real-write`, or
  `--allow-real-launchctl`.
- Launchctl modes refuse unless the plist exists and validates.

Acknowledgement phrases:

- Disabled plist write:
  - `WRITE PHASE 3C DISABLED PLIST`
- Enabled plist write:
  - `WRITE PHASE 3C ENABLED PLIST FOR BOOTSTRAP`
- Bootstrap:
  - `BOOTSTRAP PHASE 3C LAUNCHAGENT`
- Kickstart:
  - `KICKSTART PHASE 3C LOOP ONCE`
- Bootout:
  - `BOOTOUT PHASE 3C LAUNCHAGENT`
- Disable:
  - `DISABLE PHASE 3C LAUNCHAGENT`

Double confirmation rule:

- Real plist write requires both the allow flag and the exact write ack.
- Real launchctl call requires both `--allow-real-launchctl` and the exact
  mode-specific launchctl ack.
- Missing or wrong acknowledgement exits non-zero and writes/runs nothing.

## 5. LaunchAgent design

Extend `etzchaim/supervision/launchagent.py`:

```python
LABEL = "com.etzchaim.loop-once"
PROGRAM_ARGUMENTS = ["etzchaim", "loop", "--once", "--json"]

def default_launchagent_path(home: Path | None = None) -> Path: ...
def launchagent_payload(*, executable: str = "etzchaim", disabled: bool = True) -> dict[str, object]: ...
def render_launchagent_plist(*, executable: str = "etzchaim", disabled: bool = True) -> bytes: ...
def parse_launchagent_plist(path: Path) -> dict[str, object]: ...
def validate_launchagent_payload(payload: Mapping[str, object]) -> list[str]: ...
def write_launchagent_plist(*, home: Path | None = None, disabled: bool = True) -> dict[str, object]: ...
```

Validation must require:

- `Label == "com.etzchaim.loop-once"`
- `ProgramArguments == ["etzchaim", "loop", "--once", "--json"]`
- `RunAtLoad is False`
- `KeepAlive is False`
- no `StartInterval`
- no `StartCalendarInterval`
- no `WatchPaths`
- no `QueueDirectories`

`Disabled` policy:

- Install/write defaults to `Disabled=true`.
- `Disabled=false` is written only by an explicit enabled-plist write command
  with `--allow-real-write` and ack
  `WRITE PHASE 3C ENABLED PLIST FOR BOOTSTRAP`.
- Rationale: on macOS, `Disabled=true` plus launchd's override database can
  make bootstrap/kickstart behavior ambiguous. Keeping install disabled by
  default preserves dormancy; rewriting an enabled but still non-recurring plist
  immediately before bootstrap gives a clear activation boundary.
- Even with `Disabled=false`, safety remains: `RunAtLoad=false`,
  `KeepAlive=false`, no interval/calendar trigger, and no launch occurs until
  `bootstrap`/`kickstart` is separately confirmed.

Only `write_launchagent_plist(...)` may write files, and only to:

```text
Path.home() / "Library" / "LaunchAgents" / "com.etzchaim.loop-once.plist"
```

## 6. Launchctl design

Create `etzchaim/supervision/launchctl.py`.

Command builders must be pure and testable:

```python
def user_domain(uid: int | None = None) -> str:
    return f"gui/{uid or os.getuid()}"

def service_target(uid: int | None = None, label: str = LABEL) -> str:
    return f"{user_domain(uid)}/{label}"

def print_command(uid: int | None = None, label: str = LABEL) -> list[str]:
    return ["launchctl", "print", service_target(uid, label)]

def bootstrap_command(plist_path: Path, uid: int | None = None) -> list[str]:
    return ["launchctl", "bootstrap", user_domain(uid), str(plist_path)]

def kickstart_command(uid: int | None = None, label: str = LABEL) -> list[str]:
    return ["launchctl", "kickstart", "-k", service_target(uid, label)]

def bootout_command(uid: int | None = None, label: str = LABEL) -> list[str]:
    return ["launchctl", "bootout", service_target(uid, label)]

def disable_command(uid: int | None = None, label: str = LABEL) -> list[str]:
    return ["launchctl", "disable", service_target(uid, label)]
```

Execution wrapper:

```python
def run_launchctl(command: Sequence[str]) -> dict[str, object]:
    completed = subprocess.run(
        list(command),
        shell=False,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "command": list(command),
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }
```

No `os.system`, no `os.popen`, no `subprocess.Popen`, no shell strings.

## 7. Tests to add or modify

TDD order: write these tests first, run red, then implement.

### Renderer tests

Modify `tests/test_supervision_launchagent.py`:

- `test_disabled_plist_is_default_and_dormant`
- `test_enabled_plist_is_only_disabled_false_and_still_dormant`
- `test_validate_rejects_start_interval`
- `test_validate_rejects_start_calendar_interval`
- `test_write_launchagent_plist_writes_only_expected_tmp_home_path`
- `test_write_launchagent_plist_refuses_invalid_target_if_home_escape_attempt`

### Launchctl builder tests

Create `tests/test_supervision_launchctl.py`:

- `test_launchctl_command_builders_use_fixed_argument_lists`
- `test_run_launchctl_uses_subprocess_run_shell_false`
- `test_run_launchctl_captures_returncode_stdout_stderr`
- `test_no_load_start_enable_commands_are_built`

The last test intentionally rejects legacy/dangerous builders:

- no `launchctl load`
- no `launchctl start`
- no shell command string

Use `disable` only as an explicit rollback mode.

### CLI tests

Modify `tests/test_install/test_cli_supervision.py`:

- Help includes `--status`, `--bootstrap`, `--kickstart`, `--bootout`,
  `--disable`, `--write`, `--allow-real-write`, `--allow-real-launchctl`,
  `--ack`, and `--plist-state`.
- `--preflight --json` remains read-only and writes no files.
- `--install --dry-run --json` remains read-only and writes no files.
- `--install --write --json` without allow flag refuses and writes no files.
- `--install --write --allow-real-write --ack WRONG --json` refuses and writes
  no files.
- `--install --write --allow-real-write --ack "WRITE PHASE 3C DISABLED PLIST" --json`
  under tmp HOME writes exactly one disabled plist.
- `--install --write --plist-state enabled --allow-real-write --ack "WRITE PHASE 3C ENABLED PLIST FOR BOOTSTRAP" --json`
  under tmp HOME writes exactly one enabled plist.
- `--bootstrap --dry-run --json` returns the exact `launchctl bootstrap`
  command and does not call subprocess.
- `--bootstrap --allow-real-launchctl --ack WRONG --json` refuses before
  subprocess.
- `--bootstrap --allow-real-launchctl --ack "BOOTSTRAP PHASE 3C LAUNCHAGENT" --json`
  calls mocked subprocess once with
  `["launchctl", "bootstrap", f"gui/{uid}", plist_path]`.
- Equivalent mocked tests for `--kickstart`, `--bootout`, and `--disable`.
- Every test monkeypatches `subprocess.run` so no real launchctl call is made.

Keep existing Phase 3B tests and update expected refusal text only where the
new Phase 3C contract intentionally changes it.

## 8. Verification commands

Use only bounded tests, never full `make test`.

```bash
export PYTHONDONTWRITEBYTECODE=1
export PYTEST_ADDOPTS="${PYTEST_ADDOPTS:-} -p no:cacheprovider"
.venv/bin/python -m pytest tests/test_supervision_launchagent.py tests/test_supervision_launchctl.py tests/test_install/test_cli_supervision.py -q
.venv/bin/python -m pytest tests/test_metacognition_loop_once.py tests/test_install/test_cli_loop.py tests/test_install/test_cli_supervision.py tests/test_install/test_cli_version_info.py -q
.venv/bin/python -m pytest tests/test_install/test_psql_helper.py sifrei_yesod/tests/test_folio_map.py -q
git diff --check
```

Safety checks after Phase 3C-A implementation:

```bash
launchctl list | grep etzchaim || true
git status --short --branch
git ls-files --others --exclude-standard
git diff --name-only -- daemon.py 'etzchaim/autopilot/**' 'autopilot/git_integration/pr.py' 'sifrei_yesod/**'
```

Expected:

- No active launchd entry.
- `uv.lock` may remain untracked.
- No diff in guarded areas.

## 9. Isolated HOME smokes

Read-only preflight:

```bash
TMP_HOME="$(mktemp -d)"
HOME="$TMP_HOME" .venv/bin/etzchaim supervision --preflight --json
find "$TMP_HOME" -type f | wc -l
```

Expected: exit `0`, JSON valid, `0` files.

Dry-run install:

```bash
TMP_HOME="$(mktemp -d)"
HOME="$TMP_HOME" .venv/bin/etzchaim supervision --install --dry-run --json
find "$TMP_HOME" -type f | wc -l
```

Expected: exit `0`, JSON valid, `0` files.

Refused write without ack:

```bash
TMP_HOME="$(mktemp -d)"
HOME="$TMP_HOME" .venv/bin/etzchaim supervision --install --write --json
printf 'exit_code=%s\n' "$?"
find "$TMP_HOME" -type f | wc -l
```

Expected: non-zero exit, `0` files.

Controlled disabled plist write:

```bash
TMP_HOME="$(mktemp -d)"
HOME="$TMP_HOME" .venv/bin/etzchaim supervision \
  --install \
  --write \
  --allow-real-write \
  --ack "WRITE PHASE 3C DISABLED PLIST" \
  --json
find "$TMP_HOME" -type f | wc -l
PLIST="$TMP_HOME/Library/LaunchAgents/com.etzchaim.loop-once.plist"
python - <<'PY'
import os, plistlib
plist = os.environ["PLIST"]
with open(plist, "rb") as handle:
    data = plistlib.load(handle)
assert data["ProgramArguments"] == ["etzchaim", "loop", "--once", "--json"]
assert data["RunAtLoad"] is False
assert data["KeepAlive"] is False
assert data["Disabled"] is True
assert "StartInterval" not in data
assert "StartCalendarInterval" not in data
print("disabled-plist-ok")
PY
```

Expected: exit `0`, exactly `1` file, valid disabled dormant plist.

Controlled enabled plist write for later bootstrap:

```bash
TMP_HOME="$(mktemp -d)"
HOME="$TMP_HOME" .venv/bin/etzchaim supervision \
  --install \
  --write \
  --plist-state enabled \
  --allow-real-write \
  --ack "WRITE PHASE 3C ENABLED PLIST FOR BOOTSTRAP" \
  --json
find "$TMP_HOME" -type f | wc -l
```

Expected: exit `0`, exactly `1` file, `Disabled=false`, still
`RunAtLoad=false`, `KeepAlive=false`, no interval/calendar trigger.

Dry-run launchctl modes under tmp HOME:

```bash
TMP_HOME="$(mktemp -d)"
HOME="$TMP_HOME" .venv/bin/etzchaim supervision --bootstrap --dry-run --json
HOME="$TMP_HOME" .venv/bin/etzchaim supervision --kickstart --dry-run --json
HOME="$TMP_HOME" .venv/bin/etzchaim supervision --bootout --dry-run --json
```

Expected: JSON command plans only, no subprocess execution, no file writes.

## 10. HITL real activation protocol - do not run before separate GO

Precondition:

- Hermes/Yohan gives a separate explicit GO for real activation.
- Branch `codex/phase-3c-controlled-activation` has passed all Phase 3C-A tests.
- `etzchaim loop --once --json` has already passed the Phase 3A/3B bounded
  validation.

Step 1 - read-only status:

```bash
.venv/bin/etzchaim supervision --preflight --json
.venv/bin/etzchaim supervision --status --json || true
launchctl print "gui/$(id -u)/com.etzchaim.loop-once" || true
```

Step 2 - review dry-run:

```bash
.venv/bin/etzchaim supervision --install --dry-run --json
.venv/bin/etzchaim supervision --bootstrap --dry-run --json
.venv/bin/etzchaim supervision --kickstart --dry-run --json
```

Step 3 - write disabled plist first:

```bash
.venv/bin/etzchaim supervision \
  --install \
  --write \
  --allow-real-write \
  --ack "WRITE PHASE 3C DISABLED PLIST" \
  --json
```

Step 4 - inspect plist:

```bash
python - <<'PY'
from pathlib import Path
import plistlib
path = Path.home() / "Library" / "LaunchAgents" / "com.etzchaim.loop-once.plist"
with path.open("rb") as handle:
    data = plistlib.load(handle)
print(data)
assert data["ProgramArguments"] == ["etzchaim", "loop", "--once", "--json"]
assert data["RunAtLoad"] is False
assert data["KeepAlive"] is False
assert data["Disabled"] is True
assert "StartInterval" not in data
assert "StartCalendarInterval" not in data
PY
```

Step 5 - enable plist for bootstrap, still without running:

```bash
.venv/bin/etzchaim supervision \
  --install \
  --write \
  --plist-state enabled \
  --allow-real-write \
  --ack "WRITE PHASE 3C ENABLED PLIST FOR BOOTSTRAP" \
  --json
```

Step 6 - bootstrap into user launchd domain:

```bash
.venv/bin/etzchaim supervision \
  --bootstrap \
  --allow-real-launchctl \
  --ack "BOOTSTRAP PHASE 3C LAUNCHAGENT" \
  --json
```

Expected: job is loaded but does not run automatically because `RunAtLoad=false`
and `KeepAlive=false`.

Step 7 - status after bootstrap:

```bash
.venv/bin/etzchaim supervision --status --json || true
launchctl print "gui/$(id -u)/com.etzchaim.loop-once" || true
```

Step 8 - one-shot kickstart only if explicitly approved:

```bash
.venv/bin/etzchaim supervision \
  --kickstart \
  --allow-real-launchctl \
  --ack "KICKSTART PHASE 3C LOOP ONCE" \
  --json
```

Expected: at most one `etzchaim loop --once --json` execution.

Step 9 - inspect result:

```bash
.venv/bin/etzchaim supervision --status --json || true
launchctl print "gui/$(id -u)/com.etzchaim.loop-once" || true
ls -la "$HOME/.etz-chaim/state" || true
tail -n 5 "$HOME/.etz-chaim/state/loop_heartbeat.jsonl" || true
```

Expected: no recurrent process, no `KeepAlive`, no interval trigger, and only
the bounded loop output files expected from Phase 3A.

## 11. Rollback protocol

Rollback should be available before any real activation.

Bootout loaded job:

```bash
.venv/bin/etzchaim supervision \
  --bootout \
  --allow-real-launchctl \
  --ack "BOOTOUT PHASE 3C LAUNCHAGENT" \
  --json
```

Disable in launchd override database:

```bash
.venv/bin/etzchaim supervision \
  --disable \
  --allow-real-launchctl \
  --ack "DISABLE PHASE 3C LAUNCHAGENT" \
  --json
```

Rewrite plist to disabled dormant state:

```bash
.venv/bin/etzchaim supervision \
  --install \
  --write \
  --plist-state disabled \
  --allow-real-write \
  --ack "WRITE PHASE 3C DISABLED PLIST" \
  --json
```

Verify rollback:

```bash
.venv/bin/etzchaim supervision --status --json || true
launchctl print "gui/$(id -u)/com.etzchaim.loop-once" || true
python - <<'PY'
from pathlib import Path
import plistlib
path = Path.home() / "Library" / "LaunchAgents" / "com.etzchaim.loop-once.plist"
if path.exists():
    with path.open("rb") as handle:
        data = plistlib.load(handle)
    assert data["Disabled"] is True
    assert data["RunAtLoad"] is False
    assert data["KeepAlive"] is False
print("rollback-state-ok")
PY
```

No deletion is required for rollback. If removal of the plist becomes desired,
that should be a separate explicit phase with its own confirmation and report.

## 12. Safety invariants

Must remain true through Phase 3C:

- No `StartInterval`.
- No `StartCalendarInterval`.
- `KeepAlive=false`.
- `RunAtLoad=false`.
- No loop permanent.
- At most one bounded `etzchaim loop --once --json` per explicit kickstart.
- No autopilot Git/PR path.
- No corpus modification.
- No writes outside `~/Library/LaunchAgents/com.etzchaim.loop-once.plist` and
  the already-established Phase 3A loop state paths when a loop is explicitly
  kickstarted.
- Real plist write impossible without `--allow-real-write` plus exact ack.
- Real launchctl impossible without `--allow-real-launchctl` plus exact ack.
- Status/preflight available before every mutation.
- Rollback documented and tested with mocked launchctl calls.

## 13. Risks and questions

Risks:

- macOS launchd `Disabled` behavior can interact with the launchd override
  database. The plan mitigates this by separating disabled install, enabled
  plist write, bootstrap, and kickstart into distinct HITL steps.
- `ProgramArguments[0] = "etzchaim"` relies on launchd resolving the command
  from its environment. If the real macOS user environment cannot resolve it,
  Phase 3C-C may need an explicit executable path discovered by `shutil.which`
  during preflight and written into the plist only after review.
- `launchctl bootout` target syntax can vary between path and service target
  usage across macOS versions. Phase 3C-A should test the command builder, and
  Phase 3C-C should dry-run/report the exact command before execution.

Blocking questions:

- None for Phase 3C-A planning. The executable path choice can be handled as a
  tested preflight warning and does not block code/test implementation.

## 14. Verdict

PLAN ONLY — prêt pour revue Hermès
