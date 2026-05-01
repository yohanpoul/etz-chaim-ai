"""SQLite FTS5 search over autopilot cycle logs.

Each completed cycle stores a structured record (timestamp, task id, status,
PR URL, summary) into `~/.etz-chaim/autopilot/cycle_log.db`. The FTS5 virtual
table indexes the summary text so the autopilot can recall what it tried
before when picking the next task.

Inspiration acknowledged: pattern of session search via FTS5 from NousResearch
/hermes-agent (MIT). Schema and query layer are independently authored —
we use a `cycle_log` table specific to autopilot lifecycle, not chat sessions.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

ETZ_HOME = Path(os.environ.get("ETZCHAIM_STATE_DIR", "~/.etz-chaim")).expanduser()
DB_FILE = ETZ_HOME / "autopilot" / "cycle_log.db"


SCHEMA = """
CREATE TABLE IF NOT EXISTS cycle_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at  REAL NOT NULL,
    completed_at REAL,
    task_id     TEXT NOT NULL,
    status      TEXT NOT NULL,
    pr_url      TEXT,
    summary     TEXT NOT NULL,
    metadata    TEXT
);

CREATE VIRTUAL TABLE IF NOT EXISTS cycle_log_fts USING fts5(
    summary, task_id, status,
    content='cycle_log', content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS cycle_log_ai AFTER INSERT ON cycle_log BEGIN
    INSERT INTO cycle_log_fts(rowid, summary, task_id, status)
    VALUES (new.id, new.summary, new.task_id, new.status);
END;

CREATE TRIGGER IF NOT EXISTS cycle_log_ad AFTER DELETE ON cycle_log BEGIN
    INSERT INTO cycle_log_fts(cycle_log_fts, rowid, summary, task_id, status)
    VALUES ('delete', old.id, old.summary, old.task_id, old.status);
END;

CREATE TRIGGER IF NOT EXISTS cycle_log_au AFTER UPDATE ON cycle_log BEGIN
    INSERT INTO cycle_log_fts(cycle_log_fts, rowid, summary, task_id, status)
    VALUES ('delete', old.id, old.summary, old.task_id, old.status);
    INSERT INTO cycle_log_fts(rowid, summary, task_id, status)
    VALUES (new.id, new.summary, new.task_id, new.status);
END;
"""


@dataclass
class CycleRecord:
    started_at: float
    task_id: str
    status: str
    summary: str
    completed_at: float | None = None
    pr_url: str | None = None
    metadata: str | None = None
    id: int | None = None


def _connect() -> sqlite3.Connection:
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_FILE))
    conn.executescript(SCHEMA)
    return conn


def insert_cycle(record: CycleRecord) -> int:
    """Insert a cycle record. Returns the new row id."""
    with closing(_connect()) as conn, conn:
        cur = conn.execute(
            """
            INSERT INTO cycle_log (started_at, completed_at, task_id, status, pr_url, summary, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.started_at,
                record.completed_at,
                record.task_id,
                record.status,
                record.pr_url,
                record.summary,
                record.metadata,
            ),
        )
        return int(cur.lastrowid or 0)


def search_cycles(query: str, limit: int = 20) -> list[CycleRecord]:
    """Full-text search over cycle summaries.

    `query` accepts FTS5 syntax (phrases, OR, NOT, prefix*).
    """
    with closing(_connect()) as conn:
        rows = conn.execute(
            """
            SELECT cl.id, cl.started_at, cl.completed_at, cl.task_id, cl.status,
                   cl.pr_url, cl.summary, cl.metadata
            FROM cycle_log cl
            JOIN cycle_log_fts ON cycle_log_fts.rowid = cl.id
            WHERE cycle_log_fts MATCH ?
            ORDER BY cl.started_at DESC
            LIMIT ?
            """,
            (query, limit),
        ).fetchall()

    return [
        CycleRecord(
            id=r[0],
            started_at=r[1],
            completed_at=r[2],
            task_id=r[3],
            status=r[4],
            pr_url=r[5],
            summary=r[6],
            metadata=r[7],
        )
        for r in rows
    ]


def recent_cycles(limit: int = 20) -> list[CycleRecord]:
    """Return the most recent cycles regardless of content."""
    with closing(_connect()) as conn:
        rows = conn.execute(
            """
            SELECT id, started_at, completed_at, task_id, status, pr_url, summary, metadata
            FROM cycle_log
            ORDER BY started_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [
        CycleRecord(
            id=r[0],
            started_at=r[1],
            completed_at=r[2],
            task_id=r[3],
            status=r[4],
            pr_url=r[5],
            summary=r[6],
            metadata=r[7],
        )
        for r in rows
    ]
