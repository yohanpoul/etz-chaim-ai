"""Tests for memory subsystem: snapshot, search, trajectory."""

from __future__ import annotations

import os
import tempfile
import time

import pytest


@pytest.fixture(autouse=True)
def _isolate_state(monkeypatch):
    tmp = tempfile.mkdtemp()
    monkeypatch.setenv("ETZCHAIM_STATE_DIR", tmp)
    # Force reload of modules that read the env var at import time.
    yield tmp


# ─── snapshot ────────────────────────────────────────────────


def test_snapshot_renders_three_sections(tmp_path):
    from importlib import reload

    import etzchaim.autopilot.memory.snapshot as snap_mod

    reload(snap_mod)

    snap_mod.write_context("autopilot ops")
    snap_mod.write_operator("operator prefs")

    mission = tmp_path / "MISSION.md"
    mission.write_text("# Mission\n\nNorth star")
    snap = snap_mod.load_frozen_snapshot(mission_path=mission)

    rendered = snap.render()
    assert "MISSION" in rendered
    assert "OPERATOR PREFERENCES" in rendered
    assert "AUTOPILOT CONTEXT" in rendered
    assert "operator prefs" in rendered


def test_snapshot_handles_missing_files(tmp_path):
    from importlib import reload

    import etzchaim.autopilot.memory.snapshot as snap_mod

    reload(snap_mod)

    snap = snap_mod.load_frozen_snapshot(
        mission_path=tmp_path / "nope.md"
    )
    assert snap.render() == ""


# ─── trajectory ──────────────────────────────────────────────


def test_trajectory_round_trip():
    from importlib import reload

    import etzchaim.autopilot.memory.trajectory as traj_mod

    reload(traj_mod)

    t = traj_mod.Trajectory(model="claude-test")
    t.add_turn("system", "you are autopilot")
    t.add_turn("user", "do the thing")
    t.add_turn("assistant", "done")
    t.completed = True
    traj_mod.append_trajectory(t)

    assert traj_mod.TRAJECTORY_FILE.exists()
    text = traj_mod.TRAJECTORY_FILE.read_text()
    assert '"model": "claude-test"' in text
    assert '"completed": true' in text


# ─── search ──────────────────────────────────────────────────


def test_search_inserts_and_finds():
    from importlib import reload

    import etzchaim.autopilot.memory.search as search_mod

    reload(search_mod)

    rid = search_mod.insert_cycle(
        search_mod.CycleRecord(
            started_at=time.time(),
            task_id="spec-foo",
            status="ok",
            summary="Did the foo work for the bar.",
        )
    )
    assert rid > 0

    hits = search_mod.search_cycles("foo")
    assert any(h.task_id == "spec-foo" for h in hits)

    recents = search_mod.recent_cycles(10)
    assert recents


def test_search_returns_empty_for_no_match():
    from importlib import reload

    import etzchaim.autopilot.memory.search as search_mod

    reload(search_mod)

    assert search_mod.search_cycles("nothingmatchesthistermXYZ") == []
