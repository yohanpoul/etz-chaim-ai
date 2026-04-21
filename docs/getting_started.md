# Getting started

## Prerequisites

- Python 3.10 or later (3.13 recommended).
- PostgreSQL 16 with the `pgvector` extension (optional for core tests, required for the daemon).
- `make`.

## Install

```bash
git clone https://github.com/yohanpoul/etz-chaim-ai.git
cd etz-chaim-ai
make install
```

This creates a virtual environment at `.venv/`, installs the project in editable mode with development and documentation extras, and wires pre-commit hooks.

## Run the core tests

```bash
make test-core
```

You should see around 200 tests green across `bridge/`, `mazalengine/`, and `partzufim/`.

## Database setup (optional for v0.1.0)

If you want to run the daemon or the runtime validation cycle :

```bash
createdb etz_chaim
psql etz_chaim -c "CREATE EXTENSION IF NOT EXISTS pgvector;"
psql etz_chaim < partzufim/zivvug_schema.sql
psql etz_chaim < causalengine/schema.sql
```

Then configure the connection via the `ETZ_CHAIM_DB_URL` environment variable, for example :

```bash
export ETZ_CHAIM_DB_URL="postgresql://postgres@localhost:5432/etz_chaim"
```

## Run the demo cycle

```bash
make demo
```

This runs `scripts/sprint9_force_mazal_cycle.py`, which :

1. Takes a snapshot of `partzufim_state`.
2. Runs one MazalEngine cycle over the current state.
3. Verifies that no row of `partzufim_state` was written (Hitlabshut compliance).
4. Reports any Tikkunim emitted.

Expected output ends with `Verdict : ✓ FIX TIENT`.

## Explore the corpus

```python
from bridge import load_assertion, load_by_module, search

# Load a single assertion
a = load_assertion("EC-K5-001")
print(a["source_he"])
print(a["assertion"])

# All assertions that map to a specific module
for a in load_by_module("partzufim/arikh_anpin.py"):
    print(a["id"], "-", a["source_ref"])

# Substring search across Hebrew and French fields
for a in search("notzer chesed"):
    print(a["id"])
```

## Next steps

- Read the [Architecture overview](architecture.md).
- Explore the [Concepts](concepts/sephirot.md) documentation.
- Check the [Roadmap](roadmap.md) to see what is planned and where you can contribute.
