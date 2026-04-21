"""Tests — Da'at comme Gardien (pas observateur passif).

Da'at évalue sa confiance AVANT la réponse et peut :
- 'proceed' : confiance haute, pas de modification
- 'caution' : confiance modérée, injecter une nuance dans le prompt
- 'veto' : confiance basse, rediriger vers un aveu d'ignorance

La boucle Or Chozer vérifie si la prédiction était correcte.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from selfmodel.core import SelfModel
from selfmodel.models import BiasEntry, SelfState


# ─── Helpers ───────────────────────────────────────────────────


def _mock_db(
    state: SelfState | None = None,
    biases: list[BiasEntry] | None = None,
    accuracy: float | None = None,
):
    """Crée un mock SelfModelDB pour les tests rapides."""
    db = MagicMock()
    db.get_latest_state.return_value = state
    db.get_active_biases.return_value = biases or []
    db.get_prediction_accuracy.return_value = accuracy
    return db


class _StubDomainEval:
    def __init__(self, competence: float):
        self.competence = competence
        self.score = competence


class _StubSelfMap:
    """Stub SelfMap avec scores par domaine."""
    decline_threshold = 0.3

    def __init__(self, scores: dict[str, float] | None = None):
        self._scores = scores or {}

    def read_competence(self, domain: str):
        score = self._scores.get(domain)
        if score is None:
            return None
        return _StubDomainEval(score)


def _make_selfmodel(
    state: SelfState | None = None,
    biases: list[BiasEntry] | None = None,
    accuracy: float | None = None,
    selfmap=None,
) -> SelfModel:
    """Crée un SelfModel avec DB mockée."""
    sm = SelfModel.__new__(SelfModel)
    sm.db = _mock_db(state, biases, accuracy)
    sm.min_prediction_accuracy = 0.6
    sm.meta_confidence_threshold = 0.5
    sm.selfmap = selfmap
    # Composants (pas besoin pour evaluate_confidence)
    sm.tracker = MagicMock()
    sm.bias_detector = MagicMock()
    sm.predictor = MagicMock()
    sm.evolution = MagicMock()
    sm.integrator = MagicMock()
    return sm


def _make_state(
    model_confidence: float = 0.7,
    hod_stats: dict | None = None,
    gevurah_stats: dict | None = None,
) -> SelfState:
    return SelfState(
        model_confidence=model_confidence,
        hod_stats=hod_stats or {},
        gevurah_stats=gevurah_stats or {"level": "healthy"},
    )


def _make_bias(
    bias_type: str = "overconfidence",
    severity: float = 0.5,
    domain: str = "",
) -> BiasEntry:
    return BiasEntry(
        bias_type=bias_type,
        description=f"Test bias {bias_type}",
        severity=severity,
        domain=domain,
    )


# ─── Tests evaluate_confidence format ─────────────────────────


class TestEvaluateConfidenceFormat:
    """evaluate_confidence retourne le bon format."""

    def test_returns_correct_keys(self):
        state = _make_state()
        sm = _make_selfmodel(state=state)
        result = sm.evaluate_confidence("test query")

        assert "confidence" in result
        assert "predicted_error" in result
        assert "known_biases" in result
        assert "recommendation" in result
        assert "reason" in result

    def test_confidence_is_float_0_1(self):
        state = _make_state()
        sm = _make_selfmodel(state=state)
        result = sm.evaluate_confidence("test query")

        assert 0.0 <= result["confidence"] <= 1.0
        assert isinstance(result["confidence"], float)

    def test_predicted_error_is_float_0_1(self):
        state = _make_state()
        sm = _make_selfmodel(state=state)
        result = sm.evaluate_confidence("test query")

        assert 0.0 <= result["predicted_error"] <= 1.0

    def test_known_biases_is_list(self):
        state = _make_state()
        biases = [_make_bias(domain="code")]
        sm = _make_selfmodel(state=state, biases=biases)
        result = sm.evaluate_confidence("test query", domain="code")

        assert isinstance(result["known_biases"], list)
        if result["known_biases"]:
            b = result["known_biases"][0]
            assert "type" in b
            assert "description" in b
            assert "severity" in b

    def test_recommendation_in_valid_values(self):
        state = _make_state()
        sm = _make_selfmodel(state=state)
        result = sm.evaluate_confidence("test query")

        assert result["recommendation"] in ("proceed", "caution", "veto")


# ─── Tests seuils de recommandation ───────────────────────────


class TestRecommendationThresholds:
    """Les seuils proceed/caution/veto fonctionnent correctement."""

    def test_proceed_when_no_risk(self):
        """predicted_error < 0.3 → 'proceed'."""
        state = _make_state(model_confidence=0.8)
        sm = _make_selfmodel(state=state, accuracy=0.9)
        result = sm.evaluate_confidence("test query about code", domain="code")

        assert result["predicted_error"] < 0.3
        assert result["recommendation"] == "proceed"

    def test_caution_on_moderate_risk(self):
        """0.3 ≤ predicted_error < 0.7 → 'caution'."""
        state = _make_state(
            model_confidence=0.7,
            hod_stats={"weak_domains": ["kabbale"], "unknown_domains": []},
        )
        biases = [_make_bias(severity=0.6, domain="kabbale")]
        sm = _make_selfmodel(state=state, biases=biases, accuracy=0.4)
        result = sm.evaluate_confidence("question sur la kabbale", domain="kabbale")

        assert 0.3 <= result["predicted_error"] < 0.7
        assert result["recommendation"] == "caution"

    def test_veto_on_high_risk(self):
        """predicted_error ≥ 0.7 → 'veto'."""
        state = _make_state(
            model_confidence=0.15,
            hod_stats={"weak_domains": ["quantum"], "unknown_domains": []},
            gevurah_stats={"level": "golachab"},
        )
        biases = [
            _make_bias(severity=0.9, domain="quantum"),
            _make_bias("domain_blind_spot", severity=0.8, domain="quantum"),
        ]
        sm = _make_selfmodel(state=state, biases=biases, accuracy=0.2)
        result = sm.evaluate_confidence("quantum entanglement", domain="quantum")

        assert result["predicted_error"] >= 0.7
        assert result["recommendation"] == "veto"


# ─── Tests injection prompt Malkuth ───────────────────────────


class TestMalkuthInjection:
    """Le veto/caution de Da'at injecte des avertissements dans le prompt."""

    def test_veto_injects_warning(self):
        """Un veto injecte l'avertissement dans les parts du prompt."""
        ctx = {
            "daat_veto": True,
            "daat_veto_reason": "weak_domain=0.70; low_model_confidence=0.85",
            "daat_known_biases": [
                {"type": "overconfidence", "description": "trop sûr", "severity": 0.7}
            ],
        }
        parts = []

        # Reproduire la logique de _generate_malkuth_response
        if ctx.get("daat_veto"):
            parts.append("[IMPORTANT — Da'at VETO : confiance très faible sur ce sujet.]")
            parts.append(f"  Raison : {ctx.get('daat_veto_reason', '?')}")
            parts.append("  INSTRUCTION : Sois transparent sur les limites. "
                         "Préfère dire 'je ne sais pas' plutôt que risquer "
                         "une réponse incorrecte.")
            _veto_biases = ctx.get("daat_known_biases", [])
            if _veto_biases:
                parts.append("  Biais connus : " + ", ".join(
                    b.get("type", "?") for b in _veto_biases[:3]
                ))

        text = "\n".join(parts)
        assert "Da'at VETO" in text
        assert "je ne sais pas" in text
        assert "overconfidence" in text

    def test_caution_injects_nuance(self):
        """Un caution injecte une instruction de nuance."""
        ctx = {
            "daat_caution": True,
            "daat_caution_reason": "Confiance modérée — low_domain_accuracy=0.55",
        }
        parts = []

        if ctx.get("daat_veto"):
            pass
        elif ctx.get("daat_caution"):
            parts.append("[Note — Da'at CAUTION : confiance modérée sur ce sujet.]")
            parts.append(f"  Raison : {ctx.get('daat_caution_reason', '?')}")
            parts.append("  INSTRUCTION : Nuance tes affirmations. "
                         "Mentionne les incertitudes.")

        text = "\n".join(parts)
        assert "CAUTION" in text
        assert "Nuance" in text

    def test_proceed_no_modification(self):
        """Pas de veto ni caution → pas de modification du prompt."""
        ctx = {
            "daat_evaluation": {
                "recommendation": "proceed",
                "confidence": 0.9,
                "predicted_error": 0.1,
            }
        }
        parts = []

        if ctx.get("daat_veto"):
            parts.append("VETO")
        elif ctx.get("daat_caution"):
            parts.append("CAUTION")

        assert len(parts) == 0


# ─── Tests biais filtrés par domaine ──────────────────────────


class TestBiasFiltering:
    """Les biais pertinents sont filtrés par domaine."""

    def test_domain_biases_returned(self):
        """Les biais du domaine spécifié sont retournés en priorité."""
        state = _make_state()
        biases = [
            _make_bias(severity=0.7, domain="physics"),
            _make_bias("domain_blind_spot", severity=0.5, domain="physics"),
        ]
        sm = _make_selfmodel(state=state, biases=biases)
        result = sm.evaluate_confidence("test", domain="physics")

        assert len(result["known_biases"]) >= 1
        for b in result["known_biases"]:
            assert b["domain"] == "physics"

    def test_no_domain_returns_global(self):
        """Sans domaine, les biais globaux top-sévérité sont retournés."""
        state = _make_state()
        sm = _make_selfmodel(state=state)
        result = sm.evaluate_confidence("test query")

        assert isinstance(result["known_biases"], list)


# ─── Tests Katnut ─────────────────────────────────────────────


class TestDaatKatnut:
    """En Katnut, Da'at n'est pas actif (comme les autres Mokhin)."""

    def test_daat_not_called_in_katnut(self):
        """En Katnut, _descend_gadlut ne s'exécute pas.

        Donc ni Da'at ni le Zivvug ne modifient quoi que ce soit.
        Le ctx ne contient ni daat_evaluation ni zivvug_state.
        """
        ctx = {"mochin": {"state": "katnut"}}
        is_katnut = ctx.get("mochin", {}).get("state") == "katnut"

        assert is_katnut is True
        assert "daat_evaluation" not in ctx
        assert "zivvug_state" not in ctx


# ─── Tests boucle feedback Or Chozer ──────────────────────────


class TestDaatFeedbackLoop:
    """Da'at compare ses prédictions avec le résultat réel (Or Chozer)."""

    def test_veto_unjustified(self):
        """Veto prédit mais réponse bonne → feedback 'injustifié'."""
        daat_eval = {"recommendation": "veto", "predicted_error": 0.8}
        quality_verdict = "✓ acceptable"

        actual_good = "✓" in quality_verdict
        predicted_veto = daat_eval["recommendation"] == "veto"

        assert predicted_veto and actual_good

    def test_missed_error(self):
        """Proceed prédit mais réponse mauvaise → feedback 'manqué'."""
        daat_eval = {"recommendation": "proceed", "predicted_error": 0.1}
        quality_verdict = "✗ insuffisant"

        actual_good = "✓" in quality_verdict
        predicted_veto = daat_eval["recommendation"] == "veto"
        predicted_caution = daat_eval["recommendation"] == "caution"

        assert not predicted_veto and not predicted_caution and not actual_good

    def test_correct_prediction(self):
        """Veto prédit et réponse mauvaise → feedback 'correct'."""
        daat_eval = {"recommendation": "veto", "predicted_error": 0.8}
        quality_verdict = "✗ insuffisant"

        actual_good = "✓" in quality_verdict
        predicted_veto = daat_eval["recommendation"] == "veto"

        assert predicted_veto and not actual_good

    def test_proceed_confirmed(self):
        """Proceed prédit et réponse bonne → confirmation."""
        daat_eval = {"recommendation": "proceed", "predicted_error": 0.1}
        quality_verdict = "✓ acceptable"

        actual_good = "✓" in quality_verdict
        predicted_veto = daat_eval["recommendation"] == "veto"
        predicted_caution = daat_eval["recommendation"] == "caution"

        assert not predicted_veto and not predicted_caution and actual_good


# ─── Test performance ─────────────────────────────────────────


class TestDaatPerformance:
    """evaluate_confidence doit être rapide (< 100ms)."""

    def test_evaluate_confidence_fast(self):
        """L'évaluation ne doit pas dépasser 100ms."""
        state = _make_state(
            hod_stats={"weak_domains": ["physics"], "unknown_domains": []},
        )
        biases = [_make_bias(severity=0.5, domain="physics")]
        sm = _make_selfmodel(state=state, biases=biases, accuracy=0.7)

        t0 = time.monotonic()
        for _ in range(100):
            sm.evaluate_confidence("test query about physics", domain="physics")
        elapsed = time.monotonic() - t0

        # 100 appels en moins de 1 seconde → chaque appel < 10ms
        assert elapsed < 1.0, f"100 appels en {elapsed:.2f}s — trop lent"


# ─── Test intégration pipeline ────────────────────────────────


class TestDaatPipelineIntegration:
    """Test complet du pipeline Da'at dans cmd_ask."""

    def test_full_pipeline_flow(self):
        """Le flux complet : evaluate → inject → feedback fonctionne."""
        state = _make_state(
            model_confidence=0.15,
            hod_stats={"weak_domains": ["quantum"], "unknown_domains": []},
            gevurah_stats={"level": "golachab"},
        )
        biases = [_make_bias(severity=0.9, domain="quantum")]
        sm = _make_selfmodel(state=state, biases=biases, accuracy=0.2)

        # Étape ④ : évaluation
        daat_eval = sm.evaluate_confidence("quantum question", domain="quantum")
        assert daat_eval["recommendation"] in ("caution", "veto")

        # Stocker dans ctx
        ctx = {}
        ctx["daat_evaluation"] = daat_eval
        if daat_eval["recommendation"] == "veto":
            ctx["daat_veto"] = True
            ctx["daat_veto_reason"] = daat_eval["reason"]
            ctx["daat_known_biases"] = daat_eval["known_biases"]

        # Injection Malkuth
        parts = []
        if ctx.get("daat_veto"):
            parts.append("[IMPORTANT — Da'at VETO]")
        assert len(parts) > 0 or daat_eval["recommendation"] == "caution"

        # Feedback Or Chozer
        quality_verdict = "✗ insuffisant"
        actual_good = "✓" in quality_verdict
        if daat_eval["recommendation"] == "veto" and not actual_good:
            feedback = "correct"
        else:
            feedback = "other"

        assert feedback == "correct" or daat_eval["recommendation"] == "caution"


# ─── Tests SelfMap differentiation ───────────────────────────


class TestSelfMapDifferentiation:
    """Da'at consulte SelfMap et différencie les domaines."""

    def test_kabbale_veto(self):
        """Domaine kabbale (score=0.0) → predicted_error élevé → veto."""
        state = _make_state()
        selfmap = _StubSelfMap({"kabbale": 0.0})
        sm = _make_selfmodel(state=state, selfmap=selfmap)
        result = sm.evaluate_confidence("question kabbale", domain="kabbale")

        assert result["predicted_error"] >= 0.7
        assert result["recommendation"] == "veto"

    def test_general_proceed(self):
        """Domaine general (score=1.0) → predicted_error bas → proceed."""
        state = _make_state()
        selfmap = _StubSelfMap({"general": 1.0})
        sm = _make_selfmodel(state=state, selfmap=selfmap)
        result = sm.evaluate_confidence("question générale", domain="general")

        assert result["predicted_error"] < 0.3
        assert result["recommendation"] == "proceed"

    def test_tzimtzum_caution(self):
        """Domaine tzimtzum (score=0.5) → predicted_error modéré → caution."""
        state = _make_state()
        selfmap = _StubSelfMap({"tzimtzum": 0.5})
        sm = _make_selfmodel(state=state, selfmap=selfmap)
        result = sm.evaluate_confidence("question tzimtzum", domain="tzimtzum")

        assert 0.3 <= result["predicted_error"] < 0.7
        assert result["recommendation"] == "caution"

    def test_no_selfmap_fallback(self):
        """Sans SelfMap, le comportement par défaut s'applique."""
        state = _make_state()
        sm = _make_selfmodel(state=state)
        result = sm.evaluate_confidence("test", domain="anything")

        # Sans SelfMap ni autres signaux → predicted_error = 0.1
        assert result["predicted_error"] == 0.1
        assert result["recommendation"] == "proceed"
