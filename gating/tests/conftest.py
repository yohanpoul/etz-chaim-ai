"""Test fixtures for the gating micro-probe — real persistent Postgres test DB.

Reuses the epistememory test-DB pattern (epistememory/tests/conftest.py): create
`etz_chaim_test`, install pgvector, load the epistememory + dissensuengine schemas,
init the shared pool. The micro-probe MUST hit a real persistent store (Postgres),
otherwise it would not prove the round-trip — which is the only thing it proves.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tests._psql import require_psql

TEST_DB_URL = "postgresql://localhost/etz_chaim_test"
PROJECT_ROOT = str(Path(__file__).resolve().parents[2])


@pytest.fixture(scope="session", autouse=True)
def create_test_db():
    """Create/setup the test database, then initialize the shared pool."""
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
    try:
        cur.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")
    except Exception:
        pass  # timescaledb optional for this probe
    cur.close()
    conn.close()

    for schema in ("epistememory/schema.sql", "dissensuengine/schema.sql"):
        subprocess.run(
            [require_psql(), "-d", "etz_chaim_test", "-f", schema],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
        )

    from pool import init_pool

    init_pool(TEST_DB_URL)


def _truncate() -> None:
    from pool import get_conn

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE epistememory CASCADE")
            cur.execute(
                "TRUNCATE dissensuengine_conclusions, dissensuengine_tensions, "
                "dissensuengine_syntheses, dissensuengine_open_questions CASCADE"
            )


@pytest.fixture(autouse=True)
def _deterministic_embed(monkeypatch):
    """Bypass Ollama with a fixed 768-d vector.

    HONEST: the micro-probe does NOT test semantic recall — matching is exact-tag.
    Faking the embedding makes that explicit while keeping the Postgres round-trip
    fully real (the vector is written to and read back from the persistent store).
    """
    import epistememory.core as ec

    monkeypatch.setattr(ec, "embed", lambda text, model=None: [0.1] * 768)


@pytest.fixture
def mem():
    """Fresh EpisteMemory on the persistent test store, truncated between tests."""
    from epistememory.core import EpisteMemory

    memory = EpisteMemory(db_url=TEST_DB_URL)
    yield memory
    _truncate()
    memory.close()


@pytest.fixture
def dissensu():
    """Fresh DissensuEngine with explicit params (no omer/get_param DB dependency)."""
    from dissensuengine.core import DissensuEngine

    engine = DissensuEngine(
        db_url=TEST_DB_URL,
        dissensus_threshold=0.6,
        min_sources_for_synthesis=2,
        max_acceptable_divergence=0.8,
        source_coverage_min=0.7,
        confidence_floor=0.3,
        tension_staleness_days=90,
        max_open_questions=50,
    )
    yield engine
    _truncate()
