"""Point d'entrée CLI pour le module Malakhim.

Usage:
    python -m malakhim "Analyse ce texte"
    python -m malakhim "Résous ce problème" --nature strategic
    python -m malakhim --debt-report
"""

import argparse
import json
import sys

from malakhim.memuneh.router import Memuneh
from malakhim.pekidah.registry import PekidahRegistry


def main():
    parser = argparse.ArgumentParser(
        description="Malakhim — agents éphémères mono-mission"
    )
    parser.add_argument("prompt", nargs="?", help="Mission à exécuter")
    parser.add_argument(
        "--nature",
        choices=["strategic", "analytic", "execution", "mechanic"],
        help="Forcer la nature ontologique",
    )
    parser.add_argument("--budget", type=int, default=0, help="Budget max tokens")
    parser.add_argument(
        "--classify-only", action="store_true", help="Classifier sans exécuter"
    )
    parser.add_argument(
        "--debt-report", action="store_true", help="Afficher le rapport de dette"
    )
    args = parser.parse_args()

    registry = PekidahRegistry()
    memuneh = Memuneh(registry=registry)

    if args.debt_report:
        from malakhim.kategor.debt import get_debt_report

        report = get_debt_report(registry)
        print(
            json.dumps(
                {
                    "total_active": report.total_active,
                    "by_domain": report.by_domain,
                    "by_error_type": report.by_error_type,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return

    if not args.prompt:
        parser.print_help()
        sys.exit(1)

    kavvanah = {}
    if args.nature:
        kavvanah["nature"] = args.nature

    if args.classify_only:
        nature = memuneh.classify_nature(args.prompt, kavvanah)
        decision = memuneh.route(args.prompt, kavvanah, args.budget)
        print(
            json.dumps(
                {
                    "nature": nature,
                    "olam": decision.olam,
                    "model": decision.model,
                    "provider": decision.provider,
                    "masakh_level": decision.masakh_level,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return

    result = memuneh.dispatch(args.prompt, kavvanah)
    print(
        json.dumps(
            {
                "response": result.response,
                "success": result.success,
                "score": result.score,
                "warnings": result.hitkalelut_warnings,
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
