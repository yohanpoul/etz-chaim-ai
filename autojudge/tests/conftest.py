"""Fixtures de test — Gevurah (AutoJudge)."""

import subprocess
from pathlib import Path

import psycopg2
import pytest

from autojudge.core import AutoJudge
from autojudge.db import AutoJudgeDB
from failuretoinsight.core import FailureToInsight
from tests._psql import require_psql

TEST_DB_URL = "postgresql://localhost/etz_chaim_test"
PROJECT_ROOT = str(Path(__file__).resolve().parents[2])


@pytest.fixture(scope="session", autouse=True)
def apply_schemas():
    """Apply all schemas (epistememory through autojudge) once."""
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
        "autojudge/schema.sql",
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
    """Fresh AutoJudgeDB, truncated between tests."""
    database = AutoJudgeDB(TEST_DB_URL)
    yield database
    _truncate_via_pool()
    database.close()


@pytest.fixture
def fti():
    """FailureToInsight for Lamed bridge tests."""
    f = FailureToInsight(db_url=TEST_DB_URL)
    yield f
    _truncate_fti_via_pool()
    f.db.close()


@pytest.fixture
def judge(fti):
    """AutoJudge with FTI connected (sentier Lamed branché)."""
    j = AutoJudge(db_url=TEST_DB_URL, failuretoinsight=fti)
    yield j
    _truncate_via_pool()
    j.db.close()


@pytest.fixture
def judge_bare():
    """AutoJudge sans FTI — tests unitaires purs.

    Explicit Omer defaults to isolate tests from DB overrides.
    """
    j = AutoJudge(db_url=TEST_DB_URL, quality_threshold=0.6, quarantine_threshold=0.4)
    yield j
    _truncate_via_pool()
    j.db.close()


def _truncate(conn):
    with conn.cursor() as cur:
        cur.execute("TRUNCATE autojudge_experiments CASCADE")
        cur.execute("TRUNCATE autojudge_domains CASCADE")
    conn.commit()


def _truncate_fti(conn):
    with conn.cursor() as cur:
        cur.execute("TRUNCATE failuretoinsight_graph_edges CASCADE")
        cur.execute("TRUNCATE failuretoinsight_insights CASCADE")
        cur.execute("TRUNCATE failuretoinsight_analyses CASCADE")
    conn.commit()


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
