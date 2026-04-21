"""Accès base de données — Yesod-de-Netzach : la fondation de la persistance."""

from __future__ import annotations

from contextlib import contextmanager

import json
from datetime import datetime, timedelta, timezone
from uuid import UUID

import psycopg2
import psycopg2.extras

from pool import get_conn, init_pool

from intentkeeper.models import AbandonDecision, Intention, ProgressReport, SubTask

psycopg2.extras.register_uuid()


def _row_to_intention(row: dict) -> Intention:
    return Intention(
        id=row["id"],
        goal=row["goal"],
        status=row["status"],
        max_duration_days=row["max_duration_days"],
        abandon_threshold=row["abandon_threshold"],
        progress=row["progress"],
        strategy=row["strategy"],
        strategy_version=row["strategy_version"],
        total_subtasks=row["total_subtasks"],
        completed_subtasks=row["completed_subtasks"],
        failed_subtasks=row["failed_subtasks"],
        abandon_reason=row.get("abandon_reason"),
        created_at=row["created_at"],
        deadline_at=row.get("deadline_at"),
        completed_at=row.get("completed_at"),
    )


def _row_to_subtask(row: dict) -> SubTask:
    return SubTask(
        id=row["id"],
        intention_id=row["intention_id"],
        description=row["description"],
        status=row["status"],
        order_index=row["order_index"],
        strategy_version=row["strategy_version"],
        result=row.get("result"),
        failure_reason=row.get("failure_reason"),
        retries=row["retries"],
        max_retries=row["max_retries"],
        created_at=row["created_at"],
        started_at=row.get("started_at"),
        completed_at=row.get("completed_at"),
    )


class IntentKeeperDB:
    """Couche d'accès aux données pour IntentKeeper."""

    def __init__(self, db_url: str):
        self.db_url = db_url
        init_pool(db_url)  # idempotent

    def close(self):
        pass  # pool gère les connexions

    @contextmanager
    def _cursor(self, cursor_factory=None):
        """Emprunte une conn + cursor au pool, puis rend."""
        with get_conn() as conn:
            if cursor_factory:
                with conn.cursor(cursor_factory=cursor_factory) as cur:
                    yield cur
            else:
                with conn.cursor() as cur:
                    yield cur

    # --- Intentions ---

    def create_intention(
        self,
        goal: str,
        max_duration_days: int = 90,
        abandon_threshold: float = 0.2,
        strategy: str | None = None,
    ) -> Intention:
        now = datetime.now(timezone.utc)
        deadline = now + timedelta(days=max_duration_days)
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """INSERT INTO intentkeeper_intentions
                   (goal, max_duration_days, abandon_threshold, strategy, deadline_at)
                   VALUES (%s, %s, %s, %s, %s)
                   RETURNING *""",
                (goal, max_duration_days, abandon_threshold, strategy, deadline),
            )
            return _row_to_intention(cur.fetchone())

    def get_intention(self, intention_id: UUID) -> Intention | None:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM intentkeeper_intentions WHERE id = %s",
                (intention_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            intention = _row_to_intention(row)
            intention.subtasks = self.get_subtasks(intention_id)
            return intention

    def update_intention_status(
        self, intention_id: UUID, status: str, reason: str | None = None
    ):
        with self._cursor() as cur:
            cur.execute(
                """UPDATE intentkeeper_intentions
                   SET status = %s, abandon_reason = COALESCE(%s, abandon_reason),
                       completed_at = CASE WHEN %s IN ('completed', 'abandoned')
                                           THEN NOW() ELSE completed_at END,
                       updated_at = NOW()
                   WHERE id = %s""",
                (status, reason, status, intention_id),
            )

    def update_progress(self, intention_id: UUID, progress: float):
        with self._cursor() as cur:
            cur.execute(
                """UPDATE intentkeeper_intentions
                   SET progress = %s, updated_at = NOW()
                   WHERE id = %s""",
                (progress, intention_id),
            )

    def update_subtask_counts(self, intention_id: UUID):
        """Recalcule les compteurs de sous-tâches depuis la table subtasks."""
        with self._cursor() as cur:
            cur.execute(
                """UPDATE intentkeeper_intentions SET
                       total_subtasks = (SELECT COUNT(*) FROM intentkeeper_subtasks
                                         WHERE intention_id = %s),
                       completed_subtasks = (SELECT COUNT(*) FROM intentkeeper_subtasks
                                             WHERE intention_id = %s AND status = 'completed'),
                       failed_subtasks = (SELECT COUNT(*) FROM intentkeeper_subtasks
                                          WHERE intention_id = %s AND status = 'failed'),
                       updated_at = NOW()
                   WHERE id = %s""",
                (intention_id, intention_id, intention_id, intention_id),
            )

    def get_active_intentions(self) -> list[Intention]:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM active_intentions ORDER BY created_at")
            return [_row_to_intention(row) for row in cur.fetchall()]

    # --- Sous-tâches ---

    def add_subtask(
        self,
        intention_id: UUID,
        description: str,
        order_index: int,
        strategy_version: int = 1,
        max_retries: int = 3,
    ) -> SubTask:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """INSERT INTO intentkeeper_subtasks
                   (intention_id, description, order_index, strategy_version, max_retries)
                   VALUES (%s, %s, %s, %s, %s)
                   RETURNING *""",
                (intention_id, description, order_index, strategy_version, max_retries),
            )
            st = _row_to_subtask(cur.fetchone())
        self.update_subtask_counts(intention_id)
        return st

    def get_subtasks(
        self, intention_id: UUID, strategy_version: int | None = None
    ) -> list[SubTask]:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if strategy_version is not None:
                cur.execute(
                    """SELECT * FROM intentkeeper_subtasks
                       WHERE intention_id = %s AND strategy_version = %s
                       ORDER BY order_index""",
                    (intention_id, strategy_version),
                )
            else:
                cur.execute(
                    """SELECT * FROM intentkeeper_subtasks
                       WHERE intention_id = %s ORDER BY order_index""",
                    (intention_id,),
                )
            return [_row_to_subtask(row) for row in cur.fetchall()]

    def update_subtask_status(
        self,
        subtask_id: UUID,
        status: str,
        result: str | None = None,
        failure_reason: str | None = None,
    ):
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """UPDATE intentkeeper_subtasks SET
                       status = %s,
                       result = COALESCE(%s, result),
                       failure_reason = COALESCE(%s, failure_reason),
                       started_at = CASE WHEN %s = 'in_progress' AND started_at IS NULL
                                         THEN NOW() ELSE started_at END,
                       completed_at = CASE WHEN %s IN ('completed', 'failed', 'skipped')
                                           THEN NOW() ELSE completed_at END,
                       updated_at = NOW()
                   WHERE id = %s
                   RETURNING intention_id""",
                (status, result, failure_reason, status, status, subtask_id),
            )
            row = cur.fetchone()
            if row:
                self.update_subtask_counts(row["intention_id"])

    def increment_retry(self, subtask_id: UUID) -> int:
        """Incrémente le compteur de retry. Retourne le nouveau nombre."""
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """UPDATE intentkeeper_subtasks
                   SET retries = retries + 1, updated_at = NOW()
                   WHERE id = %s
                   RETURNING retries, max_retries""",
                (subtask_id,),
            )
            row = cur.fetchone()
            return row["retries"] if row else 0

    def skip_pending_subtasks(self, intention_id: UUID, strategy_version: int):
        """Skip toutes les sous-tâches pending d'une ancienne stratégie."""
        with self._cursor() as cur:
            cur.execute(
                """UPDATE intentkeeper_subtasks
                   SET status = 'skipped', updated_at = NOW()
                   WHERE intention_id = %s
                     AND strategy_version = %s
                     AND status = 'pending'""",
                (intention_id, strategy_version),
            )
        self.update_subtask_counts(intention_id)

    # --- Heartbeats ---

    def record_heartbeat(
        self,
        intention_id: UUID,
        activity_type: str,
        details: dict | None = None,
    ):
        with self._cursor() as cur:
            cur.execute(
                """INSERT INTO intentkeeper_heartbeats
                   (intention_id, activity_type, details)
                   VALUES (%s, %s, %s)""",
                (intention_id, activity_type, json.dumps(details) if details else None),
            )

    def get_last_heartbeat(self, intention_id: UUID) -> datetime | None:
        with self._cursor() as cur:
            cur.execute(
                """SELECT MAX(created_at) FROM intentkeeper_heartbeats
                   WHERE intention_id = %s""",
                (intention_id,),
            )
            row = cur.fetchone()
            return row[0] if row and row[0] else None

    def days_since_activity(self, intention_id: UUID) -> float:
        """Jours écoulés depuis le dernier heartbeat (ou la création)."""
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT EXTRACT(EPOCH FROM (NOW() - COALESCE(
                       (SELECT MAX(h.created_at) FROM intentkeeper_heartbeats h
                        WHERE h.intention_id = %s),
                       (SELECT created_at FROM intentkeeper_intentions WHERE id = %s)
                   ))) / 86400.0 AS days""",
                (intention_id, intention_id),
            )
            row = cur.fetchone()
            return row["days"] if row else 0.0

    # --- Calculs de progrès ---

    def get_time_elapsed_ratio(self, intention_id: UUID) -> float:
        """Ratio du temps écoulé (0 = début, 1 = deadline)."""
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT created_at, deadline_at FROM intentkeeper_intentions
                   WHERE id = %s""",
                (intention_id,),
            )
            row = cur.fetchone()
            if not row or not row["deadline_at"]:
                return 0.0
            total = (row["deadline_at"] - row["created_at"]).total_seconds()
            if total <= 0:
                return 1.0
            elapsed = (
                datetime.now(timezone.utc) - row["created_at"]
            ).total_seconds()
            return max(0.0, min(1.0, elapsed / total))
