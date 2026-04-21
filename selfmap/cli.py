"""Interface CLI — Malkuth-de-Hod."""

from __future__ import annotations

import argparse
import sys

from .core import SelfMap

from olamot import get_model


def _get_default_model():
    return get_model("yetzirah")


def _get_judge_model():
    return get_model("yetzirah")


def cmd_eval(sm: SelfMap, args: argparse.Namespace) -> None:
    """Évaluer un modèle sur un domaine."""
    model = args.model or sm.default_model
    print(f"Évaluation de {model} sur '{args.domain}'...")
    score = sm.eval_domain(args.domain, model_id=model)
    print(f"  Score       : {score.score:.2f} ({score.n_evals} questions)")
    print(f"  Brier       : {score.brier_score:.3f}")
    if score.eval_results:
        print("  Détail :")
        for r in score.eval_results:
            mark = "✓" if r.correct else "✗"
            print(f"    {mark} {r.question}")
            print(f"      attendu: {r.expected} | reçu: {r.actual}")


def cmd_route(sm: SelfMap, args: argparse.Namespace) -> None:
    """Router une requête."""
    decision = sm.route(args.query)
    if decision.did_decline:
        print(f"DÉCLINÉ — {decision.decline_reason}")
    else:
        print(f"Domaine  : {decision.detected_domain}")
        print(f"Modèle   : {decision.routed_to}")
        print(f"Score    : {decision.competence_score:.2f}")


def cmd_describe(sm: SelfMap) -> None:
    """Hod-de-Hod : auto-description."""
    desc = sm.describe_self()
    print("═══ SelfMap — Auto-description (Hod-de-Hod) ═══")
    print(f"  Modèle           : {desc.model_id}")
    print(f"  Domaines évalués : {desc.evaluated_domains}/{desc.total_domains}")
    print(f"  Compétence moy.  : {desc.avg_competence:.2f}")
    print(f"  Brier moyen      : {desc.avg_brier:.3f}")
    print(f"  Requêtes routées : {desc.total_queries_routed}")
    print(f"  Déclinées        : {desc.total_declined} ({desc.decline_rate:.0%})")
    if desc.strong_domains:
        print(f"  Forces           : {', '.join(desc.strong_domains)}")
    if desc.weak_domains:
        print(f"  Faiblesses       : {', '.join(desc.weak_domains)}")


def cmd_calibrate(sm: SelfMap) -> None:
    """Rapport de calibration."""
    report = sm.calibrate()
    print("═══ SelfMap — Calibration ═══")
    print(f"  Brier moyen : {report.avg_brier:.3f}")
    if report.by_domain:
        print("  Par domaine :")
        for d, b in sorted(report.by_domain.items()):
            print(f"    {d:20s} : {b:.3f}")
    if report.overconfident_domains:
        print(f"  ⚠ Sur-confiance : {', '.join(report.overconfident_domains)}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="selfmap", description="SelfMap CLI")
    parser.add_argument("--db", default="postgresql://localhost/etz_chaim")
    parser.add_argument("--model", default=None)
    parser.add_argument("--judge", default=None)
    sub = parser.add_subparsers(dest="command")

    p_eval = sub.add_parser("eval", help="Évaluer un domaine")
    p_eval.add_argument("domain")
    p_eval.add_argument("--model", default=None)

    p_route = sub.add_parser("route", help="Router une requête")
    p_route.add_argument("query")

    sub.add_parser("describe", help="Auto-description")
    sub.add_parser("calibrate", help="Rapport de calibration")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    sm = SelfMap(
        db_url=args.db,
        default_model=args.model or _get_default_model(),
        judge_model=args.judge or _get_judge_model(),
    )
    try:
        if args.command == "eval":
            cmd_eval(sm, args)
        elif args.command == "route":
            cmd_route(sm, args)
        elif args.command == "describe":
            cmd_describe(sm)
        elif args.command == "calibrate":
            cmd_calibrate(sm)
    finally:
        sm.close()


if __name__ == "__main__":
    main()
