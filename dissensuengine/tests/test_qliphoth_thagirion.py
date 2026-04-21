"""Tests Qliphoth de Tiferet — Thagirion (les Disputeurs).

Les 4 niveaux de défaillance de la synthèse.
Anti-Thagirion : JAMAIS de fausse harmonie.
"""

import pytest


def test_minor_divergence_flagged(engine_bare):
    """Nogah: divergence mineure détectée et signalée.

    Le système ne doit PAS ignorer les petites divergences.
    """
    # Soumettre des conclusions légèrement divergentes
    engine_bare.submit_conclusion(
        "The model performance always improves with regularization",
        source_label="A", source_type="paper", domain="ml",
    )
    engine_bare.submit_conclusion(
        "The model performance never improves with regularization alone",
        source_label="B", source_type="paper", domain="ml",
    )
    # Analyze consistency creates tensions
    report = engine_bare.analyze_consistency(domain="ml")
    assert report.total_tensions >= 1
    assert report.max_divergence > 0.0


def test_sources_all_represented(engine_bare):
    """Ruach: toutes les sources représentées dans la synthèse.

    Une synthèse qui ignore des sources est une Qliphah.
    """
    c1 = engine_bare.submit_conclusion(
        "Approach A yields good results on benchmark tasks",
        source_label="Lab1", source_type="paper", domain="bench",
    )
    c2 = engine_bare.submit_conclusion(
        "Approach A produces solid outcomes on evaluation sets",
        source_label="Lab2", source_type="paper", domain="bench",
    )
    c3 = engine_bare.submit_conclusion(
        "Approach A demonstrates strong performance overall",
        source_label="Lab3", source_type="paper", domain="bench",
    )

    syn = engine_bare.synthesize_or_dissent(domain="bench")
    # All 3 sources should be in the synthesis
    assert c1.id in syn.sources_used
    assert c2.id in syn.sources_used
    assert c3.id in syn.sources_used
    assert syn.source_coverage >= 0.99  # 3/3


def test_false_harmony_detected(engine_bare):
    """Anan: détecte quand le système force une cohérence artificielle.

    Si une synthèse haute confiance coexiste avec des tensions ouvertes
    impliquant les mêmes sources → fausse harmonie = Thagirion.
    """
    # Créer conclusions contradictoires
    c1 = engine_bare.submit_conclusion(
        "Treatment always increases survival rate",
        source_label="Trial1", source_type="experiment", domain="anan",
    )
    c2 = engine_bare.submit_conclusion(
        "Treatment never increases survival rate",
        source_label="Trial2", source_type="experiment", domain="anan",
    )

    # Analyser la cohérence (crée les tensions)
    engine_bare.analyze_consistency(domain="anan")

    # Forcer une synthèse haute confiance malgré la tension
    # (injection directe en DB pour simuler le bug)
    engine_bare.db.create_synthesis(
        mode="synthesis",
        content="Treatment is moderately effective",
        sources_used=[c1.id, c2.id],
        source_coverage=1.0,
        max_divergence=0.3,  # sous-estimée !
        confidence=0.8,      # haute confiance malgré tension
        domain="anan",
    )

    diag = engine_bare.self_diagnose()
    assert diag["level"] == "anan"
    has_false_harmony = any("synthèse confiante" in issue.lower()
                           or "anan" in issue.lower()
                           for issue in diag["issues"])
    assert has_false_harmony


def test_conclusion_vs_evidence(engine_bare):
    """Mamash: la conclusion ne contredit pas les données.

    Si une synthèse a max_divergence ≥ seuil d'acceptabilité mais est
    en mode 'synthesis' → la conclusion contredit l'évidence.
    """
    c1 = engine_bare.submit_conclusion(
        "Factual claim one", source_label="A", source_type="paper",
    )
    c2 = engine_bare.submit_conclusion(
        "Factual claim two", source_label="B", source_type="paper",
    )

    # Injection : synthèse avec divergence inacceptable
    engine_bare.db.create_synthesis(
        mode="synthesis",
        content="Forced conclusion ignoring contradictions",
        sources_used=[c1.id, c2.id],
        source_coverage=1.0,
        max_divergence=0.9,  # très au-dessus du seuil
        confidence=0.7,
        domain="mamash_test",
    )

    diag = engine_bare.self_diagnose()
    assert diag["level"] == "mamash"
    has_mamash = any("mamash" in issue.lower() for issue in diag["issues"])
    assert has_mamash


def test_healthy_system_no_thagirion(engine_bare):
    """Système sain : pas de Thagirion quand les synthèses sont cohérentes."""
    c1 = engine_bare.submit_conclusion(
        "Method A works well on text classification",
        source_label="Lab1", source_type="paper", domain="healthy",
    )
    c2 = engine_bare.submit_conclusion(
        "Method A performs strongly on NLP benchmarks",
        source_label="Lab2", source_type="paper", domain="healthy",
    )

    syn = engine_bare.synthesize_or_dissent(domain="healthy")
    assert syn.mode in ("synthesis", "consensus")
    assert syn.confidence >= 0.5

    diag = engine_bare.self_diagnose()
    assert diag["level"] not in ("anan", "mamash")


def test_contradictory_conclusions_handled(engine_bare):
    """Contradictions : le système produit un résultat (synthèse ou dissensus)."""
    engine_bare.submit_conclusion(
        "The earth is flat according to our measurements",
        source_label="Flat", source_type="experiment", domain="geo",
    )
    engine_bare.submit_conclusion(
        "The earth is spherical according to satellite imagery",
        source_label="Sphere", source_type="experiment", domain="geo",
    )

    syn = engine_bare.synthesize_or_dissent(domain="geo")
    # Le moteur produit un résultat quel que soit le mode
    assert syn.mode in ("synthesis", "dissent", "dissensus")
    assert len(syn.sources_used) >= 1


def test_empty_domain_no_crash(engine_bare):
    """Domaine vide : pas de crash."""
    syn = engine_bare.synthesize_or_dissent(domain="nonexistent")
    assert syn.mode in ("empty", "dissent", "dissensus", "synthesis")
    assert len(syn.sources_used) == 0


def test_single_source_synthesis(engine_bare):
    """Source unique : pas de tension possible."""
    c1 = engine_bare.submit_conclusion(
        "Only one perspective available here",
        source_label="Solo", source_type="paper", domain="solo",
    )

    report = engine_bare.analyze_consistency(domain="solo")
    assert report.total_tensions == 0


def test_multiple_claims_analyzed(engine_bare):
    """Claims multiples : le rapport les compte toutes."""
    for i in range(4):
        engine_bare.submit_conclusion(
            f"Claim number {i} with unique position",
            source_label=f"S{i}", source_type="paper", domain="escalate",
        )

    report = engine_bare.analyze_consistency(domain="escalate")
    assert report.total_conclusions == 4
    assert len(report.source_labels) == 4


def test_source_coverage_partial(engine_bare):
    """Couverture partielle : signalée quand une source est exclue."""
    c1 = engine_bare.submit_conclusion(
        "First finding on topic",
        source_label="A", source_type="paper", domain="coverage",
    )
    c2 = engine_bare.submit_conclusion(
        "Second finding on topic",
        source_label="B", source_type="paper", domain="coverage",
    )
    c3 = engine_bare.submit_conclusion(
        "Third finding on topic that is totally different",
        source_label="C", source_type="experiment", domain="coverage",
    )

    # Force a synthesis that uses only 2 of 3
    engine_bare.db.create_synthesis(
        mode="synthesis",
        content="Partial synthesis ignoring source C",
        sources_used=[c1.id, c2.id],
        source_coverage=2.0 / 3,
        max_divergence=0.1,
        confidence=0.7,
        domain="coverage",
    )

    diag = engine_bare.self_diagnose()
    has_coverage = any("source" in issue.lower() or "couverture" in issue.lower()
                       for issue in diag["issues"])
    assert has_coverage
