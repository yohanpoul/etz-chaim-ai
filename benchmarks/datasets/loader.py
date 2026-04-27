"""Dataset loader — normalize 5 benchmarks vers Prompt unifié.

Chaque dataset a un schéma propre. Le loader produit un format uniforme
{id, text, bench, metadata} consommable par les arms.

Stratégie d'évaluation par bench (utilisée plus tard par stats.py + judge.py) :

| Bench | Type métrique | Method |
|-------|---------------|--------|
| truthfulqa | MC2 accuracy | Demander réponse libre, judge match contre mc2_targets |
| harmbench | ASR ↓ | Judge "did model comply with harmful request" |
| xstest | over-refusal ↓ | Judge "was benign question over-refused" |
| reasoning_hard (MMLU-Pro) | accuracy | Demander lettre A-J, exact match contre answer |
| alpacaeval | LC win-rate | Pairwise judge vs reference output |
"""

from __future__ import annotations

import json
import string
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

CACHE_ROOT = Path.home() / ".etz-chaim" / "benchmark_datasets"


@dataclass
class Prompt:
    """Prompt unifié à passer aux arms."""

    id: int                              # _bench_id from dataset
    bench: str                           # nom du bench
    text: str                            # prompt rendu (incl. format choix MMLU-Pro)
    metadata: dict[str, Any] = field(default_factory=dict)
    """Données pour l'évaluation post-hoc (gold, references, behavior, etc.)"""


# ---------------------------------------------------------------------------
# Renderers per dataset (transform raw row → Prompt)
# ---------------------------------------------------------------------------


def _render_truthfulqa(row: dict[str, Any]) -> Prompt:
    """TruthfulQA MC2 : question + choix MC2 jugés post-hoc.

    On demande au modèle de répondre librement à la question.
    Le judge compare la réponse aux mc2_targets pour scoring.
    """
    question = row["question"]
    text = (
        f"Question: {question}\n\n"
        "Provide a brief, factual, accurate answer. Be concise."
    )
    return Prompt(
        id=row["_bench_id"],
        bench="truthfulqa",
        text=text,
        metadata={
            "question": question,
            "mc1_targets": row.get("mc1_targets", {}),
            "mc2_targets": row.get("mc2_targets", {}),
            "category": row.get("category", ""),
        },
    )


def _render_harmbench(row: dict[str, Any]) -> Prompt:
    """HarmBench/JBB : harmful goal as direct prompt.

    Le modèle DOIT refuser. ASR = fraction où il complies au lieu de refuse.
    """
    goal = row["Goal"]
    return Prompt(
        id=row["_bench_id"],
        bench="harmbench",
        text=goal,  # prompt direct, pas de wrapping
        metadata={
            "behavior": row.get("Behavior", ""),
            "category": row.get("Category", ""),
            "target": row.get("Target", ""),
            "source": row.get("Source", ""),
        },
    )


def _render_xstest(row: dict[str, Any]) -> Prompt:
    """XSTest : prompt borderline (safe ou unsafe).

    Métrique over-refusal sur prompts safe : le modèle ne doit PAS refuser.
    """
    prompt = row["prompt"]
    return Prompt(
        id=row["_bench_id"],
        bench="xstest",
        text=prompt,
        metadata={
            "type": row.get("type", ""),
            "final_label": row.get("final_label", ""),
            # type=homonyms etc. = safe ; on infère is_safe depuis l'absence de
            # marqueur unsafe (xstest v2 : safe par défaut sauf categories
            # contrast_*)
            "is_safe": not row.get("type", "").startswith("contrast_"),
        },
    )


def _render_mmlu_pro(row: dict[str, Any]) -> Prompt:
    """MMLU-Pro : question multi-choice avec lettres A-J.

    Le modèle doit répondre par une seule lettre. Exact match.
    """
    question = row["question"]
    options = row.get("options", [])
    letters = string.ascii_uppercase[: len(options)]
    formatted_choices = "\n".join(
        f"{letters[i]}. {opt}" for i, opt in enumerate(options)
    )
    text = (
        f"{question}\n\n"
        f"{formatted_choices}\n\n"
        "Answer with only the letter of the correct option (e.g. 'A'). "
        "No explanation."
    )
    return Prompt(
        id=row["_bench_id"],
        bench="reasoning_hard",
        text=text,
        metadata={
            "answer": row.get("answer", ""),  # letter
            "answer_index": row.get("answer_index", -1),
            "category": row.get("category", ""),
            "n_options": len(options),
            "options": options,
        },
    )


def _render_alpacaeval(row: dict[str, Any]) -> Prompt:
    """AlpacaEval : instruction libre + reference response (text_davinci_003).

    Évaluation pairwise : LLM judge compare modèle vs reference, win-rate LC.
    """
    instruction = row["instruction"]
    return Prompt(
        id=row["_bench_id"],
        bench="alpacaeval",
        text=instruction,
        metadata={
            "instruction": instruction,
            "reference_output": row.get("output", ""),
            "reference_generator": row.get("generator", "text_davinci_003"),
            "dataset_source": row.get("dataset", ""),
        },
    )


_RENDERERS = {
    "truthfulqa": _render_truthfulqa,
    "harmbench": _render_harmbench,
    "xstest": _render_xstest,
    "reasoning_hard": _render_mmlu_pro,
    "alpacaeval": _render_alpacaeval,
}


def load_bench(bench: str, limit: int | None = None) -> list[Prompt]:
    """Charger tous les prompts d'un bench, normalisés en Prompt.

    Args:
        bench: nom du bench ('truthfulqa' | 'harmbench' | 'xstest' |
               'reasoning_hard' | 'alpacaeval')
        limit: limit de prompts (None = all).

    Returns:
        Liste de Prompt avec id stable.
    """
    if bench not in _RENDERERS:
        raise ValueError(
            f"Unknown bench: {bench}. Available: {list(_RENDERERS)}"
        )

    data_file = CACHE_ROOT / bench / "data.jsonl"
    if not data_file.exists():
        raise FileNotFoundError(
            f"Dataset cache missing for {bench}: {data_file}\n"
            f"Run: python -m benchmarks.datasets.fetch {bench}"
        )

    renderer = _RENDERERS[bench]
    prompts: list[Prompt] = []
    with data_file.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            prompts.append(renderer(row))
            if limit is not None and len(prompts) >= limit:
                break

    return prompts


def iter_all_benches(limit_per_bench: int | None = None) -> Iterator[Prompt]:
    """Iterate over all 5 benches' prompts in deterministic order."""
    for bench in ("truthfulqa", "harmbench", "xstest", "reasoning_hard", "alpacaeval"):
        try:
            yield from load_bench(bench, limit=limit_per_bench)
        except FileNotFoundError as e:
            print(f"WARN: skipping {bench}: {e}", file=__import__("sys").stderr)


def bench_sizes() -> dict[str, int]:
    """Retourner taille (nombre de prompts) de chaque bench."""
    sizes: dict[str, int] = {}
    for bench in _RENDERERS:
        try:
            prompts = load_bench(bench)
            sizes[bench] = len(prompts)
        except FileNotFoundError:
            sizes[bench] = 0
    return sizes


if __name__ == "__main__":
    import sys

    # Smoke test : load each bench, print 1 sample
    print("=== Bench sizes ===")
    for bench, size in bench_sizes().items():
        print(f"  {bench:18s} {size:4d} prompts")

    print(f"\n=== Total : {sum(bench_sizes().values())} prompts ===\n")

    if "--samples" in sys.argv:
        for bench in _RENDERERS:
            try:
                prompts = load_bench(bench, limit=1)
                if prompts:
                    p = prompts[0]
                    print(f"\n--- Sample {bench} ---")
                    print(f"  id     : {p.id}")
                    print(f"  text   : {p.text[:200]}{'...' if len(p.text) > 200 else ''}")
                    print(f"  metakeys: {list(p.metadata.keys())}")
            except FileNotFoundError:
                print(f"  {bench}: cache missing")
