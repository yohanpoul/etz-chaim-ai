"""Test _resolve_db_url priority: ETZ_CHAIM_DB_URL > ETZ_CHAIM_DB > default."""
from __future__ import annotations

import importlib
import warnings


def _reload_pool():
    """Reimport pool module to pick up fresh env vars."""
    import pool
    return importlib.reload(pool)


def test_url_from_new_env(monkeypatch):
    monkeypatch.setenv("ETZ_CHAIM_DB_URL", "postgresql://new_env/db")
    monkeypatch.delenv("ETZ_CHAIM_DB", raising=False)
    pool = _reload_pool()
    assert pool._resolve_db_url() == "postgresql://new_env/db"


def test_url_from_legacy_env_with_warning(monkeypatch):
    monkeypatch.delenv("ETZ_CHAIM_DB_URL", raising=False)
    monkeypatch.setenv("ETZ_CHAIM_DB", "postgresql://legacy/db")
    pool = _reload_pool()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        url = pool._resolve_db_url()
    assert url == "postgresql://legacy/db"
    assert any("ETZ_CHAIM_DB" in str(w.message) for w in caught if issubclass(w.category, DeprecationWarning))


def test_url_new_takes_priority_over_legacy(monkeypatch):
    monkeypatch.setenv("ETZ_CHAIM_DB_URL", "postgresql://new/db")
    monkeypatch.setenv("ETZ_CHAIM_DB", "postgresql://old/db")
    pool = _reload_pool()
    assert pool._resolve_db_url() == "postgresql://new/db"


def test_url_default_when_none_set(monkeypatch):
    monkeypatch.delenv("ETZ_CHAIM_DB_URL", raising=False)
    monkeypatch.delenv("ETZ_CHAIM_DB", raising=False)
    pool = _reload_pool()
    assert pool._resolve_db_url() == "postgresql://localhost/etz_chaim"
