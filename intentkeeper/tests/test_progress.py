"""Tests progrès — Hod-de-Netzach : le système se mesure lui-même."""

import pytest


def test_progress_basic(ik_bare):
    """Le progrès reflète l'avancement des sous-tâches."""
    intention = ik_bare.set_intention("Four steps", max_duration_days=100)
    for i in range(4):
        ik_bare.add_subtask(intention.id, f"Step {i}", order_index=i)

    report = ik_bare.check_progress(intention.id)
    assert report.progress == 0.0
    assert report.subtasks_total == 4
    assert report.subtasks_completed == 0
    assert report.is_on_track  # just started, can't be off-track yet


def test_progress_on_track(ik_bare):
    """Progrès normal — pas de warning."""
    intention = ik_bare.set_intention("Simple task", max_duration_days=100)
    st1 = ik_bare.add_subtask(intention.id, "Step 1", order_index=0)
    ik_bare.add_subtask(intention.id, "Step 2", order_index=1)

    ik_bare.start_subtask(st1.id)
    ik_bare.complete_subtask(st1.id)

    report = ik_bare.check_progress(intention.id)
    assert report.progress == 0.5
    assert report.subtasks_completed == 1
    assert report.is_on_track
    assert report.warning is None


def test_report_human_readable(ik_bare):
    """Le rapport est lisible par un humain."""
    intention = ik_bare.set_intention("Build something", strategy="iterative")
    report_text = ik_bare.report(intention.id)
    assert "Build something" in report_text
    assert "iterative" in report_text
    assert "healthy" in report_text
