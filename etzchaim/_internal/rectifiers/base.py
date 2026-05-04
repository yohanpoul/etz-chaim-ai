"""Base contracts for rectifiers.

A rectifier is a small autonomous unit that inspects an orchestrator-supplied
read-only tree, reports deviations against an invariant, and — under explicit
``act`` mode — invokes faculty channels to apply remediation while recording
a reversible undo recipe.

Three modes are honored by every rectifier:

- ``observe``: detection only, emit a ``*_deviation_observed`` event.
- ``suggest``: emit a ``*_action_proposed`` event describing the chosen
  action without applying it.
- ``act``: invoke faculty channels to apply the action and emit a
  ``*_action_applied`` event carrying an :class:`UndoRecipe` that lets a
  human reviewer roll back the change.

Rectifiers MUST NOT write directly to aggregate state. All mutations flow
through a faculty handle (``MemoryFaculty`` for the memory-oriented
rectifiers) so the orchestrator retains a single point of accountability.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping, Protocol, Sequence, runtime_checkable


class RectificationMode(str, Enum):
    """Operating mode for a rectifier's :meth:`BaseRectifier.rectify` call."""

    OBSERVE = "observe"
    SUGGEST = "suggest"
    ACT = "act"


@dataclass(frozen=True)
class Deviation:
    """A single invariant violation detected against the supplied tree."""

    rectifier_id: str
    pattern: str
    metrics: Mapping[str, object]
    spec_ref: str


@dataclass(frozen=True)
class UndoRecipe:
    """Reversal instructions for an applied rectification.

    ``action`` names the inverse operation; ``args`` carries the data needed
    to invoke it. The recipe is data only — applying it is delegated to
    :meth:`BaseRectifier.apply_undo` so the rectifier stays the single
    authority on what its actions mean.
    """

    action: str
    args: Mapping[str, object]


@dataclass(frozen=True)
class Event:
    """Structured event emitted by :meth:`BaseRectifier.rectify`."""

    type: str
    rectifier_id: str
    payload: Mapping[str, object]
    undo: UndoRecipe | None = None


@runtime_checkable
class MemoryFaculty(Protocol):
    """Channel through which memory-oriented rectifiers mutate state.

    The protocol is intentionally narrow: rectifiers never read the faculty
    directly (they read the orchestrator's tree snapshot) and never delete
    entries. Implementations own persistence, locking, and audit logging.
    """

    def get_status(self, entry_id: str) -> str:  # pragma: no cover - protocol
        ...

    def set_status(self, entry_id: str, status: str) -> None:  # pragma: no cover - protocol
        ...

    def open_dissensus_ticket(
        self, entry_a_id: str, entry_b_id: str, reason: str
    ) -> str:  # pragma: no cover - protocol
        ...

    def close_dissensus_ticket(self, ticket_id: str) -> None:  # pragma: no cover - protocol
        ...


class BaseRectifier(ABC):
    """Abstract base every rectifier extends.

    Subclasses set ``rectifier_id`` and ``spec_ref`` as class attributes and
    implement :meth:`detect` and :meth:`rectify`. The default
    :meth:`apply_undo` dispatches to a ``_undo_<action>`` method on the
    subclass, keeping the inverse colocated with the forward action.
    """

    rectifier_id: str = ""
    spec_ref: str = ""

    @abstractmethod
    def detect(self, tree: Mapping[str, object]) -> list[Deviation]:
        """Return deviations observed in ``tree``; never mutates state."""

    @abstractmethod
    def rectify(
        self,
        deviations: Sequence[Deviation],
        mode: RectificationMode,
    ) -> list[Event]:
        """Process ``deviations`` under ``mode``; emits events accordingly."""

    def apply_undo(self, event: Event) -> None:
        """Reverse a previously-applied event using its attached recipe."""
        if event.undo is None:
            raise ValueError("event has no undo recipe attached")
        method_name = f"_undo_{event.undo.action}"
        method = getattr(self, method_name, None)
        if method is None:
            raise NotImplementedError(
                f"{type(self).__name__} cannot undo action {event.undo.action!r}"
            )
        method(**dict(event.undo.args))
