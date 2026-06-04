"""Manual non-permanent runtime loop for safe metacognition cycles."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

from etzchaim._paths import state_dir
from etzchaim.metacognition import report


def utc_now() -> datetime:
    return datetime.now(UTC)


def _timestamp(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def _iso_timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _cycle_id(now: datetime) -> str:
    return f"loop-{_timestamp(now)}"


def _planned_paths() -> dict[str, str]:
    base = state_dir() / "state"
    return {
        "loop_state": str(base / "last_loop_run.json"),
        "loop_heartbeat": str(base / "loop_heartbeat.jsonl"),
    }


def _heartbeat(
    *,
    generated_at: str,
    cycle_id: str,
    status: str,
    improve_payload: dict,
) -> dict:
    top_issue = improve_payload.get("top_issue") or {}
    actions = improve_payload.get("proposed_actions", [])
    guardian = improve_payload.get("faculty_evaluation", {}).get("guardian", {})
    return {
        "timestamp": generated_at,
        "cycle_id": cycle_id,
        "status": status,
        "improve_status": improve_payload.get("status"),
        "top_issue_id": top_issue.get("id"),
        "action_count": len(actions),
        "applies_patch": any(action.get("applies_patch", False) for action in actions),
        "guardian_verdict": guardian.get("verdict", "unavailable"),
    }


def run_loop_once(
    *,
    dry_run: bool,
    repo_root: Path | str | None = None,
    now: datetime | None = None,
    faculty_adapters: Mapping[str, object] | None = None,
) -> dict:
    """Run exactly one bounded runtime loop cycle."""

    current = now or utc_now()
    generated_at = _iso_timestamp(current)
    cycle_id = _cycle_id(current)
    status = "dry-run" if dry_run else "written"

    improve_payload = report.run_improve_once(
        dry_run=dry_run,
        repo_root=repo_root,
        now=current,
        faculty_adapters=faculty_adapters,
    )
    heartbeat = _heartbeat(
        generated_at=generated_at,
        cycle_id=cycle_id,
        status=status,
        improve_payload=improve_payload,
    )

    payload = {
        "status": status,
        "dry_run": dry_run,
        "generated_at": generated_at,
        "cycle_id": cycle_id,
        "heartbeat": heartbeat,
        "improve": improve_payload,
    }
    paths = _planned_paths()
    if dry_run:
        payload["would_write"] = {
            **paths,
            "improve": improve_payload.get("would_write", {}),
        }
        return payload

    payload["written"] = {
        **paths,
        "improve": improve_payload.get("written", {}),
    }
    state_path = Path(paths["loop_state"])
    heartbeat_path = Path(paths["loop_heartbeat"])
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    with heartbeat_path.open("a", encoding="utf-8") as heartbeat_file:
        heartbeat_file.write(json.dumps(heartbeat, sort_keys=True) + "\n")
    return payload
