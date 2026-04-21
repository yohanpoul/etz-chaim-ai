"""CLI pour InsightForge — Malkuth de Chokmah."""

from __future__ import annotations

import argparse
import os


def get_db_url() -> str:
    return os.environ.get(
        "ETZ_CHAIM_DB_URL",
        "postgresql://postgres@localhost:5432/etz_chaim",
    )


def cmd_forge(args):
    from insightforge.core import InsightForge
    forge = InsightForge(db_url=get_db_url())
    session = forge.forge(
        question=args.question,
        domain=args.domain,
        max_explore=args.max_explore,
    )
    print(f"Question: {session.question}")
    print(f"Domain: {session.domain or '(general)'}")
    print(f"Modules consulted: {', '.join(session.modules_consulted)}")
    print(f"Total candidates: {session.total_candidates}")
    print(f"Insights found: {session.insights_found}")
    print(f"Rejected: {session.rejected_count}")
    print(f"Pearl level: {session.pearl_level}")
    print(f"Status: {session.status}")

    if session.validated_insights:
        print("\nInsights:")
        for i, insight in enumerate(session.validated_insights, 1):
            triple = (
                insight.binah_validated
                and insight.gevurah_validated
                and insight.daat_validated
            )
            mark = "[3V]" if triple else "[  ]"
            print(
                f"  {i}. {mark} {insight.description[:80]} "
                f"(novelty: {insight.novelty_score}, "
                f"confidence: {insight.confidence})"
            )

    if session.emergence_signals:
        print("\nEmergence signals:")
        for sig in session.emergence_signals:
            print(
                f"  [{sig.signal_type}] {sig.description[:60]} "
                f"(strength: {sig.strength})"
            )

    forge.close()


def cmd_assess(args):
    from insightforge.core import InsightForge
    from insightforge.models import CandidateInsight
    forge = InsightForge(db_url=get_db_url())

    candidate = CandidateInsight(
        description=args.description,
        domain=args.domain,
        confidence=args.confidence,
        connects_domains=args.domains.split(",") if args.domains else [],
    )
    result = forge.assess_novelty(candidate)

    print(f"Description: {args.description}")
    print(f"Genuinely new: {result.is_genuinely_new}")
    print(f"Novelty score: {result.novelty_score}")
    print(f"Already known: {result.already_known}")
    print(f"Reformulation: {result.is_reformulation}")
    print(f"Trivial: {result.is_trivial}")
    print(f"Cross-domain: {result.is_cross_domain}")
    print(f"Reasoning: {result.reasoning}")

    forge.close()


def cmd_validate(args):
    from insightforge.core import InsightForge
    from insightforge.models import CandidateInsight
    forge = InsightForge(db_url=get_db_url())

    candidate = CandidateInsight(
        description=args.description,
        domain=args.domain,
        confidence=args.confidence,
        connects_domains=args.domains.split(",") if args.domains else [],
    )
    result = forge.validate_insight(candidate, domain=args.domain)

    print(f"Description: {args.description}")
    print(f"Valid: {result.is_valid}")
    print(f"Triple validated: {result.triple_validated}")
    print(f"Binah: {'OK' if result.binah_ok else 'FAIL'} — {result.binah_detail}")
    print(f"Gevurah: {'OK' if result.gevurah_ok else 'FAIL'} — {result.gevurah_detail}")
    print(f"Da'at: {'OK' if result.daat_ok else 'FAIL'} — {result.daat_detail}")
    print(f"Confidence: {result.confidence}")

    forge.close()


def cmd_diagnose(args):
    from insightforge.core import InsightForge
    forge = InsightForge(db_url=get_db_url())
    diag = forge.self_diagnose()
    print(f"Level: {diag['level']}")
    for issue in diag["issues"]:
        print(f"  - {issue}")
    forge.close()


def cmd_report(args):
    from insightforge.core import InsightForge
    forge = InsightForge(db_url=get_db_url())
    print(forge.report())
    forge.close()


def main():
    parser = argparse.ArgumentParser(
        description="InsightForge — Chokmah CLI",
    )
    sub = parser.add_subparsers(dest="command")

    p_forge = sub.add_parser("forge", help="Forge insights from a question")
    p_forge.add_argument("question", help="The question to explore")
    p_forge.add_argument("--domain", default="", help="Domain context")
    p_forge.add_argument(
        "--max-explore", type=int, default=10, help="Max exploration",
    )
    p_forge.set_defaults(func=cmd_forge)

    p_assess = sub.add_parser("assess", help="Assess novelty of a candidate")
    p_assess.add_argument("description", help="Candidate insight description")
    p_assess.add_argument("--domain", default="", help="Domain")
    p_assess.add_argument(
        "--confidence", type=float, default=0.5, help="Confidence",
    )
    p_assess.add_argument("--domains", default="", help="Connected domains (a,b)")
    p_assess.set_defaults(func=cmd_assess)

    p_val = sub.add_parser("validate", help="Triple-validate a candidate")
    p_val.add_argument("description", help="Candidate insight description")
    p_val.add_argument("--domain", default="", help="Domain")
    p_val.add_argument(
        "--confidence", type=float, default=0.5, help="Confidence",
    )
    p_val.add_argument("--domains", default="", help="Connected domains (a,b)")
    p_val.set_defaults(func=cmd_validate)

    p_diag = sub.add_parser(
        "diagnose", help="Run self-diagnosis (Anti-Ghagiel)",
    )
    p_diag.set_defaults(func=cmd_diagnose)

    p_report = sub.add_parser("report", help="Show InsightForge report")
    p_report.set_defaults(func=cmd_report)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
