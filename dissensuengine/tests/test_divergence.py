"""Tests de divergence — Gevurah de Tiferet.

Mesurer la divergence entre conclusions sans pitié.
"""

import pytest

from dissensuengine.divergence import (
    classify_tension_type,
    compute_contradiction_score,
    compute_topic_similarity,
    measure_divergence,
)


def test_same_text_zero_divergence():
    """Textes identiques → divergence 0."""
    div = measure_divergence(
        "Neural networks are effective",
        "Neural networks are effective",
    )
    assert div == 0.0


def test_contradictory_texts_high_divergence():
    """Textes contradictoires sur le même sujet → haute divergence."""
    div = measure_divergence(
        "The model always succeeds on this task",
        "The model never succeeds on this task",
    )
    assert div > 0.3


def test_different_topics_low_divergence():
    """Sujets différents → basse divergence même si ton opposé."""
    div = measure_divergence(
        "The weather is always sunny in summer",
        "Database transactions never fail silently",
    )
    assert div < 0.3


def test_topic_similarity_high_overlap():
    """Textes sur le même sujet → haute similarité thématique."""
    sim = compute_topic_similarity(
        "Neural networks learn representations from data",
        "Neural networks extract features from training data",
    )
    assert sim > 0.2


def test_topic_similarity_no_overlap():
    """Sujets sans rapport → similarité ~0."""
    sim = compute_topic_similarity(
        "The cat sat on the mat",
        "Quantum physics explains entanglement",
    )
    assert sim < 0.1


def test_contradiction_score_antonyms():
    """Paires d'antonymes détectées."""
    score = compute_contradiction_score(
        "The results are always positive and significant",
        "The results are never negative and insignificant",
    )
    # "always" vs "never" et "positive"/"significant" present
    assert score > 0.0


def test_contradiction_score_negation():
    """Négation asymétrique détectée."""
    score = compute_contradiction_score(
        "This approach is effective and reliable",
        "This approach is not effective and not reliable",
    )
    assert score > 0.0


def test_classify_contradiction():
    """Haute divergence + haute contradiction = contradiction."""
    t = classify_tension_type(0.7, 0.5, 0.6)
    assert t == "contradiction"


def test_classify_scope_conflict():
    """Topic overlap modéré + contradiction modérée = scope_conflict."""
    t = classify_tension_type(0.4, 0.5, 0.35)
    assert t == "scope_conflict"


def test_classify_nuance():
    """Basse divergence = nuance."""
    t = classify_tension_type(0.1, 0.1, 0.05)
    assert t == "nuance"


def test_divergence_score_range():
    """Le score est toujours dans [0, 1]."""
    texts = [
        ("always true", "never false"),
        ("completely positive", "completely negative"),
        ("the sky is blue", "mathematics is abstract"),
        ("increase speed significantly", "decrease speed significantly"),
    ]
    for a, b in texts:
        d = measure_divergence(a, b)
        assert 0.0 <= d <= 1.0, f"Score {d} out of range for ({a!r}, {b!r})"


def test_measure_divergence_method(engine_bare):
    """DissensuEngine.measure_divergence via IDs."""
    ca = engine_bare.submit_conclusion(
        "The effect is always positive",
        source_label="A", source_type="paper",
    )
    cb = engine_bare.submit_conclusion(
        "The effect is never positive",
        source_label="B", source_type="paper",
    )
    div = engine_bare.measure_divergence(ca.id, cb.id)
    assert div > 0.3
