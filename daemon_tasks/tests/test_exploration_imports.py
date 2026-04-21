"""Regression test — daemon_tasks.exploration must import all daemon helpers.

Sprint 7 Finding 1: commit 15ec2aa (Cycle 4 refactor) moved task_explore_full_tree
to daemon_tasks/exploration.py but dropped 5 helper functions (_assess_soul,
_compute_adam_kadmon_score, _compute_ohr_ratio, _get_nitzotzot_state,
_init_partzufim) from daemon.py. The import at line 452 then failed at runtime
whenever task_explore_full_tree was invoked (Karpathy branch, force_daily, etc).

These tests fail without the helpers and pass after they are restored.
"""
from __future__ import annotations


def test_daemon_exposes_assess_soul_family():
    """daemon.py must expose the 5 helpers imported by exploration.py."""
    import daemon

    for name in (
        "_assess_soul",
        "_compute_adam_kadmon_score",
        "_compute_ohr_ratio",
        "_get_nitzotzot_state",
        "_init_partzufim",
    ):
        assert hasattr(daemon, name), f"daemon.{name} missing"
        assert callable(getattr(daemon, name)), f"daemon.{name} not callable"


def test_task_explore_full_tree_runs_without_import_error():
    """task_explore_full_tree must not raise ImportError on the daemon helpers.

    The inner DB/LLM work may fail gracefully (empty tree, etc), but the
    top-level function must return a dict without ImportError propagating.
    """
    from daemon_tasks.exploration import task_explore_full_tree

    report = task_explore_full_tree({})
    assert isinstance(report, dict)
    assert report.get("task") == "full_tree_exploration"


def test_assess_soul_returns_soul_level_dict():
    """_assess_soul must return a dict with a 'level' key (no crash on empty tree)."""
    from daemon import _assess_soul

    result = _assess_soul({}, {})
    assert isinstance(result, dict)
    assert "level" in result
