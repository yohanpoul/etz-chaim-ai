"""Benchmark harness for Claude+EtzChaim vs Claude raw — Opus 4.7.

Conforme au plan /Users/fffff/.claude/plans/fait-dans-le-meilleur-clever-lerdorf.md.

Architecture :
    runner.py        — boucle, retry+backoff, atomic checkpoint
    arms.py          — 5 arms (raw / CoT / self-consistency / Etz / Etz det)
    judge.py         — GPT-4o-mini default + Llama 3.3 70B sensitivity
    token_tracker.py — wraps AnthropicSDKProvider pour extraire usage
    cache.py         — sha256(model+prompt+temp+system) cache LLM
    checkpoint.py    — bench_state.json atomique
    stats.py         — bootstrap CIs, paired t-test, Cohen's d, McNemar
    ablation.py      — 7 configs Etz toggling modules
    datasets/        — fetch.py + cache local par bench
    reports/         — tables.py LaTeX + plots.py matplotlib
    results/runs/<run_id>/ {bench_state.json, responses.jsonl, judgments.jsonl}

Modèle pinné : claude-opus-4-20250514 (Opus 4.7 full slug, anti-drift)
"""
