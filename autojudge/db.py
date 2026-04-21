"""Accès base de données — Yesod de Gevurah."""

from __future__ import annotations

from contextlib import contextmanager

from uuid import UUID

import psycopg2
import psycopg2.extras

from pool import get_conn, init_pool

from autojudge.models import DomainConfig, Experiment

psycopg2.extras.register_uuid()


def _row_to_domain(row: dict) -> DomainConfig:
    return DomainConfig(
        id=row["id"],
        display_name=row["display_name"],
        loss_function=row["loss_function"],
        config=row.get("config") or {},
        created_at=row.get("created_at"),
    )


def _row_to_experiment(row: dict) -> Experiment:
    sources = row.get("failure_analysis_id")
    return Experiment(
        id=row["id"],
        domain_id=row["domain_id"],
        hypothesis=row["hypothesis"],
        original_content=row.get("original_content"),
        modified_content=row.get("modified_content"),
        score_gevurah=row.get("score_gevurah"),
        score_chesed=row.get("score_chesed"),
        score_tiferet=row.get("score_tiferet"),
        score_hod=row.get("score_hod"),
        score_yesod=row.get("score_yesod"),
        score_overall=row.get("score_overall"),
        decision=row.get("decision"),
        failure_analysis_id=sources,
        nitzotzot_extracted=row.get("nitzotzot_extracted", False),
        duration_seconds=row.get("duration_seconds"),
        budget_seconds=row.get("budget_seconds", 300.0),
        loop_iteration=row.get("loop_iteration"),
        created_at=row.get("created_at"),
    )


class AutoJudgeDB:
    """CRUD pour AutoJudge — Gevurah persiste ses jugements."""

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

    # --- Domains ---

    def upsert_domain(
        self,
        domain_id: str,
        display_name: str,
        loss_function: str,
        config: dict | None = None,
    ) -> DomainConfig:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """INSERT INTO autojudge_domains (id, display_name, loss_function, config)
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT (id) DO UPDATE SET
                       display_name = EXCLUDED.display_name,
                       loss_function = EXCLUDED.loss_function,
                       config = EXCLUDED.config
                   RETURNING *""",
                (domain_id, display_name, loss_function,
                 psycopg2.extras.Json(config or {})),
            )
            return _row_to_domain(cur.fetchone())

    def get_domain(self, domain_id: str) -> DomainConfig | None:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM autojudge_domains WHERE id = %s", (domain_id,))
            row = cur.fetchone()
            return _row_to_domain(row) if row else None

    def get_all_domains(self) -> list[DomainConfig]:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM autojudge_domains ORDER BY id")
            return [_row_to_domain(r) for r in cur.fetchall()]

    # --- Experiments ---

    def create_experiment(
        self,
        domain_id: str,
        hypothesis: str,
        original_content: str | None = None,
        modified_content: str | None = None,
        score_gevurah: float | None = None,
        score_chesed: float | None = None,
        score_tiferet: float | None = None,
        score_hod: float | None = None,
        score_yesod: float | None = None,
        score_overall: float | None = None,
        decision: str | None = None,
        failure_analysis_id: UUID | None = None,
        nitzotzot_extracted: bool = False,
        duration_seconds: float | None = None,
        budget_seconds: float = 300.0,
        loop_iteration: int | None = None,
    ) -> Experiment:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """INSERT INTO autojudge_experiments (
                       domain_id, hypothesis, original_content, modified_content,
                       score_gevurah, score_chesed, score_tiferet, score_hod,
                       score_yesod, score_overall, decision,
                       failure_analysis_id, nitzotzot_extracted,
                       duration_seconds, budget_seconds, loop_iteration
                   ) VALUES (
                       %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                   ) RETURNING *""",
                (domain_id, hypothesis, original_content, modified_content,
                 score_gevurah, score_chesed, score_tiferet, score_hod,
                 score_yesod, score_overall, decision,
                 failure_analysis_id, nitzotzot_extracted,
                 duration_seconds, budget_seconds, loop_iteration),
            )
            return _row_to_experiment(cur.fetchone())

    def get_experiment(self, experiment_id: UUID) -> Experiment | None:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM autojudge_experiments WHERE id = %s",
                (experiment_id,),
            )
            row = cur.fetchone()
            return _row_to_experiment(row) if row else None

    def get_experiments(
        self,
        domain_id: str | None = None,
        decision: str | None = None,
        limit: int = 100,
    ) -> list[Experiment]:
        clauses = []
        params: list = []
        if domain_id:
            clauses.append("domain_id = %s")
            params.append(domain_id)
        if decision:
            clauses.append("decision = %s")
            params.append(decision)

        where = "WHERE " + " AND ".join(clauses) if clauses else ""
        params.append(limit)

        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"SELECT * FROM autojudge_experiments {where} "
                f"ORDER BY created_at DESC LIMIT %s",
                params,
            )
            return [_row_to_experiment(r) for r in cur.fetchall()]

    def update_experiment(
        self,
        experiment_id: UUID,
        decision: str | None = None,
        failure_analysis_id: UUID | None = None,
        nitzotzot_extracted: bool | None = None,
        score_gevurah: float | None = None,
        score_chesed: float | None = None,
        score_tiferet: float | None = None,
        score_hod: float | None = None,
        score_yesod: float | None = None,
        score_overall: float | None = None,
    ) -> Experiment | None:
        sets = []
        params: list = []
        if decision is not None:
            sets.append("decision = %s")
            params.append(decision)
        if failure_analysis_id is not None:
            sets.append("failure_analysis_id = %s")
            params.append(failure_analysis_id)
        if nitzotzot_extracted is not None:
            sets.append("nitzotzot_extracted = %s")
            params.append(nitzotzot_extracted)
        for col, val in [
            ("score_gevurah", score_gevurah), ("score_chesed", score_chesed),
            ("score_tiferet", score_tiferet), ("score_hod", score_hod),
            ("score_yesod", score_yesod), ("score_overall", score_overall),
        ]:
            if val is not None:
                sets.append(f"{col} = %s")
                params.append(val)

        if not sets:
            return self.get_experiment(experiment_id)

        params.append(experiment_id)
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"UPDATE autojudge_experiments SET {', '.join(sets)} "
                f"WHERE id = %s RETURNING *",
                params,
            )
            row = cur.fetchone()
            return _row_to_experiment(row) if row else None

    def get_rejection_rate(self, domain_id: str) -> float:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM autojudge_rejection_rates WHERE domain_id = %s",
                (domain_id,),
            )
            row = cur.fetchone()
            if not row:
                return 0.0
            return float(row["rejection_rate"] or 0.0)

    def get_unanalyzed_rejections(
        self, domain_id: str | None = None
    ) -> list[Experiment]:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if domain_id:
                cur.execute(
                    "SELECT * FROM autojudge_unanalyzed_rejections "
                    "WHERE domain_id = %s ORDER BY created_at DESC",
                    (domain_id,),
                )
            else:
                cur.execute(
                    "SELECT * FROM autojudge_unanalyzed_rejections "
                    "ORDER BY created_at DESC"
                )
            return [_row_to_experiment(r) for r in cur.fetchall()]

    def count_by_decision(self, domain_id: str | None = None) -> dict[str, int]:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if domain_id:
                cur.execute(
                    "SELECT decision, COUNT(*) as cnt FROM autojudge_experiments "
                    "WHERE domain_id = %s GROUP BY decision",
                    (domain_id,),
                )
            else:
                cur.execute(
                    "SELECT decision, COUNT(*) as cnt FROM autojudge_experiments "
                    "GROUP BY decision"
                )
            return {r["decision"]: r["cnt"] for r in cur.fetchall()}

    def count_recent_rejections(
        self, domain_id: str, last_n: int = 10
    ) -> tuple[int, int]:
        """Count rejected in last N experiments. Returns (rejected, total)."""
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT decision FROM autojudge_experiments
                   WHERE domain_id = %s
                   ORDER BY created_at DESC LIMIT %s""",
                (domain_id, last_n),
            )
            rows = cur.fetchall()
            total = len(rows)
            rejected = sum(1 for r in rows if r["decision"] == "rejected")
            return rejected, total
