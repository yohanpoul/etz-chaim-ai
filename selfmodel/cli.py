"""CLI pour SelfModel — Da'at."""

from __future__ import annotations

import argparse
import os
import sys

from selfmodel.core import SelfModel


def _get_db_url() -> str:
    return os.environ.get(
        "ETZ_CHAIM_DB_URL",
        "postgresql://localhost:5432/etz_chaim",
    )


def cmd_capture(args):
    model = SelfModel(db_url=_get_db_url())
    state = model.capture_state()
    print(f"State captured: {state.id}")
    print(f"Model confidence: {state.model_confidence:.1%}")
    print(f"Biases detected: {len(state.known_biases)}")
    print(f"Strengths: {len(state.predicted_strengths)}")
    print(f"Weaknesses: {len(state.predicted_weaknesses)}")


def cmd_predict(args):
    model = SelfModel(db_url=_get_db_url())
    predictions = model.predict_error(args.task)
    if not predictions:
        print("No predictions — system has no prior state to analyze.")
        return
    for p in predictions:
        print(f"  [{p.predicted_error_type}] {p.prediction}")
        print(f"    confidence: {p.predicted_confidence:.1%}")


def cmd_diagnose(args):
    model = SelfModel(db_url=_get_db_url())
    diag = model.self_diagnose()
    print(f"Level: {diag['level']}")
    for issue in diag["issues"]:
        print(f"  ! {issue}")


def cmd_evolution(args):
    model = SelfModel(db_url=_get_db_url())
    snap = model.track_evolution()
    print(f"Trend: {snap.trend}")
    print(f"Overall health: {snap.overall_health:.1%}")
    for seph, health in snap.health_by_sephirah.items():
        bar = "█" * int(health * 10) + "░" * (10 - int(health * 10))
        print(f"  {seph:10s} {bar} {health:.1%}")


def cmd_who_am_i(args):
    model = SelfModel(db_url=_get_db_url())
    print(model.report())


def main():
    parser = argparse.ArgumentParser(
        description="SelfModel — Da'at, the Abyss crossing"
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("capture", help="Capture system state")
    p_pred = sub.add_parser("predict", help="Predict errors for a task")
    p_pred.add_argument("task", help="Task description")
    sub.add_parser("diagnose", help="Self-diagnose (HaTehom levels)")
    sub.add_parser("evolution", help="Track evolution")
    sub.add_parser("who-am-i", help="Full self-report")

    args = parser.parse_args()
    cmds = {
        "capture": cmd_capture,
        "predict": cmd_predict,
        "diagnose": cmd_diagnose,
        "evolution": cmd_evolution,
        "who-am-i": cmd_who_am_i,
    }
    fn = cmds.get(args.command)
    if fn:
        fn(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
