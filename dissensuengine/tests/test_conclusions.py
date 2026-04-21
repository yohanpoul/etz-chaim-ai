"""Tests des conclusions — Chesed de Tiferet.

Accueillir les voix de toutes les sources.
"""

import pytest


def test_submit_conclusion(engine_bare):
    """Soumettre une conclusion avec tous les champs."""
    c = engine_bare.submit_conclusion(
        content="Transformers are effective for NLP tasks",
        source_label="Vaswani et al.",
        source_type="paper",
        domain="ml",
        confidence=0.9,
        metadata={"year": 2017},
    )
    assert c.content == "Transformers are effective for NLP tasks"
    assert c.source_label == "Vaswani et al."
    assert c.source_type == "paper"
    assert c.domain == "ml"
    assert c.confidence == 0.9
    assert c.metadata == {"year": 2017}


def test_submit_multiple_sources(engine_bare):
    """Plusieurs sources sur le même sujet."""
    engine_bare.submit_conclusion(
        "Attention is sufficient for sequence tasks",
        source_label="Vaswani", source_type="paper", domain="ml",
    )
    engine_bare.submit_conclusion(
        "RNNs remain necessary for some sequence tasks",
        source_label="Hochreiter", source_type="paper", domain="ml",
    )
    all_c = engine_bare.db.get_all_conclusions(domain="ml")
    assert len(all_c) == 2
    labels = {c.source_label for c in all_c}
    assert labels == {"Vaswani", "Hochreiter"}


def test_conclusion_persists(engine_bare):
    """La conclusion persiste en DB."""
    c = engine_bare.submit_conclusion(
        "Test persistence", source_label="test", source_type="human",
    )
    retrieved = engine_bare.db.get_conclusion(c.id)
    assert retrieved is not None
    assert retrieved.content == "Test persistence"


def test_conclusion_types(engine_bare):
    """Tous les types de source sont acceptés."""
    for stype in ["paper", "model", "tradition", "experiment", "human", "system"]:
        c = engine_bare.submit_conclusion(
            f"Conclusion from {stype}",
            source_label=f"src_{stype}",
            source_type=stype,
        )
        assert c.source_type == stype
