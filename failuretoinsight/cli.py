"""CLI — Malkuth du sentier Lamed."""

from __future__ import annotations

import argparse
import sys

from failuretoinsight.core import FailureToInsight

DEFAULT_DB_URL = "postgresql://localhost/etz_chaim"


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        prog="failuretoinsight",
        description="Sentier Lamed — transformer l'échec en connaissance",
    )
    parser.add_argument(
        "--db", default=DEFAULT_DB_URL, help="Database URL"
    )
    sub = parser.add_subparsers(dest="command")

    # analyze
    p_analyze = sub.add_parser("analyze", help="Analyser un échec")
    p_analyze.add_argument("description", help="Description de l'échec")
    p_analyze.add_argument("--source-type", default="external")
    p_analyze.add_argument("--domain")

    # report
    sub.add_parser("report", help="Rapport du sentier Lamed")

    # graph
    p_graph = sub.add_parser("graph", help="Construire le graphe des échecs")
    p_graph.add_argument("--domain")

    # guide
    p_guide = sub.add_parser("guide", help="Guidance pour prochaine hypothèse")
    p_guide.add_argument("--domain")

    # diagnose
    sub.add_parser("diagnose", help="Auto-diagnostic du sentier")

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return

    fti = FailureToInsight(db_url=args.db)

    if args.command == "analyze":
        analysis = fti.analyze_failure(
            description=args.description,
            source_type=args.source_type,
            domain=args.domain,
        )
        print(f"Analysis {analysis.id}")
        print(f"  Qliphah: {analysis.qliphah}")
        print(f"  Severity: {analysis.severity}")
        if analysis.root_cause:
            print(f"  Root cause: {analysis.root_cause}")

    elif args.command == "report":
        print(fti.report())

    elif args.command == "graph":
        graph = fti.build_failure_graph(domain=args.domain)
        print(f"Analyses: {len(graph.analyses)}")
        print(f"Edges: {len(graph.edges)}")
        print(f"Most common qliphah: {graph.most_common_qliphah}")
        print(f"Domains: {', '.join(graph.domains_affected) or 'none'}")

    elif args.command == "guide":
        guidance = fti.guide_next_hypothesis(domain=args.domain)
        print(f"Avoid: {', '.join(guidance.avoid_patterns) or 'none'}")
        print(f"Promising: {', '.join(guidance.promising_directions) or 'none'}")
        print(f"Recurring causes: {', '.join(guidance.recurring_root_causes) or 'none'}")
        print(f"Confidence: {guidance.confidence:.0%}")

    elif args.command == "diagnose":
        diag = fti.self_diagnose()
        print(f"Level: {diag['level']}")
        for issue in diag["issues"]:
            print(f"  - {issue}")

    fti.db.close()


if __name__ == "__main__":
    main()
