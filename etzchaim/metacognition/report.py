"""Build and persist Phase 1A safe improve reports."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from etzchaim._paths import state_dir
from etzchaim.metacognition.actions import choose_top_issue, propose_actions
from etzchaim.metacognition.collectors import collect_events


def utc_now() -> datetime:
    return datetime.now(UTC)


def _timestamp(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def _planned_paths(now: datetime) -> dict[str, str]:
    base = state_dir()
    return {
        "report": str(base / "runs" / f"improve-{_timestamp(now)}.md"),
        "state": str(base / "state" / "last_improve_run.json"),
    }


def build_run_payload(
    *,
    dry_run: bool,
    repo_root: Path | str | None = None,
    now: datetime | None = None,
) -> dict:
    current = now or utc_now()
    root = Path(repo_root or Path.cwd())
    events = collect_events(root)
    top_issue = choose_top_issue(events)
    actions = propose_actions(events)

    payload = {
        "status": "dry-run" if dry_run else "ready",
        "dry_run": dry_run,
        "generated_at": current.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "events": [event.to_dict() for event in events],
        "top_issue": top_issue.to_dict() if top_issue else None,
        "proposed_actions": [action.to_dict() for action in actions],
    }
    if dry_run:
        payload["would_write"] = _planned_paths(current)
    return payload


def render_markdown(payload: dict) -> str:
    lines = [
        "# Etz Chaim Improve Run",
        "",
        f"Generated at: `{payload['generated_at']}`",
        f"Dry run: `{payload['dry_run']}`",
        f"Status: `{payload['status']}`",
        "",
        "## Top Issue",
        "",
    ]
    top_issue = payload.get("top_issue")
    if top_issue:
        lines.extend(
            [
                f"- ID: `{top_issue['id']}`",
                f"- Source: `{top_issue['source']}`",
                f"- Severity: `{top_issue['severity']}`",
                f"- Priority: `{top_issue['priority']}`",
                f"- Title: {top_issue['title']}",
                f"- Verification: `{top_issue['verification_command']}`",
                "",
            ]
        )
    else:
        lines.extend(["No issue observed.", ""])

    lines.extend(["## Events", ""])
    for event in payload["events"]:
        lines.extend(
            [
                f"### {event['id']}",
                "",
                f"- Source: `{event['source']}`",
                f"- Severity: `{event['severity']}`",
                f"- Priority: `{event['priority']}`",
                f"- Title: {event['title']}",
                f"- Description: {event['description']}",
                f"- Verification: `{event['verification_command']}`",
                "- Evidence:",
            ]
        )
        lines.extend(f"  - {item}" for item in event["evidence"])
        lines.append("")

    lines.extend(["## Proposed Actions", ""])
    for action in payload["proposed_actions"]:
        lines.extend(
            [
                f"### {action['id']}",
                "",
                f"- Type: `{action['type']}`",
                f"- Applies patch automatically: `{action['applies_patch']}`",
                f"- Title: {action['title']}",
                f"- Description: {action['description']}",
                f"- Event IDs: `{', '.join(action['event_ids'])}`",
                f"- Verification: `{action['verification_command']}`",
                "",
            ]
        )
    if not payload["proposed_actions"]:
        lines.extend(["No action proposed.", ""])

    return "\n".join(lines).rstrip() + "\n"


def run_improve_once(
    *,
    dry_run: bool,
    repo_root: Path | str | None = None,
    now: datetime | None = None,
) -> dict:
    current = now or utc_now()
    payload = build_run_payload(dry_run=dry_run, repo_root=repo_root, now=current)
    if dry_run:
        return payload

    paths = _planned_paths(current)
    payload["status"] = "written"
    payload["written"] = paths

    report_path = Path(paths["report"])
    state_path = Path(paths["state"])
    report_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_markdown(payload), encoding="utf-8")
    state_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload
