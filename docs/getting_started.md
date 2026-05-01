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

You should see around 200 tests green across the core modules.

## Database setup (optional for v0.1.0)

If you want to run the daemon or the runtime validation cycle :

```bash
createdb etz_chaim
psql etz_chaim -c "CREATE EXTENSION IF NOT EXISTS pgvector;"
psql etz_chaim < scripts/init_schema.sql
```

Then configure the connection via the `ETZ_CHAIM_DB_URL` environment variable, for example :

```bash
export ETZ_CHAIM_DB_URL="postgresql://postgres@localhost:5432/etz_chaim"
```

## Run the demo cycle

```bash
make demo
```

This runs `scripts/force_probe_cycle.py`, which :

1. Takes a snapshot of the configuration state.
2. Runs one probe orchestrator cycle over the current state.
3. Verifies that no row of the configuration state was written (layered composition compliance).
4. Reports any rectifiers emitted.

Expected output ends with `Verdict : ✓ FIX HOLDS`.

## Explore the public API

```python
from etzchaim import initiate

# Plug your LLM into Etz Chaim AI
agent = initiate(llm="claude-opus-4")

# Run a query through the cognitive operating system
response = agent.query("What are your typical failure modes?")
```

For corpus exploration and advanced usage, see `etzchaim --explain-origin` or `docs/advanced.md`.

## Next steps

- Read the [Architecture overview](architecture.md).
- Check the [Roadmap](roadmap.md) to see what is planned and where you can contribute.
- See [`docs/advanced.md`](advanced.md) for the structural framework that inspired the architecture (informational, not required).
