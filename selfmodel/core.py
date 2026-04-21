"""SelfModel — Da'at, le pont au-dessus de l'Abîme.

Le système qui se connaît lui-même.
Intègre les 6 Sephiroth inférieures en un modèle unifié
qui détecte ses biais, prédit ses erreurs, et suit son évolution.

Anti-HaTehom : jamais de faux self-model.
Un self-model absent est signalé comme Mamash.
Un self-model qui rassure faussement est signalé comme Anan.
"""

from __future__ import annotations

from selfmodel.bias_detector import BiasDetector
from selfmodel.db import SelfModelDB
from selfmodel.evolution import EvolutionTracker
from selfmodel.integrator import Integrator
from selfmodel.models import (
    BiasEntry,
    EvolutionSnapshot,
    Prediction,
    SelfDescription,
    SelfState,
)
from selfmodel.predictor import Predictor
from selfmodel.state_tracker import StateTracker

# Calibration de Da'at (hors Omer standard car non-Sephirah)
DEFAULT_SNAPSHOT_INTERVAL_HOURS = 24
DEFAULT_PREDICTION_HORIZON_TASKS = 10
DEFAULT_BIAS_DETECTION_WINDOW_DAYS = 30
DEFAULT_MIN_PREDICTION_ACCURACY = 0.6
DEFAULT_EVOLUTION_COMPARISON_DAYS = 7
DEFAULT_META_CONFIDENCE_THRESHOLD = 0.5
DEFAULT_EXTERNAL_AUDIT_INTERVAL_DAYS = 30


class SelfModel:
    """Da'at — le pont au-dessus de l'Abîme. Le système qui se connaît."""

    def __init__(
        self,
        db_url: str,
        epistememory=None,
        selfmap=None,
        intentkeeper=None,
        dissensus=None,
        autojudge=None,
        exploration=None,
        # Calibration
        min_prediction_accuracy: float = DEFAULT_MIN_PREDICTION_ACCURACY,
        meta_confidence_threshold: float = DEFAULT_META_CONFIDENCE_THRESHOLD,
    ):
        self.db = SelfModelDB(db_url)
        self.min_prediction_accuracy = min_prediction_accuracy
        self.meta_confidence_threshold = meta_confidence_threshold
        self.selfmap = selfmap

        # Composants
        self.tracker = StateTracker(
            epistememory=epistememory,
            selfmap=selfmap,
            intentkeeper=intentkeeper,
            dissensus=dissensus,
            autojudge=autojudge,
            exploration=exploration,
        )
        self.bias_detector = BiasDetector()
        self.predictor = Predictor()
        self.evolution = EvolutionTracker()
        self.integrator = Integrator()

    def capture_state(self) -> SelfState:
        """Photographier l'état complet du système à cet instant."""
        state = self.tracker.capture()

        # Détecter les biais
        biases = self.bias_detector.detect(state)

        # Mettre à jour le state avec les biais et prédictions
        state.known_biases = [
            {"type": b.bias_type, "description": b.description,
             "severity": b.severity, "domain": b.domain}
            for b in biases
        ]

        # Extraire les forces et faiblesses
        desc = self.integrator.integrate(state, biases)
        state.predicted_weaknesses = desc.weaknesses
        state.predicted_strengths = desc.strengths
        state.model_confidence = desc.confidence_in_self_model

        # Persister
        saved = self.db.save_state(state)

        # Persister les nouveaux biais détectés
        for bias in biases:
            self.db.save_bias(bias)

        return saved

    def feed_insight(
        self,
        source_module: str,
        source_id,
        description: str,
        confidence: float = 0.5,
        domain: str | None = None,
        novelty_score: float | None = None,
    ) -> bool:
        """Ingérer un insight validé par un module externe (bridge I2).

        Da'at n'est plus un pur agrégateur passif : il peut recevoir les
        verdicts d'InsightForge, AutoJudge, etc. Idempotent via la clé
        (source_module, source_id).

        Args:
            source_module: Nom du module source (ex: 'insightforge').
            source_id: Identifiant (UUID ou str) de l'insight côté source.
            description: Texte de l'insight.
            confidence: Confiance [0-1].
            domain: Domaine (optionnel).
            novelty_score: Score de nouveauté (optionnel, [0-1]).

        Returns:
            True si ingéré, False si doublon (idempotence).
        """
        return self.db.save_external_insight(
            source_module=source_module,
            source_id=source_id,
            description=description,
            confidence=confidence,
            domain=domain,
            novelty_score=novelty_score,
        )

    def detect_biases(self, state: SelfState | None = None) -> list[BiasEntry]:
        """Analyser les patterns dans les erreurs passées pour détecter les biais."""
        if state is None:
            state = self.db.get_latest_state()
        if state is None:
            return []

        # Aussi chercher dans l'historique
        history = self.db.get_states(limit=10)
        if len(history) >= 3:
            return self.bias_detector.detect_from_history(history)

        return self.bias_detector.detect(state)

    def predict_error(self, task_description: str) -> list[Prediction]:
        """AVANT de lancer une tâche, prédire où le système va échouer."""
        state = self.db.get_latest_state()
        biases = self.db.get_active_biases()
        history = self.db.get_predictions(verified_only=True, limit=50)

        predictions = self.predictor.predict(
            task_description=task_description,
            state=state,
            active_biases=biases,
            prediction_history=history,
        )

        # Persister les prédictions
        saved = []
        for pred in predictions:
            saved.append(self.db.save_prediction(pred))

        return saved

    def verify_prediction(
        self, prediction_id, was_correct: bool, actual_outcome: str = "",
    ) -> Prediction | None:
        """Vérifier une prédiction après l'exécution de la tâche."""
        return self.db.verify_prediction(prediction_id, was_correct, actual_outcome)

    def track_evolution(self) -> EvolutionSnapshot:
        """Suivre comment le système évolue dans le temps."""
        state = self.db.get_latest_state()
        if state is None:
            state = self.capture_state()

        previous = self.db.get_latest_evolution()
        snapshot = self.evolution.snapshot(state, previous)

        return self.db.save_evolution(snapshot)

    def who_am_i(self) -> SelfDescription:
        """La question ultime de Da'at : qui suis-je ?"""
        state = self.db.get_latest_state()
        if state is None:
            state = self.capture_state()

        biases = self.db.get_active_biases()
        accuracy = self.db.get_prediction_accuracy()
        latest_evo = self.db.get_latest_evolution()
        trend = latest_evo.trend if latest_evo else "stable"

        health_map = {}
        if latest_evo:
            health_map = latest_evo.health_by_sephirah

        return self.integrator.integrate(
            state=state,
            biases=biases,
            prediction_accuracy=accuracy,
            evolution_trend=trend,
            health_by_sephirah=health_map,
        )

    # ------------------------------------------------------------------
    # evaluate_confidence — Da'at comme GARDIEN (pas observateur passif)
    # ------------------------------------------------------------------

    def evaluate_confidence(
        self,
        query: str,
        domain: str = "",
        intent: dict | None = None,
    ) -> dict:
        """דַּעַת הַשׁוֹמֵר — Da'at évalue sa confiance AVANT la réponse.

        Heuristiques rapides (< 100ms) — PAS de LLM, PAS de capture_state().
        Consulte le dernier état en cache, les biais par domaine, l'accuracy.

        Seuils :
            predicted_error < 0.3 → 'proceed'  (confiance haute)
            0.3 ≤ predicted_error < 0.7 → 'caution' (injecter avertissement)
            predicted_error ≥ 0.7 → 'veto' (rediriger vers aveu d'ignorance)

        Returns:
            dict avec confidence, predicted_error, known_biases,
            recommendation ('proceed'|'caution'|'veto'), reason
        """
        # État en cache (une seule requête DB, pas de capture complète)
        state = self.db.get_latest_state()

        # Biais filtrés par domaine
        domain_biases = self.db.get_active_biases(domain=domain) if domain else []
        global_biases = self.db.get_active_biases() if not domain_biases else domain_biases

        # Accuracy par domaine
        domain_accuracy = (
            self.db.get_prediction_accuracy(domain=domain)
            if domain else None
        )

        # ── Signaux d'erreur ─────────────────────────────────────
        error_signals: list[tuple[str, float]] = []

        # 0. SelfMap competence — signal LE PLUS FORT
        #    Un domaine à score 0.0 → error signal 0.8 (veto)
        #    Un domaine à score 1.0 → pas de signal (proceed)
        #    Seuil 0.8 : au-dessus, le domaine est maîtrisé → pas de signal
        #    LECTURE SEULE — jamais eval_domain() ici (destructif + lent)
        if domain and self.selfmap is not None:
            try:
                sm_result = self.selfmap.read_competence(domain)
                if sm_result is None:
                    # Domaine inconnu — signal modéré (caution, pas veto).
                    # Claude est un LLM généraliste, l'absence du domaine
                    # dans le SelfMap ne signifie pas incompétence.
                    error_signals.append(("selfmap_unknown_domain", 0.4))
                elif sm_result.score < self.selfmap.decline_threshold:
                    # Score sous le seuil de déclin → veto direct.
                    # Le système SE SAIT incompétent — décliner.
                    error_signals.append(("selfmap_decline", 0.85))
                elif sm_result.score < 0.8:
                    selfmap_error = round((1.0 - sm_result.score) * 0.8, 3)
                    error_signals.append(("selfmap_competence", selfmap_error))
            except Exception as _exc:

                import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

        # 1. Sévérité des biais du domaine
        if domain_biases:
            avg_severity = sum(b.severity for b in domain_biases) / len(domain_biases)
            if avg_severity > 0.4:
                error_signals.append(("high_bias_severity", min(1.0, avg_severity)))

        # 2. Accuracy historique du domaine
        if domain_accuracy is not None and domain_accuracy < 0.5:
            error_signals.append(("low_domain_accuracy", 1.0 - domain_accuracy))

        # 3. Domaine faible ou inconnu (Hod)
        if state and state.hod_stats:
            weak = state.hod_stats.get("weak_domains", [])
            unknown = state.hod_stats.get("unknown_domains", [])
            if domain and domain in weak:
                error_signals.append(("weak_domain", 0.7))
            elif domain and domain in unknown:
                error_signals.append(("unknown_domain", 0.6))

        # 4. Confiance du self-model globalement basse
        if state and state.model_confidence < 0.3:
            error_signals.append(("low_model_confidence", 1.0 - state.model_confidence))

        # 5. Gevurah en mauvaise santé
        if state and state.gevurah_stats and state.gevurah_stats.get("level") != "healthy":
            error_signals.append(("unhealthy_judge", 0.5))

        # ── Agrégation ───────────────────────────────────────────
        if error_signals:
            predicted_error = sum(s[1] for s in error_signals) / len(error_signals)
            predicted_error = round(min(1.0, predicted_error), 3)
        else:
            predicted_error = 0.1

        confidence = round(1.0 - predicted_error, 3)

        # ── Recommandation ───────────────────────────────────────
        if predicted_error >= 0.7:
            recommendation = "veto"
            reason = "Erreur prédite élevée — " + "; ".join(
                f"{s[0]}={s[1]:.2f}" for s in error_signals
            )
        elif predicted_error >= 0.3:
            recommendation = "caution"
            reason = "Confiance modérée — " + "; ".join(
                f"{s[0]}={s[1]:.2f}" for s in error_signals
            )
        else:
            recommendation = "proceed"
            reason = "Aucun risque significatif détecté"

        # Biais pertinents (domaine d'abord, puis globaux par sévérité)
        relevant = domain_biases[:5] if domain_biases else global_biases[:3]

        return {
            "confidence": confidence,
            "predicted_error": predicted_error,
            "known_biases": [
                {"type": b.bias_type, "description": b.description,
                 "severity": b.severity, "domain": b.domain}
                for b in relevant
            ],
            "recommendation": recommendation,
            "reason": reason,
        }

    def self_diagnose(self) -> dict:
        """Auto-diagnostic de Da'at — les 4 niveaux de HaTehom.

        Mamash : pas de self-model (aucun snapshot)
        Anan : self-model rassure mais prédictions fausses (accuracy < min)
        Ruach : self-model sur-estime (overconfidence détectée)
        Nogah : self-model légèrement décalé (prédictions 60-70%)
        """
        diagnostics = {"level": "healthy", "issues": []}

        # Mamash : pas de self-model
        latest = self.db.get_latest_state()
        if latest is None:
            diagnostics["level"] = "mamash"
            diagnostics["issues"].append(
                "Mamash: no SelfModel state exists — the Abyss is uncrossed"
            )
            return diagnostics

        # Check model confidence
        if latest.model_confidence < 0.2:
            diagnostics["level"] = "mamash"
            diagnostics["issues"].append(
                f"Mamash: model confidence critically low ({latest.model_confidence:.1%})"
            )
            return diagnostics

        # Anan : self-model rassure mais prédictions fausses
        accuracy = self.db.get_prediction_accuracy()
        if accuracy is not None and accuracy < self.min_prediction_accuracy * 0.7:
            diagnostics["level"] = "anan"
            diagnostics["issues"].append(
                f"Anan: prediction accuracy ({accuracy:.1%}) critically below "
                f"threshold ({self.min_prediction_accuracy:.1%}) — "
                f"false self-image"
            )

        # Ruach : overconfidence détectée
        biases = self.db.get_active_biases()
        overconfidence_biases = [
            b for b in biases if b.bias_type == "overconfidence" and b.severity > 0.5
        ]
        if overconfidence_biases:
            if diagnostics["level"] == "healthy":
                diagnostics["level"] = "ruach"
            diagnostics["issues"].append(
                f"Ruach: {len(overconfidence_biases)} active overconfidence biases "
                f"(avg severity {sum(b.severity for b in overconfidence_biases) / len(overconfidence_biases):.2f})"
            )

        # Nogah : prédictions légèrement décalées
        if (accuracy is not None
                and accuracy < self.min_prediction_accuracy
                and diagnostics["level"] == "healthy"):
            diagnostics["level"] = "nogah"
            diagnostics["issues"].append(
                f"Nogah: prediction accuracy ({accuracy:.1%}) below threshold "
                f"({self.min_prediction_accuracy:.1%}) — recalibration needed"
            )

        return diagnostics

    def report(self) -> str:
        """Rapport lisible — Malkuth de Da'at."""
        desc = self.who_am_i()
        diag = self.self_diagnose()

        lines = [
            "=== SelfModel Report (Da'at) ===",
            "",
            f"Self-diagnosis: {diag['level']}",
        ]

        if diag["issues"]:
            for issue in diag["issues"]:
                lines.append(f"  ! {issue}")

        lines.append(f"\nConfidence in self-model: {desc.confidence_in_self_model:.1%}")
        lines.append(f"Evolution trend: {desc.evolution_trend}")

        if desc.prediction_accuracy is not None:
            lines.append(f"Prediction accuracy: {desc.prediction_accuracy:.1%}")

        if desc.strengths:
            lines.append("\nStrengths:")
            for s in desc.strengths:
                lines.append(f"  + {s}")

        if desc.weaknesses:
            lines.append("\nWeaknesses:")
            for w in desc.weaknesses:
                lines.append(f"  - {w}")

        if desc.biases:
            lines.append(f"\nActive biases: {len(desc.biases)}")
            for b in desc.biases[:5]:
                lines.append(f"  [{b.bias_type}] {b.description} (severity={b.severity:.2f})")

        if desc.blind_spots:
            lines.append("\nBlind spots:")
            for bs in desc.blind_spots:
                lines.append(f"  ? {bs}")

        if desc.health_by_sephirah:
            lines.append("\nHealth by Sephirah:")
            for seph, health in desc.health_by_sephirah.items():
                bar = "█" * int(health * 10) + "░" * (10 - int(health * 10))
                lines.append(f"  {seph:10s} {bar} {health:.1%}")

        return "\n".join(lines)
