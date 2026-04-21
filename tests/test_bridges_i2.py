"""Tests pour les 3 ponts inter-modules — recommandation I2 audit Cycle 4.

Vérifie :
- Bridge A : task_autojudge_to_partzuf → trigger_katnut/gadlut selon seuils.
- Bridge B : task_insightforge_to_selfmodel → daat.feed_insight() appelé.
- Bridge C : task_beinoni_to_selfmap → selfmap.record_beinoni_signal() appelé
             par domaine.

Toutes les connexions DB sont mockées — tests unitaires purs, sans PostgreSQL.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ─── Helpers : mock du context manager pool.get_conn ───────────


def _mock_conn(cursor_returns):
    """Construit un mock de connexion où cur.fetchone/fetchall retourne
    les valeurs fournies en séquence.

    cursor_returns: list[(kind, value)] où kind ∈ {'one', 'all'}.
    """
    cur = MagicMock()
    fetchone_values = [v for k, v in cursor_returns if k == "one"]
    fetchall_values = [v for k, v in cursor_returns if k == "all"]
    cur.fetchone.side_effect = fetchone_values
    cur.fetchall.side_effect = fetchall_values

    conn = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cur)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=conn)
    ctx.__exit__ = MagicMock(return_value=False)
    return ctx, cur


# ─── Bridge A — AutoJudge → Partzufim ──────────────────────────


class TestBridgeA:
    def test_triggers_katnut_on_low_ratio(self):
        from daemon_tasks.tzimtzum import task_autojudge_to_partzuf

        ctx, _ = _mock_conn([
            ("one", (2, 10, 12, 0.35)),  # accepted, rejected, total, avg
        ])
        with patch("pool.get_conn", return_value=ctx):
            reg = MagicMock()
            reg.trigger_katnut.return_value = True
            with patch(
                "partzufim.regulator.PartzufimRegulator", return_value=reg
            ):
                result = task_autojudge_to_partzuf({})

        assert result["transition"] == "katnut"
        assert result["accepted"] == 2
        assert result["rejected"] == 10
        reg.trigger_katnut.assert_called_once()
        reg.trigger_gadlut.assert_not_called()

    def test_triggers_gadlut_on_high_ratio(self):
        from daemon_tasks.tzimtzum import task_autojudge_to_partzuf

        ctx, _ = _mock_conn([
            ("one", (9, 1, 10, 0.75)),
        ])
        with patch("pool.get_conn", return_value=ctx):
            reg = MagicMock()
            reg.trigger_gadlut.return_value = True
            with patch(
                "partzufim.regulator.PartzufimRegulator", return_value=reg
            ):
                result = task_autojudge_to_partzuf({})

        assert result["transition"] == "gadlut"
        reg.trigger_gadlut.assert_called_once()
        reg.trigger_katnut.assert_not_called()

    def test_no_transition_on_insufficient_data(self):
        from daemon_tasks.tzimtzum import task_autojudge_to_partzuf

        ctx, _ = _mock_conn([
            ("one", (1, 1, 2, 0.5)),  # total=2 < 3
        ])
        with patch("pool.get_conn", return_value=ctx):
            with patch(
                "partzufim.regulator.PartzufimRegulator"
            ) as reg_cls:
                result = task_autojudge_to_partzuf({})

        assert result["transition"] is None
        assert result["experiments_scanned"] == 2
        # PartzufimRegulator ne doit même pas être instancié.
        reg_cls.assert_not_called()

    def test_no_transition_in_healthy_range(self):
        from daemon_tasks.tzimtzum import task_autojudge_to_partzuf

        ctx, _ = _mock_conn([
            ("one", (5, 5, 10, 0.55)),  # ratio=0.5, avg=0.55 → ni bas ni haut
        ])
        with patch("pool.get_conn", return_value=ctx):
            reg = MagicMock()
            with patch(
                "partzufim.regulator.PartzufimRegulator", return_value=reg
            ):
                result = task_autojudge_to_partzuf({})

        assert result["transition"] is None
        reg.trigger_katnut.assert_not_called()
        reg.trigger_gadlut.assert_not_called()


# ─── Bridge B — InsightForge → SelfModel ───────────────────────


class TestBridgeB:
    def test_no_daat_returns_error(self):
        from daemon_tasks.chokmah import task_insightforge_to_selfmodel

        result = task_insightforge_to_selfmodel({})
        assert "error" in result
        assert result["fed"] == 0

    def test_feeds_validated_insights(self):
        from daemon_tasks.chokmah import task_insightforge_to_selfmodel

        uid1, uid2 = uuid4(), uuid4()
        rows = [
            {"id": uid1, "description": "Insight 1", "confidence": 0.8,
             "domain": "kabbale", "novelty_score": 0.7},
            {"id": uid2, "description": "Insight 2", "confidence": 0.6,
             "domain": "ml", "novelty_score": 0.5},
        ]
        ctx, _ = _mock_conn([("all", rows)])

        daat = MagicMock()
        # Premier True (inséré), deuxième False (doublon).
        daat.feed_insight.side_effect = [True, False]

        with patch("pool.get_conn", return_value=ctx):
            result = task_insightforge_to_selfmodel({"daat": daat})

        assert result["candidates_read"] == 2
        assert result["fed"] == 1
        assert result["duplicates"] == 1
        assert daat.feed_insight.call_count == 2

        # Vérifier que les args propagés sont corrects (1er appel).
        kwargs = daat.feed_insight.call_args_list[0].kwargs
        assert kwargs["source_module"] == "insightforge"
        assert kwargs["source_id"] == uid1
        assert kwargs["description"] == "Insight 1"
        assert kwargs["confidence"] == 0.8
        assert kwargs["domain"] == "kabbale"
        assert kwargs["novelty_score"] == 0.7

    def test_empty_source_is_noop(self):
        from daemon_tasks.chokmah import task_insightforge_to_selfmodel

        ctx, _ = _mock_conn([("all", [])])
        daat = MagicMock()

        with patch("pool.get_conn", return_value=ctx):
            result = task_insightforge_to_selfmodel({"daat": daat})

        assert result["candidates_read"] == 0
        assert result["fed"] == 0
        daat.feed_insight.assert_not_called()


# ─── Bridge C — BeinoniTracker → SelfMap ───────────────────────


class TestBridgeC:
    def test_no_selfmap_returns_error(self):
        from daemon_tasks.omer import task_beinoni_to_selfmap

        result = task_beinoni_to_selfmap({})
        assert "error" in result

    def test_aggregates_by_domain_and_upserts(self):
        from daemon_tasks.omer import task_beinoni_to_selfmap

        # 2 domaines + (regressions=1, elevations=2) sur la fenêtre.
        domain_rows = [
            ("kabbale", 20, 0.75, 0.82),
            ("ml",      10, 0.40, 0.55),
        ]
        ctx, _ = _mock_conn([
            ("all", domain_rows),  # GROUP BY domain
            ("one", (1, 2)),       # regressions, elevations
        ])

        selfmap = MagicMock()
        with patch("pool.get_conn", return_value=ctx):
            result = task_beinoni_to_selfmap({"selfmap": selfmap})

        assert result["domains_updated"] == 2
        assert result["total_interactions"] == 30
        assert selfmap.record_beinoni_signal.call_count == 2

        # Vérif 1er call
        kwargs = selfmap.record_beinoni_signal.call_args_list[0].kwargs
        assert kwargs["domain"] == "kabbale"
        assert kwargs["n_interactions"] == 20
        assert kwargs["elokit_ratio"] == pytest.approx(0.75)
        assert kwargs["avg_response_score"] == pytest.approx(0.82)
        assert kwargs["regressions_count"] == 1
        assert kwargs["elevations_count"] == 2
        assert kwargs["window_seconds"] == 3600

    def test_accepts_hod_key_as_fallback(self):
        """tree['hod'] doit être accepté si 'selfmap' absent."""
        from daemon_tasks.omer import task_beinoni_to_selfmap

        ctx, _ = _mock_conn([
            ("all", [("default", 5, 0.6, 0.7)]),
            ("one", (0, 0)),
        ])
        selfmap = MagicMock()
        with patch("pool.get_conn", return_value=ctx):
            result = task_beinoni_to_selfmap({"hod": selfmap})

        assert result["domains_updated"] == 1
        selfmap.record_beinoni_signal.assert_called_once()

    def test_empty_window_is_noop(self):
        from daemon_tasks.omer import task_beinoni_to_selfmap

        ctx, _ = _mock_conn([
            ("all", []),        # aucun domaine
            ("one", (0, 0)),
        ])
        selfmap = MagicMock()
        with patch("pool.get_conn", return_value=ctx):
            result = task_beinoni_to_selfmap({"selfmap": selfmap})

        assert result["domains_updated"] == 0
        selfmap.record_beinoni_signal.assert_not_called()


# ─── API unitaire : feed_insight idempotence ───────────────────


class TestFeedInsightAPI:
    def test_feed_insight_delegates_to_db(self):
        """SelfModel.feed_insight appelle db.save_external_insight."""
        from selfmodel.core import SelfModel

        # Instancier sans DB : on patch SelfModelDB au niveau classe.
        with patch("selfmodel.core.SelfModelDB") as db_cls:
            db = MagicMock()
            db.save_external_insight.return_value = True
            db_cls.return_value = db
            sm = SelfModel(db_url="postgresql://fake")

            uid = uuid4()
            ok = sm.feed_insight(
                source_module="insightforge",
                source_id=uid,
                description="test",
                confidence=0.9,
                domain="kabbale",
                novelty_score=0.5,
            )

        assert ok is True
        db.save_external_insight.assert_called_once_with(
            source_module="insightforge",
            source_id=uid,
            description="test",
            confidence=0.9,
            domain="kabbale",
            novelty_score=0.5,
        )
