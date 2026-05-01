# Examples

Runnable demonstrations of Etz Chaim AI components. Each example is self-contained.

## Available examples

- `02_probe_orchestrator_demo.py` — instantiate the probe orchestrator in `observe` mode and run one cycle (requires DB).

Additional examples for advanced corpus exploration are in `docs/internal/examples/`.

## Running

```bash
source .venv/bin/activate
python examples/02_probe_orchestrator_demo.py
```

## Adding an example

Keep each example under 150 lines. Favor clarity over completeness. Submit a PR with the example + an entry in this README.

Public-facing examples must pass `bash scripts/check_public_surface.sh`.
