"""Tests des 4 niveaux de HaTehom — Anti-Qliphoth de Da'at.

Mamash : pas de self-model → l'Abîme n'est pas traversé
Anan  : faux self-model → le nuage qui rassure faussement
Ruach : self-model qui sur-estime → le vent de l'orgueil
Nogah : self-model légèrement décalé → la lueur trompeuse
"""

from selfmodel.models import (
    BiasEntry,
    EvolutionSnapshot,
    Prediction,
    SelfState,
)


class TestMamash:
    """Mamash — pas de self-model, l'Abîme béant."""

    def test_mamash_no_state(self, model):
        """Aucun état → Mamash."""
        diag = model.self_diagnose()
        assert diag["level"] == "mamash"
        assert any("no SelfModel state" in i for i in diag["issues"])

    def test_mamash_critically_low_confidence(self, model):
        """Confiance < 0.2 → Mamash même avec un état."""
        state = SelfState(model_confidence=0.1)
        model.db.save_state(state)
        diag = model.self_diagnose()
        assert diag["level"] == "mamash"
        assert any("critically low" in i for i in diag["issues"])


class TestAnan:
    """Anan — le faux self-model qui rassure."""

    def test_anan_false_predictions(self, model):
        """Accuracy bien en dessous du seuil → Anan."""
        # Create a state
        state = SelfState(model_confidence=0.5)
        model.db.save_state(state)

        # Create verified predictions that are mostly wrong
        for i in range(10):
            pred = Prediction(
                prediction=f"pred {i}",
                predicted_error_type="samael",
                predicted_confidence=0.8,
            )
            saved = model.db.save_prediction(pred)
            model.db.verify_prediction(saved.id, i < 2)  # 2/10 correct = 20%

        diag = model.self_diagnose()
        assert diag["level"] == "anan"
        assert any("Anan" in i for i in diag["issues"])
        assert any("false self-image" in i for i in diag["issues"])


class TestRuach:
    """Ruach — le vent de l'overconfidence."""

    def test_ruach_overconfidence_biases(self, model):
        """Biais d'overconfidence actifs → Ruach."""
        # Create a state with adequate confidence
        state = SelfState(model_confidence=0.6)
        model.db.save_state(state)

        # Create active overconfidence biases with high severity
        for domain in ["physics", "biology"]:
            bias = BiasEntry(
                bias_type="overconfidence",
                description=f"Overconfident in {domain}",
                severity=0.7,
                domain=domain,
            )
            model.db.save_bias(bias)

        diag = model.self_diagnose()
        assert diag["level"] == "ruach"
        assert any("Ruach" in i for i in diag["issues"])
        assert any("overconfidence" in i for i in diag["issues"])


class TestNogah:
    """Nogah — la lueur légèrement trompeuse."""

    def test_nogah_accuracy_below_threshold(self, model):
        """Accuracy en dessous du seuil mais pas critique → Nogah."""
        # Create a state
        state = SelfState(model_confidence=0.6)
        model.db.save_state(state)

        # Create verified predictions: 5/10 correct = 50% < 60% threshold
        for i in range(10):
            pred = Prediction(
                prediction=f"pred {i}",
                predicted_error_type="samael",
                predicted_confidence=0.5,
            )
            saved = model.db.save_prediction(pred)
            model.db.verify_prediction(saved.id, i < 5)  # 5/10 = 50%

        diag = model.self_diagnose()
        assert diag["level"] == "nogah"
        assert any("Nogah" in i for i in diag["issues"])
        assert any("recalibration" in i for i in diag["issues"])


class TestHealthy:
    """Healthy — Da'at traverse l'Abîme avec clarté."""

    def test_healthy_no_issues(self, model):
        """État sain, bonnes prédictions → healthy."""
        state = SelfState(model_confidence=0.7)
        model.db.save_state(state)

        # Good predictions: 8/10 correct = 80%
        for i in range(10):
            pred = Prediction(
                prediction=f"pred {i}",
                predicted_error_type="samael",
                predicted_confidence=0.7,
            )
            saved = model.db.save_prediction(pred)
            model.db.verify_prediction(saved.id, i < 8)

        diag = model.self_diagnose()
        assert diag["level"] == "healthy"
        assert diag["issues"] == []


class TestHierarchyPriority:
    """Les niveaux HaTehom suivent une hiérarchie stricte."""

    def test_mamash_overrides_all(self, model):
        """Mamash (pas d'état) prime sur tout."""
        diag = model.self_diagnose()
        assert diag["level"] == "mamash"

    def test_anan_checked_before_ruach(self, model):
        """Anan (faux self-image) est vérifié avant Ruach."""
        state = SelfState(model_confidence=0.6)
        model.db.save_state(state)

        # Both: bad predictions AND overconfidence biases
        for i in range(10):
            pred = Prediction(
                prediction=f"pred {i}",
                predicted_error_type="samael",
                predicted_confidence=0.8,
            )
            saved = model.db.save_prediction(pred)
            model.db.verify_prediction(saved.id, i < 2)  # 20% accuracy

        bias = BiasEntry(
            bias_type="overconfidence",
            description="Global overconfidence",
            severity=0.8,
        )
        model.db.save_bias(bias)

        diag = model.self_diagnose()
        # Anan should be detected (accuracy < min * 0.7)
        assert diag["level"] == "anan"
        # Ruach should also be reported as secondary issue
        assert any("Ruach" in i for i in diag["issues"])


class TestCaptureState:
    """capture_state() — pipeline complet de Da'at."""

    def test_capture_minimal(self, model):
        """Capture avec aucun module → état basique mais valide."""
        state = model.capture_state()
        assert state.id is not None
        assert state.model_confidence > 0

    def test_capture_persists(self, model):
        """L'état capturé est persisté en DB."""
        state = model.capture_state()
        latest = model.db.get_latest_state()
        assert latest is not None
        assert latest.id == state.id

    def test_capture_detects_biases(self, model):
        """La capture détecte aussi les biais."""
        state = model.capture_state()
        # With no modules, no biases expected
        assert isinstance(state.known_biases, list)


class TestPredictError:
    """predict_error() — prédiction pré-exécution."""

    def test_predict_requires_state(self, model):
        """Sans état, pas de prédictions."""
        preds = model.predict_error("Do something")
        assert preds == []

    def test_predict_after_capture(self, model_with_state):
        """Après capture, prédictions basiques disponibles."""
        preds = model_with_state.predict_error("Analyze kabbale text about sefirot")
        # At least some predictions from state analysis
        assert isinstance(preds, list)


class TestTrackEvolution:
    """track_evolution() — suivi temporel."""

    def test_first_evolution(self, model):
        """Premier track → snapshot stable."""
        snap = model.track_evolution()
        assert snap.id is not None
        assert snap.trend == "stable"
        assert 0 <= snap.overall_health <= 1

    def test_evolution_after_multiple_captures(self, model):
        """Plusieurs captures → évolution traçable."""
        model.capture_state()
        snap1 = model.track_evolution()
        model.capture_state()
        snap2 = model.track_evolution()
        assert snap2.id is not None
        assert snap2.id != snap1.id


class TestWhoAmI:
    """who_am_i() — la question ultime de Da'at."""

    def test_who_am_i_minimal(self, model):
        """Réponse minimale sans modules."""
        desc = model.who_am_i()
        assert isinstance(desc.strengths, list)
        assert isinstance(desc.weaknesses, list)
        assert isinstance(desc.blind_spots, list)
        assert desc.confidence_in_self_model > 0

    def test_who_am_i_reports_blind_spots(self, model):
        """Les modules non connectés sont signalés."""
        desc = model.who_am_i()
        # All 6 modules disconnected → 6 blind spots
        assert len(desc.blind_spots) >= 6


class TestReport:
    """report() — Malkuth de Da'at."""

    def test_report_format(self, model):
        """Le rapport est lisible et contient les sections clés."""
        report = model.report()
        assert "SelfModel Report" in report
        assert "Self-diagnosis:" in report
        assert "Confidence in self-model:" in report
