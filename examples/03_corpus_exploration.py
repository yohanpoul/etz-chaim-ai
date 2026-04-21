"""Corpus exploration — five ways to query the doctrinal corpus.

Usage:
    python examples/03_corpus_exploration.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bridge import (  # noqa: E402
    load_all_ids,
    load_by_concept,
    load_by_module,
    load_by_partzuf,
    search,
)


def main() -> None:
    print("=== Etz Chaim AI — corpus exploration ===\n")

    all_ids = load_all_ids()
    print(f"Total indexed items : {len(all_ids)}\n")

    ec_count = sum(1 for i in all_ids if i.startswith("EC-"))
    z_count = sum(1 for i in all_ids if i.startswith("Z-"))
    rel_count = sum(1 for i in all_ids if i.startswith("REL-"))
    pg_count = sum(1 for i in all_ids if i.startswith("PG-"))
    print(f"  EC-*  (Etz Chaim / Vital) : {ec_count}")
    print(f"  Z-*   (Zohar)             : {z_count}")
    print(f"  REL-* (relations)         : {rel_count}")
    print(f"  PG-*  (generative princ.) : {pg_count}\n")

    print("Concept 'notzer_chesed' appears in:")
    for a in load_by_concept("notzer_chesed"):
        print(f"  - {a['id']} ({a['source_ref']})")

    print("\nAssertions mapping to partzufim/arikh_anpin.py:")
    for a in load_by_module("partzufim/arikh_anpin.py")[:5]:
        print(f"  - {a['id']}")

    print("\nAssertions citing partzuf 'abba':")
    for a in load_by_partzuf("abba")[:5]:
        print(f"  - {a['id']}")

    print("\nSearch 'mazal elyon' (first 5 hits):")
    for a in search("mazal elyon")[:5]:
        print(f"  - {a['id']} ({a['source_ref']})")


if __name__ == "__main__":
    main()
