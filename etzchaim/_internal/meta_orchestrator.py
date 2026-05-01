"""Top-level meta-orchestrator for the Cognitive OS.

Coordinates the bring-up of cognitive faculties, dispatches agent events to
the configuration responsible for them, and records halts for post-mortem.
The orchestrator never performs reasoning itself and never writes to a
configuration's aggregate state; it sequences and supervises lifecycle.

Internal: SPEC-001 — see ``specs/01_meta_orchestrator.md``. Internal naming
``keter`` is preserved in spec frontmatter only and never surfaces in code,
docstrings, or runtime output.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Mapping, Protocol, runtime_checkable


@dataclass
class AgentEvent:
    """Inbound event addressed to a configuration.

    The ``type`` field is the routing key; it must equal a configuration name
    registered with the orchestrator.
    """

    type: str
    payload: dict
    event_id: str


@dataclass
class ConsolidationReport:
    """Outcome of a single faculty's bring-up step."""

    status: str  # "consolidated" or "failed"
    reason: str = ""


@runtime_checkable
class Faculty(Protocol):
    """Minimal protocol every faculty must satisfy.

    A faculty owns its own state and exposes ``consolidate`` so the
    orchestrator can bring it online deterministically. Faculties never call
    each other directly; coordination is mediated by the orchestrator.
    """

    name: str

    def consolidate(self) -> ConsolidationReport:  # pragma: no cover - protocol
        ...


@runtime_checkable
class Configuration(Protocol):
    """Minimal protocol for a mature configuration.

    A configuration handles events of a single ``type`` and returns a plain
    dict of output. It owns its own aggregate state — the orchestrator must
    never mutate that state directly.
    """

    name: str

    def handle(self, event: AgentEvent) -> dict:  # pragma: no cover - protocol
        ...


FacultyMap = Mapping[str, Faculty]
ConfigurationMap = Mapping[str, Configuration]


@dataclass
class BootReport:
    """Result of a single ``boot()`` invocation.

    ``duration_ms`` is excluded from equality so two boots with the same
    inputs compare equal regardless of wall-clock variation.
    """

    consolidated: list[str]
    failed: list[tuple[str, str]]
    duration_ms: int = field(default=0, compare=False)


@dataclass
class DispatchResult:
    configuration: str
    output: dict
    trace_ids: list[str]


@dataclass
class HaltRecord:
    reason: str
    timestamp: float
    last_dispatched_event: str | None


HALTED_OUTPUT_KEY = "status"
HALTED_OUTPUT_VALUE = "HALTED"


class OrchestratorError(RuntimeError):
    """Base class for orchestrator-level errors."""


class NotBootedError(OrchestratorError):
    """Raised when ``dispatch`` is called before a successful ``boot``."""


class OutOfOrderError(OrchestratorError):
    """Raised when a faculty bring-up violates sequential consolidation."""


class UnknownEventTypeError(OrchestratorError):
    """Raised when ``dispatch`` receives an event with no matching configuration."""


class MetaOrchestrator:
    """Sequences faculty bring-up and routes events to configurations.

    The orchestrator is constructed once per run with two ordered maps. The
    insertion order of ``faculties`` defines the consolidation sequence;
    ``configurations`` is keyed by the event type each handles.
    """

    def __init__(
        self,
        faculties: FacultyMap,
        configurations: ConfigurationMap,
    ) -> None:
        self._faculties: FacultyMap = faculties
        self._configurations: ConfigurationMap = configurations
        self._consolidated: list[str] = []
        self._booted: bool = False
        self._halted: bool = False
        self._halt_record: HaltRecord | None = None
        self._last_event_id: str | None = None
        self._dispatch_counter: int = 0

    def boot(self) -> BootReport:
        """Bring faculties online in the prescribed sequential order.

        Iterates faculties in insertion order and calls ``consolidate`` on
        each. The first faculty to fail stops the sequence — subsequent
        faculties are not contacted, preserving the no-skip invariant.
        """
        start = time.monotonic()
        consolidated: list[str] = []
        failed: list[tuple[str, str]] = []

        for name, faculty in self._faculties.items():
            report = faculty.consolidate()
            if report.status == "consolidated":
                consolidated.append(name)
                continue
            failed.append((name, report.reason or "unknown"))
            break

        self._consolidated = list(consolidated)
        self._booted = not failed
        duration_ms = int((time.monotonic() - start) * 1000)
        return BootReport(
            consolidated=consolidated,
            failed=failed,
            duration_ms=duration_ms,
        )

    def dispatch(self, event: AgentEvent) -> DispatchResult:
        """Route an event through the configuration matching ``event.type``."""
        if self._halted:
            return DispatchResult(
                configuration="",
                output={HALTED_OUTPUT_KEY: HALTED_OUTPUT_VALUE},
                trace_ids=[],
            )
        if not self._booted:
            raise NotBootedError(
                "dispatch() called before a successful boot()"
            )

        configuration = self._configurations.get(event.type)
        if configuration is None:
            raise UnknownEventTypeError(
                f"no configuration registered for event type: {event.type!r}"
            )

        self._dispatch_counter += 1
        trace_id = f"trace-{self._dispatch_counter:08d}-{event.event_id}"
        output = configuration.handle(event)
        self._last_event_id = event.event_id
        return DispatchResult(
            configuration=configuration.name,
            output=output,
            trace_ids=[trace_id],
        )

    def halt(self, reason: str) -> HaltRecord:
        """Stop all faculties; record the halt cause for post-mortem.

        Halt is irreversible within a single process run. Subsequent
        ``dispatch`` calls return a HALTED sentinel result rather than
        executing.
        """
        record = HaltRecord(
            reason=reason,
            timestamp=time.time(),
            last_dispatched_event=self._last_event_id,
        )
        self._halted = True
        self._halt_record = record
        return record

    @property
    def is_halted(self) -> bool:
        return self._halted

    @property
    def halt_record(self) -> HaltRecord | None:
        return self._halt_record

    @property
    def consolidated_faculties(self) -> tuple[str, ...]:
        return tuple(self._consolidated)
