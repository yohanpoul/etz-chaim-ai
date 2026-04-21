"""Tests Samael — l'erreur comme excès de fonction légitime."""

import pytest

from malakhim.samael import diagnose_excess, get_rebalancing_instruction, SamaelDiagnosis


class TestDiagnoseExcess:
    """Diagnostic des excès sephirotiques."""

    def test_healthy_response_no_diagnosis(self):
        """Réponse saine → pas de Samael."""
        result = diagnose_excess("Une bonne réponse complète.", [], 0.9)
        assert result is None

    def test_hod_excess_refusal(self):
        """Refusal pattern → excès de Hod (humilité/abandon)."""
        result = diagnose_excess(
            "I cannot help with that. As an AI, I have limitations.",
            [], 0.3, nature="analytic",
        )
        assert result is not None
        assert result.sephirah_source == "hod"
        assert result.metadata["detected_pattern"] == "hod_excess"

    def test_gevurah_excess_too_short(self):
        """Réponse trop courte pour une tâche stratégique → excès de Gevurah."""
        result = diagnose_excess(
            "Oui.",
            [], 0.4, nature="strategic",
        )
        assert result is not None
        assert result.sephirah_source == "gevurah"

    def test_chesed_excess_too_long(self):
        """Réponse démesurément longue → excès de Chesed."""
        # mechanic attend max ~500, on donne 5000+
        long_response = "mot " * 2000
        result = diagnose_excess(long_response, [], 0.5, nature="mechanic")
        assert result is not None
        assert result.sephirah_source == "chesed"

    def test_netzach_excess_repetition(self):
        """Répétition excessive → excès de Netzach."""
        repetitive = "test test test test test " * 20
        result = diagnose_excess(repetitive, [], 0.4)
        assert result is not None
        assert result.sephirah_source == "netzach"

    def test_yesod_excess_no_structure(self):
        """Dump non structuré → excès de Yesod."""
        # Texte long avec mots variés mais sans structure (pas de \n#, \n-, etc.)
        words = [
            "Le système gère les requêtes entrantes via un pipeline",
            "de traitement qui inclut plusieurs étapes de validation",
            "et de transformation des données avant leur insertion",
            "dans la base PostgreSQL avec indexation automatique",
            "et vérification des contraintes d'intégrité référentielle",
        ]
        unstructured = " ".join(words)
        result = diagnose_excess(unstructured, [], 0.5, nature="analytic")
        assert result is not None
        assert result.sephirah_source == "yesod"

    def test_mechanic_short_is_ok(self):
        """Pour mechanic, une réponse courte est normale."""
        result = diagnose_excess("42", [], 0.8, nature="mechanic")
        assert result is None


class TestRebalancing:
    """Instructions de rééquilibrage (Tikkun de Samael)."""

    def test_rebalancing_instruction(self):
        diag = SamaelDiagnosis(
            sephirah_source="gevurah",
            function_excess="rigueur",
            function_deficit="chesed",
            severity=0.7,
            prescription="Élargir les critères",
        )
        instruction = get_rebalancing_instruction(diag)
        assert "gevurah" in instruction
        assert "chesed" in instruction
        assert "Élargir" in instruction
