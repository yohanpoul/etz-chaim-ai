# Etz Chaim AI - Phase 3C-D actionable real loop report

Date: 2026-06-04
Branch: `codex/phase-3c-controlled-activation`

## Objective

Make the extracted metacognition daemon component more operational in real LaunchAgent execution, without widening scope to the whole Etz Chaim project and without inventing or mutating source corpus content.

## Root cause found

The real loop was already running, but its top issue was too generic:

- Before: `pytest-bounded-subset-failed`
- Cause behind the signal: bounded pytest reached a corpus gate in `sifrei_yesod/tests/test_idra_corpus_fidelity.py`.
- Source-backed corpus debt observed:
  - Missing tikkunim outside the accepted T11 exception: `[1, 2, 3, 4, 5, 6, 9, 10, 12]`
  - First non-bidirectional `see_also` link: `Z-IR-T08-001→EC-H3S2-T08-001` missing reciprocal.

A second LaunchAgent-only blocker appeared during real execution:

- launchd's minimal environment could not find `/opt/homebrew/bin/psql`.
- The bounded pytest then failed at setup with `psql non trouvé` before reaching the corpus-gate assertions.

## Changes made

### 1. Corpus-gate signal classification

Files:

- `etzchaim/metacognition/collectors.py`
- `etzchaim/metacognition/actions.py`
- `tests/test_metacognition_collectors.py`
- `tests/test_metacognition_events.py`

Behavior:

- The pytest collector now recognizes the concrete Idra corpus-gate failure from captured pytest output.
- New top issue id:
  - `pytest-corpus-gate-missing-tikkunim-non-bidir-links`
- New action id:
  - `test-pytest-corpus-gate-missing-tikkunim-non-bidir-links`
- `applies_patch` remains `false`.
- The loop does not repair corpus content automatically.

Commit:

- `21cfb8e [verified] classify corpus gate pytest signal`

### 2. launchd pytest psql environment hardening

Files:

- `etzchaim/metacognition/verify.py`
- `tests/test_metacognition_verify.py`

Behavior:

- Pytest verification env now extends PATH with launchd-safe common paths.
- If `ETZ_PSQL_BIN` is not already set, the verifier resolves `psql` from that search path and injects the absolute path.
- This avoids adding `EnvironmentVariables` to the LaunchAgent plist and preserves the strict Phase 3C plist allowlist.

Commit:

- `b705c80 [verified] harden launchd pytest psql environment`

## Verification

TDD red tests were observed before implementation for both changes.

Passed commands:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' \
.venv/bin/python -m pytest \
  tests/test_metacognition_collectors.py \
  tests/test_metacognition_events.py \
  tests/test_metacognition_first_loop.py \
  tests/test_metacognition_loop_once.py \
  tests/test_metacognition_faculties.py \
  tests/test_metacognition_verify.py \
  tests/test_supervision_launchagent.py \
  tests/test_supervision_launchctl.py \
  -q
```

Result:

```text
57 passed in 0.14s
```

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' \
.venv/bin/python -m pytest tests/test_install/test_psql_helper.py sifrei_yesod/tests/test_folio_map.py -q
```

Result:

```text
17 passed in 0.16s
```

```bash
git diff --check
```

Result: OK.

Independent reviewer verdicts:

- Corpus-gate classification: passed, no security concerns, no logic errors.
- launchd pytest psql env hardening: passed, no security concerns, no logic errors.

## Real LaunchAgent execution

Command:

```bash
uv run etzchaim supervision --kickstart --allow-real-launchctl --ack "KICKSTART PHASE 3C LOOP ONCE"
```

launchd result:

- Before: `runs = 3`, `last exit code = 0`, `state = not running`
- After: `runs = 4`, `last exit code = 0`, `state = not running`

Latest heartbeat:

```json
{"action_count": 6, "applies_patch": false, "cycle_id": "loop-20260604T202732Z", "guardian_verdict": "unavailable", "improve_status": "written", "status": "written", "timestamp": "2026-06-04T20:27:32.873191Z", "top_issue_id": "pytest-corpus-gate-missing-tikkunim-non-bidir-links"}
```

Latest improve report:

- `/Users/fffff/.etz-chaim/runs/improve-20260604T202732Z.md`

Top issue evidence:

- `diagnostic_category=corpus-gate`
- `missing_tikkunim_unexpected=[1, 2, 3, 4, 5, 6, 9, 10, 12]`
- `non_bidirectional_first=Z-IR-T08-001→EC-H3S2-T08-001 missing reciprocal`

## Scope confirmations

- No corpus file under `sifrei_yesod/sefarim/**` was modified.
- No Docker/PostgreSQL service was started or changed.
- No LaunchAgent plist allowlist expansion was made.
- No push was run.
- Existing untracked files were left untouched:
  - `strategy/codex-prompt/codex-plan/etzchaim-phase3c-controlled-activation-plan.md`
  - `uv.lock`

## Current state

The extracted component is now operational enough to watch in action:

1. launchd starts the loop once.
2. the loop runs verification under the real daemon environment.
3. the loop writes heartbeat/report/ledger.
4. the top issue is now concrete and actionable instead of generic.
5. the safe loop still refuses to auto-mutate corpus content.

Next useful phase: connect an explicit Guardian/Intent adapter or create a source-backed corpus work phase for the reported Idra debt.
