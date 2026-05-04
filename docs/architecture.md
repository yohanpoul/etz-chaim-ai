# Architecture

## Overview

Etz Chaim AI is organized in three layers :

1. **Specification corpus** (internal) — 1696 specification items with epistemic labeling, concepts, mappings, and cross-references.
2. **Specification bridge** (internal) — indexed loader exposing the corpus via a five-method API (load by id, by concept, by module, search).
3. **Operational modules** — Python packages implementing the cognitive faculties, mature configurations, and probes, respecting layered composition discipline and adversarial testing.

For details on the structural framework that inspired this organization, see [`docs/advanced.md`](advanced.md). It is informational only — not required to use or contribute.

## Sequential consolidation

The project follows a strict consolidation order across the cognitive faculties : the foundational faculty is built first, each subsequent faculty depending on those already consolidated. Concretely : memory → introspection → persistence → harmony → contraction → expansion → bridge → causal → insight → meta-orchestrator.

Each faculty is consolidated (qualification tests green, 7 calibration parameters exposed) before the next is started.

## Module map

### Core specification infrastructure

| Module | Role |
|:-------|:-----|
| `bridge/` | Specification loader (1696 items) |
| internal corpus | Source assertions (specifications + relations + principles) |

### Cognitive faculty modules (v0.1.0)

| Module | Role |
|:-------|:-----|
| `explorationengine/` | Cross-domain exploration |
| `autojudge/` | Adversarial judgment |
| `dissensuengine/` | Productive tension / contradiction |
| `insightforge/` | Insight generation |
| `causalengine/` | Causal reasoning |
| `selfmap/` | Self-mapping |
| `epistememory/` | Memory foundation |
| `failuretoinsight/` | Failure learning |

### Mature configurations

Six configuration layers (compose internal faculties into operational units) :
- Highest-level invariants
- Strategic meta-orchestrator
- Generative configuration
- Structuring configuration
- Execution configuration
- Interface configuration

Public API exposes them as `Configuration` instances. Internal file paths use domain-specific naming — see `docs/internal/architecture.md` for the mapping.

### Dedicated engines

| Module | Role |
|:-------|:-----|
| `configurations/` | Cross-configuration coupling + persistent faculty trace |
| `probes/orchestrator.py` | Probe orchestrator |
| `probes/rectification.py` | 3-mode rectification |

## Layered composition discipline

No module writes directly to the aggregate `overall_score`. Boosts pass through faculties (`set_faculty`) and `overall` is always computed from faculties. A static check rejects any code that bypasses this discipline.

## Persistent trace coefficient

Every cross-configuration boost leaves a persistent trace coefficient on each faculty that accumulates across cycles (plateau 0.3, decay 5%/cycle). Stable modules gain cumulative advantage without violating the layered composition rule.

## Testing layers

| Layer | Location | Scope |
|:------|:---------|:------|
| Unit | `<module>/tests/` | API contract, edge cases |
| Qualification | 4 levels per module | foundation / application / excess / opposite |
| Integration | `tests/` | cross-module flows |
| Specification alignment | `scripts/check_doctrine_code_alignment.py` | specification ↔ code mapping |
| ID uniqueness | `scripts/check_id_uniqueness.py` | corpus consistency |
| Runtime | `scripts/force_probe_cycle.py` | end-to-end cycle |

## Extending the system

- Adding a new configuration : see internal guide in `docs/internal/guides/`.
- Transposing a new specification source : see internal guide `docs/internal/guides/transpose_new_sefer.md`.
- Contributing : see [`CONTRIBUTING.md`](https://github.com/yohanpoul/etz-chaim-ai/blob/main/CONTRIBUTING.md).
