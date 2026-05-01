"""CycleRunner — main autopilot loop.

One cycle :
1. Load frozen snapshot (mission + operator + autopilot context).
2. Pick the next task (highest-priority unimplemented spec, or paper draft,
   or pivot audit, depending on schedule).
3. Spawn an IsolatedWorker for the chosen skill.
4. Run pre-push gates : `check_public_surface.sh` + `pytest`.
5. Open a PR with neutral title/body if gates pass.
6. Append cycle record to FTS-indexed log + ShareGPT trajectory.
7. Update state + budget. Return a structured result.

This module is invoked from `daemon_tasks/auto_dev.py` (created elsewhere).
For dry runs : `python -m etzchaim.autopilot.loop --dry-run`.
"""

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass, field
from pathlib import Path

from etzchaim.autopilot.budget import TokenBudget
from etzchaim.autopilot.config import AutopilotConfig
from etzchaim.autopilot.delegation import WorkerSpawner
from etzchaim.autopilot.memory.search import CycleRecord, insert_cycle
from etzchaim.autopilot.memory.snapshot import load_frozen_snapshot
from etzchaim.autopilot.memory.trajectory import Trajectory, append_trajectory
from etzchaim.autopilot.skills import parse_skill_file
from etzchaim.autopilot.state import AutopilotState

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = Path(__file__).resolve().parent / "skills"
SPECS_DIR = REPO_ROOT / "specs"


def _consecutive_failures(state: AutopilotState) -> int:
    """Count consecutive failed cycles from the FTS-indexed cycle log."""
    try:
        from etzchaim.autopilot.memory.search import recent_cycles
        rows = recent_cycles(limit=10)
    except Exception:
        return 0
    failures = 0
    for row in rows:
        if row.status == "failed":
            failures += 1
        else:
            break
    return failures


def _notify(title: str, body: str) -> None:
    """Best-effort macOS notification. No-op on other platforms or on error."""
    import platform
    import subprocess as sp
    if platform.system() != "Darwin":
        return
    try:
        sp.run(
            [
                "osascript",
                "-e",
                f'display notification "{body}" with title "{title}"',
            ],
            timeout=5,
            capture_output=True,
            check=False,
        )
    except Exception:
        pass


@dataclass
class CycleOutcome:
    status: str  # ok | skipped | failed | dry-run
    task_id: str = ""
    skill: str = ""
    pr_url: str = ""
    summary: str = ""
    metadata: dict[str, str] = field(default_factory=dict)


def pick_next_task() -> tuple[str, str] | None:
    """Return (task_id, skill_name) for the next thing to work on, or None.

    Scans `specs/` recursively. Specs are picked alphabetically across the
    full tree. Use numeric prefixes (`01_`, `02_`) on filenames to enforce
    dependency ordering. Subdirectories (e.g. `rectifiers/`) are walked
    after top-level files at the same prefix level.

    Picks `implement-rectifier` as skill when the spec lives under
    `specs/rectifiers/`, else `implement-spec`.
    """
    if not SPECS_DIR.exists():
        return None
    for spec_path in sorted(SPECS_DIR.rglob("*.md")):
        marker = spec_path.with_suffix(".implemented")
        if marker.exists():
            continue
        # Resolve task id (relative path stem) and skill choice.
        rel = spec_path.relative_to(SPECS_DIR)
        task_id = "/".join(rel.with_suffix("").parts)
        if rel.parts and rel.parts[0] == "rectifiers":
            return task_id, "implement-rectifier"
        return task_id, "implement-spec"
    return None


def _load_skill(skill_name: str) -> tuple[str, str]:
    """Return (skill_body, skill_path)."""
    skill_dir = SKILLS_DIR / skill_name.replace("-", "_")
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.exists():
        raise FileNotFoundError(f"skill not found: {skill_file}")
    fm, body = parse_skill_file(skill_file)
    return body, str(skill_file)


def run_one_cycle(
    config: AutopilotConfig | None = None,
    state: AutopilotState | None = None,
    dry_run: bool = False,
) -> CycleOutcome:
    """Execute exactly one autopilot cycle."""
    cfg = config or AutopilotConfig.from_file(
        REPO_ROOT / "etzchaim" / "deploy" / "config.yaml"
    )
    st = state or AutopilotState.load()

    if not cfg.enabled and not dry_run:
        return CycleOutcome(status="skipped", summary="autopilot disabled in config")

    budget = TokenBudget(cfg, st)
    if not budget.check().allowed:
        return CycleOutcome(
            status="skipped", summary="monthly token budget exhausted"
        )

    pick = pick_next_task()
    if pick is None:
        return CycleOutcome(status="skipped", summary="no pending tasks")
    task_id, skill_name = pick

    snapshot = load_frozen_snapshot()
    skill_body, _skill_path = _load_skill(skill_name)

    started = time.time()
    summary_parts: list[str] = [f"task={task_id}", f"skill={skill_name}"]

    if dry_run:
        outcome = CycleOutcome(
            status="dry-run",
            task_id=task_id,
            skill=skill_name,
            summary="dry run; no worker dispatched",
            metadata={"started": str(int(started))},
        )
        # Log the dry-run for traceability.
        insert_cycle(
            CycleRecord(
                started_at=started,
                completed_at=time.time(),
                task_id=task_id,
                status="dry-run",
                summary="dry-run cycle, no worker invoked",
            )
        )
        return outcome

    # Halt-after-N-consecutive-failures circuit breaker.
    if _consecutive_failures(st) >= 3:
        return CycleOutcome(
            status="skipped",
            summary="halted after 3 consecutive failures; flip autopilot.enabled or clear failure counter",
        )

    spawner = WorkerSpawner(cfg)
    worker = spawner.spawn()
    task_brief = (
        f"Implement spec `specs/{task_id}.md` per the `{skill_name}` skill. "
        f"Stop after opening the PR; do not merge."
    )

    result = worker.run(
        skill_name=skill_name,
        skill_body=skill_body,
        task_brief=task_brief,
        snapshot=snapshot,
        cwd=str(REPO_ROOT),
        timeout=900,
    )

    completed = time.time()
    summary_parts.append(f"success={result.success}")
    summary = "; ".join(summary_parts)

    # Trajectory
    traj = Trajectory(model=cfg.worker, completed=result.success)
    traj.add_turn("system", "Autopilot dispatch")
    traj.add_turn("user", task_brief)
    traj.add_turn("assistant", result.output[:8000])
    traj.metadata = {
        "task_id": task_id,
        "skill": skill_name,
        "duration_ms": str(result.duration_ms),
    }
    append_trajectory(traj)

    # Cycle log
    insert_cycle(
        CycleRecord(
            started_at=started,
            completed_at=completed,
            task_id=task_id,
            status="ok" if result.success else "failed",
            summary=summary + "\n" + (result.output[:1000] if result.output else ""),
        )
    )

    st.last_autopilot = completed
    st.save()

    if result.success:
        _notify(
            "Etz Chaim Autopilot",
            f"Cycle ok : {task_id} ({skill_name})",
        )
        spec_md = SPECS_DIR / f"{task_id}.md"
        if spec_md.exists():
            spec_md.with_suffix(".implemented").touch()

    return CycleOutcome(
        status="ok" if result.success else "failed",
        task_id=task_id,
        skill=skill_name,
        summary=summary,
        metadata={
            "duration_ms": str(result.duration_ms),
            "exit_code": result.metadata.get("exit_code", "?"),
        },
    )


def _cli() -> int:
    parser = argparse.ArgumentParser(description="Autopilot cycle runner")
    parser.add_argument(
        "--dry-run", action="store_true", help="pick + log a task without dispatching"
    )
    args = parser.parse_args()

    outcome = run_one_cycle(dry_run=args.dry_run)
    print(f"status: {outcome.status}")
    if outcome.task_id:
        print(f"task: {outcome.task_id} ({outcome.skill})")
    if outcome.summary:
        print(f"summary: {outcome.summary}")
    return 0 if outcome.status in {"ok", "dry-run", "skipped"} else 1


if __name__ == "__main__":
    raise SystemExit(_cli())
