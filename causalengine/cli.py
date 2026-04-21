"""CLI pour CausalEngine — Malkuth de Binah."""

from __future__ import annotations

import argparse
import os
import sys


def get_db_url() -> str:
    return os.environ.get(
        "ETZ_CHAIM_DB_URL",
        "postgresql://postgres@localhost:5432/etz_chaim",
    )


def cmd_check(args):
    from causalengine.core import CausalEngine
    engine = CausalEngine(db_url=get_db_url())
    assessment = engine.check_claim(
        cause=args.cause,
        effect=args.effect,
        domain=args.domain,
    )
    print(f"Claim: {args.cause} → {args.effect}")
    print(f"Evidence: {assessment.claim.evidence_level}")
    print(f"Pearl level: {assessment.pearl_level}")
    print(f"Confidence: {assessment.claim.confidence}")
    print(f"Direction: {assessment.direction.verdict}")
    print(f"Confounders: {len(assessment.confounders)}")
    for c in assessment.confounders:
        ctrl = "✓" if c.controlled else "✗"
        print(f"  [{ctrl}] {c.confounder_name} (plausibility: {c.plausibility})")
    if assessment.language_correction:
        lc = assessment.language_correction
        print(f"\nLanguage: '{lc.original}' → '{lc.corrected}'")
        print(f"  Reason: {lc.reason}")
    if assessment.warnings:
        print("\nWarnings:")
        for w in assessment.warnings:
            print(f"  ⚠ {w}")


def cmd_build(args):
    from causalengine.core import CausalEngine
    from causalengine.models import CausalEdge, CausalNode
    engine = CausalEngine(db_url=get_db_url())

    # Parse nodes: "a:NodeA,b:NodeB"
    nodes = []
    for pair in args.nodes.split(","):
        nid, name = pair.split(":")
        nodes.append(CausalNode(node_id=nid.strip(), name=name.strip()))

    # Parse edges: "a->b,b->c"
    edges = []
    for pair in args.edges.split(","):
        src, tgt = pair.split("->")
        edges.append(CausalEdge(source=src.strip(), target=tgt.strip()))

    graph = engine.build_causal_graph(
        name=args.name,
        nodes=nodes,
        edges=edges,
        domain=args.domain,
    )
    print(f"Graph: {graph.name}")
    print(f"Nodes: {len(graph.nodes)}")
    print(f"Edges: {len(graph.edges)}")
    print(f"Pearl level: {graph.evidence_level}")
    print(f"Confounders checked: {graph.confounders_checked}")


def cmd_confounders(args):
    from causalengine.core import CausalEngine
    engine = CausalEngine(db_url=get_db_url())
    confounders = engine.detect_confounders(
        cause=args.cause,
        effect=args.effect,
        domain=args.domain,
    )
    print(f"Confounders for '{args.cause}' → '{args.effect}' [{args.domain}]:")
    for c in confounders:
        ctrl = "✓" if c.controlled else "✗"
        print(f"  [{ctrl}] {c.confounder_name} (plausibility: {c.plausibility})")


def cmd_language(args):
    from causalengine.core import CausalEngine
    engine = CausalEngine(db_url=get_db_url())
    corrected, corrections = engine.enforce_language(
        text=args.text,
        evidence_level=args.level,
    )
    if not corrections:
        print("No corrections needed.")
    else:
        print(f"Original:  {args.text}")
        print(f"Corrected: {corrected}")
        print(f"\nCorrections ({len(corrections)}):")
        for c in corrections:
            print(f"  '{c.original}' → '{c.corrected}'")
            print(f"    {c.reason}")


def cmd_diagnose(args):
    from causalengine.core import CausalEngine
    engine = CausalEngine(db_url=get_db_url())
    diag = engine.self_diagnose()
    print(f"Level: {diag['level']}")
    for issue in diag["issues"]:
        print(f"  - {issue}")


def cmd_report(args):
    from causalengine.core import CausalEngine
    engine = CausalEngine(db_url=get_db_url())
    print(engine.report())


def main():
    parser = argparse.ArgumentParser(description="CausalEngine — Binah CLI")
    sub = parser.add_subparsers(dest="command")

    p_check = sub.add_parser("check", help="Check a causal claim")
    p_check.add_argument("cause", help="Cause variable")
    p_check.add_argument("effect", help="Effect variable")
    p_check.add_argument("--domain", default="", help="Domain")
    p_check.set_defaults(func=cmd_check)

    p_build = sub.add_parser("build", help="Build a causal DAG")
    p_build.add_argument("--name", required=True, help="Graph name")
    p_build.add_argument("--nodes", required=True, help="Nodes (id:name,...)")
    p_build.add_argument("--edges", required=True, help="Edges (src->tgt,...)")
    p_build.add_argument("--domain", default="", help="Domain")
    p_build.set_defaults(func=cmd_build)

    p_conf = sub.add_parser("confounders", help="Detect confounders")
    p_conf.add_argument("cause", help="Cause variable")
    p_conf.add_argument("effect", help="Effect variable")
    p_conf.add_argument("--domain", default="", help="Domain")
    p_conf.set_defaults(func=cmd_confounders)

    p_lang = sub.add_parser("language", help="Enforce causal language")
    p_lang.add_argument("text", help="Text to check")
    p_lang.add_argument("--level", default="correlation_only", help="Evidence level")
    p_lang.set_defaults(func=cmd_language)

    p_diag = sub.add_parser("diagnose", help="Run self-diagnosis (Anti-Satariel)")
    p_diag.set_defaults(func=cmd_diagnose)

    p_report = sub.add_parser("report", help="Show CausalEngine report")
    p_report.set_defaults(func=cmd_report)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
