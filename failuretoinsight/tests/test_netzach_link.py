"""Tests du lien Lamed↔Netzach — analyser les subtasks échouées d'IntentKeeper.

Les échecs de sous-tâches alimentent le sentier Lamed.
"""

import pytest


def test_analyze_failed_subtask(fti):
    """FailureToInsight peut analyser un échec de subtask IntentKeeper."""
    # Créer une intention avec une subtask qui échoue
    intention = fti.intentkeeper.set_intention(
        "Test project", max_duration_days=30
    )
    st = fti.intentkeeper.add_subtask(
        intention.id, "Fetch data from API", order_index=0, max_retries=1
    )
    fti.intentkeeper.fail_subtask(st.id, "Connection timeout after 30s")

    # Analyser l'échec via le sentier Lamed
    analysis = fti.analyze_subtask_failure(st.id)
    assert analysis.source_type == "subtask"
    assert analysis.source_id == st.id
    assert "Fetch data from API" in analysis.description
    assert analysis.context["intention_id"] == str(intention.id)


def test_analyze_subtask_without_intentkeeper(fti_bare):
    """Sans IntentKeeper connecté, l'analyse de subtask échoue proprement."""
    import uuid
    with pytest.raises(ValueError, match="IntentKeeper non connecté"):
        fti_bare.analyze_subtask_failure(uuid.uuid4())
