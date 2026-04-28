"""Package run results into a portable tar.gz for replay/sharing.

Inclut :
- bench_state.json (atomic state)
- responses.jsonl (toutes les réponses arm × bench × prompt)
- report.md (markdown généré)
- *.png (plots)
- judgments.jsonl si présent (post-judging détaillé)

Excludes :
- cache/ (peut être très lourd, à part)

Usage :
    python -m benchmarks.package <run_dir> [--output bench.tar.gz]
"""

from __future__ import annotations

import argparse
import sys
import tarfile
import time
from pathlib import Path


INCLUDE_FILES = [
    "bench_state.json",
    "responses.jsonl",
    "judgments.jsonl",
    "report.md",
    "headline_scores.png",
    "ablation_delta.png",
]


def package_run(run_dir: Path, output_path: Path | None = None) -> Path:
    """Tar.gz le run_dir avec les fichiers essentiels."""
    if not run_dir.exists():
        raise FileNotFoundError(f"Run dir not found: {run_dir}")

    if output_path is None:
        ts = time.strftime("%Y-%m-%d_%H%M")
        output_path = run_dir.parent / f"{run_dir.name}_{ts}.tar.gz"

    files_added = 0
    with tarfile.open(output_path, "w:gz") as tar:
        for fname in INCLUDE_FILES:
            fpath = run_dir / fname
            if fpath.exists():
                tar.add(fpath, arcname=f"{run_dir.name}/{fname}")
                files_added += 1

    size_mb = output_path.stat().st_size / 1024 / 1024
    print(f"Packaged {files_added} files into {output_path} ({size_mb:.1f} MB)",
          file=sys.stderr)
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir")
    parser.add_argument("--output", "-o", default=None)
    args = parser.parse_args()

    try:
        output = package_run(Path(args.run_dir), Path(args.output) if args.output else None)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
