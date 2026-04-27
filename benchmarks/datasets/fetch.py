"""Fetch + cache + sha256-pin des 5 datasets publics.

Usage :
    python -m benchmarks.datasets.fetch              # fetch tous
    python -m benchmarks.datasets.fetch truthfulqa   # fetch un seul
    python -m benchmarks.datasets.fetch --verify     # verify sha256 sans fetch

Datasets gated (HuggingFace token requis) :
    - GPQA-Diamond : Idavidrein/gpqa (request access via HF UI)

Datasets publics (no token) :
    - TruthfulQA : truthfulqa/truthful_qa
    - HarmBench : walledai/HarmBench
    - XSTest : natolambert/xstest-v2-copy
    - AlpacaEval : tatsu-lab/alpaca_eval

Cache :
    ~/.etz-chaim/benchmark_datasets/<bench_name>/data.jsonl
    benchmarks/datasets/cache/manifest.json (sha256, sizes, dates)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

CACHE_ROOT = Path.home() / ".etz-chaim" / "benchmark_datasets"
MANIFEST_PATH = (
    Path(__file__).resolve().parent / "cache" / "manifest.json"
)


@dataclass
class DatasetSpec:
    """Spec d'un dataset à fetch.

    Supporte 2 sources :
    - HuggingFace : hf_repo + hf_subset + hf_split
    - URL directe : direct_url (JSON ou JSONL gzipped/plain)

    Si HF échoue et url_fallback fourni, tente l'URL directe.
    """

    name: str
    hf_repo: str | None = None
    hf_subset: str | None = None
    hf_split: str = "validation"
    direct_url: str | None = None      # URL directe JSON/JSONL (fallback)
    target_size: int = 200
    requires_token: bool = False
    description: str = ""


# Plan benchmark : 5 datasets retenus, avec fallbacks publics
DATASETS: list[DatasetSpec] = [
    DatasetSpec(
        name="truthfulqa",
        hf_repo="truthfulqa/truthful_qa",
        hf_subset="multiple_choice",
        hf_split="validation",
        target_size=200,
        description="TruthfulQA MC2 — anti-sycophancy / Birur (200 of 817)",
    ),
    DatasetSpec(
        name="harmbench",
        # walledai/HarmBench est gated. JBB (JailbreakBench) est public et
        # contient 100 harmful behaviors comparables — substitution propre.
        hf_repo="JailbreakBench/JBB-Behaviors",
        hf_subset="behaviors",
        hf_split="harmful",
        target_size=100,  # JBB n'a que 100 behaviors, on prend tout
        description="JailbreakBench harmful behaviors (substitut HarmBench public, 100 of 100)",
    ),
    DatasetSpec(
        name="xstest",
        hf_repo="natolambert/xstest-v2-copy",
        hf_subset=None,
        hf_split="prompts",
        target_size=250,
        description="XSTest — over-refusal counter-bench (250 of 250)",
    ),
    DatasetSpec(
        name="reasoning_hard",
        # Substitut GPQA-Diamond (gated). MMLU-Pro est public, niveau graduate,
        # avec 12K questions multi-domaine sélectionnées pour leur difficulté.
        # Substrat équivalent pour mesurer "reasoning structuré" (claim Briah).
        hf_repo="TIGER-Lab/MMLU-Pro",
        hf_subset=None,
        hf_split="test",
        target_size=200,
        requires_token=False,
        description="MMLU-Pro (substitut GPQA-Diamond, graduate reasoning, 200 of 12K)",
    ),
    DatasetSpec(
        name="alpacaeval",
        # HF resolve URL directe contournant le script loader obsolète :
        direct_url=(
            "https://huggingface.co/datasets/tatsu-lab/alpaca_eval/"
            "resolve/main/alpaca_eval.json"
        ),
        target_size=200,
        description="AlpacaEval 2.0 eval_set (200 of 805) via HF resolve URL",
    ),
]


@dataclass
class DatasetManifestEntry:
    """Entrée du manifest cache."""

    name: str
    hf_repo: str
    sha256: str
    rows: int
    size_bytes: int
    fetched_at: str
    file_path: str


def _sha256_of_file(path: Path) -> str:
    """Compute sha256 hex digest of a file."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    """Normaliser une row pour être JSON-serializable."""
    out: dict[str, Any] = {}
    for k, v in row.items():
        if isinstance(v, (str, int, float, bool)) or v is None:
            out[k] = v
        elif isinstance(v, list):
            out[k] = [
                x if isinstance(x, (str, int, float, bool)) or x is None else str(x)
                for x in v
            ]
        elif isinstance(v, dict):
            out[k] = _normalize_row(v)
        else:
            out[k] = str(v)
    return out


def _fetch_via_direct_url(url: str, target_size: int) -> list[dict[str, Any]] | None:
    """Fetch a JSON or JSONL file via direct URL (GitHub raw, etc.)."""
    import urllib.request
    import urllib.error

    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "etzchaim-bench/0.2.18"},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            content = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        print(f"  HTTP error {e.code}: {e.reason}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  Network error: {type(e).__name__}: {e}", file=sys.stderr)
        return None

    # Try JSON array first, then JSONL
    try:
        data = json.loads(content)
        if isinstance(data, list):
            return data[:target_size]
        if isinstance(data, dict):
            # Some datasets wrap in {'data': [...]}
            for key in ("data", "rows", "examples", "results"):
                if key in data and isinstance(data[key], list):
                    return data[key][:target_size]
            print(
                f"  Unknown JSON structure: keys={list(data.keys())[:5]}",
                file=sys.stderr,
            )
            return None
    except json.JSONDecodeError:
        # Try JSONL
        rows: list[dict[str, Any]] = []
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
            if len(rows) >= target_size:
                break
        return rows if rows else None

    return None


def fetch_dataset(spec: DatasetSpec) -> DatasetManifestEntry | None:
    """Fetch un dataset (HuggingFace ou URL directe) et le cacher localement.

    Returns:
        DatasetManifestEntry si succès, None si échec.
    """
    target_dir = CACHE_ROOT / spec.name
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / "data.jsonl"

    rows_taken: list[dict[str, Any]] | None = None
    source_label = ""

    # Stratégie 1 : HuggingFace si hf_repo défini
    if spec.hf_repo:
        from datasets import load_dataset
        from datasets.exceptions import DatasetNotFoundError

        source_label = f"HF:{spec.hf_repo}"
        print(f"[{spec.name}] Fetching {source_label}", file=sys.stderr)
        try:
            if spec.hf_subset:
                ds = load_dataset(
                    spec.hf_repo, spec.hf_subset, split=spec.hf_split
                )
            else:
                ds = load_dataset(spec.hf_repo, split=spec.hf_split)
            rows_taken = list(ds)[: spec.target_size]
            print(
                f"[{spec.name}] {len(rows_taken)} rows from HF "
                f"(target {spec.target_size}, total {len(ds)})",
                file=sys.stderr,
            )
        except DatasetNotFoundError as e:
            if spec.requires_token:
                print(
                    f"[{spec.name}] GATED dataset, requires HUGGINGFACE_HUB_TOKEN",
                    file=sys.stderr,
                )
            else:
                print(f"[{spec.name}] HF not found: {e}", file=sys.stderr)
        except Exception as e:
            print(
                f"[{spec.name}] HF fetch failed: {type(e).__name__}: {e}",
                file=sys.stderr,
            )

    # Stratégie 2 : URL directe (fallback ou primaire)
    if rows_taken is None and spec.direct_url:
        source_label = f"URL:{spec.direct_url[:60]}"
        print(f"[{spec.name}] Fetching {source_label}...", file=sys.stderr)
        rows_taken = _fetch_via_direct_url(spec.direct_url, spec.target_size)
        if rows_taken:
            print(
                f"[{spec.name}] {len(rows_taken)} rows from URL",
                file=sys.stderr,
            )

    if rows_taken is None or not rows_taken:
        print(f"[{spec.name}] FAILED — no source produced rows", file=sys.stderr)
        return None

    # Write to JSONL atomically (tmp + rename)
    tmp_file = target_file.with_suffix(".jsonl.tmp")
    with tmp_file.open("w") as f:
        for i, row in enumerate(rows_taken):
            normalized = _normalize_row(row)
            normalized["_bench_id"] = i  # stable ID for prompt referencing
            f.write(json.dumps(normalized, ensure_ascii=False) + "\n")
    tmp_file.replace(target_file)

    sha = _sha256_of_file(target_file)
    size = target_file.stat().st_size

    import datetime
    entry = DatasetManifestEntry(
        name=spec.name,
        hf_repo=spec.hf_repo,
        sha256=sha,
        rows=len(rows_taken),
        size_bytes=size,
        fetched_at=datetime.datetime.now(datetime.UTC).isoformat(),
        file_path=str(target_file),
    )
    print(f"[{spec.name}] OK sha={sha[:12]}... rows={entry.rows} size={size} bytes",
          file=sys.stderr)
    return entry


def update_manifest(entries: list[DatasetManifestEntry]) -> None:
    """Update the manifest file with fetched entries."""
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[str, dict] = {}
    if MANIFEST_PATH.exists():
        existing = json.loads(MANIFEST_PATH.read_text())

    for entry in entries:
        existing[entry.name] = asdict(entry)

    MANIFEST_PATH.write_text(json.dumps(existing, indent=2, ensure_ascii=False))
    print(f"\nManifest updated: {MANIFEST_PATH}", file=sys.stderr)


def verify_all() -> bool:
    """Verify sha256 of all cached datasets vs manifest."""
    if not MANIFEST_PATH.exists():
        print("No manifest found", file=sys.stderr)
        return False

    manifest = json.loads(MANIFEST_PATH.read_text())
    all_ok = True
    for name, entry in manifest.items():
        path = Path(entry["file_path"])
        if not path.exists():
            print(f"[{name}] MISSING: {path}", file=sys.stderr)
            all_ok = False
            continue
        actual_sha = _sha256_of_file(path)
        expected = entry["sha256"]
        if actual_sha != expected:
            print(
                f"[{name}] MISMATCH expected={expected[:12]} actual={actual_sha[:12]}",
                file=sys.stderr,
            )
            all_ok = False
        else:
            print(f"[{name}] OK ({entry['rows']} rows)", file=sys.stderr)

    return all_ok


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "names",
        nargs="*",
        help="Dataset names to fetch (default: all)",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify sha256 of cached datasets without fetching",
    )
    args = parser.parse_args()

    if args.verify:
        return 0 if verify_all() else 1

    targets = (
        [d for d in DATASETS if d.name in args.names]
        if args.names
        else DATASETS
    )

    if not targets:
        print(
            f"No datasets matched. Available: {[d.name for d in DATASETS]}",
            file=sys.stderr,
        )
        return 1

    entries: list[DatasetManifestEntry] = []
    failed: list[str] = []
    for spec in targets:
        entry = fetch_dataset(spec)
        if entry:
            entries.append(entry)
        else:
            failed.append(spec.name)

    if entries:
        update_manifest(entries)

    print(
        f"\n=== Summary ===\n  fetched: {len(entries)}\n  failed: {failed or 'none'}",
        file=sys.stderr,
    )

    return 0 if not failed else 2  # exit 2 = partial success


if __name__ == "__main__":
    sys.exit(main())
