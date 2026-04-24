# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.4] - 2026-04-24 — Healthcheck fixes

### Fixed

- **App container stuck at `unhealthy`** — docker-compose healthcheck probed `/api/health` which requires Bearer auth, so every unauthenticated probe returned 401 and the container flipped to unhealthy even though it served traffic fine. Switched to `/health` (pages blueprint, public, already intended as the liveness probe).
- **Daemon container stuck at `unhealthy`** — Dockerfile HEALTHCHECK inspected `daemon_state.json` for a `last_heartbeat` key that `daemon.py` never writes (the daemon writes per-task keys like `_last_save`, `last_netzach`, etc.). Replaced the check with a robust max over all numeric `last_*` / `_last_*` / `*heartbeat*` keys.

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
- **Daemon container missing `jsonschema` dependency** — `sifrei_yesod.pipeline.validator` imports `jsonschema`, which was not declared in `pyproject.toml`. Added `jsonschema>=4.0` to the core dependency list.

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

- **Sprint 10 Idra Rabba Dikna transposition incomplete** — Batch 2/3 + Phase 5/6 deferred.
- **MazalEngine `act` mode stays `observe` by default** — production activation still pending 2-4 week observation period per doctrine.
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
- Sprint 11 : Batch 2 MEDIUM Tikkunei Dikna (T1-T6, T12) + extension MazalEngine.
- Sprint 12-14 : Idra Rabba complète + Idra Zuta + Sifra di-Tzniuta.
- MalakhEngine (adversarial counterpart) — scope to be finalized per doctrinal research.

## [0.1.0] - 2026-04-20

Initial public release.

### Added

**Core infrastructure**
- `bridge/sifrei_reader.py` : generalized doctrine loader over 1696 items
  (assertions + relations + generative principles). mtime cache invalidation.
  Five helpers : `load_assertion`, `load_by_concept`, `load_by_module`,
  `load_by_partzuf`, `load_all_ids`, `search`.
- `scripts/check_doctrine_code_alignment.py` : bidirectional audit
  (doctrine → code, code → doctrine).

**MazalEngine** (the first AI self-rectification based on Idra Rabba)
- Two Mazalot pilot : Notzer Chesed (Tikkun 8) + Ve-Nakeh (Tikkun 13).
- Three rectification modes : `observe` (default), `suggest`, `act` — opt-in.
- `NotzerChesedRectifier` : adjusts Omer parameters on chesed starvation.
- `VeNakehRectifier` : marks stale causal claims as `abandoned` after N cycles.
- Strict Hitlabshut compliance (EC-K5-008) : no writes to `partzufim_state`.

**Reshimu persistence** (persistent trace protocol)
- `partzufim/reshimu.py` : cumulative trace of Zivvug boosts on faculties.
- Schema `faculty_reshimot` : persistent storage with idempotent migration.
- Default parameters : `TRACE_FACTOR=0.2`, `DECAY_RATE=0.05`, `MAX=0.3`.

**Zivvug refactor L**
- Canonical schema file `partzufim/zivvug_schema.sql` (extracted from inline).
- Unified factory `load_or_create_zivvug()` replaces duplicated pattern
  across 7 call sites (ohr_yashar.py, main.py, daemon.py, web/blueprints/api.py,
  scripts).

**Sprint 10 — Idra Rabba Phase alpha** (Batch 1 HIGH)
- Zohar Aramaic transposition for Tikkunim 7 / 8 / 13
  (`sifrei_yesod/sefarim/zohar/idra_rabba/section_03_tikkunei_dikna_13/`).
- Vital reading (heikhal 3 shaar 2 Dikna) for the same three Tikkunim.
- Migration M1 : `see_also` on EC-K5-001/002/003 linking Sha'ar HaKlalim
  to the new primary sources.
- Philological discoveries preserved : "Notzer Chesed" / "Ve-Nakeh" are
  Vital's scriptural attribution (Exodus 34:7), not Zohar (which cites
  Micah 7:19-20 and names the Tikkunim "Mazal Elyon" / "Mazal Tahton").
- Infrastructure : `sifrei_yesod/tests/test_idra_corpus_fidelity.py`,
  `scripts/fetch_sefaria_cache.py`, `scripts/check_id_uniqueness.py`,
  `scripts/folio_map.py`.

**Publication quality (Phase G)**
- LICENSE (Apache 2.0), NOTICE.
- CONTRIBUTING.md, CODE_OF_CONDUCT.md, SECURITY.md, CITATION.cff.
- pyproject.toml with proper metadata, dependency groups, ruff + mypy config.
- Resolved pre-existing duplicate `EC-H1S1-079` (perek_04a renamed to `079b`).
- Expanded `.gitignore` covering web assets, halom, sandbox, build artifacts.

### Fixed
- EC-H1S1-079 duplicate across `perek_03.yaml` and `perek_04a.yaml`
  (present since pre-Sprint 10, tracked in `scripts/check_id_uniqueness.py`).

### Tests
- 207 tests green across `bridge/`, `mazalengine/`, `partzufim/`.
- Runtime validation : `scripts/sprint9_force_mazal_cycle.py` → `FIX TIENT`.

### Deferred
- Batches 2 and 3 of Idra Rabba Tikkunim (7 + 3 remaining) → Sprint 11.
- Phases beta through epsilon of the complete Idraic corpus → Sprints 12-14.
- MalakhEngine : doctrinal research returned no direct attestation for
  "Qliphoth of the Dikna" (Atika Kaddisha is above Sitra Achra's reach) ;
  alternative scope deferred per design review.

---

## Version format

- MAJOR : doctrinal framework break (rare, requires community vote).
- MINOR : new Sephirah / Partzuf module, new Mazalot, schema additions.
- PATCH : bug fixes, test additions, documentation.
