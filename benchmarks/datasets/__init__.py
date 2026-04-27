"""Public benchmark datasets — fetched once, sha256-pinned, cached locally.

Datasets retenus (plan benchmark) :
    1. TruthfulQA MC2 (200 / 817) — Birur, anti-sycophancy
    2. HarmBench text behaviors (200 / 400) — Klipot defense
    3. XSTest (250 / 250) — over-refusal counter-bench
    4. GPQA-Diamond (198 / 198) — reasoning structuré (gated, requires HF token)
    5. AlpacaEval 2.0 LC (200 / 805) — qualité globale

Cache : ~/.etz-chaim/benchmark_datasets/<bench>/<sha>.jsonl
Manifest : benchmarks/datasets/cache/manifest.json
"""
