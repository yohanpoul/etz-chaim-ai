"""Tests Qliphoth du sentier Lamed — les 4 niveaux de défaillance.

Le sentier Lamed peut lui-même défaillir dans son propre Birur.
"""

import pytest


def test_shallow_analysis_nogah(fti_bare):
    """Nogah: l'analyse d'échec est superficielle ("ça n'a pas marché").

    Description trop courte → le système doit le signaler.
    """
    # Créer une analyse avec description très courte
    fti_bare.analyze_failure("fail")
    fti_bare.analyze_failure("broken")
    fti_bare.analyze_failure("error")

    diag = fti_bare.self_diagnose()
    assert diag["level"] in ("nogah", "ruach", "anan")
    has_shallow = any("analyses avec description" in issue
                      for issue in diag["issues"])
    assert has_shallow


def test_wrong_classification_ruach(fti_bare):
    """Ruach: trop d'analyses classifiées "unknown" — mauvaise classification.

    Si > 30% des analyses sont "unknown", le classifieur est défaillant.
    """
    # Créer 4 analyses, 2 "unknown" (50% > 30%)
    fti_bare.analyze_failure("xyz abc def ghi jkl mno pqrs")
    fti_bare.analyze_failure("another mysterious problem here now")
    fti_bare.analyze_failure(
        "Filter rejected all results — nothing found", domain="search"
    )
    fti_bare.analyze_failure(
        "Retry stuck in infinite loop", domain="network"
    )

    diag = fti_bare.self_diagnose()
    has_unknown = any("unknown" in issue for issue in diag["issues"])
    assert has_unknown


def test_false_lesson_anan(fti_bare):
    """Anan: le système "apprend" une leçon fausse de l'échec.

    Insight haute confiance sur une analyse non classifiée = fausse leçon.
    """
    # Créer analyse "unknown" puis y mettre un insight haute confiance
    analysis = fti_bare.analyze_failure("xyz totally unknown failure desc")
    assert analysis.qliphah == "unknown"

    fti_bare.db.create_insight(
        analysis_id=analysis.id,
        content="This failure means we should always use method X",
        insight_type="pattern",
        confidence=0.9,  # haute confiance sur du "unknown" = danger
    )

    diag = fti_bare.self_diagnose()
    assert diag["level"] == "anan"
    has_false_lesson = any("insight haute confiance" in issue
                          for issue in diag["issues"])
    assert has_false_lesson


def test_no_analysis_mamash(fti_bare):
    """Mamash: les échecs ne sont pas analysés du tout.

    Ce test vérifie que le système détecte l'absence d'analyse.
    On ne peut pas tester directement dans FailureToInsight (c'est l'appelant
    qui doit envoyer les échecs), mais on vérifie que unextracted_failures
    signale les analyses sans insights.
    """
    # Créer des analyses sans jamais extraire de nitzotzot
    fti_bare.analyze_failure(
        "Failure that is never processed for insights",
        domain="testing",
    )
    fti_bare.analyze_failure(
        "Another unprocessed failure in the system",
        domain="testing",
    )

    unextracted = fti_bare.db.get_unextracted()
    assert len(unextracted) == 2

    diag = fti_bare.self_diagnose()
    has_unextracted = any("sans insights" in issue for issue in diag["issues"])
    assert has_unextracted


def test_proper_analysis_no_qliphah(fti_bare):
    """Analyse correcte : description suffisante, insights extraits → sain."""
    analysis = fti_bare.analyze_failure(
        "Database connection timeout after 30s on write-heavy workload",
        domain="infrastructure",
    )
    assert analysis.qliphah != "unknown"

    fti_bare.db.create_insight(
        analysis_id=analysis.id,
        content="Write-heavy workloads need connection pooling",
        insight_type="pattern",
        confidence=0.7,
    )

    diag = fti_bare.self_diagnose()
    # Should not raise critical issues
    assert diag["level"] in ("healthy", "nogah")


def test_multiple_insights_per_analysis(fti_bare):
    """Plusieurs insights par analyse : le Birur opère correctement."""
    analysis = fti_bare.analyze_failure(
        "Retry storm caused cascading failures across three microservices",
        domain="distributed",
    )

    fti_bare.db.create_insight(
        analysis_id=analysis.id,
        content="Circuit breakers needed between services",
        insight_type="pattern",
        confidence=0.8,
    )
    fti_bare.db.create_insight(
        analysis_id=analysis.id,
        content="Exponential backoff missing from retry logic",
        insight_type="constraint",
        confidence=0.9,
    )

    unextracted = fti_bare.db.get_unextracted()
    assert analysis.id not in [a.id for a in unextracted]


def test_low_confidence_insight_acceptable(fti_bare):
    """Insight basse confiance sur analyse classifiée : acceptable."""
    analysis = fti_bare.analyze_failure(
        "Memory leak detected in long-running worker process",
        domain="performance",
    )
    assert analysis.qliphah != "unknown"

    fti_bare.db.create_insight(
        analysis_id=analysis.id,
        content="Might be related to unclosed database cursors",
        insight_type="warning",
        confidence=0.3,  # Low but on a classified analysis = ok
    )

    diag = fti_bare.self_diagnose()
    has_false_lesson = any("insight haute confiance" in issue
                          for issue in diag["issues"])
    assert not has_false_lesson


def test_all_unknown_triggers_ruach(fti_bare):
    """100% unknown : le classifieur est clairement défaillant."""
    for i in range(5):
        fti_bare.analyze_failure(f"xyz unknown gibberish {i} abc def ghi")

    diag = fti_bare.self_diagnose()
    has_unknown = any("unknown" in issue for issue in diag["issues"])
    assert has_unknown
    assert diag["level"] in ("ruach", "anan", "mamash")


def test_two_analyses_same_domain(fti_bare):
    """Deux analyses dans le même domaine sont créées distinctement."""
    a1 = fti_bare.analyze_failure(
        "Connection refused to database server on port 5432",
        domain="database",
    )
    a2 = fti_bare.analyze_failure(
        "Connection timeout to database server on port 5432",
        domain="database",
    )

    assert a1.id != a2.id
    # Both in same domain
    assert a1.domain == a2.domain == "database"


def test_empty_system_healthy(fti_bare):
    """Système vide : diagnostic sain, pas de faux positifs."""
    diag = fti_bare.self_diagnose()
    assert diag["level"] == "healthy"
    assert len(diag["issues"]) == 0
