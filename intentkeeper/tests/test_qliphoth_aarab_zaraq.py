"""Tests Qliphoth A'arab Zaraq — les 4 niveaux de défaillance de Netzach.

A'arab Zaraq = les Corbeaux de Dispersion = retries infinis, zombie processes.
Le feu qui brûle sans fin, qui consume sans transformer.
"""

from datetime import datetime, timedelta, timezone

import pytest


def test_aarab_zaraq_nogah_slow_progress(ik_bare):
    """Nogah: progrès < 10% après 25% du temps écoulé.

    Le système ne recommande pas l'abandon, mais signale le danger.
    """
    intention = ik_bare.set_intention("Long project", max_duration_days=100)
    ik_bare.add_subtask(intention.id, "Step 1", order_index=0)

    # Manipulate created_at to simulate 30 days elapsed (30% of 100)
    with ik_bare.db._cursor() as cur:
        past = datetime.now(timezone.utc) - timedelta(days=30)
        cur.execute(
            """UPDATE intentkeeper_intentions
               SET created_at = %s, deadline_at = %s + interval '100 days'
               WHERE id = %s""",
            (past, past, intention.id),
        )

    # Progress is still 0% — well below the 10% threshold
    decision = ik_bare.should_abandon(intention.id)
    assert decision.level == "nogah"
    assert not decision.should_abandon  # Nogah = warning only
    assert "progrès lent" in decision.reason


def test_aarab_zaraq_ruach_resource_leak(ik_bare):
    """Ruach: trop de sous-tâches échouées — fuite de ressources.

    Le ratio échecs/total dépasse max_failed_ratio (60%).
    """
    intention = ik_bare.set_intention("Leaky plan", max_duration_days=30)

    # 5 subtasks, 3 will fail (60% >= threshold)
    subtasks = []
    for i in range(5):
        st = ik_bare.add_subtask(
            intention.id, f"Task {i}", order_index=i, max_retries=1
        )
        subtasks.append(st)

    # Fail 3 subtasks (exhaust max_retries=1)
    for st in subtasks[:3]:
        ik_bare.fail_subtask(st.id, "Resource exhausted")

    decision = ik_bare.should_abandon(intention.id)
    assert decision.level == "ruach"
    assert decision.should_abandon
    assert "fuite de ressources" in decision.reason


def test_aarab_zaraq_anan_false_progress(ik_bare):
    """Anan: sous-tâches complétées mais progrès stagnant.

    Le système rapporte du progrès (subtasks complétées)
    mais le progrès réel ne bouge pas — les sous-tâches bouclent.
    """
    intention = ik_bare.set_intention("Circular task", max_duration_days=30)

    # Add many subtasks and complete some, but manually keep progress at 0
    for i in range(5):
        st = ik_bare.add_subtask(intention.id, f"Loop {i}", order_index=i)
        ik_bare.start_subtask(st.id)
        ik_bare.complete_subtask(st.id, result="Done but no real progress")

    # Force progress back to 0 (simulating false progress — subtasks done,
    # but they were the wrong subtasks, or they keep resetting)
    ik_bare.db.update_progress(intention.id, 0.0)

    decision = ik_bare.should_abandon(intention.id)
    assert decision.level == "anan"
    assert decision.should_abandon
    assert "faux progrès" in decision.reason


def test_aarab_zaraq_mamash_zombie_intention(ik_bare):
    """Mamash: intention active depuis 6+ mois sans aucune activité.

    Le cas le plus grave — l'intention est morte mais personne ne l'a enterrée.
    """
    intention = ik_bare.set_intention("Forgotten project", max_duration_days=365)

    # Set created_at to 200 days ago and remove all heartbeats
    with ik_bare.db._cursor() as cur:
        past = datetime.now(timezone.utc) - timedelta(days=200)
        cur.execute(
            """UPDATE intentkeeper_intentions
               SET created_at = %s, deadline_at = %s + interval '365 days'
               WHERE id = %s""",
            (past, past, intention.id),
        )
        # Delete all heartbeats to simulate total silence
        cur.execute(
            "DELETE FROM intentkeeper_heartbeats WHERE intention_id = %s",
            (intention.id,),
        )

    decision = ik_bare.should_abandon(intention.id)
    assert decision.level == "mamash"
    assert decision.should_abandon
    assert "zombie" in decision.reason
    assert decision.days_since_activity >= 180


def test_healthy_intention_no_abandon(ik_bare):
    """Intention saine : bonne progression → pas d'abandon."""
    intention = ik_bare.set_intention("Healthy project", max_duration_days=30)
    st1 = ik_bare.add_subtask(intention.id, "Step 1", order_index=0)
    st2 = ik_bare.add_subtask(intention.id, "Step 2", order_index=1)

    ik_bare.start_subtask(st1.id)
    ik_bare.complete_subtask(st1.id, result="Done well")
    ik_bare.db.update_progress(intention.id, 0.5)

    decision = ik_bare.should_abandon(intention.id)
    assert not decision.should_abandon
    assert decision.level in ("healthy", "nogah")


def test_retry_within_limits(ik_bare):
    """Retry dans les limites : pas d'abandon si max_retries pas atteint."""
    intention = ik_bare.set_intention("Retry plan", max_duration_days=30)
    st = ik_bare.add_subtask(intention.id, "Flaky task", order_index=0, max_retries=3)

    # Fail once but max_retries=3, so still within limits
    ik_bare.fail_subtask(st.id, "Transient error")

    decision = ik_bare.should_abandon(intention.id)
    assert not decision.should_abandon


def test_all_subtasks_complete(ik_bare):
    """Toutes les sous-tâches complétées → intention terminée, pas d'abandon."""
    intention = ik_bare.set_intention("Quick win", max_duration_days=10)
    for i in range(3):
        st = ik_bare.add_subtask(intention.id, f"Task {i}", order_index=i)
        ik_bare.start_subtask(st.id)
        ik_bare.complete_subtask(st.id, result="Done")

    ik_bare.db.update_progress(intention.id, 1.0)

    decision = ik_bare.should_abandon(intention.id)
    assert not decision.should_abandon


def test_deadline_approaching_slow(ik_bare):
    """Deadline proche mais progrès lent : signal Nogah élevé."""
    intention = ik_bare.set_intention("Tight deadline", max_duration_days=10)
    ik_bare.add_subtask(intention.id, "Big task", order_index=0)

    # Set created_at to 8 days ago (80% of time elapsed)
    with ik_bare.db._cursor() as cur:
        past = datetime.now(timezone.utc) - timedelta(days=8)
        cur.execute(
            """UPDATE intentkeeper_intentions
               SET created_at = %s, deadline_at = %s + interval '10 days'
               WHERE id = %s""",
            (past, past, intention.id),
        )

    # Still 0% progress with 80% time gone
    decision = ik_bare.should_abandon(intention.id)
    assert decision.level in ("nogah", "ruach")


def test_mixed_success_and_failure(ik_bare):
    """Mix succès/échecs : sous le seuil de fuite → pas d'abandon."""
    intention = ik_bare.set_intention("Mixed results", max_duration_days=30)

    subtasks = []
    for i in range(5):
        st = ik_bare.add_subtask(
            intention.id, f"Task {i}", order_index=i, max_retries=1
        )
        subtasks.append(st)

    # 2 fail (40% < 60% threshold) and 3 succeed
    for st in subtasks[:2]:
        ik_bare.fail_subtask(st.id, "Failed")
    for st in subtasks[2:]:
        ik_bare.start_subtask(st.id)
        ik_bare.complete_subtask(st.id, result="OK")

    ik_bare.db.update_progress(intention.id, 0.6)

    decision = ik_bare.should_abandon(intention.id)
    assert decision.level in ("healthy", "nogah")
    assert not decision.should_abandon


def test_no_subtasks_early(ik_bare):
    """Intention sans sous-tâches : ne crash pas."""
    intention = ik_bare.set_intention("Empty plan", max_duration_days=30)

    decision = ik_bare.should_abandon(intention.id)
    assert decision is not None
