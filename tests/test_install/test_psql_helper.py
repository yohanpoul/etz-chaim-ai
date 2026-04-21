"""Test psql helper discovers binary cross-platform."""
from __future__ import annotations

import importlib
import shutil

import pytest


def test_psql_bin_found_via_which(monkeypatch):
    """If psql is on PATH, PSQL_BIN must find it."""
    monkeypatch.delenv("ETZ_PSQL_BIN", raising=False)
    if not shutil.which("psql"):
        pytest.skip("psql not installed on CI runner")
    import tests._psql
    importlib.reload(tests._psql)
    assert tests._psql.PSQL_BIN is not None
    assert "psql" in tests._psql.PSQL_BIN


def test_psql_bin_honors_env_override(monkeypatch):
    """ETZ_PSQL_BIN env var overrides auto-discovery."""
    monkeypatch.setenv("ETZ_PSQL_BIN", "/custom/psql")
    import tests._psql
    importlib.reload(tests._psql)
    assert tests._psql.PSQL_BIN == "/custom/psql"


def test_psql_bin_none_when_missing(monkeypatch):
    """PSQL_BIN is None when psql not found and no override."""
    monkeypatch.delenv("ETZ_PSQL_BIN", raising=False)
    monkeypatch.setenv("PATH", "/nonexistent")
    import tests._psql
    importlib.reload(tests._psql)
    assert tests._psql.PSQL_BIN is None


def test_require_psql_raises_when_none(monkeypatch):
    """require_psql() raises RuntimeError with install hint when PSQL_BIN is None."""
    monkeypatch.delenv("ETZ_PSQL_BIN", raising=False)
    monkeypatch.setenv("PATH", "/nonexistent")
    import tests._psql
    importlib.reload(tests._psql)
    with pytest.raises(RuntimeError, match="psql non trouvé"):
        tests._psql.require_psql()


def test_require_psql_returns_path_when_found(monkeypatch):
    monkeypatch.setenv("ETZ_PSQL_BIN", "/my/psql")
    import tests._psql
    importlib.reload(tests._psql)
    assert tests._psql.require_psql() == "/my/psql"
