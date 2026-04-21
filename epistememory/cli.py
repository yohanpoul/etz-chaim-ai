"""Interface CLI — Malkuth-de-Yesod : le point d'entrée."""

from __future__ import annotations

import argparse
import sys

from .core import EpisteMemory


def cmd_introspect(mem: EpisteMemory) -> None:
    """Hod-de-Yesod : la mémoire se décrit elle-même."""
    stats = mem.introspect()
    print("═══ EpisteMemory — Introspection (Hod-de-Yesod) ═══")
    print(f"  Entrées totales    : {stats.total_entries}")
    print(f"  Entrées actives    : {stats.active_entries}")
    print(f"  Deprecated         : {stats.deprecated_entries}")
    print(f"  Confiance moyenne  : {stats.avg_confidence:.2f}")
    print(f"  Contradictions     : {stats.contradictions_open}")
    print(f"  Proches expiration : {stats.near_expiration}")
    if stats.by_status:
        print("  Par statut :")
        for s, c in sorted(stats.by_status.items()):
            print(f"    {s:20s} : {c}")
    if stats.by_domain:
        print("  Par domaine :")
        for d, c in sorted(stats.by_domain.items()):
            print(f"    {d:20s} : {c}")
    if stats.by_source:
        print("  Par source :")
        for s, c in sorted(stats.by_source.items()):
            print(f"    {s:20s} : {c}")


def cmd_remember(mem: EpisteMemory, args: argparse.Namespace) -> None:
    entry_id = mem.remember(
        content=args.content,
        source_sephirah=args.source,
        confidence=args.confidence,
        domain=args.domain,
        ttl_days=args.ttl,
    )
    print(f"Stored: {entry_id}")


def cmd_recall(mem: EpisteMemory, args: argparse.Namespace) -> None:
    results = mem.recall(
        query=args.query,
        min_confidence=args.min_confidence,
        domain=args.domain,
        limit=args.limit,
    )
    if not results:
        print("No results.")
        return
    for i, entry in enumerate(results, 1):
        sim = f"{entry.similarity:.3f}" if entry.similarity is not None else "?"
        warn = f" ⚠ {entry.warning}" if entry.warning else ""
        print(
            f"[{i}] {entry.epistemic_status.value} ({entry.confidence:.2f}) "
            f"sim={sim} [{entry.source_sephirah.value}]{warn}"
        )
        print(f"    {entry.content[:120]}")
        print(f"    id={entry.id}")
        print()


def cmd_gc(mem: EpisteMemory) -> None:
    report = mem.gc()
    print("═══ Gevurah-de-Yesod — Garbage Collection ═══")
    print(f"  Expired   : {report.expired_count}")
    print(f"  Deprecated: {report.deprecated_count}")
    print(f"  Removed   : {report.total_removed}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="epistememory", description="EpisteMemory CLI")
    parser.add_argument("--db", default="postgresql://localhost/etz_chaim")
    parser.add_argument("--model", default="nomic-embed-text")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("introspect", help="Hod-de-Yesod : stats")

    p_rem = sub.add_parser("remember", help="Store an entry")
    p_rem.add_argument("content")
    p_rem.add_argument("--source", default="external")
    p_rem.add_argument("--confidence", type=float, default=0.5)
    p_rem.add_argument("--domain", default=None)
    p_rem.add_argument("--ttl", type=int, default=None)

    p_rec = sub.add_parser("recall", help="Search memory")
    p_rec.add_argument("query")
    p_rec.add_argument("--min-confidence", type=float, default=0.0)
    p_rec.add_argument("--domain", default=None)
    p_rec.add_argument("--limit", type=int, default=5)

    sub.add_parser("gc", help="Gevurah: garbage collection")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    mem = EpisteMemory(db_url=args.db, embedding_model=args.model)
    try:
        if args.command == "introspect":
            cmd_introspect(mem)
        elif args.command == "remember":
            cmd_remember(mem, args)
        elif args.command == "recall":
            cmd_recall(mem, args)
        elif args.command == "gc":
            cmd_gc(mem)
    finally:
        mem.close()


if __name__ == "__main__":
    main()
