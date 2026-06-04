"""Rank metacognition events and map them to proposed safe actions."""

from __future__ import annotations

from collections.abc import Iterable

from etzchaim.metacognition.events import MetacognitionEvent, ProposedAction


def _event_sort_key(event: MetacognitionEvent) -> tuple[int, str]:
    return (event.priority, event.id)


def choose_top_issue(events: Iterable[MetacognitionEvent]) -> MetacognitionEvent | None:
    """Return the highest-priority event, with a stable id tie-breaker."""

    event_list = list(events)
    if not event_list:
        return None
    return max(event_list, key=_event_sort_key)


def sort_events(events: Iterable[MetacognitionEvent]) -> list[MetacognitionEvent]:
    return sorted(events, key=lambda event: (-event.priority, event.id))


def propose_action(event: MetacognitionEvent) -> ProposedAction:
    if event.id == "known-p0-psql-helper-pollution":
        return ProposedAction(
            id="patch-known-p0-psql-helper-pollution",
            type="patch",
            title="Patch the known psql helper pollution",
            description=(
                "Add a narrow regression test and reset the psql helper state between "
                "tests; do not modify PostgreSQL services in this phase."
            ),
            event_ids=[event.id],
            verification_command=event.verification_command,
        )

    if event.source == "python":
        return ProposedAction(
            id=f"rule-{event.id}",
            type="rule",
            title=f"Record environment rule for {event.title}",
            description=(
                "Capture the local Python command/version drift as an explicit setup "
                "rule before changing packaging."
            ),
            event_ids=[event.id],
            verification_command=event.verification_command,
        )

    if event.source in {"doctor", "status"}:
        return ProposedAction(
            id=f"alert-{event.id}",
            type="alert",
            title=f"Alert on {event.title}",
            description=(
                "Report the local environment weakness without starting services or "
                "changing Docker/PostgreSQL state."
            ),
            event_ids=[event.id],
            verification_command=event.verification_command,
        )

    return ProposedAction(
        id=f"alert-{event.id}",
        type="alert",
        title=f"Review {event.title}",
        description="Keep this observed weakness visible for the next validated phase.",
        event_ids=[event.id],
        verification_command=event.verification_command,
    )


def propose_actions(events: Iterable[MetacognitionEvent]) -> list[ProposedAction]:
    return [propose_action(event) for event in sort_events(events)]
