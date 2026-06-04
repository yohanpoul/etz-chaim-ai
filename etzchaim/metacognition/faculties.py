"""Safe read-only adapters for metacognition faculty signals."""

from __future__ import annotations

from collections.abc import Mapping
from etzchaim.metacognition.events import MetacognitionEvent, ProposedAction

GUARDIAN_VERDICTS = frozenset({"proceed", "caution", "veto", "unavailable"})


def _get(value: object, key: str, default: object = None) -> object:
    if isinstance(value, Mapping):
        return value.get(key, default)
    return getattr(value, key, default)


def _event_domain(event: MetacognitionEvent | None) -> str:
    if event is None:
        return "metacognition"
    return event.source or "metacognition"


def _event_query(
    event: MetacognitionEvent | None,
    action: ProposedAction | None,
) -> str:
    if event is None:
        return "No top issue observed."
    parts = [event.title, event.description]
    if action is not None:
        parts.append(f"Proposed action: {action.title}")
    return " | ".join(part for part in parts if part)


def _as_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_list(value: object) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple | set):
        return list(value)
    return [value]


def _failure_unavailable(reason: str) -> dict:
    return {
        "status": "unavailable",
        "hypothesis": reason,
        "source": "stub",
    }


def _evaluate_failure_insight(
    event: MetacognitionEvent | None,
    action: ProposedAction | None,
    adapter: object | None,
) -> dict:
    if adapter is None:
        return _failure_unavailable(
            "FailureToInsight DB adapter is not configured for this P2C read-only run."
        )

    domain = _event_domain(event)
    try:
        if hasattr(adapter, "guide_next_hypothesis"):
            guidance = adapter.guide_next_hypothesis(domain=domain)
            recurring = _as_list(_get(guidance, "recurring_root_causes", []))
            avoid = _as_list(_get(guidance, "avoid_patterns", []))
            promising = _as_list(_get(guidance, "promising_directions", []))
            fragments: list[str] = []
            if recurring:
                fragments.append(f"Recurring root causes: {', '.join(map(str, recurring))}")
            if avoid:
                fragments.append(f"Avoid patterns: {', '.join(map(str, avoid))}")
            if promising:
                fragments.append(
                    f"Promising directions: {', '.join(map(str, promising))}"
                )
            if not fragments:
                fragments.append("No recurring failure pattern reported.")
            return {
                "status": "available",
                "hypothesis": "; ".join(fragments),
                "source": "failuretoinsight.guide_next_hypothesis",
                "confidence": _as_float(_get(guidance, "confidence")),
            }

        if hasattr(adapter, "analyze_failure"):
            return _failure_unavailable(
                "FailureToInsight analyze_failure is not read-only by default; "
                "provide guide_next_hypothesis for P2C-bis."
            )
    except Exception as exc:
        return _failure_unavailable(f"{type(exc).__name__}: {exc}")

    return _failure_unavailable(
        "FailureToInsight adapter has no supported P2C read-only method."
    )


def _evaluate_guardian(
    event: MetacognitionEvent | None,
    action: ProposedAction | None,
    adapter: object | None,
) -> dict:
    if adapter is None:
        return {
            "verdict": "unavailable",
            "confidence": None,
            "reason": "No explicit Guardian adapter/context is configured for this P2C-bis read-only run.",
            "active_biases": [],
        }

    try:
        raw = adapter.evaluate_confidence(
            domain=_event_domain(event),
            query=_event_query(event, action),
        )
        verdict = str(raw.get("recommendation") or raw.get("verdict") or "unavailable")
        if verdict not in GUARDIAN_VERDICTS:
            verdict = "unavailable"
        return {
            "verdict": verdict,
            "confidence": _as_float(raw.get("confidence")),
            "reason": str(raw.get("reason") or ""),
            "active_biases": [str(item) for item in _as_list(raw.get("active_biases"))],
        }
    except Exception as exc:
        return {
            "verdict": "unavailable",
            "confidence": None,
            "reason": f"{type(exc).__name__}: {exc}",
            "active_biases": [],
        }


def _evaluate_intent(
    event: MetacognitionEvent | None,
    action: ProposedAction | None,
    adapter: object | None,
) -> dict:
    if adapter is None:
        return {
            "status": "no_active_intent",
            "intent_id": None,
            "summary": "No IntentKeeper adapter configured for this P2C read-only run.",
        }

    try:
        if hasattr(adapter, "summarize_event_intent"):
            raw = adapter.summarize_event_intent(event, action=action)
            return {
                "status": str(raw.get("status") or "no_active_intent"),
                "intent_id": raw.get("intent_id"),
                "summary": str(raw.get("summary") or ""),
            }

        intention_id = getattr(adapter, "active_intent_id", None) or getattr(
            adapter,
            "current_intention_id",
            None,
        )
        if intention_id and hasattr(adapter, "report"):
            return {
                "status": "linked",
                "intent_id": str(intention_id),
                "summary": str(adapter.report(intention_id)),
            }
    except Exception as exc:
        return {
            "status": "unavailable",
            "intent_id": None,
            "summary": f"{type(exc).__name__}: {exc}",
        }

    return {
        "status": "no_active_intent",
        "intent_id": None,
        "summary": "IntentKeeper adapter has no active intent for this event.",
    }


def evaluate_faculties_for_event(
    event: MetacognitionEvent | None,
    action: ProposedAction | None = None,
    adapters: Mapping[str, object] | None = None,
) -> dict:
    """Evaluate P2C faculty hints without requiring services or databases."""

    selected = dict(adapters or {})
    failure_adapter = selected.get("failure_to_insight") or selected.get(
        "failure_insight"
    )
    return {
        "failure_insight": _evaluate_failure_insight(
            event,
            action,
            failure_adapter,
        ),
        "guardian": _evaluate_guardian(event, action, selected.get("guardian")),
        "intent": _evaluate_intent(event, action, selected.get("intentkeeper")),
    }
