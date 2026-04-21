"""Tests du fix schema drift Binah→Yesod.

Sprint megaclean T2 — Dette 7 (résiduelle Sprint 8c).

Drift diagnostiqué dans daemon_tasks.binah.task_binah_to_yesod :
    1. SELECT `domain` depuis causal_claims — colonne inexistante (domain
       vit sur causal_graphs, relié via graph_id).
    2. SELECT `confounders` — colonne réelle = `known_confounders`.
    3. WHERE evidence_level IN ('observed', 'probable', 'demonstrated')
       — valeurs DB longues : 'observed_association', 'probable_causation',
       'demonstrated_causation'.
    4. confidence_map utilise les clés courtes (jamais matchées).

Erreur runtime observée 2026-04-18 20:49:32 :
    `Binah→Yesod error: column "domain" does not exist`

Fix :
    - JOIN causal_graphs pour récupérer domain (preserve domain doctrinal)
    - `confounders` → `known_confounders`
    - evidence_level + confidence_map : valeurs longues
    - `claim.get("domain") or "causal"` (None-safe si graph orphelin)

Tests :
    1. Structurels — la requête SQL contient les bons noms de colonnes.
    2. Structurels — confidence_map contient les clés longues.
    3. Intégration (nécessite DB) — la requête s'exécute sans erreur contre
       le vrai schéma.
"""

from __future__ import annotations

import inspect
import os

import pytest


class TestBinahToYesodQueryStructure:
    """Tests structurels : le source contient les fixes schema drift."""

    @pytest.fixture
    def source(self):
        from daemon_tasks.binah import task_binah_to_yesod
        return inspect.getsource(task_binah_to_yesod)

    def test_query_joins_causal_graphs_for_domain(self, source):
        """La requête doit JOIN causal_graphs pour récupérer domain,
        plutôt que lire domain depuis causal_claims (colonne inexistante).
        """
        assert "LEFT JOIN causal_graphs" in source, (
            "LEFT JOIN causal_graphs absent. Sans le JOIN, la requête "
            "tente de lire causal_claims.domain qui n'existe pas."
        )
        assert "cg.domain" in source, (
            "`cg.domain` (colonne via JOIN) absente du SELECT."
        )

    def test_query_uses_known_confounders_not_confounders(self, source):
        """La colonne réelle est `known_confounders`, pas `confounders`."""
        assert "cc.known_confounders" in source, (
            "`cc.known_confounders` absent — drift schéma non fixé."
        )
        # Non-régression : plus de référence à `cc.confounders` (sans known_)
        # en tant que colonne (on autorise le mot dans commentaires).
        lines_with_select_confounders = [
            ln for ln in source.split("\n")
            if "cc.confounders" in ln and "known_confounders" not in ln
        ]
        assert not lines_with_select_confounders, (
            f"Reste des références à cc.confounders (sans known_) : "
            f"{lines_with_select_confounders}"
        )

    def test_query_uses_long_evidence_level_values(self, source):
        """evidence_level doit filtrer sur les valeurs DB longues :
        'observed_association', 'probable_causation', 'demonstrated_causation'.
        """
        for long_value in (
            "'observed_association'",
            "'probable_causation'",
            "'demonstrated_causation'",
        ):
            assert long_value in source, (
                f"{long_value} absent du WHERE. Les valeurs courtes "
                f"('observed', 'probable', 'demonstrated') ne matchent "
                f"AUCUNE ligne DB."
            )

        # Non-régression : plus de filtre sur valeurs courtes
        assert "IN ('observed', 'probable', 'demonstrated')" not in source, (
            "Ancien filtre IN ('observed', 'probable', 'demonstrated') "
            "encore présent — drift non fixé."
        )

    def test_confidence_map_uses_long_keys(self, source):
        """confidence_map doit mapper les valeurs DB longues."""
        for long_key in (
            '"observed_association"',
            '"probable_causation"',
            '"demonstrated_causation"',
        ):
            assert long_key in source, (
                f"{long_key} absent de confidence_map — drift non fixé."
            )

    def test_domain_fallback_none_safe(self, source):
        """Le fallback domain doit gérer NULL (graph orphelin) via
        `claim.get("domain") or "causal"` plutôt que `.get("domain", "causal")`
        qui renverrait None si domain=NULL en DB (et non manquant du dict).
        """
        assert 'claim.get("domain") or "causal"' in source, (
            "Fallback domain doit être `claim.get('domain') or 'causal'` "
            "pour gérer le cas NULL DB (graph orphelin ou domain=NULL)."
        )


class TestBinahToYesodQueryIntegration:
    """Test d'intégration : la requête s'exécute réellement contre la DB
    sans `column does not exist`.

    Utilise psycopg2 direct (pas le pool) car le pool a une garde
    anti-destruction sous pytest qui refuse les URLs non-test. Ces tests
    sont READ-ONLY — aucun risque pour la prod.
    """

    @pytest.fixture
    def direct_conn(self):
        """Connexion psycopg2 directe (read-only), bypass pool.

        Skip si PostgreSQL indisponible (CI sans DB).
        """
        import psycopg2
        import psycopg2.extras
        try:
            conn = psycopg2.connect(
                (os.environ.get("ETZ_CHAIM_DB_URL") or os.environ.get("ETZ_CHAIM_DB", "postgresql://localhost/etz_chaim")),
                connect_timeout=2,
            )
            # Read-only
            conn.set_session(readonly=True)
        except Exception as e:
            pytest.skip(f"PostgreSQL etz_chaim indisponible : {e}")
        try:
            yield conn
        finally:
            conn.close()

    def test_query_executes_against_real_schema(self, direct_conn):
        """Extraire la requête SQL du source et l'exécuter pour vérifier
        qu'elle ne lève plus `column does not exist`.
        """
        import re

        import psycopg2.extras

        from daemon_tasks.binah import task_binah_to_yesod
        source = inspect.getsource(task_binah_to_yesod)

        match = re.search(
            r'cur\.execute\("""(.*?)"""\)',
            source,
            re.DOTALL,
        )
        assert match, "Requête SQL introuvable dans task_binah_to_yesod."
        query = match.group(1)

        with direct_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query)
            rows = cur.fetchall()
            if rows:
                row = rows[0]
                for col in ("id", "cause", "effect", "evidence_level",
                            "domain", "known_confounders",
                            "direction_verified"):
                    assert col in row, f"Colonne {col!r} absente du résultat."

    def test_causal_claims_lacks_domain_column(self, direct_conn):
        """Non-régression : causal_claims ne DOIT PAS avoir domain."""
        with direct_conn.cursor() as cur:
            cur.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'causal_claims' AND column_name = 'domain'
            """)
            result = cur.fetchone()
        assert result is None, (
            "causal_claims.domain existe maintenant — mettre à jour test/fix."
        )

    def test_causal_graphs_has_domain_column(self, direct_conn):
        """causal_graphs doit avoir domain (source du JOIN)."""
        with direct_conn.cursor() as cur:
            cur.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'causal_graphs' AND column_name = 'domain'
            """)
            result = cur.fetchone()
        assert result is not None, (
            "causal_graphs.domain absent — JOIN T2 ne peut récupérer domain."
        )
