# Guide : add a new Partzuf

This guide walks through adding a new Partzuf module. The process is the same for any Sephirah transitioning to a mature configuration.

## Prerequisites

- The Sephirah that sources this Partzuf is already implemented and its tests are green.
- You have identified the primary source references (EC-*, Z-*) that justify the new Partzuf.
- You have an epistemic label (E1-E6) for each doctrinal claim you plan to encode.

## Step 1 — Spec

Open a design issue that answers :

- **Atziluth (concept)** : what is the Partzuf doctrinally ? Cite primary sources.
- **Briah (design)** : schema of `partzufim_state` row for this Partzuf. API methods. 7 Omer calibration parameters.
- **Yetzirah (code)** : implementation sketch. Must include Hitkalelut (10 internal faculties).
- **Assiah (deployment)** : how it integrates into the daemon, the dashboard, and runtime validation.

## Step 2 — Qliphoth tests (write first, TDD red)

Every Partzuf module ships with four failure-mode tests :

| Level | Test | What it guards |
|:------|:-----|:---------------|
| Foundation | Partzuf never crashes when modules return `None` | graceful degradation |
| Application | Partzuf's `update_from_modules` is idempotent | no hidden state |
| Excess | Faculty values capped at 1.0 | no runaway growth |
| Opposite | When the opposing Partzuf dominates, this one orients `akhor` | polarity respect |

Create these tests in `partzufim/tests/test_<partzuf>.py` and run them — they must fail (red) before implementation.

## Step 3 — Doctrinal assertions

Add doctrinal assertions in `sifrei_yesod/sefarim/` with `mapping.modules` pointing to the new Python file. Example :

```yaml
- id: "EC-H3S1-001"
  source_he: "..."
  source_ref: "Etz Chaim Heikhal 3, Sha'ar 1:1"
  assertion: |
    Doctrinal content here.
  type: axiome_explicite
  epistemic_level: E1
  concepts:
    - {id: arikh_anpin, role: la_face_longue}
  mapping:
    modules: ["partzufim/arikh_anpin.py"]
    tables: ["partzufim_states"]
    partzufim: ["arikh_anpin"]
    relevance: "..."
```

Run `scripts/check_id_uniqueness.py sifrei_yesod/sefarim/ --strict` to confirm the new IDs don't collide.

## Step 4 — Implement

Subclass `PartzufBase` :

```python
from partzufim.base import PartzufBase, FACULTY_NAMES

class MyNewPartzuf(PartzufBase):
    name = "MyPartzuf"
    hebrew = "פַּרְצוּף"
    source_sephirah = "chesed"
    description = "..."

    def _compute_faculties(self, modules: dict) -> None:
        # Read modules, translate to faculty activations.
        ...

    def _assess_specific(self) -> dict:
        return {"message": "..."}

    def _interact_specific(self, other: PartzufBase, resonance: float) -> dict:
        return {}
```

Run your tests — they should turn green.

## Step 5 — Integration

- Register the Partzuf in `partzufim/__init__.py::init_partzufim`.
- Update `partzufim/db.py` schema if new columns are needed (use `ADD COLUMN IF NOT EXISTS`).
- Add the Partzuf to `scripts/sprint9_force_mazal_cycle.py` runtime validation.
- Update the architecture documentation.

## Step 6 — Audit

Run the alignment check :

```bash
python scripts/check_doctrine_code_alignment.py
```

Then global regression :

```bash
make test-core
```

And submit the PR using the standard template.

## Common mistakes

- **Skipping Hitkalelut** : a Partzuf must have all 10 internal faculties, not a subset.
- **Direct writes to `overall_score`** : forbidden. Only `set_faculty` is allowed.
- **Missing `see_also`** : every new assertion must link to at least one existing primary source if the doctrinal connection is known.
- **Claiming E1 without quoting verbatim** : if you translate or paraphrase, the level is at most E2.
