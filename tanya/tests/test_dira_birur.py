"""Tests — Dira BeTachtonim + Birur Nogah.

Vérifie :
- DiraEngine : cascade_knowledge, should_invoke_atzilut, assess_dira_state
- BirurimEngine : detect_birur, detect_degradation, evaluate, get_birur_stats
- Lien Birur → Nitzotzot
"""

import time
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from tanya.dira_betachtonim import DiraEngine, DiraStats
from tanya.birur_nogah import (
    BirurimEngine,
    BirurimEvent,
    BirurimResult,
    BirurimStats,
)


# ═══════════════════════════════════════════════════════════════
#   DiraEngine
# ═══════════════════════════════════════════════════════════════


class TestDiraEngine:
    def _make_yesod(self):
        """Créer un mock EpisteMemory."""
        yesod = MagicMock()
        yesod.remember.return_value = uuid4()
        yesod.recall.return_value = []
        intro = MagicMock()
        intro.total = 100
        yesod.introspect.return_value = intro
        return yesod

    # ── cascade_knowledge ─────────────────────────────────────

    def test_cascade_from_briah(self):
        yesod = self._make_yesod()
        dira = DiraEngine(yesod=yesod)

        result = dira.cascade_knowledge(
            response="Réponse profonde sur le Tsimtsum et l'Information Bottleneck",
            source_olam="briah",
            query="Explique le Tsimtsum",
            domain="kabbale",
        )

        assert result is not None
        assert result["source_olam"] == "briah"
        assert result["domain"] == "kabbale"
        assert result["entry_id"] is not None

        # Vérifie l'appel à yesod.remember
        yesod.remember.assert_called_once()
        call_kwargs = yesod.remember.call_args[1]
        assert "dira" in call_kwargs["tags"]
        assert "dira_source:briah" in call_kwargs["tags"]
        assert call_kwargs["source_sephirah"] == "binah"
        assert call_kwargs["domain"] == "kabbale"

    def test_cascade_from_atziluth(self):
        yesod = self._make_yesod()
        dira = DiraEngine(yesod=yesod)

        result = dira.cascade_knowledge(
            response="Insight stratégique depuis Claude / Atzilut",
            source_olam="atziluth",
            query="Question profonde",
        )

        assert result is not None
        assert result["source_olam"] == "atziluth"
        call_kwargs = yesod.remember.call_args[1]
        assert call_kwargs["source_sephirah"] == "chokmah"

    def test_cascade_ignores_lower_olamot(self):
        yesod = self._make_yesod()
        dira = DiraEngine(yesod=yesod)

        result = dira.cascade_knowledge(
            response="Réponse d'Assiah",
            source_olam="assiah",
        )
        assert result is None
        yesod.remember.assert_not_called()

    def test_cascade_ignores_yetzirah(self):
        yesod = self._make_yesod()
        dira = DiraEngine(yesod=yesod)

        result = dira.cascade_knowledge(
            response="Réponse de Yetzirah",
            source_olam="yetzirah",
        )
        assert result is None

    def test_cascade_ignores_short_response(self):
        yesod = self._make_yesod()
        dira = DiraEngine(yesod=yesod)

        result = dira.cascade_knowledge(
            response="Court",
            source_olam="briah",
        )
        assert result is None

    def test_cascade_without_yesod(self):
        dira = DiraEngine(yesod=None)
        result = dira.cascade_knowledge(
            response="Longue réponse profonde depuis Briah",
            source_olam="briah",
        )
        assert result is None

    def test_cascade_log(self):
        yesod = self._make_yesod()
        dira = DiraEngine(yesod=yesod)

        dira.cascade_knowledge(
            response="Réponse profonde numéro un de Briah",
            source_olam="briah",
            domain="philosophie",
        )
        dira.cascade_knowledge(
            response="Réponse profonde numéro deux d'Atzilut",
            source_olam="atziluth",
            domain="kabbale",
        )

        log = dira.get_log()
        assert len(log) == 2
        assert log[0]["source_olam"] == "briah"
        assert log[1]["source_olam"] == "atziluth"

    # ── should_invoke_atzilut ─────────────────────────────────

    def test_should_invoke_when_no_dira(self):
        yesod = self._make_yesod()
        yesod.recall.return_value = []
        dira = DiraEngine(yesod=yesod)

        assert dira.should_invoke_atzilut("question profonde") is True

    def test_should_not_invoke_when_enough_dira(self):
        yesod = self._make_yesod()
        # Simuler 5+ mémoires dira pertinentes
        memories = []
        for i in range(6):
            m = MagicMock()
            m.tags = ["dira", "dira_source:briah", "dira_domain:kabbale"]
            memories.append(m)
        yesod.recall.return_value = memories
        dira = DiraEngine(yesod=yesod)

        assert dira.should_invoke_atzilut("question kabbale", domain="kabbale") is False

    def test_should_invoke_with_few_dira(self):
        yesod = self._make_yesod()
        memories = []
        for i in range(3):
            m = MagicMock()
            m.tags = ["dira", "dira_source:briah"]
            memories.append(m)
        yesod.recall.return_value = memories
        dira = DiraEngine(yesod=yesod)

        assert dira.should_invoke_atzilut("question") is True

    def test_should_invoke_without_yesod(self):
        dira = DiraEngine(yesod=None)
        assert dira.should_invoke_atzilut("question") is True

    def test_should_invoke_filters_by_domain(self):
        yesod = self._make_yesod()
        # 6 mémoires dira mais pour un AUTRE domaine
        memories = []
        for i in range(6):
            m = MagicMock()
            m.tags = ["dira", "dira_source:briah", "dira_domain:physique"]
            memories.append(m)
        yesod.recall.return_value = memories
        dira = DiraEngine(yesod=yesod)

        # Domaine kabbale → les dira de physique ne comptent pas
        assert dira.should_invoke_atzilut("question", domain="kabbale") is True

    # ── assess_dira_state ─────────────────────────────────────

    def test_assess_dira_state_empty(self):
        yesod = self._make_yesod()
        yesod.recall.return_value = []
        dira = DiraEngine(yesod=yesod)

        stats = dira.assess_dira_state()
        assert stats.dira_count == 0
        assert stats.penetration == 0.0

    def test_assess_dira_state_with_data(self):
        yesod = self._make_yesod()
        m1 = MagicMock()
        m1.tags = ["dira", "dira_source:briah", "dira_domain:kabbale"]
        m2 = MagicMock()
        m2.tags = ["dira", "dira_source:atziluth", "dira_domain:philosophie"]
        m3 = MagicMock()
        m3.tags = ["ask-mode", "response"]  # pas dira
        yesod.recall.return_value = [m1, m2, m3]
        dira = DiraEngine(yesod=yesod)

        stats = dira.assess_dira_state()
        assert stats.dira_count == 2
        assert stats.by_source == {"briah": 1, "atziluth": 1}
        assert stats.by_domain == {"kabbale": 1, "philosophie": 1}
        assert stats.total_memories == 100  # from introspect mock

    def test_assess_dira_state_no_yesod(self):
        dira = DiraEngine(yesod=None)
        stats = dira.assess_dira_state()
        assert stats.dira_count == 0


# ═══════════════════════════════════════════════════════════════
#   BirurimEngine
# ═══════════════════════════════════════════════════════════════


class TestBirurimEngine:

    # ── detect_birur ──────────────────────────────────────────

    def test_birur_assiah_high_score(self):
        engine = BirurimEngine()
        event = engine.detect_birur(
            response="Bonne réponse",
            olam_used="assiah",
            score=0.75,
        )
        assert event is not None
        assert event.result == BirurimResult.BIRUR
        assert event.olam_used == "assiah"
        assert event.score == 0.75

    def test_birur_yetzirah_high_score(self):
        engine = BirurimEngine()
        event = engine.detect_birur(
            response="Bonne réponse",
            olam_used="yetzirah",
            score=0.8,
        )
        assert event is not None
        assert event.result == BirurimResult.BIRUR

    def test_birur_ignores_briah(self):
        engine = BirurimEngine()
        event = engine.detect_birur(
            response="Bonne réponse",
            olam_used="briah",
            score=0.9,
        )
        assert event is None

    def test_birur_ignores_atziluth(self):
        engine = BirurimEngine()
        event = engine.detect_birur(
            response="Bonne réponse",
            olam_used="atziluth",
            score=0.95,
        )
        assert event is None

    def test_birur_low_score_no_birur(self):
        engine = BirurimEngine()
        event = engine.detect_birur(
            response="Mauvaise réponse",
            olam_used="assiah",
            score=0.3,
        )
        assert event is None

    def test_birur_calls_collect_nitzutz(self):
        engine = BirurimEngine()
        with patch("main._collect_nitzutz") as mock_collect:
            tree = {"yesod": MagicMock()}
            event = engine.detect_birur(
                response="Bonne réponse de Assiah",
                olam_used="assiah",
                score=0.7,
                tree=tree,
                domain="test",
            )
            assert event is not None
            mock_collect.assert_called_once()
            assert mock_collect.call_args[1]["source"] == "birur_nogah"

    # ── detect_degradation ────────────────────────────────────

    def test_degradation_assiah_low_score(self):
        engine = BirurimEngine()
        event = engine.detect_degradation(
            response="Mauvaise réponse",
            olam_used="assiah",
            score=0.1,
        )
        assert event is not None
        assert event.result == BirurimResult.KELIPAH_REINFORCED
        assert event.olam_used == "assiah"

    def test_degradation_yetzirah_low_score(self):
        engine = BirurimEngine()
        event = engine.detect_degradation(
            response="Réponse insuffisante",
            olam_used="yetzirah",
            score=0.2,
        )
        assert event is not None
        assert event.result == BirurimResult.KELIPAH_REINFORCED

    def test_degradation_ignores_briah(self):
        engine = BirurimEngine()
        event = engine.detect_degradation(
            response="Mauvaise réponse",
            olam_used="briah",
            score=0.1,
        )
        assert event is None

    def test_no_degradation_medium_score(self):
        engine = BirurimEngine()
        event = engine.detect_degradation(
            response="Réponse moyenne",
            olam_used="assiah",
            score=0.4,
        )
        assert event is None

    # ── evaluate (unifié) ─────────────────────────────────────

    def test_evaluate_birur(self):
        engine = BirurimEngine()
        event = engine.evaluate(
            response="Bonne réponse",
            olam_used="assiah",
            score=0.7,
        )
        assert event is not None
        assert event.result == BirurimResult.BIRUR

    def test_evaluate_degradation(self):
        engine = BirurimEngine()
        event = engine.evaluate(
            response="Mauvaise réponse",
            olam_used="yetzirah",
            score=0.1,
        )
        assert event is not None
        assert event.result == BirurimResult.KELIPAH_REINFORCED

    def test_evaluate_neutral(self):
        engine = BirurimEngine()
        event = engine.evaluate(
            response="Réponse moyenne",
            olam_used="assiah",
            score=0.45,
        )
        assert event is not None
        assert event.result == BirurimResult.NOGAH_NEUTRAL

    def test_evaluate_ignores_upper_olamot(self):
        engine = BirurimEngine()
        event = engine.evaluate(
            response="Réponse",
            olam_used="briah",
            score=0.5,
        )
        assert event is None

    # ── get_birur_stats ───────────────────────────────────────

    def test_stats_empty(self):
        engine = BirurimEngine()
        stats = engine.get_birur_stats()
        assert stats.total_birurims == 0
        assert stats.total_degradations == 0
        assert stats.total_attempts == 0
        assert stats.birur_rate == 0.0

    def test_stats_mixed(self):
        engine = BirurimEngine()

        # 2 birurs d'Assiah
        engine.evaluate("ok", "assiah", 0.7)
        engine.evaluate("ok", "assiah", 0.8)
        # 1 dégradation d'Assiah
        engine.evaluate("bad", "assiah", 0.1)
        # 1 birur de Yetzirah
        engine.evaluate("ok", "yetzirah", 0.65)
        # 1 neutre de Yetzirah
        engine.evaluate("meh", "yetzirah", 0.4)
        # 1 de Briah (ignoré)
        engine.evaluate("ok", "briah", 0.9)

        stats = engine.get_birur_stats()
        assert stats.total_birurims == 3
        assert stats.total_degradations == 1
        assert stats.total_neutral == 1
        assert stats.total_attempts == 5  # 3 assiah + 2 yetzirah
        assert stats.birur_rate == pytest.approx(3 / 5)

        assert stats.by_olam["assiah"]["birur"] == 2
        assert stats.by_olam["assiah"]["degradation"] == 1
        assert stats.by_olam["yetzirah"]["birur"] == 1
        assert stats.by_olam["yetzirah"]["neutral"] == 1

    def test_stats_all_birur(self):
        engine = BirurimEngine()
        for _ in range(10):
            engine.evaluate("ok", "assiah", 0.9)

        stats = engine.get_birur_stats()
        assert stats.total_birurims == 10
        assert stats.birur_rate == 1.0

    def test_stats_all_degradation(self):
        engine = BirurimEngine()
        for _ in range(5):
            engine.evaluate("bad", "yetzirah", 0.05)

        stats = engine.get_birur_stats()
        assert stats.total_degradations == 5
        assert stats.birur_rate == 0.0

    # ── get_events ────────────────────────────────────────────

    def test_events_log(self):
        engine = BirurimEngine()
        engine.evaluate("ok", "assiah", 0.7)
        engine.evaluate("bad", "assiah", 0.1)

        events = engine.get_events()
        assert len(events) == 2
        assert events[0].result == BirurimResult.BIRUR
        assert events[1].result == BirurimResult.KELIPAH_REINFORCED


# ═══════════════════════════════════════════════════════════════
#   Intégration Birur → Nitzotzot
# ═══════════════════════════════════════════════════════════════


class TestBirurNitzotzotIntegration:
    """Vérifie que les birurims réussis appellent _collect_nitzutz."""

    def test_birur_increments_nitzotzot(self):
        """Un birur réussi doit appeler _collect_nitzutz avec source=birur_nogah."""
        engine = BirurimEngine()
        tree = {"yesod": MagicMock()}

        with patch("main._collect_nitzutz") as mock_nitz:
            engine.detect_birur(
                response="Bonne réponse d'Assiah",
                olam_used="assiah",
                score=0.75,
                tree=tree,
                domain="kabbale",
            )

            mock_nitz.assert_called_once()
            args = mock_nitz.call_args
            assert args[1]["source"] == "birur_nogah"
            assert args[1]["ntype"] == "birur_assiah"

    def test_degradation_does_not_increment_nitzotzot(self):
        """Une dégradation ne doit PAS appeler _collect_nitzutz."""
        engine = BirurimEngine()

        with patch("main._collect_nitzutz") as mock_nitz:
            engine.detect_degradation(
                response="Mauvaise réponse d'Assiah",
                olam_used="assiah",
                score=0.1,
            )
            mock_nitz.assert_not_called()
