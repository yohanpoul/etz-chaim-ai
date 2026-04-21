"""Tests statut 'incubating' — Sprint 8b fix 4.

Avant migration 005 : la contrainte CHECK n'autorisait pas 'incubating',
donc les candidats borderline (0.35 ≤ novelty < 0.45) marqués 'incubating'
par assess_novelty (core.py:197) ne pouvaient être persistés. Silent drop.

Après : 'incubating' est autorisé, _persist_candidates inclut la liste
incubating_candidates, et un SELECT sur ce statut retourne les rows.
"""

from __future__ import annotations

import pytest
import psycopg2

from insightforge.db import InsightDB
from insightforge.models import CandidateInsight, InsightSession

from .conftest import TEST_DB_URL


@pytest.fixture
def db_and_session():
    """DB fraîche + session parent pour ancrer les candidats."""
    db = InsightDB(db_url=TEST_DB_URL)
    # Reset direct
    with db._cursor() as cur:
        cur.execute("DELETE FROM candidate_insights")
        cur.execute("DELETE FROM insight_sessions")
    session = InsightSession(
        question="Test incubating", domain="test",
    )
    saved = db.save_session(session)
    session.id = saved.id
    yield db, session
    with db._cursor() as cur:
        cur.execute("DELETE FROM candidate_insights")
        cur.execute("DELETE FROM insight_sessions")
    db.close()


def test_incubating_status_is_persisted(db_and_session):
    """Un candidat avec status='incubating' s'insère sans exception."""
    db, session = db_and_session
    candidate = CandidateInsight(
        description="Borderline novelty candidate for incubation test",
        status="incubating",
        novelty_score=0.40,
        confidence=0.55,
        session_id=session.id,
        connects_domains=["a", "b"],
    )
    saved = db.save_candidate(candidate)
    assert saved.id is not None
    assert saved.status == "incubating"


def test_incubating_select_returns_row(db_and_session):
    """SELECT par statut retourne les candidates incubating."""
    db, session = db_and_session
    candidate = CandidateInsight(
        description="Another borderline candidate",
        status="incubating",
        novelty_score=0.42,
        session_id=session.id,
    )
    db.save_candidate(candidate)

    rows = db.get_candidates(session.id, status="incubating")
    assert len(rows) == 1
    assert rows[0].status == "incubating"


def test_arbitrary_status_still_rejected(db_and_session):
    """La contrainte CHECK refuse toujours les statuts non prévus."""
    db, session = db_and_session
    candidate = CandidateInsight(
        description="Candidate with an invalid status value",
        status="foobar_unknown",
        session_id=session.id,
    )
    with pytest.raises(psycopg2.errors.CheckViolation):
        db.save_candidate(candidate)
