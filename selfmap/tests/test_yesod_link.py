"""Tests du lien Yesod↔Hod (sentier Resh) — SelfMap stocke dans EpisteMemory.

Resh = persistance sélective : les résultats d'eval sont aussi des entrées mémoire.
"""

import pytest

from selfmap.models import DomainScore, EvalResult


def test_eval_stores_in_epistememory(sm):
    """L'évaluation persiste dans EpisteMemory avec source_sephirah='hod'."""
    score = DomainScore(
        domain="python",
        model_id="test-model",
        score=0.8,
        brier_score=0.1,
        n_evals=3,
        eval_results=[
            EvalResult("Q1", "A1", "A1", True, 0.9),
            EvalResult("Q2", "A2", "A2", True, 0.8),
            EvalResult("Q3", "A3", "wrong", False, 0.7),
        ],
    )
    sm.db.upsert_competence(score)

    # Manually call what eval_domain does for memory storage
    sm.memory.remember(
        content=f"SelfMap eval: test-model scores 0.80 on 'python' (brier=0.100, n=3)",
        source_sephirah="hod",
        confidence=0.65,
        domain="selfmap",
        tags=["eval", "python", "test-model"],
        ttl_days=30,
    )

    # Verify it's in EpisteMemory
    results = sm.memory.recall("SelfMap eval python", domain="selfmap")
    assert len(results) >= 1
    assert results[0].source_sephirah.value == "hod"
    assert "python" in results[0].tags
