# Examples

Runnable demonstrations of Etz Chaim AI components. Each example is self-contained.

## Available examples

- `01_quickstart.py` — load a doctrinal assertion and print its fields. Zero dependencies beyond `bridge/`.
- `02_mazalengine_demo.py` — instantiate MazalEngine in `observe` mode and run one cycle (requires DB).
- `03_corpus_exploration.py` — explore the corpus via `load_by_concept`, `load_by_module`, `search`.

## Running

```bash
source .venv/bin/activate
python examples/01_quickstart.py
```

## Adding an example

Keep each example under 150 lines. Favor clarity over completeness. Annotate with doctrinal references (EC-*, Z-*) where relevant. Submit a PR with the example + an entry in this README.
