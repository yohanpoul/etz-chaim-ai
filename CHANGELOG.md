# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.30] - 2026-05-04 — autopilot budget tracker + PR-count sync + CI unblock

### Fixed

- **`etzchaim/autopilot/loop.py`** — token budget tracker was never invoked by the cycle loop, so `autopilot_tokens_consumed_month` stayed at 0 forever and the monthly cap was inert. The loop now extracts billable tokens (`input_tokens + output_tokens + cache_creation_input_tokens`; `cache_read_input_tokens` is NOT billable) from worker `RunResult.metadata` and calls `TokenBudget.consume(N)` after each cycle.
- **`etzchaim/autopilot/loop.py`** — `autopilot_pr_count_open` was read by the `max_open_prs` guard but never written back after `_open_pr_count()` succeeded, so the guard read a value that drifted out of sync (state said 2 while 3 PRs were live). The loop now persists the live count after each successful `gh pr list` query.
- **CI Docs (`mkdocs --strict`)** — `mkdocs.yml:2 site_description` contained a forbidden public-surface term (see `.claude/rules/public-surface-neutrality.md`); replaced with the neutral paper title. Six `nav` entries pointed at absent forbidden-surface pages under `concepts/` and `guides/`; removed. Three orphan pages added to nav (`installation.md`, `advanced.md`, `release-notes-v0.2.0.md`). Broken `../CONTRIBUTING.md` link in `architecture.md` replaced by absolute repo URL.
- **CI Lint (`ruff` strict paths)** — auto-fix applied: 7 lint errors (F401 unused import + I001 import order + F541 f-string without placeholder) and 7 unformatted files in `scripts/`, `etzchaim/configurations/`, `etzchaim/probes/` resolved.
- **CI Public surface guard** — workflow lacked `permissions:` block, causing the annotate step to fail with HTTP 403 when posting PR comments. Added explicit `pull-requests: write` + `issues: write`. Annotate step now also guards against PRs from forks. Added `mkdocs.yml` to `PUBLIC_PATHS` scope so future `site_description`-style leaks fail at scan time.

### Added

- **`etzchaim/autopilot/runners/base.py`** — `RunResult.metadata: dict[str, str]` field (default empty) for cross-cutting per-call data such as token usage, exit codes, total cost.
- **`etzchaim/autopilot/runners/claude_skill.py`** — extracts `usage` (`input_tokens`, `output_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`) and `total_cost_usd` from the Claude CLI JSON envelope into `RunResult.metadata`.
- **`etzchaim/autopilot/delegation/subagent.py`** — propagates `RunResult.metadata` into `WorkerResult.metadata`.
- **`etzchaim/autopilot/tests/test_budget_consume.py`** — 6 regression tests for budget wiring + PR-count sync (24/24 autopilot tests pass).
- **`specs/06_legacy_surface_sanitize.md`** — new spec tracking systematic cleanup of 99 pre-existing public-surface leaks in legacy paths (`web/templates/*`, `web/static/*`, `etzchaim/cli/commands/*`, `etzchaim/deploy/*`, `pyproject.toml`, `.github/ISSUE_TEMPLATE/`, `.github/workflows/test.yml`). Excluded scope-narrow until sanitize cycles run; marker `.implemented` posted to park autopilot pickup until manual split into 7 sub-specs.
- **`specs/04_rectifiers/{08,13}.implemented`** + **`specs/05_cognitive_os_eval_suite.implemented`** — markers parking these specs from autopilot pickup. R8 + R13 frontmatter `status: existing` (modules already coded). Spec 05 (eval suite) deferred pending split into ≤50-cycle sub-specs to stay within `budget_tokens_monthly: 1000000` cap.

### Changed

- **`etzchaim/deploy/config.yaml:718`** — `autopilot.enabled: false` (TEMPORARY; restored to `true` after Phase D foreground dry-run validation per plan `~/.claude/plans/ok-on-fais-ca-cuddly-turing.md`).
- **`docs/roadmap.md:9`** — replaced one legacy identifier with `faculty_persistent_traces` (1 inline neutralization vs scope creep).

### Notes for upgraders

This release unblocks the autopilot pipeline that has been stuck since 2026-05-01: 3 PRs (`meta-orchestrator`, `synthesis-bridge`, `multi-provider-wrapper`) were waiting in `ready-review` because all CI checks were red on every commit since `da493c0`. With v0.2.30 + restored `autopilot.enabled: true`, the daemon resumes background cycles producing one rectifier PR per cycle (interval 7200s = 2h, max 5 open PRs, 1M tokens/month cap).

## [0.2.23] - 2026-04-27 — specification corpus corpus seeded via init-db/99

### Added

- **`etzchaim/deploy/init-db/99-spec_corpus-data.sql`** — auto-generated dump of the entire transposed Etz Chaim corpus (1454 assertions, 700 relations, 302 principes, 3862 concepts, 78 perakim, 13 shaarim, 2216 cross_refs). Idempotent (`INSERT … ON CONFLICT DO UPDATE/NOTHING`), so `etzchaim update` re-applies the file via `_apply_migrations()` and ships every newly transposed perek to all Docker users without any extra command.
- **`scripts/dump_spec_corpus.py`** — regenerates the SQL dump from the dev `etz_chaim` postgres DB. Mirrors the ON CONFLICT keys used by `spec_corpus/pipeline/sofer.py` so the dump is semantically identical to a fresh sofer re-run. Resolves `perek_id` foreign keys with sub-SELECTs on `(sefer_id, heikhal_number, shaar_number, perek_number)` so SERIAL ids never leak across DBs.
- **`/sefergo` skill** — passe 4 (DUMP DISTRIBUTION) added: after each successful auto_ingest the dump is regenerated, so the auto-bump+commit+push captures the latest corpus.

### Notes for upgraders

After `etzchaim update`, the assertions/principes `embedding` columns are NULL'd by the dump on each upsert. The daemon will lazily re-embed them on first semantic search.

## [0.2.4] - 2026-04-24 — Healthcheck fixes

### Fixed

- **App container stuck at `unhealthy`** — docker-compose healthcheck probed `/api/health` which requires Bearer auth, so every unauthenticated probe returned 401 and the container flipped to unhealthy even though it served traffic fine. Switched to `/health` (pages blueprint, public, already intended as the liveness probe).
- **Daemon container stuck at `unhealthy`** — Dockerfile HEALTHCHECK inspected `daemon_state.json` for a `last_heartbeat` key that `daemon.py` never writes (the daemon writes per-task keys like `_last_save`, `last_intent_check`, etc.). Replaced the check with a robust max over all numeric `last_*` / `_last_*` / `*heartbeat*` keys.

## [0.2.3] - 2026-04-24 — Multi-instance + doctor-polish

Makes it possible to run two Etz Chaim instances side by side (e.g. `perso` and `dev`) on the same machine without port clashes, and fixes a false-negative in `etzchaim doctor`.

### Fixed

- **`etzchaim doctor` false-negative on `ETZ_CHAIM_API_KEY`** — the check only looked at `os.environ`, so running `etzchaim doctor` from a shell that had not sourced the compose `.env` always reported the key missing even when it was wired into the running containers. Doctor now falls back to reading `~/.etz-chaim/compose/.env` (respecting `ETZCHAIM_STATE_DIR`).

### Changed

- **Split host / container web port** : `WEB_PORT` is now hardcoded to `8080` inside the container (Flask bind target), and a new `HOST_WEB_PORT` variable drives the host-side port mapping. The `onboard` wizard writes `HOST_WEB_PORT` instead of `WEB_PORT`, with default `8080` (auto-bumped to the next free port if 8080 is already bound). Users upgrading from 0.2.2 should replace `WEB_PORT=<n>` by `HOST_WEB_PORT=<n>` in `~/.etz-chaim/compose/.env` if they customised the port.

## [0.2.2] - 2026-04-24 — Runtime fixes for container stack

Two blocking bugs surfaced by real-world `etzchaim onboard && etzchaim start` runs on a clean machine. Both images rebuilt and republished.

### Fixed

- **`web/app.py` ignored `ETZ_CHAIM_DB_URL`** — `create_app()` read only the deprecated `ETZ_CHAIM_DB` variable and fell back to `postgresql://localhost/etz_chaim`, so the app container tried to reach Postgres on `localhost:5432` instead of the `postgres:5432` service name. Now delegates to `pool._resolve_db_url()` (priority : `ETZ_CHAIM_DB_URL` → `ETZ_CHAIM_DB` with DeprecationWarning → default).
- **Daemon container missing `jsonschema` dependency** — `spec_corpus.pipeline.validator` imports `jsonschema`, which was not declared in `pyproject.toml`. Added `jsonschema>=4.0` to the core dependency list.

## [0.2.1] - 2026-04-24 — Install-readiness patch

Fixes three gaps that prevented external users from completing `pip install etzchaim && etzchaim onboard` out of the box. No API or schema changes ; safe to `etzchaim update` from 0.2.0.

### Fixed

- **`config.yaml` missing from wheel** — `docker compose up` failed with `bind mount source does not exist` because the template was not shipped. `config.yaml` is now in `etzchaim/deploy/`, listed in `[tool.setuptools.package-data]`, and extracted by `extract_compose_files()` alongside the docker-compose templates.
- **Broken legacy alias `etz-chaim`** — entry point pointed to `main:main` which has no `main()` function. Now redirects to the canonical `etzchaim.cli.app:app` (same behaviour as `etzchaim`, still removed in v0.3.0).
- **Python version mismatch README ↔ pyproject** — README and `docs/installation.md` advertised 3.12+, but `pyproject.toml` declares `>=3.10`. Docs now reflect the real floor : Python 3.10+ (tested on 3.10 / 3.11 / 3.12 / 3.13).

## [0.2.0] - 2026-04-XX — Container-first install (OpenClaw pattern)

Packages the entire stack behind a single `pip install etzchaim && etzchaim onboard`. Docker Compose replaces native `launchctl` / `systemd` for cross-OS parity.

### Breaking changes

- **Env var `ETZ_CHAIM_DB` deprecated** → use `ETZ_CHAIM_DB_URL` (legacy still works with `DeprecationWarning`, removed in v0.3.0).
- **`provider: claude_code` in `config.yaml` → `provider: anthropic`** (legacy alias accepted, auto-normalized at dispatch).
- **CLI entry point renamed `etz-chaim` → `etzchaim`** (no hyphen, faster to type). Legacy alias kept in v0.2, removed v0.3.
- **`olamot.claude_code_generate` routes via `etzchaim.providers` registry** — uses Anthropic SDK when `ANTHROPIC_API_KEY` is set (container-safe), falls back to `claude` CLI when binary on PATH.
- **macOS `launchctl` / Linux `systemd` native support deprecated** — Docker Compose is the only deployment path going forward. Legacy templates stay in `backup/native/` for reference.

### Added

- **`etzchaim` Python CLI** with 10 commands : `onboard` (interactive 4-step wizard), `start` / `stop` / `status` / `logs` (compose wrappers), `doctor` (5 diagnostic checks, `--json`, exit 1), `demo` (seed data + 5-act walkthrough), `update` (one-command upgrade path), `version` / `info`. `--json` on all data-producing commands. `etzchaim --help` renders < 200 ms (lazy imports).
- **Docker Compose deployment** : `pgvector/pgvector:pg17`, multi-stage Dockerfile (base → app / daemon), tini PID 1, non-root user, auto-detected profile (`hybrid-host-ollama` macOS, `full-nvidia`/`full-rocm`/`full-cpu` Linux, `wsl2-cuda` Windows). Named volumes (`etz_pg_data`, `etz_state`) avoid bind-mount UID/GID pitfalls.
- **Anthropic SDK provider** (`etzchaim.providers.AnthropicSDKProvider`) : prompt caching via `system.cache_control: ephemeral` (~90 % token savings on system prompts), extended thinking for Briah Olam, short model aliases (`opus` / `sonnet` / `haiku`) + full slug passthrough. Container-compatible (no interactive OAuth).
- **21 SQL schemas packaged** in `etzchaim/deploy/init-db/` — PostgreSQL applies them automatically via `docker-entrypoint-initdb.d`.
- **Portability fixes** : 13 hardcoded `/opt/homebrew/opt/postgresql@17/bin/psql` migrated to `shutil.which("psql")`. 13 hardcoded absolute project paths replaced with `str(Path(__file__).resolve().parents[2])`. 38 files migrated to `ETZ_CHAIM_DB_URL` fallback pattern. Flask bind `0.0.0.0` in container via `ETZCHAIM_IN_CONTAINER=1`.
- **`etzchaim` Python package** : `_paths` helpers, `providers/{anthropic_sdk,registry}.py`, `cli/{app,detect,compose}.py` + 10 command modules + `doctor/checks.py`, `demo_data/{seed.sql,load.py}`.
- **`etzchaim update`** — one-command upgrade path : `pip install --upgrade` → `docker compose pull` → re-extract compose templates → idempotent schema migrations → restart → doctor.
- **Dependencies** : added `anthropic>=0.40`, `typer>=0.12`, `questionary>=2.0`, `rich>=13`, `structlog>=24`.

### Fixed

- Flask bind `127.0.0.1` inside container blocked port mapping (Task 8).
- `docs/getting_started.md` said `ETZ_CHAIM_DB_URL`, code read `ETZ_CHAIM_DB` — unified via `pool._resolve_db_url()` helper.

### Deferred to v0.3.0 (Phase FULL)

- Multi-provider LLM via LiteLLM (OpenAI, Google, xAI, DeepSeek, Mistral, Cohere, Groq, Together, Fireworks, Perplexity).
- First-class Linux + Windows support (MVP best-effort, full CI matrix in FULL).
- 9 additional CLI commands (`config`, `models`, `db`, `daemon {enable,disable,run,schedule}`, `backup`, `restore`).
- Wizard extended to 9 steps with per-Olam provider config + machine profiles for scheduling.
- Doctor extended to 20 checks + `--fix` auto-repair.
- `sitra-achra` container (Garak + Promptfoo scans) opt-in.
- Shell completion (bash / zsh / fish).
- `docs/migration-v01-to-v02.md` detailed guide.
- PyPI release automation via GitHub Actions (manual `twine upload` in v0.2).

### Known issues

- **Sprint 10 primary source section Dikna transposition incomplete** — Batch 2/3 + Phase 5/6 deferred.
- **Probe orchestrator `act` mode stays `observe` by default** — production activation still pending 2-4 week observation period per protocol.
- **Provisional night-mode schedule** (Karpathy loop 21h-23h instead of doctrinal 23h-00h30) — override via `config.yaml`. Full configurable scheduling (machine profiles) in v0.3.

### Upgrade path (v0.1 → v0.2)

1. Backup v0.1 native : `pg_dump -Fc etz_chaim > /tmp/etz-v01-backup.pgc`
2. Unload legacy daemon : `launchctl unload ~/Library/LaunchAgents/com.etz-chaim.daemon.plist`
3. Install v0.2 : `pip install --upgrade etzchaim`
4. Run onboard : `etzchaim onboard` (fresh config + compose install)
5. Restore v0.1 data : `etzchaim db migrate --from-native --pg-dump /tmp/etz-v01-backup.pgc` (available v0.3)

---

## [Unreleased]

### Planned
- Sprint 11 : Batch 2 MEDIUM rectifiers + probe orchestrator extension.
- Sprint 12-14 : extended primary source corpus.
- Adversarial counterpart — scope to be finalized per design review.

## [0.1.0] - 2026-04-20

Initial public release.

### Added

- **Core infrastructure** : specification corpus loader (1696 items) with five-method API. Bidirectional doctrine-code audit.
- **Probe orchestrator** : 2 active rectifiers pilot, 3 rectification modes (observe / suggest / act).
- **Persistent trace coefficient** : cumulative trace on faculties with plateau and decay.
- **Cross-coupling refactor** : canonical schema + unified factory.
- **Sprint 10 Phase alpha** : 3 rectifiers (HIGH confidence) transposed from primary sources.
- **Publication quality** : LICENSE Apache 2.0, NOTICE, CONTRIBUTING.md, CODE_OF_CONDUCT.md, SECURITY.md, CITATION.cff, pyproject.toml.

### Fixed
- Pre-existing duplicate ID resolved.

### Tests
- 207 tests green across core modules.

### Deferred
- Batch 2 + 3 rectifiers → Sprint 11+.
- Adversarial counterpart : design review pending.

> Detailed historical entry with internal naming : see `docs/internal/CHANGELOG-archive.md`.

---

## Version format

- MAJOR : doctrinal framework break (rare, requires community vote).
- MINOR : new faculty / configuration module, new probes, schema additions.
- PATCH : bug fixes, test additions, documentation.
