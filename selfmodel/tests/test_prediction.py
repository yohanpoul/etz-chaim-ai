"""Tests Predictor — prédiction d'erreurs AVANT exécution."""

from selfmodel.models import BiasEntry, Prediction, SelfState
from selfmodel.predictor import Predictor, _bias_to_qliphah, _detect_domains


class TestDomainDetection:
    """Détection de domaines dans une description de tâche."""

    def test_detect_ml_domain(self):
        domains = _detect_domains("Train a transformer model with attention")
        assert "machine_learning" in domains

    def test_detect_kabbale_domain(self):
        domains = _detect_domains("Analyser les sefirot du zohar")
        assert "kabbale" in domains

    def test_detect_code_domain(self):
        domains = _detect_domains("Refactor the Python class and debug the test")
        assert "code" in domains

    def test_detect_multiple_domains(self):
        domains = _detect_domains(
            "Compare neural attention in transformer with brain cortex synapse"
        )
        assert "machine_learning" in domains
        assert "neuroscience" in domains

    def test_empty_text_no_domains(self):
        domains = _detect_domains("")
        assert domains == []

    def test_unknown_text_no_domains(self):
        domains = _detect_domains("Prepare dinner with pasta and tomatoes")
        assert domains == []

    def test_primary_domain_is_best_match(self):
        """Le domaine le mieux scoré est en premier."""
        domains = _detect_domains(
            "Train neural model with attention gradient backpropagation loss"
        )
        assert domains[0] == "machine_learning"


class TestBiasToQliphah:
    """Mapping des types de biais vers les Qliphoth."""

    def test_overconfidence_to_samael(self):
        assert _bias_to_qliphah("overconfidence") == "samael"

    def test_scope_creep_to_gamchicoth(self):
        assert _bias_to_qliphah("scope_creep") == "gamchicoth"

    def test_confirmation_bias_to_thagirion(self):
        assert _bias_to_qliphah("confirmation_bias") == "thagirion"

    def test_premature_closure_to_golachab(self):
        assert _bias_to_qliphah("premature_closure") == "golachab"

    def test_domain_blind_spot_to_satariel(self):
        assert _bias_to_qliphah("domain_blind_spot") == "satariel"

    def test_unknown_type(self):
        assert _bias_to_qliphah("nonexistent") == "unknown"


class TestPredictFromBiases:
    """Prédictions basées sur les biais actifs."""

    def test_matching_bias_generates_prediction(self):
        predictor = Predictor()
        bias = BiasEntry(
            bias_type="overconfidence",
            description="Overconfident in physics",
            severity=0.7,
            domain="physics",
        )
        preds = predictor._predict_from_biases(
            [bias], "physics", "Solve quantum physics problem"
        )
        assert len(preds) == 1
        assert preds[0].predicted_error_type == "samael"
        assert preds[0].predicted_confidence == 0.56  # 0.7 * 0.8

    def test_domain_mismatch_skips_bias(self):
        """Biais pour un domaine différent n'est pas retenu."""
        predictor = Predictor()
        bias = BiasEntry(
            bias_type="overconfidence",
            description="Overconfident in physics",
            severity=0.7,
            domain="physics",
        )
        preds = predictor._predict_from_biases(
            [bias], "code", "Debug Python function"
        )
        assert preds == []

    def test_global_bias_always_matches(self):
        """Biais sans domaine (global) match toujours."""
        predictor = Predictor()
        bias = BiasEntry(
            bias_type="overconfidence",
            description="Global overconfidence",
            severity=0.5,
            domain="",  # Global
        )
        preds = predictor._predict_from_biases(
            [bias], "code", "Debug Python function"
        )
        assert len(preds) == 1

    def test_severity_modulates_confidence(self):
        """La sévérité du biais module la confiance de la prédiction."""
        predictor = Predictor()
        low = BiasEntry(bias_type="overconfidence", description="low", severity=0.3)
        high = BiasEntry(bias_type="overconfidence", description="high", severity=0.9)
        preds_low = predictor._predict_from_biases([low], "", "task")
        preds_high = predictor._predict_from_biases([high], "", "task")
        assert preds_low[0].predicted_confidence < preds_high[0].predicted_confidence


class TestPredictFromState:
    """Prédictions basées sur l'état du système."""

    def test_weak_domain_generates_prediction(self):
        predictor = Predictor()
        state = SelfState(hod_stats={
            "weak_domains": ["chimie"],
            "unknown_domains": [],
        })
        preds = predictor._predict_from_state(state, "chimie", "Chimie task")
        weak_preds = [p for p in preds if "weak" in p.prediction.lower()]
        assert len(weak_preds) == 1
        assert weak_preds[0].predicted_error_type == "samael"
        assert weak_preds[0].predicted_confidence == 0.7

    def test_unknown_domain_generates_prediction(self):
        predictor = Predictor()
        state = SelfState(hod_stats={
            "weak_domains": [],
            "unknown_domains": ["droit"],
        })
        preds = predictor._predict_from_state(state, "droit", "Legal task")
        unknown_preds = [p for p in preds if "unknown" in p.prediction.lower()]
        assert len(unknown_preds) == 1
        assert unknown_preds[0].predicted_error_type == "satariel"

    def test_high_contradictions(self):
        """Beaucoup de contradictions dans Yesod → prédiction thagirion."""
        predictor = Predictor()
        state = SelfState(yesod_stats={"contradictions_open": 8})
        preds = predictor._predict_from_state(state, "", "task")
        assert len(preds) == 1
        assert preds[0].predicted_error_type == "thagirion"
        assert preds[0].predicted_confidence == 0.8

    def test_low_contradictions_no_prediction(self):
        """Peu de contradictions → pas de prédiction."""
        predictor = Predictor()
        state = SelfState(yesod_stats={"contradictions_open": 3})
        preds = predictor._predict_from_state(state, "", "task")
        assert preds == []

    def test_unhealthy_gevurah(self):
        """Gevurah malade → prédiction golachab."""
        predictor = Predictor()
        state = SelfState(gevurah_stats={"level": "ruach"})
        preds = predictor._predict_from_state(state, "", "task")
        assert len(preds) == 1
        assert preds[0].predicted_error_type == "golachab"

    def test_healthy_gevurah_no_prediction(self):
        """Gevurah healthy → pas de prédiction."""
        predictor = Predictor()
        state = SelfState(gevurah_stats={"level": "healthy"})
        preds = predictor._predict_from_state(state, "", "task")
        assert preds == []


class TestConfidenceAdjustment:
    """Ajustement de la confiance via l'historique des prédictions."""

    def test_good_accuracy_boosts_confidence(self):
        """Historique de prédictions correctes → boost."""
        predictor = Predictor()
        history = [
            Prediction(prediction="p", predicted_error_type="samael",
                       was_correct=True),
            Prediction(prediction="p", predicted_error_type="samael",
                       was_correct=True),
            Prediction(prediction="p", predicted_error_type="samael",
                       was_correct=True),
        ]
        preds = [Prediction(
            prediction="test",
            predicted_error_type="samael",
            predicted_confidence=0.5,
        )]
        predictor._adjust_confidence(preds, history)
        # accuracy = 1.0, adjustment = (1.0 - 0.5) * 0.4 = 0.2
        assert preds[0].predicted_confidence == 0.7

    def test_poor_accuracy_lowers_confidence(self):
        """Historique de prédictions fausses → baisse."""
        predictor = Predictor()
        history = [
            Prediction(prediction="p", predicted_error_type="samael",
                       was_correct=False),
            Prediction(prediction="p", predicted_error_type="samael",
                       was_correct=False),
            Prediction(prediction="p", predicted_error_type="samael",
                       was_correct=False),
        ]
        preds = [Prediction(
            prediction="test",
            predicted_error_type="samael",
            predicted_confidence=0.5,
        )]
        predictor._adjust_confidence(preds, history)
        # accuracy = 0.0, adjustment = (0.0 - 0.5) * 0.4 = -0.2
        assert preds[0].predicted_confidence == 0.3

    def test_insufficient_history_no_adjustment(self):
        """Moins de 3 prédictions vérifiées → pas d'ajustement."""
        predictor = Predictor()
        history = [
            Prediction(prediction="p", predicted_error_type="samael",
                       was_correct=True),
            Prediction(prediction="p", predicted_error_type="samael",
                       was_correct=True),
        ]
        preds = [Prediction(
            prediction="test",
            predicted_error_type="samael",
            predicted_confidence=0.5,
        )]
        predictor._adjust_confidence(preds, history)
        assert preds[0].predicted_confidence == 0.5  # Unchanged

    def test_unverified_history_ignored(self):
        """Prédictions non vérifiées sont ignorées."""
        predictor = Predictor()
        history = [
            Prediction(prediction="p", predicted_error_type="samael",
                       was_correct=None),  # Not verified
        ] * 5
        preds = [Prediction(
            prediction="test",
            predicted_error_type="samael",
            predicted_confidence=0.5,
        )]
        predictor._adjust_confidence(preds, history)
        assert preds[0].predicted_confidence == 0.5  # Unchanged


class TestPredictFull:
    """predict() — pipeline complet."""

    def test_predict_with_biases_and_state(self):
        predictor = Predictor()
        state = SelfState(
            hod_stats={
                "weak_domains": ["chimie"],
                "unknown_domains": [],
            },
        )
        biases = [BiasEntry(
            bias_type="overconfidence",
            description="Global overconfidence",
            severity=0.6,
        )]
        preds = predictor.predict(
            task_description="Solve a chemistry problem about molecules",
            state=state,
            active_biases=biases,
        )
        assert len(preds) >= 1
        # Sorted by confidence descending
        for i in range(len(preds) - 1):
            assert preds[i].predicted_confidence >= preds[i + 1].predicted_confidence

    def test_predict_no_state_no_biases(self):
        """Sans état ni biais → pas de prédictions."""
        predictor = Predictor()
        preds = predictor.predict(
            task_description="Do something",
            state=None,
            active_biases=[],
        )
        assert preds == []

    def test_predict_returns_predictions_ordered(self):
        """Les prédictions sont triées par confiance décroissante."""
        predictor = Predictor()
        biases = [
            BiasEntry(bias_type="overconfidence", description="b1", severity=0.3),
            BiasEntry(bias_type="scope_creep", description="b2", severity=0.9),
        ]
        preds = predictor.predict(
            task_description="Explore some topic",
            active_biases=biases,
        )
        for i in range(len(preds) - 1):
            assert preds[i].predicted_confidence >= preds[i + 1].predicted_confidence


class TestPredictionDB:
    """Persistence des prédictions en DB."""

    def test_save_and_verify_prediction(self, db):
        pred = Prediction(
            prediction="Will fail at chemistry",
            domain="chemistry",
            predicted_error_type="samael",
            predicted_confidence=0.7,
        )
        saved = db.save_prediction(pred)
        assert saved.id is not None
        assert saved.was_correct is None

        verified = db.verify_prediction(saved.id, True, "Indeed failed")
        assert verified.was_correct is True
        assert verified.actual_outcome == "Indeed failed"

    def test_prediction_accuracy(self, db):
        """Calcul de l'accuracy des prédictions."""
        for i in range(4):
            pred = Prediction(
                prediction=f"pred {i}",
                predicted_error_type="samael",
                predicted_confidence=0.5,
            )
            saved = db.save_prediction(pred)
            db.verify_prediction(saved.id, i < 3)  # 3 correct, 1 wrong

        accuracy = db.get_prediction_accuracy()
        assert accuracy == 0.75
