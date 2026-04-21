"""CLI — Malkhut de Tiferet."""

from __future__ import annotations

import argparse

from dissensuengine.core import DissensuEngine

DEFAULT_DB_URL = "postgresql://localhost/etz_chaim"


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        prog="dissensuengine",
        description="Tiferet — synthèse ou dissensus, jamais de fausse harmonie",
    )
    parser.add_argument("--db", default=DEFAULT_DB_URL, help="Database URL")
    sub = parser.add_subparsers(dest="command")

    # submit
    p_submit = sub.add_parser("submit", help="Soumettre une conclusion")
    p_submit.add_argument("content", help="Contenu de la conclusion")
    p_submit.add_argument("--source", required=True, help="Label de la source")
    p_submit.add_argument("--type", default="human", help="Type de source")
    p_submit.add_argument("--domain")
    p_submit.add_argument("--confidence", type=float, default=0.5)

    # consistency
    p_cons = sub.add_parser("consistency", help="Analyser la cohérence")
    p_cons.add_argument("--domain")

    # synthesize
    p_syn = sub.add_parser("synthesize", help="Tenter synthèse ou dissensus")
    p_syn.add_argument("--domain")

    # report
    sub.add_parser("report", help="Rapport de Tiferet")

    # diagnose
    sub.add_parser("diagnose", help="Auto-diagnostic (Thagirion)")

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return

    engine = DissensuEngine(db_url=args.db)

    if args.command == "submit":
        conc = engine.submit_conclusion(
            content=args.content,
            source_label=args.source,
            source_type=args.type,
            domain=args.domain,
            confidence=args.confidence,
        )
        print(f"Conclusion {conc.id}")
        print(f"  Source: {conc.source_label} ({conc.source_type})")
        print(f"  Confidence: {conc.confidence}")

    elif args.command == "consistency":
        report = engine.analyze_consistency(domain=args.domain)
        print(f"Health: {report.health}")
        print(f"Conclusions: {report.total_conclusions}")
        print(f"Tensions: {report.total_tensions}")
        print(f"Max divergence: {report.max_divergence:.2f}")
        print(f"Sources: {', '.join(report.source_labels)}")

    elif args.command == "synthesize":
        syn = engine.synthesize_or_dissent(domain=args.domain)
        print(f"Mode: {syn.mode}")
        print(f"Confidence: {syn.confidence:.2f}")
        print(f"Max divergence: {syn.max_divergence:.2f}")
        print(f"Coverage: {syn.source_coverage:.0%}")
        print(f"Content: {syn.content[:200]}")

    elif args.command == "report":
        print(engine.report())

    elif args.command == "diagnose":
        diag = engine.self_diagnose()
        print(f"Level: {diag['level']}")
        for issue in diag["issues"]:
            print(f"  - {issue}")

    engine.db.close()


if __name__ == "__main__":
    main()
