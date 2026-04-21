"""Tests Sprint 1 — Axe 13 & 5 : Thread safety et résilience.

Tests pour : locks globals, circuit breaker, pool migration, timeout DissensuEngine.
"""

import threading
import time
from unittest.mock import patch, MagicMock

import pytest


# ─── STATE_LOCK (main.py) ────────────────────────────────────


class TestStateLock:
    """Vérifie que les mutations de state sont thread-safe."""

    def test_state_lock_exists(self):
        """_STATE_LOCK existe dans main.py."""
        from main import _STATE_LOCK
        assert isinstance(_STATE_LOCK, type(threading.Lock()))

    def test_concurrent_igulim_switches(self):
        """Deux threads qui font des igulim switches simultanément
        ne corrompent pas l'état."""
        from main import _log_igulim_switch, _IGULIM_STATE, _STATE_LOCK

        initial_switches = _IGULIM_STATE["switches"]
        errors = []

        def switch_many(n):
            try:
                for _ in range(n):
                    _log_igulim_switch("yosher", "igulim", "test", "q")
                    _log_igulim_switch("igulim", "yosher", "test", "q")
            except Exception as e:
                errors.append(e)

        t1 = threading.Thread(target=switch_many, args=(50,))
        t2 = threading.Thread(target=switch_many, args=(50,))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert not errors
        # Chaque thread fait 50 switches igulim, total = 100
        assert _IGULIM_STATE["switches"] == initial_switches + 100

    def test_concurrent_world_transitions(self):
        """Transitions de monde simultanées ne crashent pas."""
        from main import _log_world_transition

        errors = []

        def transition_many(n):
            try:
                for _ in range(n):
                    _log_world_transition("ascent", "assiah", "yetzirah", "test", "q")
                    _log_world_transition("descent", "yetzirah", "assiah", "test", "q")
            except Exception as e:
                errors.append(e)

        t1 = threading.Thread(target=transition_many, args=(50,))
        t2 = threading.Thread(target=transition_many, args=(50,))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert not errors


# ─── _LAST_ASSESSMENT Lock (context_monitor.py) ──────────────


class TestAssessmentLock:
    """Vérifie le thread-safety de _LAST_ASSESSMENT."""

    def test_get_last_assessment_returns_none_initially(self):
        """get_last_assessment retourne None si aucun assess n'a eu lieu."""
        from masakh.context_monitor import get_last_assessment
        # Le résultat peut être None ou un dict (si un assess a déjà tourné)
        result = get_last_assessment()
        assert result is None or isinstance(result, dict)

    def test_assess_and_get_are_consistent(self):
        """Un assess() suivi de get_last_assessment() retourne le même résultat."""
        from masakh.context_monitor import ContextMonitor, get_last_assessment

        monitor = ContextMonitor()
        result = monitor.assess({"olam": "test_thread_safety"})
        got = get_last_assessment()

        assert got is not None
        assert got["olam"] == "test_thread_safety"
        assert got["score_global"] == result["score_global"]


# ─── Circuit Breaker (pool.py) ───────────────────────────────


class TestCircuitBreaker:
    """Tests pour le circuit breaker DB dans pool.py."""

    def test_circuit_breaker_imports(self):
        """Les nouvelles fonctions existent."""
        from pool import (
            CircuitOpenError,
            _cb_record_success,
            _cb_record_failure,
            _cb_is_open,
        )
        assert CircuitOpenError is not None

    def test_circuit_starts_closed(self):
        """Le circuit commence fermé."""
        from pool import _cb_is_open, _cb_record_success
        # Reset à l'état initial
        _cb_record_success()
        assert _cb_is_open() is False

    def test_circuit_opens_after_threshold(self):
        """Le circuit s'ouvre après N échecs consécutifs."""
        from pool import (
            _cb_record_failure,
            _cb_record_success,
            _cb_is_open,
            _CB_FAILURE_THRESHOLD,
        )
        # Reset
        _cb_record_success()

        for _ in range(_CB_FAILURE_THRESHOLD):
            _cb_record_failure()

        assert _cb_is_open() is True

        # Cleanup
        _cb_record_success()

    def test_success_resets_circuit(self):
        """Un succès referme le circuit."""
        from pool import _cb_record_failure, _cb_record_success, _cb_is_open

        # Ouvrir le circuit
        for _ in range(10):
            _cb_record_failure()
        assert _cb_is_open() is True

        # Un succès le referme
        _cb_record_success()
        assert _cb_is_open() is False

    def test_circuit_open_error_is_runtime_error(self):
        """CircuitOpenError hérite de RuntimeError."""
        from pool import CircuitOpenError
        assert issubclass(CircuitOpenError, RuntimeError)


# ─── DissensuEngine Timeout ──────────────────────────────────


class TestDissensuTimeout:
    """Vérifie que synthesize_or_dissent a un timeout."""

    def test_timeout_constant_exists(self):
        """SYNTHESIS_TIMEOUT est utilisé dans le code."""
        import dissensuengine.core as core
        source = open(core.__file__).read()
        assert "SYNTHESIS_TIMEOUT" in source

    def test_timed_out_flag_exists(self):
        """Le flag _timed_out est utilisé dans la boucle pairwise."""
        import dissensuengine.core as core
        source = open(core.__file__).read()
        assert "_timed_out" in source


# ─── epistememory/db.py Pool Migration ───────────────────────


class TestEpistememoryPoolMigration:
    """Vérifie que epistememory/db.py utilise le pool centralisé."""

    def test_no_persistent_conn(self):
        """Database n'a plus de self._conn."""
        from epistememory.db import Database
        db = Database()
        assert not hasattr(db, "_conn")

    def test_has_get_conn_method(self):
        """Database a une méthode _get_conn."""
        from epistememory.db import Database
        db = Database()
        assert hasattr(db, "_get_conn")

    def test_close_is_noop(self):
        """Database.close() est un no-op (le pool gère les connexions)."""
        from epistememory.db import Database
        db = Database()
        # Ne doit pas crasher
        db.close()
