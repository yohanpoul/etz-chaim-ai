"""Tests LamedBridge — le sentier Lamed (Gevurah → Tiferet).

Les rejets ne sont plus jetés — ils passent par FailureToInsight.
"""

import pytest

from autojudge.lamed_bridge import LamedBridge
from autojudge.models import MultiScore


class TestLamedBridgeUnit:
    """Tests unitaires — sans FTI."""

    def test_disconnected_returns_none(self):
        bridge = LamedBridge(failure_to_insight=None)
        assert not bridge.connected
        fid, nitz = bridge.process_rejection(
            domain_id="test",
            hypothesis="improve text",
            original="hello",
            modified="hello world",
        )
        assert fid is None
        assert nitz is False

    def test_quarantine_disconnected(self):
        bridge = LamedBridge(failure_to_insight=None)
        fid, nitz = bridge.process_quarantine(
            domain_id="test",
            hypothesis="improve text",
        )
        assert fid is None
        assert nitz is False

    def test_guidance_disconnected(self):
        bridge = LamedBridge(failure_to_insight=None)
        assert bridge.get_guidance() is None

    def test_infer_qliphah_none_scores(self):
        bridge = LamedBridge()
        assert bridge._infer_qliphah(None) == "golachab"

    def test_infer_qliphah_thagirion(self):
        bridge = LamedBridge()
        scores = MultiScore(gevurah=0.8, chesed=0.5, tiferet=0.2, hod=0.5, yesod=0.5)
        assert bridge._infer_qliphah(scores) == "thagirion"

    def test_infer_qliphah_golachab_low_overall(self):
        bridge = LamedBridge()
        scores = MultiScore(gevurah=0.1, chesed=0.1, tiferet=0.1, hod=0.1, yesod=0.1)
        assert bridge._infer_qliphah(scores) == "golachab"


class TestLamedBridgeIntegration:
    """Tests d'intégration — avec FTI connecté."""

    def test_rejection_analyzed(self, fti):
        """Un rejet passe par FailureToInsight et produit une analyse."""
        bridge = LamedBridge(failure_to_insight=fti)
        assert bridge.connected

        fid, extracted = bridge.process_rejection(
            domain_id="writing",
            hypothesis="Improve clarity",
            original="The text was unclear.",
            modified="The text was still unclear.",
            multi_score=MultiScore(
                gevurah=0.3, chesed=0.2, tiferet=0.4, hod=0.3, yesod=0.5
            ),
            explanation="Quality did not improve",
        )
        assert fid is not None

    def test_quarantine_analyzed(self, fti):
        """Une quarantaine est enregistrée dans FTI et produit des Nitzotzot."""
        bridge = LamedBridge(failure_to_insight=fti)
        fid, extracted = bridge.process_quarantine(
            domain_id="code",
            hypothesis="Reduce complexity",
            multi_score=MultiScore(
                gevurah=0.5, chesed=0.4, tiferet=0.5, hod=0.4, yesod=0.5
            ),
        )
        assert fid is not None
        assert extracted is True

    def test_rejection_with_scores_in_description(self, fti):
        """Les scores multi-sephirothiques sont inclus dans la description."""
        bridge = LamedBridge(failure_to_insight=fti)
        scores = MultiScore(
            gevurah=0.4, chesed=0.3, tiferet=0.5, hod=0.3, yesod=0.4
        )
        fid, _ = bridge.process_rejection(
            domain_id="writing",
            hypothesis="Add structure",
            original="flat text",
            modified="still flat",
            multi_score=scores,
            explanation="Structure unchanged",
        )
        assert fid is not None
        # Verify the analysis exists in FTI
        analysis = fti.db.get_analysis(fid)
        assert analysis is not None
        assert "gevurah" in analysis.description.lower() or "writing" in analysis.description.lower()
