"""Build and persist Phase 1A safe improve reports."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

from etzchaim._paths import state_dir
from etzchaim.metacognition.actions import choose_top_issue, synthesize_actions
from etzchaim.metacognition.collectors import collect_events
from etzchaim.metacognition.faculties import evaluate_faculties_for_event


def utc_now() -> datetime:
    return datetime.now(UTC)


def _timestamp(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def _planned_paths(now: datetime) -> dict[str, str]:
    base = state_dir()
    return {
        "report": str(base / "runs" / f"improve-{_timestamp(now)}.md"),
        "state": str(base / "state" / "last_improve_run.json"),
        "ledger": str(base / "state" / "improve_ledger.jsonl"),
    }


def _action_for_top_issue(payload: dict) -> dict | None:
    top_issue = payload.get("top_issue")
    actions = payload.get("proposed_actions", [])
    if not actions:
        return None
    if not top_issue:
        return actions[0]
    top_issue_id = top_issue.get("id")
    for action in actions:
        if top_issue_id in action.get("event_ids", []):
            return action
    return actions[0]


def _action_for_event(event: object | None, actions: list) -> object | None:
    if not actions:
        return None
    if event is None:
        return actions[0]
    event_id = getattr(event, "id", None)
    for action in actions:
        if event_id in getattr(action, "event_ids", []):
            return action
    return actions[0]


def _ledger_entry(payload: dict) -> dict:
    top_issue = payload.get("top_issue") or {}
    action = _action_for_top_issue(payload) or {}
    guardian = payload.get("faculty_evaluation", {}).get("guardian", {})
    return {
        "timestamp": payload["generated_at"],
        "top_issue_id": top_issue.get("id"),
        "action_id": action.get("id"),
        "action_type": action.get("type"),
        "applies_patch": action.get("applies_patch", False),
        "verified": top_issue.get("verified"),
        "verification_result": top_issue.get("verification_result"),
        "guardian_verdict": guardian.get("verdict", "unavailable"),
    }


def build_run_payload(
    *,
    dry_run: bool,
    repo_root: Path | str | None = None,
    now: datetime | None = None,
    faculty_adapters: Mapping[str, object] | None = None,
) -> dict:
    current = now or utc_now()
    root = Path(repo_root or Path.cwd())
    events = collect_events(root)
    top_issue = choose_top_issue(events)
    actions = synthesize_actions(events)
    top_action = _action_for_event(top_issue, actions)
    faculty_evaluation = evaluate_faculties_for_event(
        top_issue,
        top_action,
        adapters=faculty_adapters,
    )

    payload = {
        "status": "dry-run" if dry_run else "ready",
        "dry_run": dry_run,
        "generated_at": current.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "events": [event.to_dict() for event in events],
        "top_issue": top_issue.to_dict() if top_issue else None,
        "proposed_actions": [action.to_dict() for action in actions],
        "faculty_evaluation": faculty_evaluation,
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
                f"- Verified: `{top_issue.get('verified')}`",
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
                f"- Verified: `{event.get('verified')}`",
                "- Evidence:",
            ]
        )
        lines.extend(f"  - {item}" for item in event["evidence"])
        verification_result = event.get("verification_result")
        if verification_result:
            lines.extend(
                [
                    "- Verification result:",
                    f"  - Command: `{verification_result.get('command')}`",
                    f"  - Exit code: `{verification_result.get('exit_code')}`",
                    f"  - Passed: `{verification_result.get('passed')}`",
                    f"  - Duration seconds: `{verification_result.get('duration_seconds')}`",
                ]
            )
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

    faculty_evaluation = payload.get("faculty_evaluation", {})
    failure_insight = faculty_evaluation.get("failure_insight", {})
    guardian = faculty_evaluation.get("guardian", {})
    intent = faculty_evaluation.get("intent", {})
    lines.extend(
        [
            "## Faculty Bridge",
            "",
            "### FailureToInsight",
            "",
            f"- Status: `{failure_insight.get('status')}`",
            f"- Source: `{failure_insight.get('source')}`",
            f"- Hypothesis: {failure_insight.get('hypothesis')}",
            "",
            "### Guardian",
            "",
            f"- Verdict: `{guardian.get('verdict')}`",
            f"- Confidence: `{guardian.get('confidence')}`",
            f"- Reason: {guardian.get('reason')}",
            f"- Active biases: `{', '.join(guardian.get('active_biases') or [])}`",
            "",
            "### IntentKeeper",
            "",
            f"- Status: `{intent.get('status')}`",
            f"- Intent ID: `{intent.get('intent_id')}`",
            f"- Summary: {intent.get('summary')}",
            "",
        ]
    )

    return "\n".join(lines).rstrip() + "\n"


def run_improve_once(
    *,
    dry_run: bool,
    repo_root: Path | str | None = None,
    now: datetime | None = None,
    faculty_adapters: Mapping[str, object] | None = None,
) -> dict:
    current = now or utc_now()
    payload = build_run_payload(
        dry_run=dry_run,
        repo_root=repo_root,
        now=current,
        faculty_adapters=faculty_adapters,
    )
    if dry_run:
        return payload

    paths = _planned_paths(current)
    payload["status"] = "written"
    payload["written"] = paths

    report_path = Path(paths["report"])
    state_path = Path(paths["state"])
    ledger_path = Path(paths["ledger"])
    report_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_markdown(payload), encoding="utf-8")
    state_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    with ledger_path.open("a", encoding="utf-8") as ledger_file:
        ledger_file.write(json.dumps(_ledger_entry(payload), sort_keys=True) + "\n")
    return payload
