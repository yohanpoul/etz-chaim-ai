"""Tests Haven (הָוֶן) — Qliphah de Malkuth.

Haven = "Richesse vide" — output long et bien formaté mais sans substance.
Anti-pattern : le système produit des analyses verbeuses qui n'engendrent aucun insight.
Tikkun : forcer Gevurah (discernement) avant Malkuth (manifestation).
"""

import psycopg2
import pytest


def _insert_analysis(conn, description: str, domain: str = "test"):
    """Insert a failuretoinsight_analyses row."""
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO failuretoinsight_analyses
               (source_type, description, qliphah, severity, domain)
               VALUES ('external', %s, 'unknown', 'nogah', %s)
               RETURNING id""",
            (description, domain),
        )
        return cur.fetchone()[0]


def _insert_insight(conn, analysis_id, content: str = "insight"):
    """Insert a failuretoinsight_insights row."""
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO failuretoinsight_insights
               (analysis_id, content, insight_type, confidence)
               VALUES (%s, %s, 'pattern', 0.5)""",
            (analysis_id, content),
        )


def test_haven_detected_when_verbose_no_insight(omer):
    """Haven détecté : analyses longues sans insights."""
    conn = psycopg2.connect(omer.db_url)
    conn.autocommit = True

    # Long description (> 200 chars) but no insight
    long_desc = "A" * 250
    _insert_analysis(conn, long_desc)

    conn.close()

    suggestions = omer.tune()
    haven_suggestions = [s for s in suggestions if "Haven" in s.reason]
    assert len(haven_suggestions) == 1
    assert haven_suggestions[0].severity == "warning"
    assert "הָוֶן" in haven_suggestions[0].reason


def test_haven_not_triggered_with_insights(omer):
    """Pas de Haven si les analyses longues ont des insights."""
    conn = psycopg2.connect(omer.db_url)
    conn.autocommit = True

    long_desc = "B" * 300
    aid = _insert_analysis(conn, long_desc)
    _insert_insight(conn, aid, "Real insight extracted")

    conn.close()

    suggestions = omer.tune()
    haven_suggestions = [s for s in suggestions if "Haven" in s.reason]
    assert len(haven_suggestions) == 0


def test_haven_not_triggered_short_descriptions(omer):
    """Pas de Haven pour des descriptions courtes sans insights."""
    conn = psycopg2.connect(omer.db_url)
    conn.autocommit = True

    _insert_analysis(conn, "Short fail")
    _insert_analysis(conn, "Another short one")

    conn.close()

    suggestions = omer.tune()
    haven_suggestions = [s for s in suggestions if "Haven" in s.reason]
    assert len(haven_suggestions) == 0


def test_haven_counts_multiple(omer):
    """Haven compte correctement N analyses verbeuses."""
    conn = psycopg2.connect(omer.db_url)
    conn.autocommit = True

    for i in range(5):
        _insert_analysis(conn, f"Verbose analysis number {i}: " + "X" * 250)

    conn.close()

    suggestions = omer.tune()
    haven_suggestions = [s for s in suggestions if "Haven" in s.reason]
    assert len(haven_suggestions) == 1
    assert "5 analyse(s)" in haven_suggestions[0].reason


def test_haven_lowers_gevurah(omer):
    """Haven réduit le max_unknown_ratio (Gevurah dans Malkuth)."""
    conn = psycopg2.connect(omer.db_url)
    conn.autocommit = True

    _insert_analysis(conn, "C" * 300)

    conn.close()

    suggestions = omer.tune()
    haven_suggestions = [s for s in suggestions if "Haven" in s.reason]
    assert len(haven_suggestions) == 1
    s = haven_suggestions[0]
    assert s.param == "max_unknown_ratio"
    assert s.new_value < s.old_value


def test_haven_mixed_long_and_short(omer):
    """Haven ne compte que les longues sans insights."""
    conn = psycopg2.connect(omer.db_url)
    conn.autocommit = True

    # 1 short without insight (ok)
    _insert_analysis(conn, "Short")
    # 1 long with insight (ok)
    aid = _insert_analysis(conn, "D" * 250)
    _insert_insight(conn, aid, "Valid insight")
    # 1 long without insight (Haven!)
    _insert_analysis(conn, "E" * 300)

    conn.close()

    suggestions = omer.tune()
    haven_suggestions = [s for s in suggestions if "Haven" in s.reason]
    assert len(haven_suggestions) == 1
    assert "1 analyse(s)" in haven_suggestions[0].reason
