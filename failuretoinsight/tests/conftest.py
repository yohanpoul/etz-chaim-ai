"""Fixtures de test — sentier Lamed (FailureToInsight)."""

import subprocess
from pathlib import Path

import psycopg2
import pytest

from pool import get_conn as __pool_get_conn

from epistememory.core import EpisteMemory
from failuretoinsight.core import FailureToInsight
from failuretoinsight.db import FailureToInsightDB
from intentkeeper.core import IntentKeeper
from selfmap.core import SelfMap
from tests._psql import require_psql

TEST_DB_URL = "postgresql://localhost/etz_chaim_test"
PROJECT_ROOT = str(Path(__file__).resolve().parents[2])


@pytest.fixture(scope="session", autouse=True)
def apply_schemas():
    """Apply all schemas (epistememory + selfmap + intentkeeper + fti) once."""
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

    for schema in [
        "epistememory/schema.sql",
        "selfmap/schema.sql",
        "intentkeeper/schema.sql",
        "failuretoinsight/schema.sql",
        "insightforge/schema.sql",
    ]:
        subprocess.run(
            [require_psql(), "-d", "etz_chaim_test",
             "-f", schema],
            cwd=PROJECT_ROOT, check=True, capture_output=True,
        )

    # Pool init for modules that borrow from the shared pool
    from pool import init_pool
    init_pool(TEST_DB_URL)


@pytest.fixture
def db():
    """Fresh FailureToInsightDB, truncated between tests."""
    database = FailureToInsightDB(TEST_DB_URL)
    yield database
    _truncate_via_pool()
    database.close()


@pytest.fixture
def fti():
    """FailureToInsight with EpisteMemory, SelfMap, IntentKeeper connected."""
    memory = EpisteMemory(db_url=TEST_DB_URL)
    selfmap = SelfMap(db_url=TEST_DB_URL, default_model="test-model")
    intentkeeper = IntentKeeper(db_url=TEST_DB_URL)
    fti_instance = FailureToInsight(
        db_url=TEST_DB_URL,
        memory=memory,
        selfmap=selfmap,
        intentkeeper=intentkeeper,
    )
    yield fti_instance
    _truncate_via_pool()
    _truncate_deps(memory, selfmap, intentkeeper)
    memory.close()
    selfmap.db.close()
    intentkeeper.db.close()
    fti_instance.db.close()


@pytest.fixture
def fti_bare():
    """FailureToInsight sans connexions — tests unitaires purs."""
    fti_instance = FailureToInsight(db_url=TEST_DB_URL)
    yield fti_instance
    _truncate_via_pool()
    fti_instance.db.close()


def _truncate(conn):
    with conn.cursor() as cur:
        cur.execute("TRUNCATE failuretoinsight_graph_edges CASCADE")
        cur.execute("TRUNCATE failuretoinsight_insights CASCADE")
        cur.execute("TRUNCATE failuretoinsight_analyses CASCADE")
    conn.commit()


def _truncate_deps(memory, selfmap, intentkeeper):
    with __pool_get_conn() as __conn, __conn.cursor() as cur:
        cur.execute("TRUNCATE epistememory CASCADE")
    with selfmap.db._cursor() as cur:
        cur.execute("TRUNCATE selfmap_competence CASCADE")
        cur.execute("TRUNCATE selfmap_routing_log CASCADE")
    with intentkeeper.db._cursor() as cur:
        cur.execute("TRUNCATE intentkeeper_heartbeats CASCADE")
        cur.execute("TRUNCATE intentkeeper_subtasks CASCADE")
        cur.execute("TRUNCATE intentkeeper_intentions CASCADE")


def _truncate_via_pool():
    """Pool-based truncate wrapper for post-migration DB classes."""
    from pool import get_conn
    with get_conn() as conn:
        _truncate(conn)
