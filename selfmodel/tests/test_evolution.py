"""Tests EvolutionTracker — suivi de l'évolution du système."""

from selfmodel.evolution import EvolutionTracker
from selfmodel.models import EvolutionSnapshot, SelfState


def _healthy_state():
    """État sain de référence."""
    return SelfState(
        yesod_stats={
            "total_entries": 100,
            "active_entries": 85,
            "deprecated_entries": 15,
            "avg_confidence": 0.8,
            "contradictions_open": 1,
        },
        hod_stats={
            "total_domains": 8,
            "evaluated_domains": 6,
            "avg_competence": 0.7,
            "decline_rate": 0.05,
        },
        netzach_stats={
            "active_intentions": 2,
            "intentions": [
                {"goal": "A", "progress": 0.6},
                {"goal": "B", "progress": 0.4},
            ],
        },
        tiferet_stats={"level": "healthy", "issues": []},
        gevurah_stats={"level": "healthy", "issues": []},
        chesed_stats={"level": "healthy", "issues": []},
    )


def _degraded_state():
    """État dégradé."""
    return SelfState(
        yesod_stats={
            "total_entries": 50,
            "active_entries": 20,
            "avg_confidence": 0.4,
            "contradictions_open": 8,
        },
        hod_stats={
            "total_domains": 8,
            "evaluated_domains": 2,
            "avg_competence": 0.3,
            "decline_rate": 0.5,
        },
        netzach_stats={"active_intentions": 0},
        tiferet_stats={"level": "anan", "issues": []},
        gevurah_stats={"level": "ruach", "issues": []},
        chesed_stats={"level": "nogah", "issues": []},
    )


class TestHealthComputation:
    """Calcul de la santé de chaque Sephirah."""

    def test_health_yesod_healthy(self):
        tracker = EvolutionTracker()
        health = tracker._health_yesod({
            "total_entries": 100,
            "active_entries": 90,
            "avg_confidence": 0.8,
            "contradictions_open": 1,
        })
        # active_ratio=0.9*0.4 + confidence=0.8*0.4 - contradiction_penalty=0.05 + 0.2
        expected = 0.9 * 0.4 + 0.8 * 0.4 - 0.05 + 0.2
        assert abs(health - expected) < 0.01

    def test_health_yesod_empty(self):
        """Stats vides → neutre (0.5)."""
        tracker = EvolutionTracker()
        assert tracker._health_yesod({}) == 0.5

    def test_health_yesod_error(self):
        """Erreur dans stats → neutre."""
        tracker = EvolutionTracker()
        assert tracker._health_yesod({"error": "introspect failed"}) == 0.5

    def test_health_yesod_no_entries(self):
        """Pas d'entrées → neutre."""
        tracker = EvolutionTracker()
        assert tracker._health_yesod({"total_entries": 0}) == 0.5

    def test_health_hod_healthy(self):
        tracker = EvolutionTracker()
        health = tracker._health_hod({
            "total_domains": 8,
            "evaluated_domains": 6,
            "avg_competence": 0.7,
            "decline_rate": 0.05,
        })
        # coverage=0.75*0.4 + competence=0.7*0.4 - decline=0.025 + 0.2
        expected = 0.75 * 0.4 + 0.7 * 0.4 - 0.025 + 0.2
        assert abs(health - expected) < 0.01

    def test_health_hod_empty(self):
        tracker = EvolutionTracker()
        assert tracker._health_hod({}) == 0.5

    def test_health_netzach_with_progress(self):
        tracker = EvolutionTracker()
        health = tracker._health_netzach({
            "active_intentions": 2,
            "intentions": [
                {"goal": "A", "progress": 0.6},
                {"goal": "B", "progress": 0.4},
            ],
        })
        # avg_progress = 0.5, health = 0.3 + 0.5 * 0.7 = 0.65
        assert abs(health - 0.65) < 0.01

    def test_health_netzach_no_intentions(self):
        """Pas d'intentions → neutre-bon (0.6)."""
        tracker = EvolutionTracker()
        assert tracker._health_netzach({"active_intentions": 0}) == 0.6

    def test_health_netzach_empty(self):
        tracker = EvolutionTracker()
        assert tracker._health_netzach({}) == 0.5

    def test_health_diagnostic_levels(self):
        """Chaque niveau HaTehom → score correspondant."""
        tracker = EvolutionTracker()
        assert tracker._health_diagnostic({"level": "healthy"}) == 0.9
        assert tracker._health_diagnostic({"level": "nogah"}) == 0.7
        assert tracker._health_diagnostic({"level": "ruach"}) == 0.5
        assert tracker._health_diagnostic({"level": "anan"}) == 0.3
        assert tracker._health_diagnostic({"level": "mamash"}) == 0.1

    def test_health_diagnostic_empty(self):
        tracker = EvolutionTracker()
        assert tracker._health_diagnostic({}) == 0.5


class TestSnapshot:
    """snapshot() — création de snapshots d'évolution."""

    def test_first_snapshot_is_stable(self):
        """Premier snapshot → tendance stable."""
        tracker = EvolutionTracker()
        state = _healthy_state()
        snap = tracker.snapshot(state, previous_snapshot=None)
        assert snap.trend == "stable"
        assert snap.trend_details["reason"] == "first snapshot, no comparison"
        assert snap.overall_health > 0.5

    def test_improving_trend(self):
        """Amélioration significative → tendance improving."""
        tracker = EvolutionTracker()
        # Previous: dégradé
        previous = EvolutionSnapshot(
            yesod_health=0.3, hod_health=0.3, netzach_health=0.3,
            tiferet_health=0.3, gevurah_health=0.3, chesed_health=0.3,
            overall_health=0.3, trend="stable",
        )
        # Current: sain
        state = _healthy_state()
        snap = tracker.snapshot(state, previous_snapshot=previous)
        assert snap.trend == "improving"
        assert snap.overall_health > previous.overall_health

    def test_degrading_trend(self):
        """Dégradation significative → tendance degrading."""
        tracker = EvolutionTracker()
        previous = EvolutionSnapshot(
            yesod_health=0.9, hod_health=0.9, netzach_health=0.9,
            tiferet_health=0.9, gevurah_health=0.9, chesed_health=0.9,
            overall_health=0.9, trend="stable",
        )
        state = _degraded_state()
        snap = tracker.snapshot(state, previous_snapshot=previous)
        assert snap.trend == "degrading"

    def test_stable_trend(self):
        """Pas de changement significatif → stable."""
        tracker = EvolutionTracker()
        state = _healthy_state()
        # First snapshot
        snap1 = tracker.snapshot(state, previous_snapshot=None)
        # Second snapshot with same state
        snap2 = tracker.snapshot(state, previous_snapshot=snap1)
        assert snap2.trend == "stable"

    def test_per_sephirah_changes_tracked(self):
        """Les changements par Sephirah sont suivis."""
        tracker = EvolutionTracker()
        previous = EvolutionSnapshot(
            yesod_health=0.3, hod_health=0.9, netzach_health=0.5,
            tiferet_health=0.5, gevurah_health=0.5, chesed_health=0.5,
            overall_health=0.5, trend="stable",
        )
        state = _healthy_state()
        snap = tracker.snapshot(state, previous_snapshot=previous)
        details = snap.trend_details
        assert "improving_sephiroth" in details
        assert "yesod" in details["improving_sephiroth"]

    def test_health_by_sephirah_property(self):
        """La property health_by_sephirah retourne les 6 Sephiroth."""
        tracker = EvolutionTracker()
        state = _healthy_state()
        snap = tracker.snapshot(state)
        hbs = snap.health_by_sephirah
        assert set(hbs.keys()) == {"yesod", "hod", "netzach", "tiferet", "gevurah", "chesed"}
        assert all(0 <= v <= 1 for v in hbs.values())


class TestTrendFromHistory:
    """compute_trend_from_history — tendance sur historique long."""

    def test_improving_history(self):
        tracker = EvolutionTracker()
        snapshots = [
            EvolutionSnapshot(overall_health=0.8),  # Most recent
            EvolutionSnapshot(overall_health=0.6),
            EvolutionSnapshot(overall_health=0.4),
        ]
        assert tracker.compute_trend_from_history(snapshots) == "improving"

    def test_degrading_history(self):
        tracker = EvolutionTracker()
        snapshots = [
            EvolutionSnapshot(overall_health=0.3),  # Most recent
            EvolutionSnapshot(overall_health=0.5),
            EvolutionSnapshot(overall_health=0.8),
        ]
        assert tracker.compute_trend_from_history(snapshots) == "degrading"

    def test_stable_history(self):
        tracker = EvolutionTracker()
        snapshots = [
            EvolutionSnapshot(overall_health=0.51),
            EvolutionSnapshot(overall_health=0.50),
            EvolutionSnapshot(overall_health=0.49),
        ]
        assert tracker.compute_trend_from_history(snapshots) == "stable"

    def test_single_snapshot_stable(self):
        """Un seul snapshot → stable."""
        tracker = EvolutionTracker()
        assert tracker.compute_trend_from_history(
            [EvolutionSnapshot(overall_health=0.5)]
        ) == "stable"

    def test_empty_history_stable(self):
        tracker = EvolutionTracker()
        assert tracker.compute_trend_from_history([]) == "stable"


class TestEvolutionDB:
    """Persistence de l'évolution en DB."""

    def test_save_and_retrieve_evolution(self, db):
        snap = EvolutionSnapshot(
            yesod_health=0.8, hod_health=0.7, netzach_health=0.6,
            tiferet_health=0.9, gevurah_health=0.8, chesed_health=0.7,
            overall_health=0.75, trend="improving",
            trend_details={"reason": "test"},
        )
        saved = db.save_evolution(snap)
        assert saved.id is not None
        assert saved.trend == "improving"

        latest = db.get_latest_evolution()
        assert latest is not None
        assert latest.overall_health == 0.75

    def test_evolution_history(self, db):
        """Historique d'évolution ordonné."""
        for i in range(3):
            snap = EvolutionSnapshot(
                overall_health=0.5 + i * 0.1,
                trend="improving",
            )
            db.save_evolution(snap)

        history = db.get_evolution_history(limit=3)
        assert len(history) == 3
        # Most recent first
        assert history[0].overall_health >= history[-1].overall_health
