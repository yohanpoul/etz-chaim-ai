"""Tests compétence — Gevurah-de-Hod : évaluer sans complaisance."""

import pytest

from selfmap.db import SelfMapDB
from selfmap.models import DomainScore, EvalResult


def test_upsert_and_get_competence(db):
    """Stocker et récupérer un score de compétence."""
    score = DomainScore(
        domain="python",
        model_id="test-model",
        score=0.8,
        brier_score=0.12,
        n_evals=5,
        eval_results=[
            EvalResult(
                question="What does list.append return?",
                expected="None",
                actual="None",
                correct=True,
                confidence=0.9,
            ),
        ],
    )
    db.upsert_competence(score)

    retrieved = db.get_competence("python", "test-model")
    assert retrieved is not None
    assert retrieved.domain == "python"
    assert retrieved.score == 0.8
    assert retrieved.brier_score == 0.12
    assert retrieved.n_evals == 5


def test_upsert_updates_existing(db):
    """Upsert met à jour un score existant et accumule n_evals."""
    s1 = DomainScore(domain="math", model_id="test-model",
                     score=0.6, brier_score=0.2, n_evals=5)
    db.upsert_competence(s1)

    s2 = DomainScore(domain="math", model_id="test-model",
                     score=0.7, brier_score=0.15, n_evals=5)
    db.upsert_competence(s2)

    result = db.get_competence("math", "test-model")
    assert result.score == 0.7  # updated
    assert result.n_evals == 10  # accumulated


def test_get_all_competences(db):
    """Récupérer toutes les compétences d'un modèle."""
    for domain, score in [("python", 0.9), ("math", 0.5), ("history", 0.3)]:
        db.upsert_competence(DomainScore(
            domain=domain, model_id="test-model",
            score=score, brier_score=0.1, n_evals=5,
        ))

    all_scores = db.get_all_competences("test-model")
    assert len(all_scores) == 3
    # Ordered by score DESC
    assert all_scores[0].domain == "python"
    assert all_scores[-1].domain == "history"


def test_get_best_model(db):
    """Trouver le meilleur modèle pour un domaine."""
    db.upsert_competence(DomainScore(
        domain="python", model_id="model-a",
        score=0.6, brier_score=0.2, n_evals=5,
    ))
    db.upsert_competence(DomainScore(
        domain="python", model_id="model-b",
        score=0.9, brier_score=0.1, n_evals=5,
    ))

    best = db.get_best_model("python")
    assert best is not None
    assert best.model_id == "model-b"


def test_unknown_domain_returns_none(db):
    """Domaine inconnu retourne None."""
    result = db.get_competence("quantum_physics", "test-model")
    assert result is None
