"""CLI — Malkhut-de-Netzach : l'interface avec le monde."""

from __future__ import annotations

import argparse
import sys
from uuid import UUID

from intentkeeper.core import IntentKeeper

DB_URL = "dbname=etz_chaim"


def main():
    parser = argparse.ArgumentParser(
        description="IntentKeeper — Tikkun de Netzach"
    )
    sub = parser.add_subparsers(dest="command")

    # set
    p_set = sub.add_parser("set", help="Définir une nouvelle intention")
    p_set.add_argument("goal", help="But de haut niveau")
    p_set.add_argument("--max-days", type=int, default=90)
    p_set.add_argument("--abandon-threshold", type=float, default=0.2)

    # report
    p_report = sub.add_parser("report", help="Rapport de progrès")
    p_report.add_argument("intention_id", type=UUID)

    # abandon-check
    p_abandon = sub.add_parser("abandon-check", help="Vérifier le critère d'abandon")
    p_abandon.add_argument("intention_id", type=UUID)

    # list
    sub.add_parser("list", help="Lister les intentions actives")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    ik = IntentKeeper(DB_URL)

    if args.command == "set":
        intention = ik.set_intention(
            goal=args.goal,
            max_duration_days=args.max_days,
            abandon_threshold=args.abandon_threshold,
        )
        print(f"Intention created: {intention.id}")
        print(f"  Goal: {intention.goal}")
        print(f"  Deadline: {intention.deadline_at}")

    elif args.command == "report":
        print(ik.report(args.intention_id))

    elif args.command == "abandon-check":
        decision = ik.should_abandon(args.intention_id)
        print(f"Level: {decision.level}")
        print(f"Should abandon: {decision.should_abandon}")
        if decision.reason:
            print(f"Reason: {decision.reason}")

    elif args.command == "list":
        intentions = ik.db.get_active_intentions()
        if not intentions:
            print("No active intentions.")
        for i in intentions:
            print(f"  [{i.id}] {i.goal} — {i.progress:.0%} — v{i.strategy_version}")


if __name__ == "__main__":
    main()
