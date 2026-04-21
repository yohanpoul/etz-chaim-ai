"""Tests explore_open_questions — Chesed → Tiferet (R2.7).

Vérifie que ExplorationEngine consomme les open_questions de DissensuEngine
comme graines d'exploration.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest

from explorationengine.core import ExplorationEngine
from explorationengine.models import Connection, ExplorationResult


# ── Fixtures ─────────────────────────────────────────────────


@dataclass
class FakeOpenQuestion:
    """Minimal OpenQuestion for testing without DB."""

    id: UUID
    tension_id: UUID
    question: str
    missing_evidence: str | None = None
    priority: str = "medium"
    domain: str | None = None
    created_at: datetime | None = None
    resolved_at: datetime | None = None


def _make_oq(
    question: str = "What evidence supports X?",
    domain: str = "kabbale",
    priority: str = "medium",
) -> FakeOpenQuestion:
    return FakeOpenQuestion(
        id=uuid4(),
        tension_id=uuid4(),
        question=question,
        missing_evidence="Need experimental data",
        priority=priority,
        domain=domain,
    )


# ── Tests ────────────────────────────────────────────────────


class TestExploreOpenQuestions:
    """Chesed explore les open_questions de Tiferet."""

    def test_no_dissensus_returns_empty(self, engine):
        """Sans Tiferet connecté, retourne une liste vide."""
        assert engine.dissensus is None
        result = engine.explore_open_questions()
        assert result == []

    def test_no_open_questions_returns_empty(self, engine):
        """Si aucune question ouverte, retourne vide."""
        mock_dissensus = MagicMock()
        mock_dissensus.db.get_open_questions.return_value = []
        engine.dissensus = mock_dissensus

        result = engine.explore_open_questions()
        assert result == []

    def test_explores_questions_and_returns_results(self, engine):
        """Explore les questions et retourne des resultats structures."""
        oq1 = _make_oq("Lien entre tsimtsum et information bottleneck?", "kabbale")
        oq2 = _make_oq("Evidence for causal link in pruning?", "machine_learning")

        mock_dissensus = MagicMock()
        mock_dissensus.db.get_open_questions.return_value = [oq1, oq2]
        engine.dissensus = mock_dissensus

        # explore() returns an ExplorationResult with some connections
        fake_result = ExplorationResult(
            exploration_id=uuid4(),
            connections=[
                Connection(
                    concept_a="tsimtsum",
                    domain_a="kabbale",
                    concept_b="bottleneck",
                    domain_b="machine_learning",
                    connection_type="analogy",
                    description="Both involve purposeful restriction",
                    novelty_score=0.6,
                    relevance_score=0.4,
                    confidence=0.5,
                ),
            ],
            status="completed",
            domains_explored=["kabbale", "machine_learning"],
        )

        with patch.object(engine, "explore", return_value=fake_result):
            results = engine.explore_open_questions(max_questions=5)

        assert len(results) == 2
        assert results[0]["explored"] is True
        assert results[0]["connections_found"] == 1
        # Low confidence (0.5 < 0.7), should NOT be resolved
        assert results[0]["resolved"] is False

    def test_resolves_question_on_strong_connection(self, engine):
        """Resout la question si une connexion forte est trouvee."""
        oq = _make_oq("Missing evidence for X?", "kabbale", priority="high")

        mock_dissensus = MagicMock()
        mock_dissensus.db.get_open_questions.return_value = [oq]
        engine.dissensus = mock_dissensus

        # Strong connection: confidence >= 0.7 AND relevance >= 0.5
        strong_result = ExplorationResult(
            exploration_id=uuid4(),
            connections=[
                Connection(
                    concept_a="X",
                    domain_a="kabbale",
                    concept_b="Y",
                    domain_b="neuroscience",
                    connection_type="causal",
                    description="Strong causal evidence found",
                    novelty_score=0.8,
                    relevance_score=0.7,
                    confidence=0.85,
                ),
            ],
            status="completed",
            domains_explored=["kabbale", "neuroscience"],
        )

        with patch.object(engine, "explore", return_value=strong_result):
            results = engine.explore_open_questions(max_questions=5)

        assert len(results) == 1
        assert results[0]["resolved"] is True
        mock_dissensus.db.resolve_question.assert_called_once_with(oq.id)

    def test_max_questions_respected(self, engine):
        """Le cap max_questions est respecte."""
        questions = [_make_oq(f"Question {i}?", "kabbale") for i in range(10)]

        mock_dissensus = MagicMock()
        mock_dissensus.db.get_open_questions.return_value = questions
        engine.dissensus = mock_dissensus

        empty_result = ExplorationResult(
            connections=[], status="completed", domains_explored=[]
        )

        with patch.object(engine, "explore", return_value=empty_result):
            results = engine.explore_open_questions(max_questions=3)

        assert len(results) == 3

    def test_exploration_error_does_not_crash(self, engine):
        """Une erreur d'exploration n'arrete pas le traitement."""
        oq1 = _make_oq("Question OK?", "kabbale")
        oq2 = _make_oq("Question crash?", "physics")

        mock_dissensus = MagicMock()
        mock_dissensus.db.get_open_questions.return_value = [oq1, oq2]
        engine.dissensus = mock_dissensus

        empty_result = ExplorationResult(
            connections=[], status="completed", domains_explored=[]
        )

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("Simulated exploration crash")
            return empty_result

        with patch.object(engine, "explore", side_effect=side_effect):
            results = engine.explore_open_questions(max_questions=5)

        assert len(results) == 2
        assert results[0]["explored"] is True
        assert results[0]["error"] is None
        assert results[1]["explored"] is False
        assert results[1]["error"] is not None
