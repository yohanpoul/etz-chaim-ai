"""Fixtures de test pour SelfMap."""

import subprocess
from pathlib import Path

import psycopg2
import pytest

from selfmap.core import SelfMap
from selfmap.db import SelfMapDB
from tests._psql import require_psql

TEST_DB_URL = "postgresql://localhost/etz_chaim_test"
PROJECT_ROOT = str(Path(__file__).resolve().parents[2])


@pytest.fixture(scope="session", autouse=True)
def setup_selfmap_schema():
    """Create selfmap tables in the test database."""
    conn = psycopg2.connect("postgresql://localhost/postgres")
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = 'etz_chaim_test'")
    if not cur.fetchone():
        cur.execute("CREATE DATABASE etz_chaim_test")
    cur.close()
    conn.close()

    # Ensure extensions
    conn = psycopg2.connect(TEST_DB_URL)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
    cur.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")
    cur.close()
    conn.close()

    # Apply both schemas (epistememory needed as dependency)
    for schema in ["epistememory/schema.sql", "selfmap/schema.sql"]:
        subprocess.run(
            [require_psql(), "-d", "etz_chaim_test", "-f", schema],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
        )

    # Pool init for SelfMapDB which borrows from the shared pool
    from pool import init_pool
    init_pool(TEST_DB_URL)


@pytest.fixture
def db():
    """Fresh SelfMapDB, truncated between tests."""
    database = SelfMapDB(TEST_DB_URL)
    yield database
    with database._cursor() as cur:
        cur.execute("TRUNCATE selfmap_competence CASCADE")
        cur.execute("TRUNCATE selfmap_routing_log CASCADE")
    database.close()


@pytest.fixture
def sm():
    """Fresh SelfMap instance, truncated between tests."""
    selfmap = SelfMap(
        db_url=TEST_DB_URL,
        default_model="test-model",
        decline_threshold=0.3,
    )
    yield selfmap
    with selfmap.db._cursor() as cur:
        cur.execute("TRUNCATE selfmap_competence CASCADE")
        cur.execute("TRUNCATE selfmap_routing_log CASCADE")
        cur.execute("TRUNCATE epistememory CASCADE")
    selfmap.close()
