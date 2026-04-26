"""Snapshot des metriques de trajectoire — collecte hebdomadaire 90j.

Sprint 1.2 (preparation Sprint 2) — capture les metriques d'evolution
cognitive necessaires au benchmark long-trajectoire 90j (Claude+Etz vs
Claude-brut).

Tables snapshotees (avec timestamps natifs preserves) :
    - epistememory : confidence moyenne, count par status, contradictions
    - selfmap_competence : score moyen, calibration, novelty
    - partzufim_state : facultes, mochin_state, orientation
    - active_intentions : count, age moyen, completion_rate
    - faculty_reshimot : reshimu accumule par partzuf/faculty
    - hitbonenut_sessions : score progression, principles emergents

Usage :
    python scripts/snapshot_trajectory_metrics.py
        # snapshot dans ~/.etz-chaim/trajectory_snapshots/YYYY-MM-DD.json
    python scripts/snapshot_trajectory_metrics.py --label claude_brut
        # snapshot avec label (cf. Sprint 2 dual instance)
    python scripts/snapshot_trajectory_metrics.py --replay --range 30
        # replay 30 derniers jours pour debug

Format snapshot : JSON, idempotent (rejoue overwrite).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DB_URL = os.environ.get("DB_URL", "postgresql://localhost/etz_chaim")
SNAPSHOT_DIR = Path.home() / ".etz-chaim" / "trajectory_snapshots"


@dataclass
class TrajectoryMetrics:
    """Snapshot complet des metriques d'evolution a un instant t."""

    timestamp: float = field(default_factory=time.time)
    label: str = "default"

    # EpisteMemory
    epistememory_total: int = 0
    epistememory_avg_confidence: float = 0.0
    epistememory_active_count: int = 0
    epistememory_contested_count: int = 0
    epistememory_open_contradictions: int = 0

    # SelfMap (compétence par domaine)
    selfmap_total_domains: int = 0
    selfmap_avg_score: float = 0.0
    selfmap_calibrated_count: int = 0
    selfmap_overconfident_count: int = 0

    # SelfModel (predictions et evolution)
    selfmodel_predictions_total: int = 0
    selfmodel_predictions_correct: int = 0
    selfmodel_evolution_count: int = 0

    # Partzufim
    partzufim_states: dict[str, dict[str, Any]] = field(default_factory=dict)
    partzufim_avg_overall: float = 0.0
    partzufim_gadlut_count: int = 0
    partzufim_panim_count: int = 0

    # Reshimu (memoire cumulative)
    reshimu_total_traces: int = 0
    reshimu_by_partzuf: dict[str, float] = field(default_factory=dict)

    # IntentKeeper
    intentions_active: int = 0
    intentions_completed: int = 0
    intentions_avg_age_hours: float = 0.0

    # Hitbonenut (auto-contemplation)
    hitbonenut_sessions_total: int = 0
    hitbonenut_avg_session_score: float = 0.0
    hitbonenut_principles_emerged: int = 0

    # Sitra Achra (post-Sprint 1.1 : par categorie ontologique)
    sitra_achra_anomalies_klipat_nogah: int = 0
    sitra_achra_anomalies_klippot_haTemeot: int = 0
    sitra_achra_teshuvah_count: int = 0


def _safe_query(cur, sql: str, default: Any = 0) -> Any:
    """Execute a SQL query, return default on error (table missing, etc.)."""
    try:
        cur.execute(sql)
        result = cur.fetchone()
        return result[0] if result and result[0] is not None else default
    except Exception:
        return default


def collect_metrics(label: str = "default", db_url: str = DB_URL) -> TrajectoryMetrics:
    """Collecter tous les metrics d'un instant pour le snapshot."""
    from pool import get_pool, init_pool  # type: ignore[import-not-found]

    init_pool(db_url)
    pool = get_pool()
    conn = pool.getconn()
    conn.autocommit = True
    metrics = TrajectoryMetrics(label=label)

    try:
        cur = conn.cursor()

        # EpisteMemory
        metrics.epistememory_total = _safe_query(
            cur, "SELECT COUNT(*) FROM epistememory"
        )
        metrics.epistememory_avg_confidence = float(_safe_query(
            cur, "SELECT AVG(confidence) FROM epistememory", 0.0
        ) or 0.0)
        metrics.epistememory_active_count = _safe_query(
            cur, "SELECT COUNT(*) FROM epistememory WHERE epistemic_status = 'active'"
        )
        metrics.epistememory_contested_count = _safe_query(
            cur, "SELECT COUNT(*) FROM epistememory WHERE epistemic_status = 'contested'"
        )
        metrics.epistememory_open_contradictions = _safe_query(
            cur,
            "SELECT COUNT(*) FROM epistememory "
            "WHERE contradicts IS NOT NULL AND array_length(contradicts, 1) > 0"
        )

        # SelfMap
        metrics.selfmap_total_domains = _safe_query(
            cur, "SELECT COUNT(DISTINCT domain) FROM selfmap_competence"
        )
        metrics.selfmap_avg_score = float(_safe_query(
            cur, "SELECT AVG(score) FROM selfmap_competence", 0.0
        ) or 0.0)
        metrics.selfmap_calibrated_count = _safe_query(
            cur, "SELECT COUNT(*) FROM selfmap_competence WHERE n_evals >= 5"
        )

        # SelfModel
        metrics.selfmodel_predictions_total = _safe_query(
            cur, "SELECT COUNT(*) FROM selfmodel_predictions"
        )
        metrics.selfmodel_predictions_correct = _safe_query(
            cur,
            "SELECT COUNT(*) FROM selfmodel_predictions "
            "WHERE actual = predicted"
        )
        metrics.selfmodel_evolution_count = _safe_query(
            cur, "SELECT COUNT(*) FROM selfmodel_evolution"
        )

        # Partzufim
        try:
            cur.execute(
                "SELECT name, overall_score, mochin_state, orientation, "
                "faculties FROM partzufim_state"
            )
            for row in cur.fetchall():
                metrics.partzufim_states[row[0]] = {
                    "overall_score": float(row[1]) if row[1] else 0.0,
                    "mochin_state": row[2],
                    "orientation": row[3],
                    "faculties": row[4] if row[4] else {},
                }
            if metrics.partzufim_states:
                scores = [s["overall_score"] for s in metrics.partzufim_states.values()]
                metrics.partzufim_avg_overall = sum(scores) / len(scores)
                metrics.partzufim_gadlut_count = sum(
                    1 for s in metrics.partzufim_states.values()
                    if s["mochin_state"] == "gadlut"
                )
                metrics.partzufim_panim_count = sum(
                    1 for s in metrics.partzufim_states.values()
                    if s["orientation"] == "panim"
                )
        except Exception:
            pass

        # Reshimu
        try:
            cur.execute(
                "SELECT partzuf, SUM(reshimu_value) FROM faculty_reshimot "
                "GROUP BY partzuf"
            )
            for row in cur.fetchall():
                metrics.reshimu_by_partzuf[row[0]] = float(row[1] or 0.0)
            metrics.reshimu_total_traces = _safe_query(
                cur, "SELECT COUNT(*) FROM faculty_reshimot"
            )
        except Exception:
            pass

        # IntentKeeper
        metrics.intentions_active = _safe_query(
            cur, "SELECT COUNT(*) FROM active_intentions WHERE status = 'active'"
        )
        metrics.intentions_completed = _safe_query(
            cur, "SELECT COUNT(*) FROM active_intentions WHERE status = 'completed'"
        )
        metrics.intentions_avg_age_hours = float(_safe_query(
            cur,
            "SELECT AVG(EXTRACT(EPOCH FROM (NOW() - created_at)) / 3600.0) "
            "FROM active_intentions WHERE status = 'active'",
            0.0,
        ) or 0.0)

        # Hitbonenut
        metrics.hitbonenut_sessions_total = _safe_query(
            cur, "SELECT COUNT(*) FROM hitbonenut_sessions"
        )
        metrics.hitbonenut_avg_session_score = float(_safe_query(
            cur, "SELECT AVG(session_score) FROM hitbonenut_sessions", 0.0
        ) or 0.0)
        metrics.hitbonenut_principles_emerged = _safe_query(
            cur, "SELECT COUNT(*) FROM hitbonenut_principles"
        )

        cur.close()
    finally:
        pool.putconn(conn)

    return metrics


def save_snapshot(metrics: TrajectoryMetrics) -> Path:
    """Sauver le snapshot en JSON dans ~/.etz-chaim/trajectory_snapshots/."""
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

    # Format YYYY-MM-DD_label.json (idempotent par jour : overwrite)
    date_str = time.strftime("%Y-%m-%d", time.localtime(metrics.timestamp))
    filename = f"{date_str}_{metrics.label}.json"
    filepath = SNAPSHOT_DIR / filename

    filepath.write_text(json.dumps(asdict(metrics), indent=2, default=str))
    return filepath


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default="default",
                        help="Label snapshot (e.g. claude_etz, claude_brut)")
    parser.add_argument("--print", action="store_true",
                        help="Print metrics on stdout (debug)")
    args = parser.parse_args()

    print(f"Collecting trajectory metrics (label={args.label})...", file=sys.stderr)
    metrics = collect_metrics(label=args.label)

    filepath = save_snapshot(metrics)
    print(f"Snapshot saved: {filepath}", file=sys.stderr)

    summary = {
        "label": metrics.label,
        "timestamp": metrics.timestamp,
        "epistememory_total": metrics.epistememory_total,
        "epistememory_avg_confidence": round(metrics.epistememory_avg_confidence, 3),
        "selfmap_avg_score": round(metrics.selfmap_avg_score, 3),
        "partzufim_avg_overall": round(metrics.partzufim_avg_overall, 3),
        "partzufim_gadlut_count": metrics.partzufim_gadlut_count,
        "intentions_active": metrics.intentions_active,
        "hitbonenut_sessions_total": metrics.hitbonenut_sessions_total,
        "reshimu_total_traces": metrics.reshimu_total_traces,
    }
    print(f"\nSummary:")
    for k, v in summary.items():
        print(f"  {k:35s} {v}", file=sys.stderr)

    if args.print:
        print(json.dumps(asdict(metrics), indent=2, default=str))

    return 0


if __name__ == "__main__":
    sys.exit(main())
