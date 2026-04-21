"""Fixtures de test — Tiferet (DissensuEngine)."""

import subprocess
from pathlib import Path

import psycopg2
import pytest

from dissensuengine.core import DissensuEngine
from dissensuengine.db import DissensuEngineDB
from epistememory.core import EpisteMemory
from failuretoinsight.core import FailureToInsight
from intentkeeper.core import IntentKeeper
from selfmap.core import SelfMap
from tests._psql import require_psql

TEST_DB_URL = "postgresql://localhost/etz_chaim_test"
PROJECT_ROOT = str(Path(__file__).resolve().parents[2])


@pytest.fixture(scope="session", autouse=True)
def apply_schemas():
    """Apply all schemas (epistememory + selfmap + intentkeeper + fti + dissensu) once."""
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
        "dissensuengine/schema.sql",
    ]:
        subprocess.run(
            [require_psql(), "-d", "etz_chaim_test",
             "-f", schema],
            cwd=PROJECT_ROOT, check=True, capture_output=True,
        )

    # Init the shared pool on the test DB — epistememory (and anything pool-based)
    # must point at etz_chaim_test, not prod. idempotent if already init'd.
    from pool import init_pool
    init_pool(TEST_DB_URL)


@pytest.fixture
def db():
    """Fresh DissensuEngineDB, truncated between tests."""
    database = DissensuEngineDB(TEST_DB_URL)
    yield database
    _truncate_via_pool()
    database.close()


@pytest.fixture
def engine():
    """DissensuEngine with all connections."""
    memory = EpisteMemory(db_url=TEST_DB_URL)
    selfmap = SelfMap(db_url=TEST_DB_URL, default_model="test-model")
    intentkeeper = IntentKeeper(db_url=TEST_DB_URL)
    fti = FailureToInsight(db_url=TEST_DB_URL)
    eng = DissensuEngine(
        db_url=TEST_DB_URL,
        memory=memory,
        selfmap=selfmap,
        intentkeeper=intentkeeper,
        failuretoinsight=fti,
    )
    yield eng
    _truncate_via_pool()
    _truncate_fti_via_pool()
    _truncate_deps(memory, selfmap, intentkeeper)
    memory.close()
    selfmap.db.close()
    intentkeeper.db.close()
    fti.db.close()
    eng.db.close()


@pytest.fixture
def engine_bare():
    """DissensuEngine sans connexions — tests unitaires purs."""
    eng = DissensuEngine(db_url=TEST_DB_URL)
    yield eng
    _truncate_via_pool()
    eng.db.close()


def _truncate(conn):
    with conn.cursor() as cur:
        cur.execute("TRUNCATE dissensuengine_open_questions CASCADE")
        cur.execute("TRUNCATE dissensuengine_syntheses CASCADE")
        cur.execute("TRUNCATE dissensuengine_tensions CASCADE")
        cur.execute("TRUNCATE dissensuengine_conclusions CASCADE")
    conn.commit()


def _truncate_fti(conn):
    with conn.cursor() as cur:
        cur.execute("TRUNCATE failuretoinsight_graph_edges CASCADE")
        cur.execute("TRUNCATE failuretoinsight_insights CASCADE")
        cur.execute("TRUNCATE failuretoinsight_analyses CASCADE")
    conn.commit()


def _truncate_deps(memory, selfmap, intentkeeper):
    # epistememory now borrows from the shared pool — no .conn attribute
    from pool import get_conn
    with get_conn() as conn, conn.cursor() as cur:
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


def _truncate_fti_via_pool():
    """Pool-based FTI truncate wrapper."""
    from pool import get_conn
    with get_conn() as conn:
        _truncate_fti(conn)
