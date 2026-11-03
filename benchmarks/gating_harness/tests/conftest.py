"""Fixtures for the gating-harness smoke — real persistent Postgres test DB.

Mirrors gating/tests/conftest.py (create etz_chaim_test, install pgvector, load the
epistememory + dissensuengine schemas, init the shared pool). Unlike that file, embed
is NOT faked globally: the live run uses real Ollama embeddings. Tests that want to
isolate the gate's exact-tag logic from embedding noise request the explicit
``fake_embed`` fixture (documented at the call site).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tests._psql import require_psql

TEST_DB_URL = "postgresql://localhost/etz_chaim_test"
PROJECT_ROOT = str(Path(__file__).resolve().parents[3])


@pytest.fixture(scope="session", autouse=True)
def create_test_db():
    import psycopg2

    conn = psycopg2.connect("postgresql://localhost/postgres")
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = 'etz_chaim_test'")
    if not cur.fetchone():
        cur.execute("CREATE DATABASE etz_chaim_test")
    cur.close()
    conn.close()

    conn = psycopg2.connect(TEST_DB_URL)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
    cur.close()
    conn.close()

    for schema in ("epistememory/schema.sql", "dissensuengine/schema.sql"):
        subprocess.run(
            [require_psql(), "-d", "etz_chaim_test", "-f", schema],
            cwd=PROJECT_ROOT, check=True, capture_output=True,
        )

    from pool import init_pool

    init_pool(TEST_DB_URL)


def _truncate() -> None:
    from pool import get_conn

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE epistememory CASCADE")


@pytest.fixture
def mem():
    """Fresh EpisteMemory on the persistent test store, truncated around the test."""
    from epistememory.core import EpisteMemory

    _truncate()
    memory = EpisteMemory(db_url=TEST_DB_URL)
    yield memory
    _truncate()
    memory.close()


@pytest.fixture
def fake_embed(monkeypatch):
    """Bypass Ollama embeddings with a fixed 768-d vector.

    HONEST: isolates the gate's EXACT-TAG matching from semantic recall noise, exactly
    as the TEMPS-1 micro-probe does. The live run (run.py) uses real embeddings.
    """
    import epistememory.core as ec

    monkeypatch.setattr(ec, "embed", lambda text, model=None: [0.1] * 768)
