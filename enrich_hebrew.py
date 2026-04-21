#!/usr/bin/env python3
"""enrich_hebrew.py — Script de rétro-enrichissement des hebrew_word.

Usage:
    python enrich_hebrew.py --dry-run     # Rapport seulement
    python enrich_hebrew.py --apply       # Applique les modifications
    python enrich_hebrew.py --report      # Stats détaillées
    python enrich_hebrew.py --sample N    # Montre N exemples
"""

from __future__ import annotations

import argparse
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Rétro-enrichissement hebrew_word")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true",
                       help="Rapport seulement, aucune modification")
    group.add_argument("--apply", action="store_true",
                       help="Applique les modifications en DB")
    group.add_argument("--report", action="store_true",
                       help="Stats détaillées avant/après")
    group.add_argument("--sample", type=int, metavar="N",
                       help="Montre N exemples de résolution")
    parser.add_argument("--db-url", default="postgresql://localhost/etz_chaim")
    args = parser.parse_args()

    from kabbalah.hebrew_enrichment import HebrewEnrichment

    enricher = HebrewEnrichment(db_url=args.db_url)

    if args.sample:
        # Show sample resolutions
        enricher._load_vocabulary()
        null_concepts = enricher.get_null_concepts()
        print(f"\n{'concept':<40} {'hebrew':<25} {'source':<20} {'resolved'}")
        print("─" * 100)
        for concept in null_concepts[:args.sample]:
            r = enricher.find_hebrew(concept)
            hebrew = r.new_hebrew or "—"
            ratio = f"{r.tokens_resolved}/{r.tokens_total}"
            print(f"{r.concept:<40} {hebrew:<25} {r.source:<20} {ratio}")
        return

    if args.report or args.dry_run:
        stats = enricher.enrich_all(dry_run=True)
        _print_report(stats, enricher)
        return

    if args.apply:
        # First show what will happen
        stats = enricher.enrich_all(dry_run=True)
        _print_report(stats, enricher)
        print(f"\n{'='*60}")
        print(f"APPLYING {stats.enriched} enrichments...")
        print(f"{'='*60}\n")
        stats = enricher.enrich_all(dry_run=False)
        print(f"\nDone. Coverage: {stats.coverage_before:.1%} → {stats.coverage_after:.1%}")


def _print_report(stats, enricher):
    print(f"\n{'='*60}")
    print(f"  RAPPORT D'ENRICHISSEMENT HEBREW_WORD")
    print(f"{'='*60}")
    print(f"\n  Concepts sans hebrew_word : {stats.total_null}")
    print(f"  Enrichissables            : {stats.enriched}")
    print(f"  Non résolus               : {len(stats.failed)}")
    print(f"\n  Couverture avant : {stats.coverage_before:.1%}")
    print(f"  Couverture après : {stats.coverage_after:.1%}")
    print(f"\n  Par source :")
    for source, count in sorted(stats.by_source.items(), key=lambda x: -x[1]):
        print(f"    {source:<25} : {count:>4}")

    if stats.failed:
        print(f"\n  Non résolus ({len(stats.failed)}) :")
        for concept in sorted(stats.failed)[:50]:
            print(f"    - {concept}")
        if len(stats.failed) > 50:
            print(f"    ... et {len(stats.failed) - 50} autres")


if __name__ == "__main__":
    main()
