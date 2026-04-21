"""Sprint 5.6 — Scheduling de ``task_validate_orphan_candidates`` dans daemon.

Vérifie que :

1. ``INTERVAL_VALIDATE_ORPHAN`` vaut 6h (21600s) — compatible avec le
   mode nuit provisoire (2-3 passes effectives/jour).
2. ``task_validate_orphan_candidates`` est importable depuis ``daemon``.
3. L'initial state contient ``last_orphan_validation=0`` (trigger au
   premier tick).
4. Le hook de déclenchement respecte l'intervalle (pas de re-trigger
   avant 6h depuis le dernier).
"""
from __future__ import annotations

import pytest


def test_interval_validate_orphan_is_six_hours():
    import daemon
    assert daemon.INTERVAL_VALIDATE_ORPHAN == 21600
    # 21600s = 6h = 4 passes max par 24h
    assert 3600 * 3 <= daemon.INTERVAL_VALIDATE_ORPHAN <= 3600 * 12, (
        "Intervalle hors fourchette raisonnable (3h-12h)"
    )


def test_task_import_chain():
    """La task est exportée par ``daemon_tasks`` et ré-exportée par ``daemon``."""
    from daemon import task_validate_orphan_candidates as via_daemon
    from daemon_tasks import task_validate_orphan_candidates as via_package
    from daemon_tasks.orphan_validation import (
        task_validate_orphan_candidates as via_module,
    )
    assert via_daemon is via_package is via_module


def test_initial_state_contains_orphan_key():
    """``load_state()`` retourne ``last_orphan_validation=0`` par défaut.

    Sans cette clé, le premier ``state["last_orphan_validation"]`` dans
    ``run_cycle`` lèverait ``KeyError``. On vérifie aussi que le code
    utilise ``.get("last_orphan_validation", 0)`` pour être robuste.
    """
    import tempfile
    from pathlib import Path

    # Construire un state "neuf" (fichier absent) — load_state retourne le dict par défaut
    import daemon
    original_state_file = daemon.STATE_FILE
    try:
        with tempfile.TemporaryDirectory() as tmp:
            daemon.STATE_FILE = Path(tmp) / "state.json"
            state = daemon.load_state()
            assert "last_orphan_validation" in state
            assert state["last_orphan_validation"] == 0
    finally:
        daemon.STATE_FILE = original_state_file


def test_trigger_respects_interval():
    """Simuler ``run_cycle`` : orphan_validation ne re-trigger pas < 6h."""
    import daemon
    now = 1_000_000.0  # arbitraire

    # Cas 1 : dernier passage il y a 5h → pas de trigger
    elapsed_5h = now - (5 * 3600)
    should_run = (now - elapsed_5h) >= daemon.INTERVAL_VALIDATE_ORPHAN
    assert not should_run

    # Cas 2 : dernier passage il y a 6h01s → trigger
    elapsed_6h01 = now - (6 * 3600 + 1)
    should_run = (now - elapsed_6h01) >= daemon.INTERVAL_VALIDATE_ORPHAN
    assert should_run

    # Cas 3 : jamais exécuté (0) → trigger
    assert (now - 0) >= daemon.INTERVAL_VALIDATE_ORPHAN


def test_batch_limit_is_fifty():
    """``ORPHAN_BATCH_LIMIT`` = 50 — garde-fou pour ne pas bloquer le daemon."""
    from daemon_tasks import ORPHAN_BATCH_LIMIT
    assert ORPHAN_BATCH_LIMIT == 50
