"""Tests de synthèse/dissensus — le verdict de Tiferet.

Le cœur : synthèse quand convergence, dissensus quand divergence.
"""

import pytest


def test_synthesis_agreeing_sources(engine_bare):
    """Sources concordantes → mode synthesis."""
    engine_bare.submit_conclusion(
        "Attention mechanisms improve model performance on language tasks",
        source_label="Vaswani", source_type="paper", domain="nlp",
    )
    engine_bare.submit_conclusion(
        "Self-attention helps models capture long-range dependencies in text",
        source_label="Devlin", source_type="paper", domain="nlp",
    )
    syn = engine_bare.synthesize_or_dissent(domain="nlp")
    assert syn.mode == "synthesis"
    assert syn.confidence > engine_bare.confidence_floor


def test_dissensus_contradictory_sources(engine_bare):
    """Sources contradictoires → mode dissensus."""
    engine_bare.submit_conclusion(
        "The drug always increases patient survival rate significantly",
        source_label="Trial A", source_type="experiment", domain="pharma",
    )
    engine_bare.submit_conclusion(
        "The drug never increases patient survival rate and is ineffective",
        source_label="Trial B", source_type="experiment", domain="pharma",
    )
    syn = engine_bare.synthesize_or_dissent(domain="pharma")
    assert syn.mode == "dissensus"
    assert "DISSENSUS" in syn.content


def test_dissensus_insufficient_sources(engine_bare):
    """Pas assez de sources → dissensus par défaut."""
    engine_bare.submit_conclusion(
        "Single source claim", source_label="A",
        source_type="paper", domain="solo",
    )
    syn = engine_bare.synthesize_or_dissent(domain="solo")
    assert syn.mode == "dissensus"
    assert "insuffisantes" in syn.content.lower()


def test_synthesis_includes_source_ids(engine_bare):
    """La synthèse référence les conclusions utilisées."""
    c1 = engine_bare.submit_conclusion(
        "Feature extraction works with convolutions",
        source_label="LeCun", source_type="paper", domain="cv",
    )
    c2 = engine_bare.submit_conclusion(
        "Convolutional layers extract hierarchical features from images",
        source_label="Krizhevsky", source_type="paper", domain="cv",
    )
    syn = engine_bare.synthesize_or_dissent(domain="cv")
    assert c1.id in syn.sources_used
    assert c2.id in syn.sources_used


def test_synthesis_confidence_bounded(engine_bare):
    """La confiance est toujours ≥ confidence_floor."""
    engine_bare.submit_conclusion(
        "A general claim about X", source_label="A",
        source_type="paper", domain="test",
    )
    engine_bare.submit_conclusion(
        "Another general claim about Y", source_label="B",
        source_type="paper", domain="test",
    )
    syn = engine_bare.synthesize_or_dissent(domain="test")
    assert syn.confidence >= engine_bare.confidence_floor


def test_dissensus_content_shows_tensions(engine_bare):
    """Le dissensus expose les tensions détectées."""
    engine_bare.submit_conclusion(
        "Performance always increases with more data",
        source_label="Big Data Inc", source_type="paper", domain="scale",
    )
    engine_bare.submit_conclusion(
        "Performance never increases with more data alone",
        source_label="Quality Lab", source_type="paper", domain="scale",
    )
    syn = engine_bare.synthesize_or_dissent(domain="scale")
    if syn.mode == "dissensus":
        assert "Big Data Inc" in syn.content or "Quality Lab" in syn.content


def test_synthesis_by_ids(engine_bare):
    """Synthèse sur un sous-ensemble de conclusions par IDs."""
    c1 = engine_bare.submit_conclusion(
        "Claim one about topic", source_label="A",
        source_type="paper", domain="sub",
    )
    c2 = engine_bare.submit_conclusion(
        "Claim two about same topic", source_label="B",
        source_type="paper", domain="sub",
    )
    engine_bare.submit_conclusion(
        "Unrelated claim", source_label="C",
        source_type="paper", domain="sub",
    )
    syn = engine_bare.synthesize_or_dissent(conclusion_ids=[c1.id, c2.id])
    assert len(syn.sources_used) == 2
