"""Tests adaptation — Tiferet-de-Netzach : changer de stratégie, pas juste retry."""

import pytest


def test_adapt_strategy_creates_new_subtasks(ik_bare):
    """L'adaptation crée de nouvelles sous-tâches et skip les anciennes."""
    intention = ik_bare.set_intention("Research topic", strategy="breadth-first")
    st1 = ik_bare.add_subtask(intention.id, "Survey papers", order_index=0)
    st2 = ik_bare.add_subtask(intention.id, "Read abstracts", order_index=1)
    st3 = ik_bare.add_subtask(intention.id, "Write summary", order_index=2)

    # Fail the first subtask
    ik_bare.start_subtask(st1.id)
    for _ in range(3):  # exhaust retries
        ik_bare.fail_subtask(st1.id, "Too many papers")

    # Adapt strategy
    new_strat = ik_bare.adapt_strategy(
        intention.id, st1.id,
        new_strategy="depth-first",
        new_subtask_descriptions=["Pick 3 key papers", "Deep-read each", "Compare findings"],
    )

    assert new_strat.new_version == 2
    assert new_strat.old_strategy == "breadth-first"
    assert new_strat.new_strategy == "depth-first"

    # Old pending subtasks should be skipped
    old_subtasks = ik_bare.db.get_subtasks(intention.id, strategy_version=1)
    pending_old = [s for s in old_subtasks if s.status == "pending"]
    assert len(pending_old) == 0  # all skipped

    # New subtasks should exist
    new_subtasks = ik_bare.db.get_subtasks(intention.id, strategy_version=2)
    assert len(new_subtasks) == 3
    assert new_subtasks[0].description == "Pick 3 key papers"


def test_strategy_version_increments(ik_bare):
    """Chaque adaptation incrémente la version de stratégie."""
    intention = ik_bare.set_intention("Evolving plan", strategy="v1")
    st = ik_bare.add_subtask(intention.id, "Try A", order_index=0)
    for _ in range(3):
        ik_bare.fail_subtask(st.id, "Nope")

    ik_bare.adapt_strategy(intention.id, st.id, "v2", ["Try B"])
    updated = ik_bare.db.get_intention(intention.id)
    assert updated.strategy_version == 2
    assert updated.strategy == "v2"

    st2 = ik_bare.db.get_subtasks(intention.id, strategy_version=2)[0]
    for _ in range(3):
        ik_bare.fail_subtask(st2.id, "Still nope")

    ik_bare.adapt_strategy(intention.id, st2.id, "v3", ["Try C"])
    updated = ik_bare.db.get_intention(intention.id)
    assert updated.strategy_version == 3


def test_heartbeat_on_strategy_change(ik_bare):
    """Le changement de stratégie enregistre un heartbeat."""
    intention = ik_bare.set_intention("Tracked plan", strategy="initial")
    st = ik_bare.add_subtask(intention.id, "Fail me", order_index=0)
    for _ in range(3):
        ik_bare.fail_subtask(st.id, "Broken")

    ik_bare.adapt_strategy(intention.id, st.id, "new approach", ["Step X"])

    last_hb = ik_bare.db.get_last_heartbeat(intention.id)
    assert last_hb is not None
