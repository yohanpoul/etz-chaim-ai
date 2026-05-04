---
public_name: LegacySurfaceSanitize
module_path: scripts/sanitize_legacy_surface.py
spec_id: SPEC-006
version: 0.1.0
internal_name: birur_legacy
internal_source: ".claude/rules/public-surface-neutrality.md"
internal_e_label: E1
status: draft
validated_by: []
---

# Legacy Surface Sanitize

## Purpose

Sanitize the legacy public-facing surface that was excluded from
`scripts/check_public_surface.sh` via scope-narrow patterns on 2026-05-04
to unblock autopilot PR pipeline. Each excluded path must be cleaned of
forbidden terminology and the corresponding entry removed from
`EXCLUDED_PATTERNS`.

The exclusions are tech debt acknowledged at unblock time and tracked
here for systematic resolution. Once all sub-tasks complete, the
`EXCLUDED_PATTERNS` block tagged "Legacy panel pre-pivot" is deleted and
`bash scripts/check_public_surface.sh` exits 0 against the full original
scope.

## Sub-tasks (each independent, autopilot pickup as separate cycle)

### 06.1 — Web templates legacy

Files :
- `web/templates/avatars.html`
- `web/templates/import.html`
- `web/templates/systeme/erreurs.html`
- `web/templates/systeme/personnages.html`
- `web/templates/partials/_card_avatar.html`

Replace forbidden terms (Sephir*, Partzuf, Abba/Imma/Anpin/Nukva/Atik/Yomin/Arikh,
Sitra Achra, Qliphoth, Zivvug, Kabbal*) with public aliases per
`.claude/rules/public-surface-neutrality.md` mapping table. Update
data-bound class names + ids consistently. Keep visual layout unchanged.

### 06.2 — Web static JS / CSS legacy

Files :
- `web/static/app.js`
- `web/static/style.css`
- `web/static/css/erreurs.css`
- `web/static/css/adversite.css`
- `web/static/css/avatars.css`
- `web/static/js/procedural-models.js`

Rename forbidden symbols + comments. Map :
- `keter/chokmah/binah/...` → `meta_orchestrator / intuition / structure / ...`
  (preserve key name compat via fallback dict if other modules read these)
- `arikh_anpin / zeir_anpin / nukva / atik_yomin` → `strategist / executor / interface / sage`
- `sitra_achra / qliphoth` → `adversarial_diagnostic / failure_modes`
- `tzimtzum / hitbonenut / birur` → `restriction / continuous_learn / triage`

### 06.3 — CLI copywriting legacy

Files :
- `etzchaim/cli/commands/demo.py` (lines 29-30 mention Yesod / Tiferet in copy)
- `etzchaim/cli/commands/onboard.py` (line 726 `MAZAL_RECTIFICATION_MODE` env var)

For `demo.py` : rewrite copy with neutral terms (e.g., "5 concepts loaded
in episodic memory module" instead of "Yesod, persistent memory").

For `onboard.py` : rename `MAZAL_RECTIFICATION_MODE` → `PROBE_RECTIFICATION_MODE`
(already aliased in `etzchaim/deploy/config.yaml:705-708`). Update all
read sites to support both env var names during one minor version (back-compat
shim), emit deprecation warning when `MAZAL_*` is used.

### 06.4 — Backend config sephirot mapping

File : `etzchaim/deploy/config.yaml` lines 666-688.

The `sephirot:` block maps faculty names to olamot tiers for backend
dispatch. Renaming the YAML keys breaks every code site that does
`config["sephirot"]["yesod"]["olam"]`.

Approach :
1. Add a parallel `faculties:` block with neutral keys :
   ```yaml
   faculties:
     memory: { olam: assiah, embedding: true }
     introspection: { olam: yetzirah, judge_olam: briah }
     ...
   ```
2. Migrate all read sites to prefer `faculties.*` with fallback to
   `sephirot.*` (back-compat one minor version).
3. Once all read sites migrated + tests green, delete `sephirot:` block.
4. Remove `etzchaim/deploy/config.yaml` from `EXCLUDED_PATTERNS`.

Requires : grep all `config["sephirot"]` and `config.get("sephirot")` sites
across `etzchaim/`, `bridge/`, `partzufim/`, `mazalengine/`. Estimated 20-50
sites.

### 06.5 — Docker compose service names

File : `etzchaim/deploy/docker-compose.yml`.

Likely contains kabbalistic service names. Rename to neutral aliases
(e.g., `db`, `web`, `worker`, `bridge` → keep as-is if neutral, otherwise
`integrator`).

### 06.6 — Build manifest package paths

File : `pyproject.toml` lines 90, 122-123, 136, 159.

References to `bridge*`, `mazalengine*`, `partzufim*`, `sifrei_yesod/external`.
These are package directory names that exist on disk and must match.

Approach :
1. Move internal packages under `etzchaim/_internal/` namespace
   (`bridge/` → `etzchaim/_internal/bridge/`, etc.).
2. Update all imports across codebase.
3. Remove top-level dirs.
4. Update `pyproject.toml` to reference `etzchaim._internal.*` only.
5. Remove `pyproject.toml` from `EXCLUDED_PATTERNS`.

Requires : large refactor (50+ import sites). Defer until rectifiers + paper done.

### 06.7 — GitHub templates + workflows

Files :
- `.github/ISSUE_TEMPLATE/bug_report.md`
- `.github/ISSUE_TEMPLATE/feature_request.md`
- `.github/workflows/test.yml`

Rewrite issue templates with neutral product framing. Audit `test.yml`
for forbidden term references.

## Tests

`tests/test_legacy_surface_sanitize.py` (post-implementation) :
- For each sub-task : after running the sanitize script, assert that the
  corresponding EXCLUDED_PATTERNS entry has been removed and
  `bash scripts/check_public_surface.sh` against the now-included path
  exits 0.

## Definition of Done

- All 7 sub-tasks shipped (each as separate PR per autopilot cycle).
- `EXCLUDED_PATTERNS` no longer contains any "Legacy panel pre-pivot" entry.
- `bash scripts/check_public_surface.sh` exits 0 with no scope-narrow exclusions.
- No regression in user-visible UI / CLI behavior (visual snapshot tests pass).

## Non-goals

- Does not change the cognitive faculty mapping itself; only renames the
  user-visible identifiers.
- Does not migrate `tests/` (already excluded; separate spec).
- Does not touch `docs/internal/`, `.internal/`, `paper/sections/appendix_historical.md`
  (correctly excluded paths).
