"""Tests Sprint 0 — Axe 16 : Daemon zombie fix.

Tests pour : PID lock, state atomique, auto-restart, zombie flag, /health.
"""

import json
import os
import signal
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


# ─── Fixtures ─────────────────────────────────────────────────


@pytest.fixture
def tmp_etz_home(tmp_path):
    """Crée un répertoire temporaire simulant ~/.etz-chaim/."""
    (tmp_path / "reports").mkdir()
    return tmp_path


@pytest.fixture
def _patch_paths(tmp_etz_home):
    """Patch les chemins du daemon vers le répertoire temporaire."""
    with patch("daemon.ETZ_HOME", tmp_etz_home), \
         patch("daemon.PID_FILE", tmp_etz_home / "daemon.pid"), \
         patch("daemon.STATE_FILE", tmp_etz_home / "daemon_state.json"), \
         patch("daemon.LOG_FILE", tmp_etz_home / "daemon.log"):
        # Re-bind module-level references
        import daemon
        daemon.PID_FILE = tmp_etz_home / "daemon.pid"
        daemon.STATE_FILE = tmp_etz_home / "daemon_state.json"
        yield tmp_etz_home


# ─── PID Lock ─────────────────────────────────────────────────


class TestPidLock:
    """Tests pour acquire_pid_lock / release_pid_lock."""

    def test_acquire_fresh(self, _patch_paths):
        """Acquisition sur PID file absent — doit réussir."""
        from daemon import acquire_pid_lock, PID_FILE
        acquire_pid_lock()
        assert PID_FILE.exists()
        assert int(PID_FILE.read_text().strip()) == os.getpid()

    def test_acquire_stale_pid(self, _patch_paths):
        """PID file avec un processus mort — doit nettoyer et acquérir."""
        from daemon import acquire_pid_lock, PID_FILE
        # Écrire un PID qui n'existe certainement pas
        PID_FILE.write_text("999999")
        acquire_pid_lock()
        assert int(PID_FILE.read_text().strip()) == os.getpid()

    def test_acquire_live_pid_refuses(self, _patch_paths):
        """PID file avec un processus vivant — doit refuser (sys.exit)."""
        from daemon import acquire_pid_lock, PID_FILE
        # Notre propre PID est vivant
        PID_FILE.write_text(str(os.getpid()))
        with pytest.raises(SystemExit):
            acquire_pid_lock()

    def test_acquire_corrupted_pid(self, _patch_paths):
        """PID file corrompu (non-numérique) — doit nettoyer."""
        from daemon import acquire_pid_lock, PID_FILE
        PID_FILE.write_text("not-a-pid")
        acquire_pid_lock()
        assert int(PID_FILE.read_text().strip()) == os.getpid()

    def test_release_own_pid(self, _patch_paths):
        """release_pid_lock supprime le fichier si c'est notre PID."""
        from daemon import acquire_pid_lock, release_pid_lock, PID_FILE
        acquire_pid_lock()
        assert PID_FILE.exists()
        release_pid_lock()
        assert not PID_FILE.exists()

    def test_release_other_pid_keeps_file(self, _patch_paths):
        """release_pid_lock ne supprime PAS si le PID n'est pas le nôtre."""
        from daemon import release_pid_lock, PID_FILE
        PID_FILE.write_text("1")  # PID 1 = launchd, pas nous
        release_pid_lock()
        assert PID_FILE.exists()  # Pas touché


# ─── State Atomique ───────────────────────────────────────────


class TestAtomicState:
    """Tests pour save_state atomique (write-then-rename)."""

    def test_save_creates_file(self, _patch_paths):
        """save_state crée le fichier JSON."""
        from daemon import save_state, STATE_FILE
        state = {"last_netzach": 12345}
        save_state(state)
        assert STATE_FILE.exists()
        data = json.loads(STATE_FILE.read_text())
        assert data["last_netzach"] == 12345

    def test_save_no_tmp_leftover(self, _patch_paths):
        """Pas de fichier .tmp résiduel après save."""
        from daemon import save_state, STATE_FILE
        save_state({"last_gc": 0})
        tmp_file = STATE_FILE.with_suffix(".tmp")
        assert not tmp_file.exists()

    def test_save_includes_metadata(self, _patch_paths):
        """save_state ajoute _daemon_pid et _last_save."""
        from daemon import save_state, STATE_FILE
        save_state({"last_gc": 0})
        data = json.loads(STATE_FILE.read_text())
        assert data["_daemon_pid"] == os.getpid()
        assert data["_last_save"] > 0
        assert time.time() - data["_last_save"] < 5

    def test_save_overwrites_safely(self, _patch_paths):
        """Deux saves consécutifs — le second remplace le premier."""
        from daemon import save_state, STATE_FILE
        save_state({"version": 1})
        save_state({"version": 2})
        data = json.loads(STATE_FILE.read_text())
        assert data["version"] == 2

    def test_load_state_from_saved(self, _patch_paths):
        """load_state relit ce que save_state a écrit."""
        from daemon import save_state, load_state, STATE_FILE
        save_state({"last_netzach": 42})
        loaded = load_state()
        assert loaded["last_netzach"] == 42

    def test_load_state_default_on_missing(self, _patch_paths):
        """load_state retourne les défauts si pas de fichier."""
        from daemon import load_state
        state = load_state()
        assert state["last_netzach"] == 0
        assert state["last_gc"] == 0


# ─── is_pid_alive ────────────────────────────────────────────


class TestIsPidAlive:
    """Tests pour _is_pid_alive."""

    def test_own_pid_alive(self):
        """Notre propre PID est vivant."""
        from daemon import _is_pid_alive
        assert _is_pid_alive(os.getpid()) is True

    def test_dead_pid(self):
        """Un PID très élevé est probablement mort."""
        from daemon import _is_pid_alive
        assert _is_pid_alive(4194304) is False  # Au-delà du max PID macOS

    def test_negative_pid(self):
        """PID négatif — ne doit pas crasher."""
        from daemon import _is_pid_alive
        # os.kill(-1, 0) tuerait tout — on vérifie que notre code est safe
        assert _is_pid_alive(-1) is False


# ─── Zombie Flag ──────────────────────────────────────────────


class TestZombieFlag:
    """Tests pour la correction du zombie flag hitbonenut_running."""

    def test_save_state_reflects_runner(self, _patch_paths):
        """save_state écrit le vrai statut du runner, pas un cache."""
        from daemon import save_state, STATE_FILE, _hitbonenut_runner
        # Le runner n'est pas démarré → doit être False
        save_state({"test": True})
        data = json.loads(STATE_FILE.read_text())
        assert data["hitbonenut_running"] is False

    def test_stale_hitbonenut_flag_cleaned(self, _patch_paths):
        """Si daemon_state.json dit hitbonenut_running=True mais le runner
        est arrêté, save_state corrige."""
        from daemon import save_state, STATE_FILE
        # Simuler un state zombie
        STATE_FILE.write_text(json.dumps({"hitbonenut_running": True}))
        # save_state doit corriger
        save_state({"hitbonenut_running": True})  # valeur entrante ignorée
        data = json.loads(STATE_FILE.read_text())
        assert data["hitbonenut_running"] is False


# ─── Health Endpoint ──────────────────────────────────────────


class TestHealthEndpoint:
    """Tests pour /health dans web/app.py."""

    @pytest.fixture
    def client(self):
        """Crée un client de test Flask."""
        # Patch la DB pour ne pas nécessiter PostgreSQL
        with patch("pool.init_pool"):
            from web.app import create_app
            app = create_app("postgresql://localhost/test_nonexistent")
            app.config["TESTING"] = True
            with app.test_client() as client:
                yield client

    def test_health_endpoint_exists(self, client):
        """Le endpoint /health répond."""
        with patch("pool.get_conn") as mock_conn:
            # Mock la vérification DB
            mock_ctx = MagicMock()
            mock_cur = MagicMock()
            mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
            mock_ctx.__exit__ = MagicMock(return_value=False)
            mock_ctx.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
            mock_ctx.cursor.return_value.__exit__ = MagicMock(return_value=False)
            mock_conn.return_value = mock_ctx
            resp = client.get("/health")
            assert resp.status_code in (200, 503)
            data = json.loads(resp.data)
            assert "status" in data
            assert "checks" in data
            assert "timestamp" in data

    def test_health_returns_json(self, client):
        """Le endpoint retourne du JSON valide."""
        with patch("pool.get_conn") as mock_conn:
            mock_ctx = MagicMock()
            mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
            mock_ctx.__exit__ = MagicMock(return_value=False)
            mock_conn.return_value = mock_ctx
            resp = client.get("/health")
            assert resp.content_type == "application/json"
