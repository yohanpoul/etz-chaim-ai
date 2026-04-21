"""Accès base de données — Yesod de Da'at."""

from __future__ import annotations

import json
from contextlib import contextmanager
from uuid import UUID

import psycopg2
import psycopg2.extras

from pool import get_conn, init_pool
from selfmodel.models import (
    BiasEntry,
    EvolutionSnapshot,
    Prediction,
    SelfState,
)

psycopg2.extras.register_uuid()


def _row_to_state(row: dict) -> SelfState:
    return SelfState(
        id=row["id"],
        captured_at=row.get("captured_at"),
        yesod_stats=row.get("yesod_stats") or {},
        hod_stats=row.get("hod_stats") or {},
        netzach_stats=row.get("netzach_stats") or {},
        tiferet_stats=row.get("tiferet_stats") or {},
        gevurah_stats=row.get("gevurah_stats") or {},
        chesed_stats=row.get("chesed_stats") or {},
        known_biases=row.get("known_biases") or [],
        predicted_weaknesses=row.get("predicted_weaknesses") or [],
        predicted_strengths=row.get("predicted_strengths") or [],
        model_confidence=row.get("model_confidence", 0.5),
    )


def _row_to_prediction(row: dict) -> Prediction:
    return Prediction(
        id=row["id"],
        predicted_at=row.get("predicted_at"),
        prediction=row["prediction"],
        domain=row.get("domain", ""),
        predicted_error_type=row.get("predicted_error_type", ""),
        predicted_confidence=row.get("predicted_confidence", 0.5),
        verified_at=row.get("verified_at"),
        was_correct=row.get("was_correct"),
        actual_outcome=row.get("actual_outcome", ""),
        prediction_accuracy_running=row.get("prediction_accuracy_running"),
    )


def _row_to_bias(row: dict) -> BiasEntry:
    return BiasEntry(
        id=row["id"],
        detected_at=row.get("detected_at"),
        bias_type=row["bias_type"],
        description=row["description"],
        evidence=row.get("evidence") or {},
        severity=row.get("severity", 0.5),
        domain=row.get("domain", ""),
        mitigation=row.get("mitigation", ""),
        still_active=row.get("still_active", True),
    )


def _row_to_evolution(row: dict) -> EvolutionSnapshot:
    return EvolutionSnapshot(
        id=row["id"],
        snapshot_at=row.get("snapshot_at"),
        yesod_health=row.get("yesod_health", 0.5),
        hod_health=row.get("hod_health", 0.5),
        netzach_health=row.get("netzach_health", 0.5),
        tiferet_health=row.get("tiferet_health", 0.5),
        gevurah_health=row.get("gevurah_health", 0.5),
        chesed_health=row.get("chesed_health", 0.5),
        overall_health=row.get("overall_health", 0.5),
        trend=row.get("trend", "stable"),
        trend_details=row.get("trend_details") or {},
    )


class SelfModelDB:
    """CRUD pour SelfModel — Da'at persiste sa connaissance de soi.

    Emprunte les connexions au pool centralisé (pool.py). Chaque méthode
    ouvre/rend sa connexion via `_cursor()` — le circuit breaker DB
    protège l'ensemble.
    """

    def __init__(self, db_url: str):
        self.db_url = db_url
        init_pool(db_url)  # idempotent

    def close(self):
        pass  # Le pool gère les connexions

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

    # --- States ---

    def save_state(self, state: SelfState) -> SelfState:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """INSERT INTO selfmodel_states
                   (yesod_stats, hod_stats, netzach_stats,
                    tiferet_stats, gevurah_stats, chesed_stats,
                    known_biases, predicted_weaknesses, predicted_strengths,
                    model_confidence)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING *""",
                (
                    json.dumps(state.yesod_stats),
                    json.dumps(state.hod_stats),
                    json.dumps(state.netzach_stats),
                    json.dumps(state.tiferet_stats),
                    json.dumps(state.gevurah_stats),
                    json.dumps(state.chesed_stats),
                    json.dumps(state.known_biases),
                    json.dumps(state.predicted_weaknesses),
                    json.dumps(state.predicted_strengths),
                    state.model_confidence,
                ),
            )
            return _row_to_state(cur.fetchone())

    def get_latest_state(self) -> SelfState | None:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM selfmodel_states ORDER BY captured_at DESC LIMIT 1"
            )
            row = cur.fetchone()
            return _row_to_state(row) if row else None

    def get_states(self, limit: int = 10) -> list[SelfState]:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM selfmodel_states ORDER BY captured_at DESC LIMIT %s",
                (limit,),
            )
            return [_row_to_state(r) for r in cur.fetchall()]

    # --- Predictions ---

    def save_prediction(self, pred: Prediction) -> Prediction:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """INSERT INTO selfmodel_predictions
                   (prediction, domain, predicted_error_type,
                    predicted_confidence, prediction_accuracy_running)
                   VALUES (%s, %s, %s, %s, %s)
                   RETURNING *""",
                (
                    pred.prediction,
                    pred.domain,
                    pred.predicted_error_type,
                    pred.predicted_confidence,
                    pred.prediction_accuracy_running,
                ),
            )
            return _row_to_prediction(cur.fetchone())

    def verify_prediction(
        self, prediction_id: UUID, was_correct: bool, actual_outcome: str = "",
    ) -> Prediction | None:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """UPDATE selfmodel_predictions
                   SET verified_at = NOW(), was_correct = %s, actual_outcome = %s
                   WHERE id = %s RETURNING *""",
                (was_correct, actual_outcome, prediction_id),
            )
            row = cur.fetchone()
            return _row_to_prediction(row) if row else None

    def get_predictions(
        self,
        domain: str | None = None,
        verified_only: bool = False,
        limit: int = 50,
    ) -> list[Prediction]:
        clauses: list[str] = []
        params: list = []
        if domain:
            clauses.append("domain = %s")
            params.append(domain)
        if verified_only:
            clauses.append("was_correct IS NOT NULL")

        where = "WHERE " + " AND ".join(clauses) if clauses else ""
        params.append(limit)

        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"SELECT * FROM selfmodel_predictions {where} "
                f"ORDER BY predicted_at DESC LIMIT %s",
                params,
            )
            return [_row_to_prediction(r) for r in cur.fetchall()]

    def get_prediction_accuracy(self, domain: str | None = None) -> float | None:
        """Taux de prédictions correctes (calibration du SelfModel)."""
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if domain:
                cur.execute(
                    """SELECT COUNT(*) FILTER (WHERE was_correct = true) AS correct,
                              COUNT(*) AS total
                       FROM selfmodel_predictions
                       WHERE was_correct IS NOT NULL AND domain = %s""",
                    (domain,),
                )
            else:
                cur.execute(
                    """SELECT COUNT(*) FILTER (WHERE was_correct = true) AS correct,
                              COUNT(*) AS total
                       FROM selfmodel_predictions
                       WHERE was_correct IS NOT NULL"""
                )
            row = cur.fetchone()
            if not row or row["total"] == 0:
                return None
            return round(row["correct"] / row["total"], 4)

    # --- Biases ---

    def save_bias(self, bias: BiasEntry) -> BiasEntry:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """INSERT INTO selfmodel_biases
                   (bias_type, description, evidence, severity,
                    domain, mitigation, still_active)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)
                   RETURNING *""",
                (
                    bias.bias_type,
                    bias.description,
                    json.dumps(bias.evidence),
                    bias.severity,
                    bias.domain,
                    bias.mitigation,
                    bias.still_active,
                ),
            )
            return _row_to_bias(cur.fetchone())

    def get_active_biases(self, domain: str | None = None) -> list[BiasEntry]:
        if domain:
            query = ("SELECT * FROM selfmodel_biases "
                     "WHERE still_active = true AND domain = %s "
                     "ORDER BY severity DESC")
            params: tuple = (domain,)
        else:
            query = ("SELECT * FROM selfmodel_biases "
                     "WHERE still_active = true ORDER BY severity DESC")
            params = ()

        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            return [_row_to_bias(r) for r in cur.fetchall()]

    def deactivate_bias(self, bias_id: UUID) -> BiasEntry | None:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """UPDATE selfmodel_biases SET still_active = false
                   WHERE id = %s RETURNING *""",
                (bias_id,),
            )
            row = cur.fetchone()
            return _row_to_bias(row) if row else None

    def get_biases(self, limit: int = 50) -> list[BiasEntry]:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM selfmodel_biases ORDER BY detected_at DESC LIMIT %s",
                (limit,),
            )
            return [_row_to_bias(r) for r in cur.fetchall()]

    # --- Evolution ---

    def save_evolution(self, snap: EvolutionSnapshot) -> EvolutionSnapshot:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """INSERT INTO selfmodel_evolution
                   (yesod_health, hod_health, netzach_health,
                    tiferet_health, gevurah_health, chesed_health,
                    overall_health, trend, trend_details)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING *""",
                (
                    snap.yesod_health, snap.hod_health, snap.netzach_health,
                    snap.tiferet_health, snap.gevurah_health, snap.chesed_health,
                    snap.overall_health, snap.trend,
                    json.dumps(snap.trend_details),
                ),
            )
            return _row_to_evolution(cur.fetchone())

    def get_latest_evolution(self) -> EvolutionSnapshot | None:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM selfmodel_evolution ORDER BY snapshot_at DESC LIMIT 1"
            )
            row = cur.fetchone()
            return _row_to_evolution(row) if row else None

    def get_evolution_history(self, limit: int = 30) -> list[EvolutionSnapshot]:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM selfmodel_evolution ORDER BY snapshot_at DESC LIMIT %s",
                (limit,),
            )
            return [_row_to_evolution(r) for r in cur.fetchall()]

    # --- External insights (bridge I2) ---

    def save_external_insight(
        self,
        source_module: str,
        source_id,
        description: str,
        confidence: float = 0.5,
        domain: str | None = None,
        novelty_score: float | None = None,
    ) -> bool:
        """Persister un insight ingéré depuis un module externe.

        Idempotent via UNIQUE (source_module, source_id) : une ré-ingestion
        du même insight retourne False sans lever.

        Returns:
            True si inséré, False si doublon (ON CONFLICT).
        """
        with self._cursor() as cur:
            cur.execute(
                """INSERT INTO selfmodel_external_insights
                   (source_module, source_id, description, confidence,
                    domain, novelty_score)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   ON CONFLICT (source_module, source_id) DO NOTHING""",
                (source_module, source_id, description, confidence,
                 domain, novelty_score),
            )
            return cur.rowcount > 0
