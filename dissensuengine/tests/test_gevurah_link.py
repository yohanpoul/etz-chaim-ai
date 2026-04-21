"""Tests du lien Tiferet↔Gevurah — les dissensus alimentent FailureToInsight.

Un dissensus = une synthèse échouée → classifiée comme Thagirion.
"""

import pytest


def test_dissensus_feeds_failuretoinsight(engine):
    """Un dissensus est enregistré comme échec Thagirion dans FailureToInsight."""
    engine.submit_conclusion(
        "The approach always produces correct and valid results",
        source_label="Optimist", source_type="paper", domain="fti_link",
    )
    engine.submit_conclusion(
        "The approach never produces correct results and always fails",
        source_label="Pessimist", source_type="paper", domain="fti_link",
    )
    syn = engine.synthesize_or_dissent(domain="fti_link")

    if syn.mode == "dissensus":
        analyses = engine.failuretoinsight.db.get_all_analyses()
        thagirion = [a for a in analyses if a.qliphah == "thagirion"]
        assert len(thagirion) >= 1
        assert "dissensus" in thagirion[0].description.lower()
