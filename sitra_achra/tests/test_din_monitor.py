"""Tests Din Monitor — surveillance tamid."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from sitra_achra.gevurah_interne import Anomalie, DinStatus, GevurahReport
from sitra_achra.din_monitor import DinMonitor, DinMonitorResult


@pytest.fixture
def monitor(tmp_path):
    """DinMonitor avec budget persiste dans tmp."""
    state_file = tmp_path / "sitra_achra_budget.json"
    with patch("sitra_achra.budget_parasitaire._BUDGET_STATE", state_file), \
         patch("sitra_achra.budget_parasitaire._STATE_DIR", tmp_path):
        yield DinMonitor(db_url="postgresql://localhost/test")


class TestDinMonitor:

    def test_all_sain_no_trigger(self, monitor):
        """Tous modules sains → SA pas instancie."""
        sain = GevurahReport(module="test", status=DinStatus.SAIN)

        with patch.object(monitor.gevurah, "diagnostiquer_tous", return_value=[sain]):
            result = monitor.run_cycle()

        assert not result.sitra_achra_triggered
        assert result.modules_sain == 1
        assert result.targets == []

    def test_defaillance_triggers_sa(self, monitor):
        """Module en defaillance → SA instancie sur ce module."""
        malade = GevurahReport(
            module="epistememory",
            status=DinStatus.DEFAILLANCE,
            anomalies=[Anomalie(
                module="epistememory", qliphah="gamaliel",
                description="test", severity="anan",
                metric_name="x", metric_value=1, threshold=0,
            )],
        )

        with patch.object(monitor.gevurah, "diagnostiquer_tous", return_value=[malade]):
            result = monitor.run_cycle()

        assert result.sitra_achra_triggered
        assert "epistememory" in result.targets
        assert result.modules_defaillance == 1

    def test_debordement_also_triggers(self, monitor):
        """Debordement (rigueur excessive) aussi instancie le SA."""
        deborde = GevurahReport(
            module="autojudge",
            status=DinStatus.DEBORDEMENT,
            anomalies=[Anomalie(
                module="autojudge", qliphah="golachab",
                description="sur-filtrage", severity="ruach",
                metric_name="rejection_rate", metric_value=0.75, threshold=0.70,
            )],
        )

        with patch.object(monitor.gevurah, "diagnostiquer_tous", return_value=[deborde]):
            result = monitor.run_cycle()

        assert result.sitra_achra_triggered
        assert "autojudge" in result.targets

    def test_mixed_modules(self, monitor):
        """Mix sain + malade → SA cible uniquement les malades."""
        sain = GevurahReport(module="selfmap", status=DinStatus.SAIN)
        malade = GevurahReport(
            module="epistememory",
            status=DinStatus.DEFAILLANCE,
            anomalies=[Anomalie(
                module="epistememory", qliphah="gamaliel",
                description="test", severity="mamash",
                metric_name="x", metric_value=1, threshold=0,
            )],
        )

        with patch.object(
            monitor.gevurah, "diagnostiquer_tous",
            return_value=[sain, malade],
        ):
            result = monitor.run_cycle()

        assert result.sitra_achra_triggered
        assert result.targets == ["epistememory"]
        assert result.modules_sain == 1
        assert result.modules_defaillance == 1

    def test_critical_flaws_feed_budget(self, monitor):
        """Failles critiques (anan/mamash) nourrissent le budget SA."""
        initial_budget = monitor.budget.current_budget

        malade = GevurahReport(
            module="epistememory",
            status=DinStatus.DEFAILLANCE,
            anomalies=[
                Anomalie(
                    module="epistememory", qliphah="gamaliel",
                    description="corruption", severity="mamash",
                    metric_name="x", metric_value=1, threshold=0,
                ),
                Anomalie(
                    module="epistememory", qliphah="gamaliel",
                    description="silent", severity="anan",
                    metric_name="y", metric_value=1, threshold=0,
                ),
            ],
        )

        with patch.object(monitor.gevurah, "diagnostiquer_tous", return_value=[malade]):
            monitor.run_cycle()

        # 2 failles critiques → budget augmente
        assert monitor.budget.current_budget > initial_budget

    def test_result_has_budget_status(self, monitor):
        """Le resultat inclut le statut du budget parasitaire."""
        sain = GevurahReport(module="test", status=DinStatus.SAIN)

        with patch.object(monitor.gevurah, "diagnostiquer_tous", return_value=[sain]):
            result = monitor.run_cycle()

        assert "current_budget" in result.budget_status
        assert "parasitism_rate" in result.budget_status
