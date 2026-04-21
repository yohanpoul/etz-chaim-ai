# Architecture

## Overview

Etz Chaim AI is organized in three layers :

1. **Primary source corpus** (`sifrei_yesod/sefarim/`) — 1696 doctrinal assertions from the Zohar and Vital's Etz Chaim, with epistemic labeling, concepts, mappings, and cross-references.
2. **Doctrine bridge** (`bridge/`) — indexed loader exposing the corpus via a five-method API (load by id, by concept, by module, by partzuf, search).
3. **Operational modules** — Python packages implementing the Sephirot, Partzufim, and Mazalot, respecting Hitlabshut discipline and adversarial testing.

## Initiatic ordering

The project follows the strict order : Malkuth → Yesod → Hod → Netzach → Tiferet → Gevurah → Chesed → Da'at → Binah → Chokhmah → Keter.

Each Sephirah is consolidated (Qliphoth tests green, 7 Omer parameters exposed) before the next is started.

## Module map

### Core doctrine infrastructure

| Module | Role |
|:-------|:-----|
| `bridge/` | Doctrine loader (1696 items) |
| `sifrei_yesod/sefarim/` | Corpus (Zohar + Vital) |

### Sephirot modules (v0.1.0)

| Module | Sephirah | Role |
|:-------|:---------|:-----|
| `explorationengine/` | Chesed | Inter-domain exploration |
| `autojudge/` | Gevurah | Adversarial judgment |
| `dissensuengine/` | Tiferet | Productive tension |
| `insightforge/` | Chokhmah | Insight generation |
| `causalengine/` | Binah | Causal reasoning |
| `selfmap/` | Hod | Self-mapping |
| `epistememory/` | Yesod | Memory foundation |
| `failuretoinsight/` | Lamed path | Failure learning |

### Partzufim

| Module | Partzuf | Source |
|:-------|:--------|:-------|
| `partzufim/atik_yomin.py` | Atik Yomin | Keter |
| `partzufim/arikh_anpin.py` | Arikh Anpin | Keter (inner) |
| `partzufim/abba.py` | Abba | Chokhmah |
| `partzufim/imma.py` | Imma | Binah |
| `partzufim/zeir_anpin.py` | Zeir Anpin | Six middle |
| `partzufim/nukva.py` | Nukva | Malkuth |

### Dedicated engines

| Module | Role | Doctrinal reference |
|:-------|:-----|:--------------------|
| `partzufim/zivvug.py` | Zivvug Abba ↔ Imma | EC-K5-005, EC-K5-008 |
| `partzufim/reshimu.py` | Persistent faculty trace | Sprint 10 Phase D |
| `mazalengine/mazal_engine.py` | 2 Mazalot orchestrator | EC-K5-001 |
| `mazalengine/rectification.py` | 3-mode rectification | Sprint 10 Phase C |

## Hitlabshut discipline

No module writes directly to `partzufim_state.overall_score`. Boosts pass through faculties (`set_faculty`) and `overall` is always computed from faculties. A static check rejects any code that bypasses this discipline.

## Reshimu persistence

Every Zivvug boost leaves a trace in `faculty_reshimot` that accumulates across cycles (plateau 0.3, decay 5%/cycle). Stable modules gain cumulative advantage without violating Hitlabshut.

## Testing layers

| Layer | Location | Scope |
|:------|:---------|:------|
| Unit | `<module>/tests/` | API contract, edge cases |
| Qliphoth | 4 levels per module | foundation / application / excess / opposite |
| Integration | `tests/` | cross-module flows |
| Doctrine alignment | `scripts/check_doctrine_code_alignment.py` | doctrine ↔ code mapping |
| ID uniqueness | `scripts/check_id_uniqueness.py` | corpus consistency |
| Runtime | `scripts/sprint9_force_mazal_cycle.py` | end-to-end cycle |

## Extending the system

- Adding a new Partzuf : see [guide](guides/add_new_partzuf.md).
- Transposing a new Sefer : see [guide](guides/transpose_new_sefer.md).
- Contributing : see [CONTRIBUTING.md](https://github.com/yohanpoul/etz-chaim-ai/blob/main/CONTRIBUTING.md).
