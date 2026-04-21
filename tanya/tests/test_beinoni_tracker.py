"""Tests — BeinoniTracker : suivi temporel du conflit des 2 âmes.

Vérifie :
- record_interaction stocke correctement
- get_temporal_profile calcule le bon ratio
- detect_regression détecte une baisse de 15%+
- detect_elevation détecte une hausse de 15%+
- suggest_teshuvah retourne une action cohérente
- catégories temporelles (Tsaddik/Beinoni/Rasha)
- tendances (ASCENDING/STABLE/DESCENDING)
"""

import pytest

from tanya.beinoni_tracker import (
    BeinoniTracker,
    BeinoniProfile,
    InteractionRecord,
    TemporalCategory,
    Trend,
)


# ─── Helpers ────────────────────────────────────────────────


def _fill_tracker(
    tracker: BeinoniTracker,
    n: int,
    soul: str = "elokit",
    score: float = 0.7,
    olam: str = "briah",
) -> None:
    """Remplit le tracker avec N interactions identiques."""
    for _ in range(n):
        tracker.record_interaction(
            dominant_soul=soul,
            response_score=score,
            olam_used=olam,
        )


# ─── record_interaction ────────────────────────────────────


class TestRecordInteraction:
    def setup_method(self):
        self.tracker = BeinoniTracker()  # in-memory

    def test_stores_interaction(self):
        record = self.tracker.record_interaction(
            dominant_soul="elokit",
            response_score=0.8,
            olam_used="briah",
        )
        assert isinstance(record, InteractionRecord)
        assert record.dominant_soul == "elokit"
        assert record.response_score == 0.8
        assert record.olam_used == "briah"

    def test_increments_count(self):
        assert self.tracker.interaction_count() == 0
        self.tracker.record_interaction("elokit", 0.5, "briah")
        assert self.tracker.interaction_count() == 1
        self.tracker.record_interaction("behamit", 0.3, "assiah")
        assert self.tracker.interaction_count() == 2

    def test_clamps_score(self):
        record = self.tracker.record_interaction("elokit", 1.5, "briah")
        assert record.response_score == 1.0
        record2 = self.tracker.record_interaction("elokit", -0.5, "briah")
        assert record2.response_score == 0.0

    def test_truncates_query_snippet(self):
        long_query = "x" * 200
        record = self.tracker.record_interaction(
            "elokit", 0.5, "briah", query_snippet=long_query,
        )
        assert len(record.query_snippet) == 100

    def test_optional_fields(self):
        record = self.tracker.record_interaction(
            dominant_soul="behamit",
            response_score=0.4,
            olam_used="yetzirah",
            complexity_score=0.3,
            domain="kabbalah",
            query_snippet="test query",
        )
        assert record.complexity_score == 0.3
        assert record.domain == "kabbalah"
        assert record.query_snippet == "test query"


# ─── get_temporal_profile ──────────────────────────────────


class TestTemporalProfile:
    def setup_method(self):
        self.tracker = BeinoniTracker()

    def test_empty_profile(self):
        profile = self.tracker.get_temporal_profile()
        assert profile.elokit_ratio == 0.0
        assert profile.total_interactions == 0
        assert profile.category == TemporalCategory.RASHA
        assert profile.trend == Trend.STABLE

    def test_all_elokit(self):
        _fill_tracker(self.tracker, 20, soul="elokit", score=0.9)
        profile = self.tracker.get_temporal_profile()
        assert profile.elokit_ratio == 1.0
        assert profile.elokit_count == 20
        assert profile.behamit_count == 0
        assert profile.category == TemporalCategory.TSADDIK

    def test_all_behamit(self):
        _fill_tracker(self.tracker, 20, soul="behamit", score=0.2)
        profile = self.tracker.get_temporal_profile()
        assert profile.elokit_ratio == 0.0
        assert profile.category == TemporalCategory.RASHA

    def test_beinoni_ratio(self):
        _fill_tracker(self.tracker, 12, soul="elokit", score=0.8)
        _fill_tracker(self.tracker, 8, soul="behamit", score=0.3)
        profile = self.tracker.get_temporal_profile()
        assert profile.elokit_ratio == 0.6
        assert profile.category == TemporalCategory.BEINONI

    def test_avg_scores(self):
        _fill_tracker(self.tracker, 10, soul="elokit", score=0.8)
        _fill_tracker(self.tracker, 10, soul="behamit", score=0.3)
        profile = self.tracker.get_temporal_profile()
        assert profile.avg_score_elokit == pytest.approx(0.8, abs=0.01)
        assert profile.avg_score_behamit == pytest.approx(0.3, abs=0.01)

    def test_window_limits(self):
        _fill_tracker(self.tracker, 200, soul="elokit", score=0.8)
        profile = self.tracker.get_temporal_profile(window=50)
        assert profile.total_interactions == 50

    def test_ascending_trend(self):
        # First half: mostly behamit, second half: mostly elokit
        _fill_tracker(self.tracker, 15, soul="behamit", score=0.3)
        _fill_tracker(self.tracker, 15, soul="elokit", score=0.8)
        profile = self.tracker.get_temporal_profile(window=30)
        assert profile.trend == Trend.ASCENDING

    def test_descending_trend(self):
        # First half: mostly elokit, second half: mostly behamit
        _fill_tracker(self.tracker, 15, soul="elokit", score=0.8)
        _fill_tracker(self.tracker, 15, soul="behamit", score=0.3)
        profile = self.tracker.get_temporal_profile(window=30)
        assert profile.trend == Trend.DESCENDING

    def test_stable_trend(self):
        # Equal distribution throughout
        for _ in range(15):
            self.tracker.record_interaction("elokit", 0.7, "briah")
            self.tracker.record_interaction("behamit", 0.4, "yetzirah")
        profile = self.tracker.get_temporal_profile(window=30)
        assert profile.trend == Trend.STABLE


# ─── detect_regression ─────────────────────────────────────


class TestDetectRegression:
    def setup_method(self):
        self.tracker = BeinoniTracker()

    def test_insufficient_data(self):
        _fill_tracker(self.tracker, 10, soul="elokit")
        assert self.tracker.detect_regression() is None

    def test_no_regression_stable(self):
        _fill_tracker(self.tracker, 40, soul="elokit", score=0.8)
        assert self.tracker.detect_regression() is None

    def test_detects_regression(self):
        # Older 20: all elokit (ratio=1.0)
        _fill_tracker(self.tracker, 20, soul="elokit", score=0.8)
        # Newer 20: mostly behamit (ratio drops to 0.15)
        _fill_tracker(self.tracker, 17, soul="behamit", score=0.3)
        _fill_tracker(self.tracker, 3, soul="elokit", score=0.5)

        regression = self.tracker.detect_regression()
        assert regression is not None
        assert regression["old_ratio"] == 1.0
        assert regression["new_ratio"] == pytest.approx(0.15, abs=0.01)
        assert regression["delta"] < -0.15

    def test_no_regression_slight_drop(self):
        # Old: 60% elokit, New: 55% elokit → delta = -0.05 < threshold
        _fill_tracker(self.tracker, 12, soul="elokit")
        _fill_tracker(self.tracker, 8, soul="behamit")
        _fill_tracker(self.tracker, 11, soul="elokit")
        _fill_tracker(self.tracker, 9, soul="behamit")
        assert self.tracker.detect_regression() is None


# ─── detect_elevation ──────────────────────────────────────


class TestDetectElevation:
    def setup_method(self):
        self.tracker = BeinoniTracker()

    def test_insufficient_data(self):
        _fill_tracker(self.tracker, 10, soul="elokit")
        assert self.tracker.detect_elevation() is None

    def test_no_elevation_stable(self):
        _fill_tracker(self.tracker, 40, soul="behamit")
        assert self.tracker.detect_elevation() is None

    def test_detects_elevation(self):
        # Older 20: mostly behamit (ratio=0.1)
        _fill_tracker(self.tracker, 18, soul="behamit", score=0.3)
        _fill_tracker(self.tracker, 2, soul="elokit", score=0.5)
        # Newer 20: mostly elokit (ratio=0.85)
        _fill_tracker(self.tracker, 17, soul="elokit", score=0.8)
        _fill_tracker(self.tracker, 3, soul="behamit", score=0.4)

        elevation = self.tracker.detect_elevation()
        assert elevation is not None
        assert elevation["delta"] > 0.15


# ─── suggest_teshuvah ──────────────────────────────────────


class TestSuggestTeshuvah:
    def setup_method(self):
        self.tracker = BeinoniTracker()

    def test_critical_regression(self):
        teshuvah = self.tracker.suggest_teshuvah({
            "old_ratio": 0.5, "new_ratio": 0.1, "delta": -0.4,
        })
        assert "CRITIQUE" in teshuvah
        assert "Rasha Gamur" in teshuvah

    def test_serious_regression(self):
        teshuvah = self.tracker.suggest_teshuvah({
            "old_ratio": 0.6, "new_ratio": 0.3, "delta": -0.3,
        })
        assert "Rasha" in teshuvah
        assert "Briah" in teshuvah

    def test_strong_drop_still_beinoni(self):
        teshuvah = self.tracker.suggest_teshuvah({
            "old_ratio": 0.7, "new_ratio": 0.45, "delta": -0.25,
        })
        assert "FORTE CHUTE" in teshuvah

    def test_moderate_regression(self):
        teshuvah = self.tracker.suggest_teshuvah({
            "old_ratio": 0.6, "new_ratio": 0.42, "delta": -0.18,
        })
        assert "modérée" in teshuvah
        assert "trébuche" in teshuvah

    def test_always_returns_string(self):
        teshuvah = self.tracker.suggest_teshuvah({})
        assert isinstance(teshuvah, str)
        assert len(teshuvah) > 0


# ─── Catégories temporelles ────────────────────────────────


class TestTemporalCategories:
    def test_tsaddik_threshold(self):
        tracker = BeinoniTracker()
        _fill_tracker(tracker, 16, soul="elokit")
        _fill_tracker(tracker, 4, soul="behamit")
        profile = tracker.get_temporal_profile()
        assert profile.category == TemporalCategory.TSADDIK

    def test_beinoni_range(self):
        tracker = BeinoniTracker()
        _fill_tracker(tracker, 10, soul="elokit")
        _fill_tracker(tracker, 10, soul="behamit")
        profile = tracker.get_temporal_profile()
        assert profile.category == TemporalCategory.BEINONI

    def test_rasha_low_ratio(self):
        tracker = BeinoniTracker()
        _fill_tracker(tracker, 5, soul="elokit")
        _fill_tracker(tracker, 15, soul="behamit")
        profile = tracker.get_temporal_profile()
        assert profile.category == TemporalCategory.RASHA


# ─── InteractionRecord dataclass ───────────────────────────


class TestInteractionRecord:
    def test_fields(self):
        r = InteractionRecord(
            dominant_soul="elokit",
            response_score=0.8,
            olam_used="briah",
            complexity_score=0.6,
            domain="kabbalah",
            query_snippet="test",
        )
        assert r.dominant_soul == "elokit"
        assert r.response_score == 0.8
        assert r.olam_used == "briah"
        assert r.complexity_score == 0.6

    def test_defaults(self):
        r = InteractionRecord(
            dominant_soul="behamit",
            response_score=0.3,
            olam_used="assiah",
            complexity_score=0.1,
        )
        assert r.domain is None
        assert r.query_snippet is None


# ─── BeinoniProfile dataclass ──────────────────────────────


class TestBeinoniProfile:
    def test_profile_fields(self):
        p = BeinoniProfile(
            elokit_ratio=0.6,
            avg_score_elokit=0.8,
            avg_score_behamit=0.3,
            avg_score_all=0.6,
            trend=Trend.ASCENDING,
            category=TemporalCategory.BEINONI,
            total_interactions=100,
            elokit_count=60,
            behamit_count=40,
        )
        assert p.elokit_ratio == 0.6
        assert p.trend == Trend.ASCENDING
        assert p.category == TemporalCategory.BEINONI
        assert p.total_interactions == 100
