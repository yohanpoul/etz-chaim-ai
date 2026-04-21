"""Quickstart — load a primary-source doctrinal assertion.

Zero external dependencies beyond the project's `bridge` package.

Usage:
    python examples/01_quickstart.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bridge import load_all_ids, load_assertion, search  # noqa: E402


def main() -> None:
    print("=== Etz Chaim AI — quickstart example ===\n")

    # Direct load by canonical ID.
    a = load_assertion("EC-K5-001")
    if a is None:
        print("EC-K5-001 not found. Is `sifrei_yesod/sefarim/` present?")
        return

    print(f"ID              : {a['id']}")
    print(f"Source ref      : {a['source_ref']}")
    print(f"Type            : {a.get('type')}")
    print()
    print("Assertion (first 300 chars):")
    print(a["assertion"][:300].strip())
    print()

    # Corpus size.
    ids = load_all_ids()
    print(f"Total items indexed : {len(ids)}")

    # Simple search.
    print()
    print("Assertions matching 'notzer':")
    for hit in search("notzer")[:5]:
        print(f"  - {hit['id']} ({hit['source_ref']})")


if __name__ == "__main__":
    main()
