"""Interface PostgreSQL — Yesod-de-Hod : persistance de la self-knowledge."""

from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import psycopg2
import psycopg2.extras

from pool import get_conn, init_pool

from .models import CalibrationReport, DomainScore, EvalResult, SelfDescription

psycopg2.extras.register_uuid()


class SelfMapDB:
    """Accès PostgreSQL pour SelfMap — emprunte au pool centralisé."""

    def __init__(self, db_url: str = "postgresql://localhost/etz_chaim") -> None:
        self.db_url = db_url
        init_pool(db_url)  # idempotent

    def close(self) -> None:
        pass  # pool gère

    @contextmanager
    def _cursor(self, cursor_factory=None):
        """Emprunte une conn + cursor au pool."""
        with get_conn() as conn:
            if cursor_factory:
                with conn.cursor(cursor_factory=cursor_factory) as cur:
                    yield cur
            else:
                with conn.cursor() as cur:
                    yield cur

    def upsert_competence(self, score: DomainScore) -> None:
        """Insert or update a domain competence score."""
        results_json = json.dumps([
            {
                "question": r.question,
                "expected": r.expected,
                "actual": r.actual,
                "correct": r.correct,
                "confidence": r.confidence,
                "latency_ms": r.latency_ms,
            }
            for r in score.eval_results
        ])

        with self._cursor() as cur:
            cur.execute(
                """
                INSERT INTO selfmap_competence
                    (domain, model_id, score, brier_score, n_evals,
                     last_eval, eval_results, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (domain, model_id) DO UPDATE SET
                    score = EXCLUDED.score,
                    brier_score = EXCLUDED.brier_score,
                    n_evals = selfmap_competence.n_evals + EXCLUDED.n_evals,
                    last_eval = EXCLUDED.last_eval,
                    eval_results = EXCLUDED.eval_results,
                    updated_at = NOW()
                """,
                (
                    score.domain,
                    score.model_id,
                    score.score,
                    score.brier_score,
                    score.n_evals,
                    score.last_eval or datetime.now(timezone.utc),
                    results_json,
                ),
            )

    def get_competence(self, domain: str, model_id: str) -> DomainScore | None:
        """Get competence for a specific domain/model pair."""
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM selfmap_competence WHERE domain = %s AND model_id = %s",
                (domain, model_id),
            )
            row = cur.fetchone()
            if row is None:
                return None

            results = []
            if row["eval_results"]:
                for r in row["eval_results"]:
                    results.append(EvalResult(**r))

            return DomainScore(
                domain=row["domain"],
                model_id=row["model_id"],
                score=row["score"],
                brier_score=row["brier_score"] or 0.0,
                n_evals=row["n_evals"],
                eval_results=results,
                last_eval=row["last_eval"],
            )

    def get_all_competences(self, model_id: str) -> list[DomainScore]:
        """Get all domain scores for a model."""
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM selfmap_competence WHERE model_id = %s ORDER BY score DESC",
                (model_id,),
            )
            rows = cur.fetchall()

        return [
            DomainScore(
                domain=r["domain"],
                model_id=r["model_id"],
                score=r["score"],
                brier_score=r["brier_score"] or 0.0,
                n_evals=r["n_evals"],
                last_eval=r["last_eval"],
            )
            for r in rows
        ]

    def get_best_model(self, domain: str) -> DomainScore | None:
        """Get the best model for a domain."""
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT * FROM selfmap_competence
                   WHERE domain = %s
                   ORDER BY score DESC LIMIT 1""",
                (domain,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return DomainScore(
                domain=row["domain"],
                model_id=row["model_id"],
                score=row["score"],
                brier_score=row["brier_score"] or 0.0,
                n_evals=row["n_evals"],
                last_eval=row["last_eval"],
            )

    def log_routing(
        self,
        query: str,
        detected_domain: str | None,
        competence_score: float | None,
        routed_to: str | None,
        did_decline: bool = False,
        decline_reason: str | None = None,
    ) -> UUID:
        """Log a routing decision."""
        with self._cursor() as cur:
            cur.execute(
                """INSERT INTO selfmap_routing_log
                       (query, detected_domain, competence_score,
                        routed_to, did_decline, decline_reason)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   RETURNING id""",
                (query, detected_domain, competence_score,
                 routed_to, did_decline, decline_reason),
            )
            log_id = cur.fetchone()[0]
        return log_id

    def record_outcome(self, log_id: UUID, quality: float) -> None:
        """Record the outcome quality of a routed query."""
        with self._cursor() as cur:
            cur.execute(
                "UPDATE selfmap_routing_log SET outcome_quality = %s WHERE id = %s",
                (quality, log_id),
            )

    # --- Beinoni signals (bridge I2) ---

    def upsert_beinoni_signal(
        self,
        domain: str,
        elokit_ratio: float,
        avg_response_score: float,
        n_interactions: int,
        regressions_count: int = 0,
        elevations_count: int = 0,
        window_seconds: int = 3600,
    ) -> None:
        """Upsert d'un signal Beinoni agrégé par domaine.

        BeinoniTracker → SelfMap : un signal scalaire par domaine
        (qualité d'âme) que Da'at peut croiser avec la compétence.
        """
        with self._cursor() as cur:
            cur.execute(
                """INSERT INTO selfmap_beinoni_signals
                       (domain, elokit_ratio, avg_response_score,
                        n_interactions, regressions_count, elevations_count,
                        window_seconds, updated_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                   ON CONFLICT (domain) DO UPDATE SET
                       elokit_ratio = EXCLUDED.elokit_ratio,
                       avg_response_score = EXCLUDED.avg_response_score,
                       n_interactions = EXCLUDED.n_interactions,
                       regressions_count = EXCLUDED.regressions_count,
                       elevations_count = EXCLUDED.elevations_count,
                       window_seconds = EXCLUDED.window_seconds,
                       updated_at = NOW()""",
                (domain, elokit_ratio, avg_response_score, n_interactions,
                 regressions_count, elevations_count, window_seconds),
            )

    def get_beinoni_signal(self, domain: str) -> dict | None:
        """Lire le signal Beinoni courant pour un domaine."""
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM selfmap_beinoni_signals WHERE domain = %s",
                (domain,),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def get_self_description(self, model_id: str) -> SelfDescription:
        """Hod-de-Hod: the system describes itself."""
        competences = self.get_all_competences(model_id)

        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT COUNT(*) AS c FROM selfmap_routing_log")
            total_routed = cur.fetchone()["c"]

            cur.execute(
                "SELECT COUNT(*) AS c FROM selfmap_routing_log WHERE did_decline",
            )
            total_declined = cur.fetchone()["c"]

        strong = [c.domain for c in competences if c.score >= 0.7]
        weak = [c.domain for c in competences if c.score < 0.4]
        avg_score = sum(c.score for c in competences) / len(competences) if competences else 0.0
        avg_brier = (
            sum(c.brier_score for c in competences) / len(competences) if competences else 0.0
        )

        return SelfDescription(
            model_id=model_id,
            total_domains=len(competences),
            evaluated_domains=sum(1 for c in competences if c.n_evals > 0),
            strong_domains=strong,
            weak_domains=weak,
            unknown_domains=[],
            avg_competence=avg_score,
            avg_brier=avg_brier,
            total_queries_routed=total_routed,
            total_declined=total_declined,
            decline_rate=total_declined / total_routed if total_routed > 0 else 0.0,
        )
