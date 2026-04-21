"""Tests sous-tâches — Yetzirah-de-Netzach : décomposition et exécution."""

import pytest


def test_add_subtask(ik_bare):
    """Ajouter une sous-tâche à une intention."""
    intention = ik_bare.set_intention("Build SelfMap")
    st = ik_bare.add_subtask(intention.id, "Design schema", order_index=0)
    assert st.description == "Design schema"
    assert st.status == "pending"
    assert st.order_index == 0

    updated = ik_bare.db.get_intention(intention.id)
    assert updated.total_subtasks == 1


def test_start_subtask(ik_bare):
    """Démarrer une sous-tâche enregistre un heartbeat."""
    intention = ik_bare.set_intention("Build SelfMap")
    st = ik_bare.add_subtask(intention.id, "Write models.py", order_index=0)
    ik_bare.start_subtask(st.id)

    subtasks = ik_bare.db.get_subtasks(intention.id)
    assert subtasks[0].status == "in_progress"

    last_hb = ik_bare.db.get_last_heartbeat(intention.id)
    assert last_hb is not None


def test_complete_subtask_updates_progress(ik_bare):
    """Compléter une sous-tâche recalcule le progrès."""
    intention = ik_bare.set_intention("Three steps")
    st1 = ik_bare.add_subtask(intention.id, "Step 1", order_index=0)
    ik_bare.add_subtask(intention.id, "Step 2", order_index=1)
    ik_bare.add_subtask(intention.id, "Step 3", order_index=2)

    ik_bare.start_subtask(st1.id)
    ik_bare.complete_subtask(st1.id, result="Done")

    updated = ik_bare.db.get_intention(intention.id)
    assert updated.completed_subtasks == 1
    assert updated.total_subtasks == 3
    assert abs(updated.progress - 1 / 3) < 0.01


def test_fail_subtask_retries(ik_bare):
    """Échouer une sous-tâche incrémente les retries."""
    intention = ik_bare.set_intention("Fragile task")
    st = ik_bare.add_subtask(intention.id, "Flaky operation", order_index=0, max_retries=3)

    # First two failures → back to pending (retry)
    ik_bare.fail_subtask(st.id, "Network error")
    subtask = ik_bare.db.get_subtasks(intention.id)[0]
    assert subtask.retries == 1
    assert subtask.status == "pending"  # retry, not failed yet

    ik_bare.fail_subtask(st.id, "Timeout")
    subtask = ik_bare.db.get_subtasks(intention.id)[0]
    assert subtask.retries == 2
    assert subtask.status == "pending"

    # Third failure → max reached → marked failed
    ik_bare.fail_subtask(st.id, "Permanent error")
    subtask = ik_bare.db.get_subtasks(intention.id)[0]
    assert subtask.retries == 3
    assert subtask.status == "failed"

    updated = ik_bare.db.get_intention(intention.id)
    assert updated.failed_subtasks == 1


def test_skip_subtask(ik_bare):
    """Passer une sous-tâche."""
    intention = ik_bare.set_intention("Flexible plan")
    st = ik_bare.add_subtask(intention.id, "Optional step", order_index=0)
    ik_bare.skip_subtask(st.id)

    subtask = ik_bare.db.get_subtasks(intention.id)[0]
    assert subtask.status == "skipped"
