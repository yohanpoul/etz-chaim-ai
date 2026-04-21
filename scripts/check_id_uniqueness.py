"""Scan YAML corpus for duplicate EC-* and Z-* assertion IDs.

Sprint 10 §12.0.d : garde contre collisions lors de batches parallèles.

Usage:
    python scripts/check_id_uniqueness.py sifrei_yesod/sefarim/
    python scripts/check_id_uniqueness.py sifrei_yesod/sefarim/ --prefix Z-IR,EC-H3S2

Known pre-Sprint 10 duplicates (résolus Sprint 10 Phase G) :
    - EC-H1S1-079 : perek_03 + perek_04a (Heikhal 1 Shaar 1 igulim)
      FIXED 2026-04-20 : perek_04a renommé en EC-H1S1-079b (Phase G.5).
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

import yaml

KNOWN_PREEXISTING_DUPLICATES: set[str] = set()


def scan_ids(root: Path) -> dict[str, list[Path]]:
    """Return {id: [files where seen]}."""
    seen: dict[str, list[Path]] = defaultdict(list)
    for yaml_path in root.rglob("*.yaml"):
        try:
            with yaml_path.open("r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
        except (OSError, yaml.YAMLError):
            continue
        assertions = (data or {}).get("assertions", []) or []
        for a in assertions:
            if isinstance(a, dict) and "id" in a:
                seen[a["id"]].append(yaml_path)
    return seen


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", help="Directory to scan recursively")
    parser.add_argument(
        "--prefix",
        default=None,
        help="Only check IDs matching one of these comma-separated prefixes",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail even on known pre-Sprint 10 duplicates",
    )
    args = parser.parse_args(argv[1:])

    root = Path(args.root)
    if not root.exists():
        print(f"Path does not exist: {root}", file=sys.stderr)
        return 2

    seen = scan_ids(root)

    if args.prefix:
        prefixes = tuple(p.strip() for p in args.prefix.split(",") if p.strip())
        seen = {k: v for k, v in seen.items() if k.startswith(prefixes)}

    duplicates = {k: v for k, v in seen.items() if len(v) > 1}

    unknown_duplicates = {
        k: v for k, v in duplicates.items()
        if args.strict or k not in KNOWN_PREEXISTING_DUPLICATES
    }

    if unknown_duplicates:
        print("Duplicate IDs detected:")
        for k, files in sorted(unknown_duplicates.items()):
            print(f"  {k}: {len(files)} occurrences")
            for f in files:
                print(f"    - {f}")
        return 1

    if duplicates:
        print(f"Known pre-Sprint 10 duplicates (ignored): {sorted(duplicates)}")

    scope = f" matching prefix {args.prefix}" if args.prefix else ""
    print(f"All {len(seen)} IDs{scope} are unique under {root}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
