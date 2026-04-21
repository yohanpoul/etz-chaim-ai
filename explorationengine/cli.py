"""CLI pour ExplorationEngine — Malkuth de Chesed."""

from __future__ import annotations

import argparse
import os
import sys


def get_db_url() -> str:
    return os.environ.get(
        "ETZ_CHAIM_DB_URL",
        "postgresql://postgres@localhost:5432/etz_chaim",
    )


def cmd_explore(args):
    from explorationengine.core import ExplorationEngine
    engine = ExplorationEngine(db_url=get_db_url())
    targets = args.domains.split(",") if args.domains else None
    result = engine.explore(
        query=args.query,
        seed_domain=args.seed,
        target_domains=targets,
        max_connections=args.max,
    )
    print(f"Status: {result.status}")
    print(f"Connections: {result.total_connections} ({result.novel_connections} novel)")
    print(f"Avg novelty: {result.avg_novelty:.2f}")
    for c in result.connections:
        print(f"  [{c.connection_type}] {c.domain_a}→{c.domain_b}: {c.description[:80]}")


def cmd_analogies(args):
    from explorationengine.core import ExplorationEngine
    engine = ExplorationEngine(db_url=get_db_url())
    targets = args.domains.split(",") if args.domains else None
    conns = engine.find_analogies(args.concept, args.source, targets)
    for c in conns:
        print(f"  [{c.domain_a}→{c.domain_b}] {c.description[:100]}")


def cmd_walk(args):
    from explorationengine.core import ExplorationEngine
    engine = ExplorationEngine(db_url=get_db_url())
    conns = engine.serendipity_walk(args.start, args.domain, args.steps)
    for c in conns:
        print(f"  [{c.connection_type}] {c.domain_a}→{c.domain_b}: {c.description[:80]}")


def cmd_diagnose(args):
    from explorationengine.core import ExplorationEngine
    engine = ExplorationEngine(db_url=get_db_url())
    diag = engine.self_diagnose()
    print(f"Level: {diag['level']}")
    for issue in diag["issues"]:
        print(f"  - {issue}")


def cmd_report(args):
    from explorationengine.core import ExplorationEngine
    engine = ExplorationEngine(db_url=get_db_url())
    print(engine.report())


def main():
    parser = argparse.ArgumentParser(description="ExplorationEngine — Chesed CLI")
    sub = parser.add_subparsers(dest="command")

    p_explore = sub.add_parser("explore", help="Explore inter-domain connections")
    p_explore.add_argument("query", help="Seed query")
    p_explore.add_argument("--seed", required=True, help="Seed domain")
    p_explore.add_argument("--domains", default=None, help="Target domains (comma-separated)")
    p_explore.add_argument("--max", type=int, default=50, help="Max connections")
    p_explore.set_defaults(func=cmd_explore)

    p_analogy = sub.add_parser("analogies", help="Find structural analogies")
    p_analogy.add_argument("concept", help="Source concept")
    p_analogy.add_argument("--source", required=True, help="Source domain")
    p_analogy.add_argument("--domains", default=None, help="Target domains")
    p_analogy.set_defaults(func=cmd_analogies)

    p_walk = sub.add_parser("walk", help="Serendipity walk")
    p_walk.add_argument("start", help="Starting concept")
    p_walk.add_argument("--domain", required=True, help="Starting domain")
    p_walk.add_argument("--steps", type=int, default=5, help="Number of steps")
    p_walk.set_defaults(func=cmd_walk)

    p_diag = sub.add_parser("diagnose", help="Run self-diagnosis")
    p_diag.set_defaults(func=cmd_diagnose)

    p_report = sub.add_parser("report", help="Show exploration report")
    p_report.set_defaults(func=cmd_report)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
