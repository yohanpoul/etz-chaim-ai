"""Tests du classificateur Qliphoth — Gevurah du sentier Lamed."""

import pytest

from failuretoinsight.classifier import classify_qliphah, classify_severity


class TestQliphahClassification:
    """Chaque Qliphah = le mode de défaillance SPÉCIFIQUE d'une Sephirah."""

    def test_gamaliel_memory(self):
        assert classify_qliphah("Data loss in memory storage") == "gamaliel"

    def test_samael_confidence(self):
        assert classify_qliphah("Overconfident routing to wrong model") == "samael"

    def test_aarab_zaraq_retry(self):
        assert classify_qliphah("Stuck in infinite retry loop, zombie process") == "aarab_zaraq"

    def test_thagirion_contradiction(self):
        assert classify_qliphah("Synthesis failed due to contradiction in sources") == "thagirion"

    def test_golachab_overfilter(self):
        assert classify_qliphah("Filter too strict, empty result set, nothing found") == "golachab"

    def test_gamchicoth_scope(self):
        assert classify_qliphah("Scope creep: too many resources consumed, overflow") == "gamchicoth"

    def test_hatehom_disconnect(self):
        assert classify_qliphah("Self-model disconnect: wrong capability assessment") == "hatehom"

    def test_satariel_false_pattern(self):
        assert classify_qliphah("False pattern detected: spurious correlation in noise") == "satariel"

    def test_ghagiel_divergence(self):
        assert classify_qliphah("No convergence in hypothesis generation, diverge") == "ghagiel"

    def test_thaumiel_dual_intent(self):
        assert classify_qliphah("Contradictory goals: two plans incompatible") == "thaumiel"

    def test_unknown_fallback(self):
        assert classify_qliphah("Something happened xyz") == "unknown"


class TestSeverityClassification:
    """4 niveaux — du plus grave au moins grave."""

    def test_mamash_crash(self):
        assert classify_severity("Total failure, system crash, data loss") == "mamash"

    def test_anan_silent(self):
        assert classify_severity("Seems ok but wrong — silent failure undetected") == "anan"

    def test_ruach_propagation(self):
        assert classify_severity("Error propagates to neighbor, resource leak") == "ruach"

    def test_nogah_minor(self):
        assert classify_severity("Minor warning, slow but recoverable") == "nogah"

    def test_default_nogah(self):
        assert classify_severity("Something went wrong") == "nogah"
