"""Tests pour les diagnostics Qliphothiques des 3 Sephiroth supérieures.

Binah  — Satariel (סתריאל) : faux patterns causaux
Chokmah — Ghagiel (עגיאל) : divergence sans convergence
Keter  — Thaumiel (תאומיאל) : intentions contradictoires

Chaque diagnostic est testé en mode healthy et en mode Qliphothique
avec des données simulées (mock _safe_query).
"""

import unittest
from unittest.mock import MagicMock, patch

from omer.core import OmerManager, Suggestion


def _make_manager():
    """Crée un OmerManager sans connexion DB ni config YAML."""
    mgr = object.__new__(OmerManager)
    mgr.db_url = "mock://test"
    mgr.config = {}
    return mgr


# ── Binah — Satariel ────────────────────────────────────────


class TestTuneBinah(unittest.TestCase):
    """Satariel — diagnostic de Binah/CausalEngine."""

    def setUp(self):
        self.mgr = _make_manager()
        self.conn = MagicMock()

    def test_healthy_no_data(self):
        """Pas de claims causales → pas de suggestion."""
        self.mgr._safe_query = MagicMock(return_value=[(0, 0, 0)])
        s = self.mgr._tune_binah(self.conn, {})
        self.assertEqual(s, [])

    def test_healthy_table_missing(self):
        """Table absente → pas de crash."""
        self.mgr._safe_query = MagicMock(return_value=None)
        s = self.mgr._tune_binah(self.conn, {})
        self.assertEqual(s, [])

    def test_healthy_good_validation_rate(self):
        """< 60% non validées, < 40% low confidence → healthy."""
        # total=20, unvalidated=5 (25%), low_conf=2 (10%)
        self.mgr._safe_query = MagicMock(return_value=[(20, 5, 2)])
        s = self.mgr._tune_binah(self.conn, {})
        self.assertEqual(s, [])

    def test_healthy_not_enough_data(self):
        """< 5 claims → pas de diagnostic (données insuffisantes)."""
        # total=3, unvalidated=3 (100%), low_conf=3 (100%) — mais total < 5
        self.mgr._safe_query = MagicMock(return_value=[(3, 3, 3)])
        s = self.mgr._tune_binah(self.conn, {})
        self.assertEqual(s, [])

    def test_satariel_primary(self):
        """> 60% claims non validées → Satariel actif."""
        # total=10, unvalidated=8 (80%), low_conf=1
        self.mgr._safe_query = MagicMock(return_value=[(10, 8, 1)])
        s = self.mgr._tune_binah(self.conn, {})
        self.assertEqual(len(s), 1)
        self.assertIn("Satariel actif", s[0].reason)
        self.assertEqual(s[0].severity, "warning")
        self.assertEqual(s[0].sephirah, "binah")
        self.assertEqual(s[0].module, "causalengine")

    def test_satariel_secondary_low_confidence(self):
        """> 40% low confidence → Satariel secondaire."""
        # total=10, unvalidated=3 (30% — ok), low_conf=5 (50% — qliphothique)
        self.mgr._safe_query = MagicMock(return_value=[(10, 3, 5)])
        s = self.mgr._tune_binah(self.conn, {})
        self.assertEqual(len(s), 1)
        self.assertIn("secondaire", s[0].reason)
        self.assertEqual(s[0].severity, "info")

    def test_satariel_both_metrics(self):
        """Les deux seuils dépassés → 2 suggestions."""
        # total=10, unvalidated=7 (70%), low_conf=5 (50%)
        self.mgr._safe_query = MagicMock(return_value=[(10, 7, 5)])
        s = self.mgr._tune_binah(self.conn, {})
        self.assertEqual(len(s), 2)
        reasons = [x.reason for x in s]
        self.assertTrue(any("Satariel actif" in r for r in reasons))
        self.assertTrue(any("secondaire" in r for r in reasons))


# ── Chokmah — Ghagiel ───────────────────────────────────────


class TestTuneChokmah(unittest.TestCase):
    """Ghagiel — diagnostic de Chokmah/InsightForge."""

    def setUp(self):
        self.mgr = _make_manager()
        self.conn = MagicMock()

    def test_healthy_no_sessions(self):
        """Pas de sessions → pas de suggestion."""
        self.mgr._safe_query = MagicMock(return_value=[(0, 0)])
        s = self.mgr._tune_chokmah(self.conn, {})
        self.assertEqual(s, [])

    def test_healthy_table_missing(self):
        """Table absente → pas de crash."""
        self.mgr._safe_query = MagicMock(return_value=None)
        s = self.mgr._tune_chokmah(self.conn, {})
        self.assertEqual(s, [])

    def test_healthy_good_convergence(self):
        """Convergence > 20%, peu de stale → healthy."""
        self.mgr._safe_query = MagicMock(side_effect=[
            [(20, 8)],   # sessions : 8/20 = 40% convergence
            [(1,)],      # 1 stale insight (< seuil 5)
        ])
        s = self.mgr._tune_chokmah(self.conn, {})
        self.assertEqual(s, [])

    def test_healthy_not_enough_candidates(self):
        """< 10 candidats → pas de diagnostic (données insuffisantes)."""
        self.mgr._safe_query = MagicMock(side_effect=[
            [(5, 0)],    # 5 candidats (< 10)
            [(0,)],
        ])
        s = self.mgr._tune_chokmah(self.conn, {})
        self.assertEqual(s, [])

    def test_ghagiel_low_convergence(self):
        """Convergence < 20% → Ghagiel actif."""
        self.mgr._safe_query = MagicMock(side_effect=[
            [(20, 2)],   # 2/20 = 10% convergence
            [(0,)],      # pas de stale
        ])
        s = self.mgr._tune_chokmah(self.conn, {})
        self.assertEqual(len(s), 1)
        self.assertIn("Ghagiel actif", s[0].reason)
        self.assertEqual(s[0].severity, "warning")
        self.assertEqual(s[0].sephirah, "chokmah")
        self.assertEqual(s[0].module, "insightforge")

    def test_ghagiel_stale_insights(self):
        """Bonne convergence mais beaucoup de stale → secondaire."""
        self.mgr._safe_query = MagicMock(side_effect=[
            [(20, 8)],   # 40% convergence (ok)
            [(12,)],     # 12 stale insights (> 5)
        ])
        s = self.mgr._tune_chokmah(self.conn, {})
        self.assertEqual(len(s), 1)
        self.assertIn("secondaire", s[0].reason)
        self.assertEqual(s[0].severity, "info")

    def test_ghagiel_both_metrics(self):
        """Convergence basse + beaucoup de stale → 2 suggestions."""
        self.mgr._safe_query = MagicMock(side_effect=[
            [(20, 2)],   # 10% convergence
            [(10,)],     # 10 stale
        ])
        s = self.mgr._tune_chokmah(self.conn, {})
        self.assertEqual(len(s), 2)


# ── Keter — Thaumiel ────────────────────────────────────────


class TestTuneKeter(unittest.TestCase):
    """Thaumiel — diagnostic de Keter/Strategy."""

    def setUp(self):
        self.mgr = _make_manager()
        self.conn = MagicMock()

    def test_healthy_no_intentions(self):
        """Pas d'intentions actives → pas de suggestion."""
        self.mgr._safe_query = MagicMock(return_value=[(0,)])
        s = self.mgr._tune_keter(self.conn, {})
        self.assertEqual(s, [])

    def test_healthy_table_missing(self):
        """Table absente → pas de crash."""
        self.mgr._safe_query = MagicMock(return_value=None)
        s = self.mgr._tune_keter(self.conn, {})
        self.assertEqual(s, [])

    def test_healthy_few_intentions(self):
        """<= 5 intentions, peu de changements → healthy."""
        self.mgr._safe_query = MagicMock(side_effect=[
            [(3,)],   # 3 intentions actives (ok)
            [(1,)],   # 1 changement stratégie (ok)
        ])
        s = self.mgr._tune_keter(self.conn, {})
        self.assertEqual(s, [])

    def test_thaumiel_too_many_intentions(self):
        """> 5 intentions actives → Thaumiel actif."""
        self.mgr._safe_query = MagicMock(side_effect=[
            [(8,)],   # 8 intentions (> 5)
            [(1,)],   # 1 changement (ok)
        ])
        s = self.mgr._tune_keter(self.conn, {})
        self.assertEqual(len(s), 1)
        self.assertIn("Thaumiel actif", s[0].reason)
        self.assertEqual(s[0].severity, "warning")
        self.assertEqual(s[0].sephirah, "keter")
        self.assertEqual(s[0].module, "strategy")

    def test_thaumiel_strategy_instability(self):
        """> 3 changements de stratégie en 24h → secondaire."""
        self.mgr._safe_query = MagicMock(side_effect=[
            [(3,)],   # 3 intentions (ok)
            [(5,)],   # 5 changements (> 3)
        ])
        s = self.mgr._tune_keter(self.conn, {})
        self.assertEqual(len(s), 1)
        self.assertIn("secondaire", s[0].reason)

    def test_thaumiel_critical_instability(self):
        """> 5 changements de stratégie → severity critical."""
        self.mgr._safe_query = MagicMock(side_effect=[
            [(3,)],   # ok
            [(6,)],   # 6 changements (> 5 → critical)
        ])
        s = self.mgr._tune_keter(self.conn, {})
        critical = [x for x in s if x.severity == "critical"]
        self.assertEqual(len(critical), 1)

    def test_thaumiel_both_metrics(self):
        """Trop d'intentions + instabilité → 2 suggestions."""
        self.mgr._safe_query = MagicMock(side_effect=[
            [(8,)],   # 8 intentions
            [(6,)],   # 6 changements
        ])
        s = self.mgr._tune_keter(self.conn, {})
        self.assertEqual(len(s), 2)

    def test_thaumiel_info_severity(self):
        """4 changements (> 3 mais <= 5) → severity info, pas critical."""
        self.mgr._safe_query = MagicMock(side_effect=[
            [(3,)],   # ok
            [(4,)],   # 4 changements (info, pas critical)
        ])
        s = self.mgr._tune_keter(self.conn, {})
        self.assertEqual(len(s), 1)
        self.assertEqual(s[0].severity, "info")


# ── Intégration — tune() appelle les 10 diagnostics ─────────


class TestTuneIntegration(unittest.TestCase):
    """Le cycle tune() appelle bien les 10 diagnostics."""

    @patch('omer.core.psycopg2.connect')
    def test_tune_calls_all_10(self, mock_connect):
        """tune() invoque les 10 méthodes de diagnostic."""
        mgr = _make_manager()
        mock_conn = MagicMock()
        mock_connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_connect.return_value.__exit__ = MagicMock(return_value=False)

        mgr.get_params = MagicMock(return_value=[])

        methods = [
            '_tune_binah', '_tune_chokmah', '_tune_keter',
            '_tune_gevurah', '_tune_chesed', '_tune_tiferet',
            '_tune_netzach', '_tune_hod', '_tune_yesod', '_tune_malkuth',
        ]
        for m in methods:
            setattr(mgr, m, MagicMock(return_value=[]))

        mgr.tune()

        for m in methods:
            getattr(mgr, m).assert_called_once()

    @patch('omer.core.psycopg2.connect')
    def test_tune_upper_before_lower(self, mock_connect):
        """Les 3 supérieures sont appelées avant les 7 inférieures."""
        mgr = _make_manager()
        mock_conn = MagicMock()
        mock_connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_connect.return_value.__exit__ = MagicMock(return_value=False)

        mgr.get_params = MagicMock(return_value=[])

        call_order = []
        for name in ['_tune_binah', '_tune_chokmah', '_tune_keter',
                      '_tune_gevurah', '_tune_chesed', '_tune_tiferet',
                      '_tune_netzach', '_tune_hod', '_tune_yesod',
                      '_tune_malkuth']:
            def make_tracker(n):
                def tracker(conn, pm):
                    call_order.append(n)
                    return []
                return tracker
            setattr(mgr, name, make_tracker(name))

        mgr.tune()

        self.assertEqual(call_order[:3], [
            '_tune_binah', '_tune_chokmah', '_tune_keter',
        ])
        self.assertEqual(len(call_order), 10)


# ── Labels ───────────────────────────────────────────────────


class TestLabels(unittest.TestCase):
    """Les labels incluent les 3 Sephiroth supérieures."""

    def test_sephirot_labels_has_10(self):
        from omer.core import SEPHIROT_LABELS
        self.assertIn("binah", SEPHIROT_LABELS)
        self.assertIn("chokmah", SEPHIROT_LABELS)
        self.assertIn("keter", SEPHIROT_LABELS)
        self.assertEqual(len(SEPHIROT_LABELS), 10)

    def test_module_labels_has_10(self):
        from omer.core import MODULE_LABELS
        self.assertEqual(MODULE_LABELS["binah"], "CausalEngine")
        self.assertEqual(MODULE_LABELS["chokmah"], "InsightForge")
        self.assertEqual(MODULE_LABELS["keter"], "Strategy")
        self.assertEqual(len(MODULE_LABELS), 10)

    def test_format_suggestions_handles_upper(self):
        """format_suggestions affiche correctement les Sephiroth supérieures."""
        suggestions = [
            Suggestion(
                key="binah_satariel",
                param="causal_sensitivity",
                sephirah="binah",
                inner="gevurah",
                module="causalengine",
                old_value=0.80,
                new_value=0.60,
                reason="Satariel actif — test",
                severity="warning",
            ),
        ]
        output = OmerManager.format_suggestions(suggestions)
        self.assertIn("Binah", output)
        self.assertIn("Satariel", output)

    def test_status_shows_upper_sephiroth(self):
        """status() mentionne les 3 Sephiroth supérieures."""
        mgr = _make_manager()
        mgr.get_params = MagicMock(return_value=[])
        output = mgr.status()
        self.assertIn("Binah", output)
        self.assertIn("Chokmah", output)
        self.assertIn("Keter", output)
        self.assertIn("Satariel", output)
        self.assertIn("Ghagiel", output)
        self.assertIn("Thaumiel", output)


if __name__ == "__main__":
    unittest.main()
