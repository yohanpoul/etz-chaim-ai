"""Fixtures de test — base de données éphémère."""

from pathlib import Path

import pytest

from epistememory.core import EpisteMemory
from epistememory.db import Database
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

    # Setup extensions and schema
    conn = psycopg2.connect(TEST_DB_URL)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
    cur.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")
    cur.close()
    conn.close()

    # Apply schema
    import subprocess
    subprocess.run(
        [require_psql(), "-d", "etz_chaim_test",
         "-f", "epistememory/schema.sql"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
    )

    # Database/EpisteMemory borrow from the shared pool — must be initialized
    # before any test touches the DB. idempotent.
    from pool import init_pool
    init_pool(TEST_DB_URL)


def _truncate_epistememory() -> None:
    """Clean state between tests via the shared pool."""
    from pool import get_conn
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE epistememory CASCADE")


@pytest.fixture
def db():
    """Fresh database interface, truncated between tests."""
    database = Database(TEST_DB_URL)
    yield database
    _truncate_epistememory()
    database.close()


@pytest.fixture
def mem():
    """Fresh EpisteMemory instance, truncated between tests."""
    memory = EpisteMemory(db_url=TEST_DB_URL)
    yield memory
    _truncate_epistememory()
    memory.close()
