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

Sanitize the legacy public-facing surface that was excluded from `scripts/check_public_surface.sh` via scope-narrow patterns on 2026-05-04 to unblock the autopilot PR pipeline. Each excluded path must be cleaned of forbidden terminology and the corresponding entry removed from `EXCLUDED_PATTERNS`.

The exclusions are tech debt acknowledged at unblock time and tracked here for systematic resolution. Once all sub-tasks complete, the `EXCLUDED_PATTERNS` block tagged "Legacy panel pre-pivot" is deleted and `bash scripts/check_public_surface.sh` exits 0 against the full original scope.

## Reference

The canonical forbidden-term list and public-alias mapping table live in `.claude/rules/public-surface-neutrality.md`. Workers picking sub-tasks below must consult that rule file for the verbatim term categories and rename mappings.

## Sub-tasks (each independent, autopilot pickup as separate cycle)

| ID | Scope | Files |
|---|---|---|
| 06.1 | Web templates legacy | 5 Jinja templates under `web/templates/` |
| 06.2 | Web static JS / CSS legacy | 6 files under `web/static/` |
| 06.3 | CLI copywriting legacy | `etzchaim/cli/commands/demo.py`, `etzchaim/cli/commands/onboard.py` |
| 06.4 | Backend config faculty mapping | `etzchaim/deploy/config.yaml` block at lines 666-688 |
| 06.5 | Docker compose service names | `etzchaim/deploy/docker-compose.yml` |
| 06.6 | Build manifest package paths | `pyproject.toml` lines 90, 122-123, 136, 159 |
| 06.7 | GitHub templates + workflows | `.github/ISSUE_TEMPLATE/*`, `.github/workflows/test.yml` |

For each sub-task, see `docs/internal/sanitize_legacy_surface_terms.md` for the exact rename table and migration approach.

## Tests

`tests/test_legacy_surface_sanitize.py` (post-implementation) :
- For each sub-task : after running the sanitize script, assert that the corresponding `EXCLUDED_PATTERNS` entry has been removed and `bash scripts/check_public_surface.sh` against the now-included path exits 0.

## Definition of Done

- All 7 sub-tasks shipped (each as separate PR per autopilot cycle).
- `EXCLUDED_PATTERNS` no longer contains any "Legacy panel pre-pivot" entry.
- `bash scripts/check_public_surface.sh` exits 0 with no scope-narrow exclusions.
- No regression in user-visible UI / CLI behavior (visual snapshot tests pass).

## Non-goals

- Does not change the cognitive faculty mapping itself; only renames the user-visible identifiers.
- Does not migrate `tests/` (already excluded; separate spec).
- Does not touch `docs/internal/`, `.internal/`, `paper/sections/appendix_historical.md` (correctly excluded paths).
