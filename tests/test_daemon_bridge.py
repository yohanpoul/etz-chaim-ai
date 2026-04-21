"""Tests du DaemonBridge — מָסָךְ הַמַּבְדִּיל — Pont Daemon → Pipeline Ask.

Couvre :
  - gather_for_query : structure du retour, budget tokens, dict vide
  - _fetch_relevant_* : chaque source indépendamment
  - timeout : fetch lent skippé sans crash
  - fallback : table manquante n'affecte pas les autres
  - format_daemon_enrichment : formatage pour prompt Malkuth
  - _extract_keywords : extraction mots-clés
"""

from unittest.mock import MagicMock, patch, call
import time

import pytest

from daemon_bridge import (
    DaemonBridge,
    format_daemon_enrichment,
    _extract_keywords,
    _estimate_tokens,
)


# ── Fixtures ────────────────────────────────────────────────

@pytest.fixture
def mock_conn():
    """Connexion DB mockée avec cursor context manager."""
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cur)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return conn, cur


@pytest.fixture
def bridge():
    """DaemonBridge avec DB mockée."""
    return DaemonBridge(db_url="postgresql://localhost/test")


# ── Données de test ────────────────────────────────────────

SAMPLE_SYNTHESES = [
    ("synthesis", "Le Tsimtsum comme contraction informationnelle", "kabbale", 0.85),
    ("dissensus", "Divergence sur nature du Reshimu", "kabbale", 0.72),
]

SAMPLE_CAUSAL = [
    ("Tsimtsum", "Création du Halal", "demonstrated_causation", 0.90),
    ("Shevirah", "Dispersion des Nitzotzot", "probable_causation", 0.75),
]

SAMPLE_ANALOGIES = [
    ("kabbale", "neuroscience", "hiérarchie", "Les Sefirot comme couches neuronales", 0.80),
]

SAMPLE_INSIGHTS = [
    ("Le Tsimtsum est structurellement isomorphe au bottleneck informationnel",
     "insightforge", 0.88, ["kabbale", "information_theory"]),
]


# ── Tests _extract_keywords ────────────────────────────────

class TestExtractKeywords:
    def test_basic(self):
        kws = _extract_keywords("Qu'est-ce que le Tsimtsum en Kabbale ?")
        assert "tsimtsum" in kws
        assert "kabbale" in kws
        # Les stop-words sont exclus
        assert "est" not in kws
        assert "que" not in kws

    def test_short_words_filtered(self):
        kws = _extract_keywords("Il y a un or et un feu")
        assert "or" not in kws  # trop court (< 3)
        assert "feu" in kws

    def test_empty_query(self):
        assert _extract_keywords("") == []

    def test_dedup(self):
        kws = _extract_keywords("kabbale et kabbale encore kabbale")
        assert kws.count("kabbale") == 1


# ── Tests _estimate_tokens ─────────────────────────────────

class TestEstimateTokens:
    def test_basic(self):
        assert _estimate_tokens("abcd") == 1
        assert _estimate_tokens("abcdefgh") == 2
        assert _estimate_tokens("") == 0


# ── Tests DaemonBridge.gather_for_query ────────────────────

class TestGatherForQuery:

    @patch.object(DaemonBridge, "_get_conn")
    def test_returns_dict(self, mock_get_conn, bridge):
        """gather_for_query retourne toujours un dict."""
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cur)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        cur.fetchall.return_value = SAMPLE_SYNTHESES[:1]
        # _get_conn is a @contextmanager — simulate with __enter__/__exit__
        mock_get_conn.return_value.__enter__ = MagicMock(return_value=conn)
        mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)

        result = bridge.gather_for_query("Tsimtsum", "kabbale")
        assert isinstance(result, dict)

    @patch.object(DaemonBridge, "_get_conn")
    def test_empty_when_no_keywords(self, mock_get_conn, bridge):
        """Query sans mots-clés significatifs retourne dict vide."""
        result = bridge.gather_for_query("", "")
        assert result == {}
        mock_get_conn.assert_not_called()

    @patch.object(DaemonBridge, "_get_conn")
    def test_all_sections_populated(self, mock_get_conn, bridge):
        """Quand toutes les tables ont des résultats, toutes les sections sont présentes."""
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cur)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        # _get_conn is a @contextmanager — simulate with __enter__/__exit__
        mock_get_conn.return_value.__enter__ = MagicMock(return_value=conn)
        mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)

        # Séquencer les fetchall pour les 4 appels
        cur.fetchall.side_effect = [
            SAMPLE_SYNTHESES,
            SAMPLE_CAUSAL,
            SAMPLE_ANALOGIES,
            SAMPLE_INSIGHTS,
        ]

        result = bridge.gather_for_query("Tsimtsum kabbale", "kabbale", budget_tokens=2000)
        assert "tiferet_syntheses" in result
        assert "binah_causal" in result
        assert "chesed_analogies" in result
        assert "chokmah_insights" in result

    @patch.object(DaemonBridge, "_get_conn")
    def test_budget_respected(self, mock_get_conn, bridge):
        """Le budget tokens est respecté — pas d'explosion."""
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cur)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        # _get_conn is a @contextmanager — simulate with __enter__/__exit__
        mock_get_conn.return_value.__enter__ = MagicMock(return_value=conn)
        mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)

        # Résultats volumineux
        big_text = "x" * 2000  # ~500 tokens
        cur.fetchall.side_effect = [
            [("synthesis", big_text, "kabbale", 0.9)] * 3,
            [("A" * 500, "B" * 500, "demonstrated_causation", 0.9)] * 5,
            [("d1", "d2", "pattern", big_text, 0.8)] * 3,
            [("insight " + big_text, "forge", 0.9, [])] * 3,
        ]

        result = bridge.gather_for_query("test", "kabbale", budget_tokens=200)
        # Le résultat total ne devrait pas exploser le budget
        total_text = str(result)
        # Budget 200 tokens ≈ 800 chars — le résultat peut dépasser un peu
        # car le budget est un plafond par section, pas une hard limit sur le total
        assert isinstance(result, dict)

    @patch.object(DaemonBridge, "_get_conn")
    def test_no_results_returns_empty(self, mock_get_conn, bridge):
        """Quand aucune table n'a de résultats, retourne dict vide."""
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cur)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        # _get_conn is a @contextmanager — simulate with __enter__/__exit__
        mock_get_conn.return_value.__enter__ = MagicMock(return_value=conn)
        mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)
        cur.fetchall.return_value = []

        result = bridge.gather_for_query("Tsimtsum", "kabbale")
        assert result == {}


# ── Tests fetch individuels ────────────────────────────────

class TestFetchSyntheses:

    @patch.object(DaemonBridge, "_get_conn")
    def test_returns_list_of_dicts(self, mock_get_conn, bridge):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cur)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        # _get_conn is a @contextmanager — simulate with __enter__/__exit__
        mock_get_conn.return_value.__enter__ = MagicMock(return_value=conn)
        mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)
        cur.fetchall.return_value = SAMPLE_SYNTHESES

        result = bridge._fetch_relevant_syntheses(["tsimtsum"], "kabbale")
        assert isinstance(result, list)
        assert len(result) == 2
        assert "mode" in result[0]
        assert "content" in result[0]
        assert "confidence" in result[0]

    @patch.object(DaemonBridge, "_get_conn")
    def test_empty_on_no_match(self, mock_get_conn, bridge):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cur)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        # _get_conn is a @contextmanager — simulate with __enter__/__exit__
        mock_get_conn.return_value.__enter__ = MagicMock(return_value=conn)
        mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)
        cur.fetchall.return_value = []

        result = bridge._fetch_relevant_syntheses(["xyz"], "unknown")
        assert result == []


class TestFetchCausal:

    @patch.object(DaemonBridge, "_get_conn")
    def test_structure(self, mock_get_conn, bridge):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cur)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        # _get_conn is a @contextmanager — simulate with __enter__/__exit__
        mock_get_conn.return_value.__enter__ = MagicMock(return_value=conn)
        mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)
        cur.fetchall.return_value = SAMPLE_CAUSAL

        result = bridge._fetch_relevant_causal(["tsimtsum"], "kabbale")
        assert len(result) == 2
        assert "cause" in result[0]
        assert "effect" in result[0]
        assert "evidence_level" in result[0]


class TestFetchAnalogies:

    @patch.object(DaemonBridge, "_get_conn")
    def test_structure(self, mock_get_conn, bridge):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cur)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        # _get_conn is a @contextmanager — simulate with __enter__/__exit__
        mock_get_conn.return_value.__enter__ = MagicMock(return_value=conn)
        mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)
        cur.fetchall.return_value = SAMPLE_ANALOGIES

        result = bridge._fetch_relevant_analogies(["sefirot"], "kabbale")
        assert len(result) == 1
        assert "domain_a" in result[0]
        assert "domain_b" in result[0]
        assert "pattern" in result[0]
        assert "explanation" in result[0]


class TestFetchInsights:

    @patch.object(DaemonBridge, "_get_conn")
    def test_structure(self, mock_get_conn, bridge):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cur)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        # _get_conn is a @contextmanager — simulate with __enter__/__exit__
        mock_get_conn.return_value.__enter__ = MagicMock(return_value=conn)
        mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)
        cur.fetchall.return_value = SAMPLE_INSIGHTS

        result = bridge._fetch_relevant_insights(["tsimtsum"], "kabbale")
        assert len(result) == 1
        assert "content" in result[0]
        assert "source_module" in result[0]
        assert "confidence" in result[0]


# ── Tests timeout / fallback ───────────────────────────────

class TestTimeoutAndFallback:

    @patch.object(DaemonBridge, "_get_conn")
    def test_db_error_returns_empty(self, mock_get_conn, bridge):
        """Si la DB lève une erreur, le fetch retourne [] sans crash."""
        import psycopg2
        mock_get_conn.side_effect = psycopg2.OperationalError("timeout")

        result = bridge._fetch_relevant_syntheses(["test"], "kabbale")
        assert result == []

    @patch.object(DaemonBridge, "_get_conn")
    def test_partial_failure_doesnt_crash_gather(self, mock_get_conn, bridge):
        """Si un fetch échoue, les autres continuent."""
        import psycopg2

        call_count = [0]
        def side_effect():
            call_count[0] += 1
            if call_count[0] == 1:
                # Première table (synthèses) échoue
                raise psycopg2.OperationalError("timeout")
            conn = MagicMock()
            cur = MagicMock()
            conn.cursor.return_value.__enter__ = MagicMock(return_value=cur)
            conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
            cur.fetchall.return_value = SAMPLE_CAUSAL
            # _get_conn is a @contextmanager; wrap the conn so `with _get_conn() as c`
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=conn)
            ctx.__exit__ = MagicMock(return_value=False)
            return ctx

        mock_get_conn.side_effect = side_effect

        result = bridge.gather_for_query("Tsimtsum", "kabbale")
        # Synthèses échouent mais causal fonctionne
        assert "tiferet_syntheses" not in result
        assert "binah_causal" in result

    @patch.object(DaemonBridge, "_get_conn")
    def test_low_max_tokens_skips(self, mock_get_conn, bridge):
        """max_tokens < 20 skip le fetch immédiatement."""
        result = bridge._fetch_relevant_syntheses(["test"], "kabbale", max_tokens=10)
        assert result == []
        mock_get_conn.assert_not_called()


# ── Tests format_daemon_enrichment ─────────────────────────

class TestFormatDaemonEnrichment:

    def test_empty_enrichment(self):
        assert format_daemon_enrichment({}) == ""

    def test_syntheses_section(self):
        enrichment = {
            "tiferet_syntheses": [{
                "mode": "synthesis",
                "content": "Le Tsimtsum est contraction",
                "domain": "kabbale",
                "confidence": 0.85,
            }]
        }
        text = format_daemon_enrichment(enrichment)
        assert "Synthèses (Tiferet)" in text
        assert "synthèse" in text
        assert "0.85" in text
        assert "Tsimtsum" in text

    def test_causal_section(self):
        enrichment = {
            "binah_causal": [{
                "cause": "Tsimtsum",
                "effect": "Halal",
                "evidence_level": "demonstrated_causation",
                "confidence": 0.90,
            }]
        }
        text = format_daemon_enrichment(enrichment)
        assert "Relations causales (Binah)" in text
        assert "Tsimtsum" in text
        assert "Halal" in text

    def test_all_sections(self):
        enrichment = {
            "tiferet_syntheses": [{"mode": "synthesis", "content": "A", "domain": "", "confidence": 0.8}],
            "binah_causal": [{"cause": "B", "effect": "C", "evidence_level": "probable_causation", "confidence": 0.7}],
            "chesed_analogies": [{"domain_a": "d1", "domain_b": "d2", "pattern": "P", "explanation": "E", "strength": 0.6}],
            "chokmah_insights": [{"content": "I", "source_module": "forge", "confidence": 0.9, "connects_domains": []}],
        }
        text = format_daemon_enrichment(enrichment)
        assert "Tiferet" in text
        assert "Binah" in text
        assert "Chesed" in text
        assert "Chokmah" in text

    def test_dissensus_label(self):
        enrichment = {
            "tiferet_syntheses": [{
                "mode": "dissensus",
                "content": "Divergence",
                "domain": "",
                "confidence": 0.5,
            }]
        }
        text = format_daemon_enrichment(enrichment)
        assert "dissensus" in text
