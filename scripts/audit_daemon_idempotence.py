"""Audit d'idempotence du daemon — pre-requis pour long-trajectoire 90j.

Sprint 1.2 — verifie que les ecritures critiques du daemon sont
idempotentes : un cycle execute deux fois de suite ne doit pas creer
de divergence (sauf changements legitimes : nouvelles donnees externes,
nouveaux insights generes par exploration, etc.).

Methodologie :
    1. Snapshot etat initial (COUNT + checksum dernieres rows par table)
    2. Run cycle daemon #1 + snapshot
    3. Run cycle daemon #2 (court intervalle) + snapshot
    4. Detect divergences inattendues entre #1 et #2

Tables auditees :
    - epistememory (memoire doctrinale)
    - selfmap_competence (carte des competences)
    - partzufim_state (etats Partzufim)
    - active_intentions (intentions actives)

Usage :
    python scripts/audit_daemon_idempotence.py
    python scripts/audit_daemon_idempotence.py --task hitbonenut
    python scripts/audit_daemon_idempotence.py --json > audit_report.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DB_URL = os.environ.get("DB_URL", "postgresql://localhost/etz_chaim")

# Tables critiques pour la collecte long-trajectoire 90j
AUDITED_TABLES = [
    ("epistememory", "id", "updated_at"),
    ("selfmap_competence", "domain", "updated_at"),
    ("partzufim_state", "partzuf_name", "updated_at"),
    ("active_intentions", "id", "created_at"),
]


@dataclass
class TableSnapshot:
    """Snapshot d'une table a un instant t."""

    table: str
    row_count: int
    last_id_or_key: str | None
    last_n_rows_hash: str  # MD5 hash des 10 dernieres rows
    timestamp: float = field(default_factory=time.time)


@dataclass
class AuditReport:
    """Rapport d'audit complet."""

    initial_snapshots: list[TableSnapshot] = field(default_factory=list)
    after_cycle_1: list[TableSnapshot] = field(default_factory=list)
    after_cycle_2: list[TableSnapshot] = field(default_factory=list)
    divergences: list[dict[str, Any]] = field(default_factory=list)
    cycle_1_duration_s: float = 0.0
    cycle_2_duration_s: float = 0.0
    verdict: str = "PENDING"

    def to_dict(self) -> dict[str, Any]:
        return {
            "initial_snapshots": [asdict(s) for s in self.initial_snapshots],
            "after_cycle_1": [asdict(s) for s in self.after_cycle_1],
            "after_cycle_2": [asdict(s) for s in self.after_cycle_2],
            "divergences": self.divergences,
            "cycle_1_duration_s": self.cycle_1_duration_s,
            "cycle_2_duration_s": self.cycle_2_duration_s,
            "verdict": self.verdict,
        }


def snapshot_table(
    table: str, key_col: str, ts_col: str, db_url: str = DB_URL
) -> TableSnapshot:
    """Capturer un snapshot d'une table."""
    from pool import get_pool, init_pool  # type: ignore[import-not-found]

    init_pool(db_url)
    pool = get_pool()
    conn = pool.getconn()
    conn.autocommit = True
    try:
        cur = conn.cursor()

        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]

        cur.execute(
            f"SELECT {key_col} FROM {table} ORDER BY {ts_col} DESC NULLS LAST LIMIT 1"
        )
        last_row = cur.fetchone()
        last_key = str(last_row[0]) if last_row else None

        cur.execute(
            f"SELECT * FROM {table} ORDER BY {ts_col} DESC NULLS LAST LIMIT 10"
        )
        last_rows = cur.fetchall()
        rows_str = "|".join(
            "_".join(str(v) for v in row) for row in last_rows
        )
        rows_hash = hashlib.md5(rows_str.encode()).hexdigest()

        cur.close()
        return TableSnapshot(
            table=table,
            row_count=count,
            last_id_or_key=last_key,
            last_n_rows_hash=rows_hash,
        )
    finally:
        pool.putconn(conn)


def snapshot_all() -> list[TableSnapshot]:
    """Snapshot toutes les tables critiques."""
    snaps: list[TableSnapshot] = []
    for table, key_col, ts_col in AUDITED_TABLES:
        try:
            snaps.append(snapshot_table(table, key_col, ts_col))
        except Exception as exc:
            print(f"WARN: snapshot {table} failed: {exc}", file=sys.stderr)
            snaps.append(TableSnapshot(
                table=table, row_count=-1, last_id_or_key=None,
                last_n_rows_hash=f"ERROR:{exc}",
            ))
    return snaps


def run_daemon_cycle(task: str | None = None) -> float:
    """Lancer un cycle daemon (ou une task specifique) et mesurer la duree."""
    cmd = [sys.executable, "daemon.py"]
    if task:
        cmd += ["--task", task]
    else:
        cmd += ["--once"]

    t0 = time.time()
    result = subprocess.run(
        cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=300
    )
    duration = time.time() - t0

    if result.returncode != 0:
        print(f"WARN: daemon exit code {result.returncode}", file=sys.stderr)
        if result.stderr:
            print(result.stderr[-500:], file=sys.stderr)

    return duration


def find_divergences(
    snap_a: list[TableSnapshot], snap_b: list[TableSnapshot]
) -> list[dict[str, Any]]:
    """Detecter les divergences entre deux snapshots."""
    divergences: list[dict[str, Any]] = []
    by_table_a = {s.table: s for s in snap_a}
    by_table_b = {s.table: s for s in snap_b}

    for table in by_table_a:
        a = by_table_a[table]
        b = by_table_b.get(table)
        if not b:
            divergences.append({
                "table": table,
                "kind": "missing_in_b",
            })
            continue
        if a.row_count != b.row_count:
            divergences.append({
                "table": table,
                "kind": "row_count_change",
                "a": a.row_count,
                "b": b.row_count,
                "delta": b.row_count - a.row_count,
            })
        if a.last_n_rows_hash != b.last_n_rows_hash:
            divergences.append({
                "table": table,
                "kind": "hash_change",
                "a_hash": a.last_n_rows_hash,
                "b_hash": b.last_n_rows_hash,
                "note": (
                    "rows changed: insert/update on tail. Acceptable if "
                    "task generates new insights, suspicious if not."
                ),
            })

    return divergences


def assess_verdict(report: AuditReport) -> str:
    """Verdict global d'idempotence."""
    if not report.divergences:
        return "PASS — fully idempotent"

    # Divergences entre cycle_1 et cycle_2 (seules les changements
    # inattendus comptent — un cycle daemon legitime peut creer des rows)
    cycle_to_cycle_divs = find_divergences(
        report.after_cycle_1, report.after_cycle_2
    )

    if not cycle_to_cycle_divs:
        return "PASS — divergences only between initial and cycle_1 (legitimate cycle work)"

    critical = [d for d in cycle_to_cycle_divs if d["kind"] == "row_count_change"]
    if critical:
        return f"FAIL — {len(critical)} unexpected row insertions between consecutive cycles"

    return f"WARN — {len(cycle_to_cycle_divs)} hash changes between cycles (review needed)"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", help="Run a specific daemon task instead of full cycle")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--interval", type=int, default=2, help="Seconds between cycles")
    args = parser.parse_args()

    report = AuditReport()

    print("=" * 60, file=sys.stderr)
    print("Daemon idempotence audit (Sprint 1.2)", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    print("\n[1/5] Snapshot initial...", file=sys.stderr)
    report.initial_snapshots = snapshot_all()
    for s in report.initial_snapshots:
        print(f"  {s.table:25s}: {s.row_count:6d} rows, hash={s.last_n_rows_hash[:8]}",
              file=sys.stderr)

    print(f"\n[2/5] Cycle daemon #1 (task={args.task or 'all'})...", file=sys.stderr)
    report.cycle_1_duration_s = run_daemon_cycle(args.task)
    print(f"  duree: {report.cycle_1_duration_s:.1f}s", file=sys.stderr)

    print("\n[3/5] Snapshot apres cycle 1...", file=sys.stderr)
    report.after_cycle_1 = snapshot_all()
    initial_to_1 = find_divergences(report.initial_snapshots, report.after_cycle_1)
    for d in initial_to_1:
        print(f"  {d['table']}: {d['kind']} ({d.get('delta', '')})", file=sys.stderr)

    print(f"\n[4/5] Wait {args.interval}s puis cycle daemon #2...", file=sys.stderr)
    time.sleep(args.interval)
    report.cycle_2_duration_s = run_daemon_cycle(args.task)
    print(f"  duree: {report.cycle_2_duration_s:.1f}s", file=sys.stderr)

    print("\n[5/5] Snapshot apres cycle 2 + analyse divergences...", file=sys.stderr)
    report.after_cycle_2 = snapshot_all()
    cycle_1_to_2 = find_divergences(report.after_cycle_1, report.after_cycle_2)
    report.divergences = cycle_1_to_2

    for d in cycle_1_to_2:
        print(f"  {d['table']}: {d['kind']} ({d.get('delta', '')})", file=sys.stderr)

    report.verdict = assess_verdict(report)
    print(f"\nVerdict: {report.verdict}", file=sys.stderr)

    if args.json:
        print(json.dumps(report.to_dict(), indent=2, default=str))

    return 0 if "PASS" in report.verdict else 1


if __name__ == "__main__":
    sys.exit(main())
