"""Tests du lien Netzach↔Hod (sentier Ayin) — StatusSync via SelfMap.

Ayin ע = l'oeil : la persistance s'observe elle-même via Hod.
"""

import pytest

from selfmap.models import DomainScore


def test_selfmap_connected(ik):
    """IntentKeeper a accès à SelfMap pour vérifier la compétence."""
    assert ik.selfmap is not None

    # Register a competence in SelfMap
    ik.selfmap.db.upsert_competence(DomainScore(
        domain="python", model_id="test-model",
        score=0.85, brier_score=0.1, n_evals=10,
    ))

    # IntentKeeper can query SelfMap through the Ayin channel
    domain, score = ik.selfmap.get_competence("Python asyncio patterns")
    assert domain == "python"
    assert score == 0.85
