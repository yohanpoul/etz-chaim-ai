"""Tests intentions — Keter-de-Netzach : le cycle de vie d'une intention."""

import pytest


def test_create_intention(ik_bare):
    """Créer une intention simple."""
    intention = ik_bare.set_intention("Learn category theory", max_duration_days=30)
    assert intention.goal == "Learn category theory"
    assert intention.status == "active"
    assert intention.max_duration_days == 30
    assert intention.progress == 0.0
    assert intention.deadline_at is not None


def test_get_intention(ik_bare):
    """Récupérer une intention par ID."""
    created = ik_bare.set_intention("Build EpisteMemory")
    fetched = ik_bare.db.get_intention(created.id)
    assert fetched is not None
    assert fetched.goal == "Build EpisteMemory"
    assert fetched.status == "active"


def test_complete_intention(ik_bare):
    """Compléter une intention."""
    intention = ik_bare.set_intention("Write tests")
    ik_bare.complete(intention.id)
    updated = ik_bare.db.get_intention(intention.id)
    assert updated.status == "completed"
    assert updated.progress == 1.0
    assert updated.completed_at is not None


def test_abandon_intention(ik_bare):
    """Abandonner une intention avec raison — Gevurah-de-Netzach."""
    intention = ik_bare.set_intention("Solve P=NP")
    ik_bare.abandon(intention.id, "Problem intractable")
    updated = ik_bare.db.get_intention(intention.id)
    assert updated.status == "abandoned"
    assert updated.abandon_reason == "Problem intractable"


def test_list_active_intentions(ik_bare):
    """Lister les intentions actives."""
    ik_bare.set_intention("Task A")
    i2 = ik_bare.set_intention("Task B")
    ik_bare.complete(i2.id)
    ik_bare.set_intention("Task C")

    active = ik_bare.db.get_active_intentions()
    assert len(active) == 2
    goals = [i.goal for i in active]
    assert "Task A" in goals
    assert "Task C" in goals
    assert "Task B" not in goals
