"""Fixtures de test — IntentKeeper (Netzach)."""

import subprocess
from pathlib import Path

import psycopg2
import pytest

from epistememory.core import EpisteMemory
from intentkeeper.core import IntentKeeper
from intentkeeper.db import IntentKeeperDB
from selfmap.core import SelfMap
from tests._psql import require_psql

TEST_DB_URL = "postgresql://localhost/etz_chaim_test"
PROJECT_ROOT = str(Path(__file__).resolve().parents[2])


@pytest.fixture(scope="session", autouse=True)
def apply_schemas():
    """Apply all schemas (epistememory + selfmap + intentkeeper) once."""
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
    cur.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")
    cur.close()
    conn.close()

    for schema in ["epistememory/schema.sql", "selfmap/schema.sql",
                    "intentkeeper/schema.sql"]:
        subprocess.run(
            [require_psql(), "-d", "etz_chaim_test",
             "-f", schema],
            cwd=PROJECT_ROOT, check=True, capture_output=True,
        )

    # EpisteMemory borrows from the shared pool — init before tests touch it.
    from pool import init_pool
    init_pool(TEST_DB_URL)


@pytest.fixture
def db():
    """Fresh IntentKeeperDB, truncated between tests."""
    database = IntentKeeperDB(TEST_DB_URL)
    yield database
    _truncate_via_pool()
    database.close()


@pytest.fixture
def ik():
    """IntentKeeper with Yesod (EpisteMemory) and Hod (SelfMap) connected."""
    memory = EpisteMemory(db_url=TEST_DB_URL)
    selfmap = SelfMap(db_url=TEST_DB_URL, default_model="test-model")
    keeper = IntentKeeper(
        db_url=TEST_DB_URL,
        selfmap=selfmap,
        memory=memory,
    )
    yield keeper
    _truncate_via_pool()
    # epistememory now borrows from the shared pool — no .conn attribute
    from pool import get_conn
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("TRUNCATE epistememory CASCADE")
    with selfmap.db._cursor() as cur:
        cur.execute("TRUNCATE selfmap_competence CASCADE")
        cur.execute("TRUNCATE selfmap_routing_log CASCADE")
    memory.close()
    selfmap.db.close()
    keeper.db.close()


@pytest.fixture
def ik_bare():
    """IntentKeeper sans connexion Yesod/Hod — tests unitaires purs."""
    keeper = IntentKeeper(db_url=TEST_DB_URL)
    yield keeper
    _truncate_via_pool()
    keeper.db.close()


def _truncate(conn):
    with conn.cursor() as cur:
        cur.execute("TRUNCATE intentkeeper_heartbeats CASCADE")
        cur.execute("TRUNCATE intentkeeper_subtasks CASCADE")
        cur.execute("TRUNCATE intentkeeper_intentions CASCADE")
    conn.commit()


def _truncate_via_pool():
    """Pool-based truncate wrapper for post-migration DB classes."""
    from pool import get_conn
    with get_conn() as conn:
        _truncate(conn)
