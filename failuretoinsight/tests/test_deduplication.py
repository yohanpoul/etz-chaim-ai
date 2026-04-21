"""Tests déduplication FTI 24h — Sprint 8b fix 2.

Les qliphah extractions canned ("Boucle de retry détectée…") produisaient
31% du bruit rejeté par novelty_assessor dans candidate_insights : le
même insight FTI arrivait plusieurs fois par jour. Déduplication glissante
à 24h au niveau storage.
"""

from __future__ import annotations

import pytest


def test_same_content_within_24h_skipped(fti_bare):
    """Même content dans un second appel < 24h : skip, seul le 1er insère."""
    analysis1 = fti_bare.analyze_failure(
        description="First retry loop failure in domain X",
        domain="net",
    )
    insights1 = fti_bare.extract_nitzotzot(
        analysis1.id,
        insights_data=[{
            "content": "Boucle de retry détectée — adapter la stratégie",
            "insight_type": "warning",
            "confidence": 0.6,
        }],
    )
    assert len(insights1) == 1

    # Deuxième analyse, même content proposé → doit être skippé
    analysis2 = fti_bare.analyze_failure(
        description="Second retry loop failure in domain Y",
        domain="net",
    )
    insights2 = fti_bare.extract_nitzotzot(
        analysis2.id,
        insights_data=[{
            "content": "Boucle de retry détectée — adapter la stratégie",
            "insight_type": "warning",
            "confidence": 0.6,
        }],
    )
    assert insights2 == []


def test_different_content_both_inserted(fti_bare):
    """Deux contents différents → les deux insèrent."""
    analysis1 = fti_bare.analyze_failure(
        description="Filter too strict in search", domain="search",
    )
    insights1 = fti_bare.extract_nitzotzot(
        analysis1.id,
        insights_data=[{
            "content": "Threshold adaptatif recommandé pour les filtres",
            "insight_type": "constraint",
            "confidence": 0.7,
        }],
    )
    analysis2 = fti_bare.analyze_failure(
        description="Scope creep in planning", domain="planning",
    )
    insights2 = fti_bare.extract_nitzotzot(
        analysis2.id,
        insights_data=[{
            "content": "Scope creep détecté — poser des limites fermes",
            "insight_type": "constraint",
            "confidence": 0.5,
        }],
    )
    assert len(insights1) == 1
    assert len(insights2) == 1


def test_same_content_after_24h_inserted(fti_bare):
    """Même content mais > 24h dans le passé : insère à nouveau.

    On vérifie le contrat via recent_insight_exists() en manipulant
    directement created_at dans la DB pour simuler un insight > 24h.
    """
    analysis = fti_bare.analyze_failure(
        description="Recurring pattern A", domain="test",
    )
    fti_bare.extract_nitzotzot(
        analysis.id,
        insights_data=[{
            "content": "Canned content X pour test 24h window",
            "insight_type": "warning",
            "confidence": 0.5,
        }],
    )
    # Reculer le created_at de 48h
    with fti_bare.db._cursor() as cur:
        cur.execute(
            """UPDATE failuretoinsight_insights
               SET created_at = NOW() - INTERVAL '48 hours'
               WHERE content = %s""",
            ("Canned content X pour test 24h window",),
        )

    # Le check doit indiquer que l'insight n'est plus "récent"
    assert not fti_bare.db.recent_insight_exists(
        "Canned content X pour test 24h window", hours=24,
    )

    # Un nouvel appel doit réinsérer
    analysis2 = fti_bare.analyze_failure(
        description="Recurring pattern A bis", domain="test",
    )
    insights = fti_bare.extract_nitzotzot(
        analysis2.id,
        insights_data=[{
            "content": "Canned content X pour test 24h window",
            "insight_type": "warning",
            "confidence": 0.5,
        }],
    )
    assert len(insights) == 1
