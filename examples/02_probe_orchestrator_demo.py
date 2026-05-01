"""Probe orchestrator demo — run one detect + rectify cycle in observe mode.

Requires a running PostgreSQL instance configured via ETZ_CHAIM_DB_URL.
Stays in `observe` mode (default) — no side effects.

Usage:
    python examples/02_probe_orchestrator_demo.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from etzchaim.probes import ProbeOrchestrator, RectificationMode  # noqa: E402


def main() -> None:
    print("=== Probe orchestrator demo (observe mode) ===\n")

    engine = ProbeOrchestrator()
    print(f"Rectification mode : {engine.mode}")
    assert engine.mode == RectificationMode.OBSERVE

    deviations = engine.detect(tree=None)
    print(f"Deviations detected : {len(deviations)}")
    for d in deviations:
        print(f"  - {json.dumps(d)}")

    events = engine.rectify(deviations)
    print(f"\nEvents emitted : {len(events)}")
    for e in events:
        print(f"  - {json.dumps(e)}")

    if not events:
        print("\nNo deviations detected — system is at equilibrium.")


if __name__ == "__main__":
    main()
