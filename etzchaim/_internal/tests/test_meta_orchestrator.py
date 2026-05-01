"""Tests for ``etzchaim._internal.meta_orchestrator``.

The tests use minimal fake Faculty and Configuration implementations rather
than the real components so the orchestrator's contract is exercised in
isolation.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

from etzchaim._internal.meta_orchestrator import (
    AgentEvent,
    BootReport,
    Configuration,
    ConsolidationReport,
    DispatchResult,
    Faculty,
    HaltRecord,
    MetaOrchestrator,
    NotBootedError,
    UnknownEventTypeError,
)


class FakeFaculty:
    def __init__(self, name: str, *, fail: bool = False, reason: str = "") -> None:
        self.name = name
        self._fail = fail
        self._reason = reason
        self.consolidate_calls = 0

    def consolidate(self) -> ConsolidationReport:
        self.consolidate_calls += 1
        if self._fail:
            return ConsolidationReport(status="failed", reason=self._reason or "boom")
        return ConsolidationReport(status="consolidated")


class FakeConfiguration:
    def __init__(self, name: str, output: dict | None = None) -> None:
        self.name = name
        self._output = output or {"ok": True}
        self.handled: list[AgentEvent] = []

    def handle(self, event: AgentEvent) -> dict:
        self.handled.append(event)
        return dict(self._output)


def _make_orchestrator(
    faculties: list[FakeFaculty] | None = None,
    configurations: list[FakeConfiguration] | None = None,
) -> MetaOrchestrator:
    facs = {f.name: f for f in (faculties or [])}
    cfgs = {c.name: c for c in (configurations or [])}
    return MetaOrchestrator(faculties=facs, configurations=cfgs)


def test_construction_does_not_boot() -> None:
    orch = _make_orchestrator(
        faculties=[FakeFaculty("alpha"), FakeFaculty("beta")],
        configurations=[FakeConfiguration("plan")],
    )
    assert orch.consolidated_faculties == ()
    assert orch.is_halted is False


def test_boot_consolidates_in_insertion_order() -> None:
    facs = [FakeFaculty("alpha"), FakeFaculty("beta"), FakeFaculty("gamma")]
    orch = _make_orchestrator(faculties=facs)
    report = orch.boot()
    assert report.consolidated == ["alpha", "beta", "gamma"]
    assert report.failed == []
    assert orch.consolidated_faculties == ("alpha", "beta", "gamma")


def test_boot_stops_on_first_failure_no_skip() -> None:
    facs = [
        FakeFaculty("alpha"),
        FakeFaculty("beta", fail=True, reason="seed missing"),
        FakeFaculty("gamma"),
    ]
    orch = _make_orchestrator(faculties=facs)
    report = orch.boot()
    assert report.consolidated == ["alpha"]
    assert report.failed == [("beta", "seed missing")]
    # Sequential consolidation invariant: gamma never contacted because beta failed.
    assert facs[2].consolidate_calls == 0


def test_boot_is_deterministic_for_equal_inputs() -> None:
    def fresh() -> MetaOrchestrator:
        facs = [FakeFaculty("alpha"), FakeFaculty("beta")]
        cfgs = [FakeConfiguration("plan")]
        return _make_orchestrator(faculties=facs, configurations=cfgs)

    report_a = fresh().boot()
    report_b = fresh().boot()
    assert report_a == report_b
    # Equality must hold even if the wall-clock duration differs slightly.
    forced = BootReport(
        consolidated=list(report_a.consolidated),
        failed=list(report_a.failed),
        duration_ms=report_a.duration_ms + 999,
    )
    assert report_a == forced


def test_dispatch_routes_by_event_type() -> None:
    plan_cfg = FakeConfiguration("plan", output={"steps": ["a", "b"]})
    review_cfg = FakeConfiguration("review", output={"verdict": "ok"})
    orch = _make_orchestrator(
        faculties=[FakeFaculty("alpha")],
        configurations=[plan_cfg, review_cfg],
    )
    orch.boot()

    event = AgentEvent(type="review", payload={"text": "hello"}, event_id="e-1")
    result = orch.dispatch(event)

    assert isinstance(result, DispatchResult)
    assert result.configuration == "review"
    assert result.output == {"verdict": "ok"}
    assert result.trace_ids and result.trace_ids[0].endswith("e-1")
    assert review_cfg.handled == [event]
    assert plan_cfg.handled == []


def test_dispatch_before_boot_raises() -> None:
    orch = _make_orchestrator(
        faculties=[FakeFaculty("alpha")],
        configurations=[FakeConfiguration("plan")],
    )
    with pytest.raises(NotBootedError):
        orch.dispatch(AgentEvent(type="plan", payload={}, event_id="e-1"))


def test_dispatch_unknown_event_type_raises() -> None:
    orch = _make_orchestrator(
        faculties=[FakeFaculty("alpha")],
        configurations=[FakeConfiguration("plan")],
    )
    orch.boot()
    with pytest.raises(UnknownEventTypeError):
        orch.dispatch(AgentEvent(type="unknown", payload={}, event_id="e-1"))


def test_halt_makes_subsequent_dispatch_return_halted() -> None:
    cfg = FakeConfiguration("plan")
    orch = _make_orchestrator(
        faculties=[FakeFaculty("alpha")],
        configurations=[cfg],
    )
    orch.boot()
    orch.dispatch(AgentEvent(type="plan", payload={}, event_id="e-1"))

    record = orch.halt("operator stop")
    assert isinstance(record, HaltRecord)
    assert record.reason == "operator stop"
    assert record.last_dispatched_event == "e-1"
    assert orch.is_halted is True

    result = orch.dispatch(AgentEvent(type="plan", payload={}, event_id="e-2"))
    assert result.output == {"status": "HALTED"}
    # Configuration must not have been called after halt.
    assert len(cfg.handled) == 1


def test_halt_is_irreversible_within_one_run() -> None:
    orch = _make_orchestrator(
        faculties=[FakeFaculty("alpha")],
        configurations=[FakeConfiguration("plan")],
    )
    orch.boot()
    orch.halt("first")
    # Calling halt again does not unhalt; record updates but flag stays True.
    orch.halt("second")
    result = orch.dispatch(AgentEvent(type="plan", payload={}, event_id="e-3"))
    assert result.output == {"status": "HALTED"}
    assert orch.is_halted is True


def test_protocols_runtime_checkable() -> None:
    fac = FakeFaculty("alpha")
    cfg = FakeConfiguration("plan")
    assert isinstance(fac, Faculty)
    assert isinstance(cfg, Configuration)


def test_orchestrator_does_not_write_aggregate_state() -> None:
    """Static check : the orchestrator source contains no assignment to
    a configuration's aggregate state attributes (``overall_score``,
    ``score``, ``aggregate``)."""
    src_path = pathlib.Path(__file__).resolve().parents[1] / "meta_orchestrator.py"
    tree = ast.parse(src_path.read_text())
    forbidden = {"overall_score", "score", "aggregate"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Attribute):
                    assert target.attr not in forbidden, (
                        f"forbidden assignment to .{target.attr} in orchestrator source"
                    )
        if isinstance(node, ast.AugAssign):
            target = node.target
            if isinstance(target, ast.Attribute):
                assert target.attr not in forbidden, (
                    f"forbidden aug-assignment to .{target.attr} in orchestrator source"
                )
