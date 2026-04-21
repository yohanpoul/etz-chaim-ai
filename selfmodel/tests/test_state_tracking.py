"""Tests StateTracker — capture d'état du système."""

from selfmodel.state_tracker import StateTracker
from selfmodel.models import SelfState


class _FakeMemory:
    """Mock EpisteMemory.introspect()."""
    class Stats:
        total_entries = 42
        active_entries = 35
        deprecated_entries = 7
        by_status = {"fact": 10, "hypothesis": 25}
        by_domain = {"kabbale": 15, "ml": 20}
        by_source = {"yesod": 30, "chesed": 12}
        avg_confidence = 0.72
        contradictions_open = 3
        near_expiration = 2
        oldest_entry = None
        newest_entry = None

    def introspect(self):
        return self.Stats()


class _FakeSelfMap:
    """Mock SelfMap.describe_self() + calibrate()."""
    class Desc:
        model_id = "test-model"
        total_domains = 8
        evaluated_domains = 5
        strong_domains = ["kabbale", "code"]
        weak_domains = ["chimie"]
        unknown_domains = ["droit", "musique", "architecture"]
        avg_competence = 0.65
        avg_brier = 0.15
        total_queries_routed = 100
        total_declined = 10
        decline_rate = 0.1

    class Cal:
        model_id = "test-model"
        by_domain = {}
        avg_brier = 0.15
        overconfident_domains = ["physique"]
        underconfident_domains = ["code"]
        uncalibrated_domains = []

    def describe_self(self):
        return self.Desc()

    def calibrate(self):
        return self.Cal()


class _FakeDiagModule:
    """Mock module with self_diagnose()."""
    def __init__(self, level="healthy", issues=None):
        self._level = level
        self._issues = issues or []

    def self_diagnose(self, **kwargs):
        return {"level": self._level, "issues": self._issues}


class _FakeIntentKeeper:
    """Mock IntentKeeper.list_active()."""
    class Intent:
        def __init__(self, goal, progress):
            self.goal = goal
            self.progress = progress

    def list_active(self):
        return [
            self.Intent("Build SelfModel", 0.5),
            self.Intent("Test everything", 0.3),
        ]


class TestStateTracker:
    """Capture d'état du système."""

    def test_capture_empty(self):
        """Capture avec aucun module connecté."""
        tracker = StateTracker()
        state = tracker.capture()
        assert isinstance(state, SelfState)
        assert state.yesod_stats == {}
        assert state.hod_stats == {}

    def test_connected_modules(self):
        """Modules connectés correctement détectés."""
        tracker = StateTracker(
            epistememory=_FakeMemory(),
            selfmap=_FakeSelfMap(),
        )
        connected = tracker.connected_modules()
        assert "yesod" in connected
        assert "hod" in connected
        assert "netzach" not in connected

    def test_capture_yesod(self):
        """Capture des stats de Yesod (EpisteMemory)."""
        tracker = StateTracker(epistememory=_FakeMemory())
        state = tracker.capture()
        assert state.yesod_stats["total_entries"] == 42
        assert state.yesod_stats["active_entries"] == 35
        assert state.yesod_stats["avg_confidence"] == 0.72
        assert state.yesod_stats["contradictions_open"] == 3

    def test_capture_hod(self):
        """Capture des stats de Hod (SelfMap)."""
        tracker = StateTracker(selfmap=_FakeSelfMap())
        state = tracker.capture()
        assert state.hod_stats["total_domains"] == 8
        assert state.hod_stats["strong_domains"] == ["kabbale", "code"]
        assert state.hod_stats["weak_domains"] == ["chimie"]
        assert "physique" in state.hod_stats["overconfident_domains"]

    def test_capture_netzach(self):
        """Capture des stats de Netzach (IntentKeeper)."""
        tracker = StateTracker(intentkeeper=_FakeIntentKeeper())
        state = tracker.capture()
        assert state.netzach_stats["active_intentions"] == 2

    def test_capture_diagnostic_module(self):
        """Capture de Tiferet/Gevurah/Chesed (modules avec self_diagnose)."""
        tracker = StateTracker(
            dissensus=_FakeDiagModule("healthy"),
            autojudge=_FakeDiagModule("nogah", ["Nogah: high rejection rate"]),
            exploration=_FakeDiagModule("healthy"),
        )
        state = tracker.capture()
        assert state.tiferet_stats["level"] == "healthy"
        assert state.gevurah_stats["level"] == "nogah"
        assert state.chesed_stats["level"] == "healthy"

    def test_capture_all_connected(self):
        """Capture complète avec tous les modules."""
        tracker = StateTracker(
            epistememory=_FakeMemory(),
            selfmap=_FakeSelfMap(),
            intentkeeper=_FakeIntentKeeper(),
            dissensus=_FakeDiagModule(),
            autojudge=_FakeDiagModule(),
            exploration=_FakeDiagModule(),
        )
        state = tracker.capture()
        assert all([
            state.yesod_stats,
            state.hod_stats,
            state.netzach_stats,
            state.tiferet_stats,
            state.gevurah_stats,
            state.chesed_stats,
        ])

    def test_capture_handles_broken_module(self):
        """Un module qui plante ne casse pas la capture."""
        class BrokenModule:
            def introspect(self):
                raise RuntimeError("Broken!")

        tracker = StateTracker(epistememory=BrokenModule())
        state = tracker.capture()
        assert state.yesod_stats == {"error": "introspect failed"}

    def test_state_persists_to_db(self, db):
        """L'état est persisté en DB."""
        from selfmodel.models import SelfState
        state = SelfState(
            yesod_stats={"total_entries": 10},
            model_confidence=0.7,
        )
        saved = db.save_state(state)
        assert saved.id is not None

        latest = db.get_latest_state()
        assert latest is not None
        assert latest.yesod_stats["total_entries"] == 10
        assert latest.model_confidence == 0.7
