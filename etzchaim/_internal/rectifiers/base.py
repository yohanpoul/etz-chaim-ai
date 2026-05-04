"""Shared abstract surface for the structured rectifier family.

Every rectifier specification under ``specs/04_rectifiers/`` ships a public
class extending :class:`BaseRectifier`. Two methods form the contract:

* :meth:`BaseRectifier.detect` reads a read-only snapshot of the upstream
  faculty tree and returns a list of :class:`Deviation` records.
* :meth:`BaseRectifier.rectify` translates each deviation into a list of
  :class:`Event` records, honouring the requested :class:`RectificationMode`.

Rectifiers never delete data and never write directly to aggregate state.
Every action applied in :attr:`RectificationMode.ACT` mode must record an
undo recipe inside the corresponding :class:`Event` so a human reviewer
can roll the change back.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class RectificationMode:
    """Operating mode for :meth:`BaseRectifier.rectify`."""

    OBSERVE = "observe"
    SUGGEST = "suggest"
    ACT = "act"

    ALL = (OBSERVE, SUGGEST, ACT)


@dataclass
class Deviation:
    """A single deviation report produced by :meth:`BaseRectifier.detect`.

    ``metrics`` carries scalar measurements consumed by dashboards, while
    ``payload`` carries the structured detail (e.g. the offending entry
    ids) used by :meth:`BaseRectifier.rectify` to pick an action.
    """

    rectifier_id: str
    pattern: str
    metrics: dict[str, Any]
    spec_ref: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class Event:
    """An event emitted by a rectifier.

    ``event_type`` follows the convention ``r<id>_<verb>`` for the spec
    family ; ``deviation_observed`` is reserved for ``observe`` mode.
    ``undo`` is populated only when the event reflects an applied action,
    and stores everything required for :meth:`BaseRectifier.apply_undo`
    to reverse the change.
    """

    rectifier_id: str
    event_type: str
    action: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    undo: dict[str, Any] | None = None


class BaseRectifier:
    """Abstract base class for structured rectifiers.

    Subclasses must declare :attr:`rectifier_id` and :attr:`spec_ref`, and
    must implement :meth:`detect` and :meth:`rectify`. Subclasses that
    support ``act`` mode must also implement :meth:`apply_undo` so a
    recorded undo recipe can be replayed.
    """

    rectifier_id: str = ""
    spec_ref: str = ""

    def detect(self, tree: dict[str, Any]) -> list[Deviation]:
        raise NotImplementedError

    def rectify(
        self,
        deviations: list[Deviation],
        mode: str,
        tree: dict[str, Any] | None = None,
    ) -> list[Event]:
        raise NotImplementedError

    def apply_undo(self, undo: dict[str, Any], tree: dict[str, Any]) -> None:
        raise NotImplementedError
