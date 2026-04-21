"""Tests KavvanahGate — évaluation de la qualité de l'intention."""

import pytest

from malakhim.kavvanah_gate import kavvanah_score, TIER_HIGH, TIER_LOW
from malakhim.models import KavvanahGrade


class TestKavvanahScore:
    """Score et tier de la kavvanah."""

    def test_empty_kavvanah_short_prompt_is_low(self):
        """Pas de kavvanah, prompt court → LOW (Assiah/Ishim)."""
        grade = kavvanah_score(None, "résume ça")
        assert grade.tier == "low"
        assert grade.score < TIER_LOW

    def test_empty_kavvanah_long_prompt_is_still_low(self):
        """Même un long prompt sans kavvanah reste en dessous de medium."""
        grade = kavvanah_score(None, "a" * 200)
        assert grade.tier in ("low", "medium")
        # Au mieux : prompt_specificity (0.15) + not_question_only (0.10) = 0.25 < 0.3
        assert grade.score < TIER_HIGH

    def test_full_kavvanah_is_high(self):
        """Kavvanah complète → HIGH (Atziluth, pas de Malakh)."""
        kav = {
            "intention": "analyser les failles de sécurité",
            "critere_succes": "lister au moins 3 vulnérabilités OWASP",
            "anti_pattern": "VERBOSE",
            "domain": "security",
            "required_keywords": ["XSS", "injection"],
        }
        prompt = "Analyse les failles de sécurité de ce module d'authentification qui gère les sessions utilisateur et les tokens JWT"
        grade = kavvanah_score(kav, prompt)
        assert grade.tier == "high"
        assert grade.score >= TIER_HIGH
        assert len(grade.missing) <= 1

    def test_partial_kavvanah_is_medium(self):
        """Kavvanah partielle → MEDIUM (Yetzirah, Malakh engendré)."""
        kav = {
            "intention": "analyser le code",
            "domain": "code",
        }
        prompt = "Regarde ce fichier et dis-moi si tu vois des problèmes dans l'architecture du module de paiement et les patterns utilisés"
        grade = kavvanah_score(kav, prompt)
        assert grade.tier == "medium"
        assert TIER_LOW <= grade.score < TIER_HIGH

    def test_question_only_penalized(self):
        """Une simple question sans contexte perd des points."""
        kav = {"intention": "comprendre", "domain": "code"}
        grade_question = kavvanah_score(kav, "Comment ça marche?")
        grade_statement = kavvanah_score(
            kav,
            "Explique le fonctionnement du pipeline de validation en détaillant chaque étape du processus de traitement",
        )
        assert grade_statement.score > grade_question.score

    def test_returns_kavvanah_grade(self):
        """Le retour est toujours un KavvanahGrade."""
        grade = kavvanah_score({}, "test")
        assert isinstance(grade, KavvanahGrade)
        assert isinstance(grade.score, float)
        assert grade.tier in ("high", "medium", "low")
        assert isinstance(grade.missing, list)

    def test_missing_lists_absent_fields(self):
        """Les champs manquants sont listés."""
        grade = kavvanah_score({"intention": "test"}, "court")
        assert "critere_succes" in grade.missing
        assert "anti_pattern" in grade.missing
        assert "intention" not in grade.missing

    def test_score_clamped_to_0_1(self):
        """Le score ne dépasse jamais 1.0."""
        kav = {
            "intention": "x", "critere_succes": "x", "anti_pattern": "x",
            "domain": "x", "required_keywords": ["x"],
        }
        grade = kavvanah_score(kav, "a" * 200)
        assert grade.score <= 1.0

    def test_none_kavvanah_is_safe(self):
        """kavvanah=None ne crash pas."""
        grade = kavvanah_score(None, "test prompt")
        assert grade.tier in ("low", "medium", "high")

    def test_empty_prompt_is_low(self):
        """Prompt vide → LOW."""
        grade = kavvanah_score({}, "")
        assert grade.tier == "low"
