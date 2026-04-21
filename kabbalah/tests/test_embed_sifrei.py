"""Tests for kabbalah.embed_sifrei — Embedding hybride Sifrei Yesod."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from kabbalah.hybrid_embedding import HYBRID_DIM, KABBALISTIC_DIM, ML_DIM, HybridVector


# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def mock_db():
    """Mock psycopg2 connection returning test concepts."""
    concepts = [
        {"id": 1, "concept_id": "igulim_as_heavens", "nom_he": "עיגולים כרקיעים",
         "nom_fr": None, "description": "Les Igulim comme cieux concentriques"},
        {"id": 2, "concept_id": "keli_nitkayem", "nom_he": "כלי",
         "nom_fr": None, "description": None},
        {"id": 3, "concept_id": "test_with_fr", "nom_he": "בדיקה",
         "nom_fr": "Test avec FR", "description": "Description existante"},
    ]

    mock_cursor = MagicMock()
    mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
    mock_cursor.__exit__ = MagicMock(return_value=False)
    mock_cursor.fetchall.return_value = concepts
    mock_cursor.close = MagicMock()

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.closed = False

    return mock_conn, concepts


@pytest.fixture
def embedder(mock_db):
    """SifreiYesodEmbedder with mocked DB connection."""
    from kabbalah.embed_sifrei import SifreiYesodEmbedder

    conn, _ = mock_db
    emb = SifreiYesodEmbedder.__new__(SifreiYesodEmbedder)
    emb.db_url = "postgresql://localhost/test"
    emb.batch_size = 50
    emb._conn = conn
    emb._he = None
    return emb


# ═══════════════════════════════════════════════════════════════
# _build_embed_text
# ═══════════════════════════════════════════════════════════════

class TestBuildEmbedText:
    """Test le texte construit pour l'embedding ML."""

    def test_uses_description_first(self, embedder):
        concept = {"description": "Les Igulim comme cieux", "nom_fr": "Igulim", "concept_id": "igulim", "nom_he": "עיגולים"}
        assert embedder._build_embed_text(concept) == "Les Igulim comme cieux"

    def test_uses_nom_fr_without_description(self, embedder):
        concept = {"description": None, "nom_fr": "Keli", "concept_id": "keli", "nom_he": "כלי"}
        text = embedder._build_embed_text(concept)
        assert "Keli" in text
        assert "כלי" in text

    def test_uses_concept_id_without_nom_fr(self, embedder):
        concept = {"description": None, "nom_fr": None, "concept_id": "igulim_as_heavens", "nom_he": "עיגולים"}
        text = embedder._build_embed_text(concept)
        assert "igulim as heavens" in text
        assert "עיגולים" in text

    def test_empty_concept(self, embedder):
        concept = {"description": None, "nom_fr": None, "concept_id": "", "nom_he": ""}
        text = embedder._build_embed_text(concept)
        assert "kabbalistique" in text


class TestConceptLabel:
    """Test la clé utilisée dans hybrid_embeddings.concept."""

    def test_prefers_nom_fr(self, embedder):
        concept = {"nom_fr": "Label FR", "concept_id": "cid"}
        assert embedder._concept_label(concept) == "Label FR"

    def test_falls_back_to_concept_id(self, embedder):
        concept = {"nom_fr": None, "concept_id": "my_concept"}
        assert embedder._concept_label(concept) == "my_concept"


# ═══════════════════════════════════════════════════════════════
# find_unembedded
# ═══════════════════════════════════════════════════════════════

class TestFindUnembedded:
    """Test la requête de concepts manquants."""

    def test_returns_list_of_dicts(self, embedder, mock_db):
        _, concepts = mock_db
        result = embedder.find_unembedded()
        assert isinstance(result, list)
        assert len(result) == len(concepts)
        for r in result:
            assert "concept_id" in r
            assert "nom_he" in r

    def test_query_uses_coalesce(self, embedder, mock_db):
        """Verify the SQL uses COALESCE(nom_fr, concept_id)."""
        embedder.find_unembedded()
        conn, _ = mock_db
        call_args = conn.cursor().execute.call_args
        sql = call_args[0][0]
        assert "COALESCE" in sql


# ═══════════════════════════════════════════════════════════════
# embed_concept
# ═══════════════════════════════════════════════════════════════

class TestEmbedConcept:
    """Test l'embedding d'un seul concept."""

    def test_embed_concept_produces_798d(self, embedder):
        """Embedding skip_ml produit un vecteur 798d (30+768 zeros pour ML)."""
        from kabbalah.hybrid_embedding import HybridEmbedding

        he = HybridEmbedding()
        embedder._he = he

        # Mock save_to_db to avoid real DB
        saved = []
        he.save_to_db = lambda vec: saved.append(vec)

        concept = {
            "concept_id": "test_concept",
            "nom_he": "בדיקה",
            "nom_fr": None,
            "description": "Test concept for embedding",
        }
        ok = embedder.embed_concept(concept)
        assert ok is True
        assert len(saved) == 1
        assert saved[0].hybrid.shape == (HYBRID_DIM,)
        assert saved[0].concept == "test_concept"
        assert saved[0].hebrew_word == "בדיקה"

    def test_embed_concept_with_nom_fr(self, embedder):
        """Concept with nom_fr uses it as label."""
        from kabbalah.hybrid_embedding import HybridEmbedding

        he = HybridEmbedding()
        embedder._he = he

        saved = []
        he.save_to_db = lambda vec: saved.append(vec)

        concept = {
            "concept_id": "cid",
            "nom_he": "בדיקה",
            "nom_fr": "Mon Label",
            "description": "Description",
        }
        ok = embedder.embed_concept(concept)
        assert ok is True
        assert saved[0].concept == "Mon Label"

    def test_embed_concept_retries_on_connection_error(self, embedder):
        """Retry on connection errors."""
        from kabbalah.hybrid_embedding import HybridEmbedding

        he = HybridEmbedding()
        embedder._he = he

        call_count = 0

        def flaky_save(vec):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("connection refused")

        he.save_to_db = flaky_save

        concept = {
            "concept_id": "retry_test",
            "nom_he": "ניסיון",
            "nom_fr": None,
            "description": "Retry test",
        }
        ok = embedder.embed_concept(concept, max_retries=3)
        assert ok is True
        assert call_count == 2

    def test_embed_concept_fails_on_non_retryable(self, embedder):
        """Non-retryable errors return False immediately."""
        from kabbalah.hybrid_embedding import HybridEmbedding

        he = HybridEmbedding()
        embedder._he = he
        he.save_to_db = MagicMock(side_effect=ValueError("bad data"))

        concept = {
            "concept_id": "fail_test",
            "nom_he": "כשלון",
            "nom_fr": None,
            "description": "Fail test",
        }
        ok = embedder.embed_concept(concept)
        assert ok is False


# ═══════════════════════════════════════════════════════════════
# embed_all_missing
# ═══════════════════════════════════════════════════════════════

class TestEmbedAllMissing:
    """Test du peuplement batch."""

    def test_dry_run_does_not_embed(self, embedder, mock_db):
        stats = embedder.embed_all_missing(dry_run=True)
        _, concepts = mock_db
        assert stats["found"] == len(concepts)
        assert stats["embedded"] == 0
        assert stats["errors"] == 0

    def test_embed_all_returns_stats(self, embedder, mock_db):
        """Full run returns correct stats."""
        from kabbalah.hybrid_embedding import HybridEmbedding

        he = HybridEmbedding()
        embedder._he = he
        he.save_to_db = MagicMock()

        stats = embedder.embed_all_missing()
        _, concepts = mock_db
        assert stats["found"] == len(concepts)
        assert stats["embedded"] == len(concepts)
        assert stats["errors"] == 0


# ═══════════════════════════════════════════════════════════════
# embed_new_since
# ═══════════════════════════════════════════════════════════════

class TestEmbedNewSince:
    """Test du pipeline incrémental par date."""

    def test_embed_new_since_filters_by_date(self, embedder):
        """embed_new_since passes datetime to SQL."""
        from kabbalah.hybrid_embedding import HybridEmbedding

        he = HybridEmbedding()
        embedder._he = he
        he.save_to_db = MagicMock()

        # Mock cursor for this specific query
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = [
            {"id": 99, "concept_id": "new_concept", "nom_he": "חדש",
             "nom_fr": None, "description": "New concept"},
        ]
        mock_cursor.close = MagicMock()
        embedder.conn.cursor.return_value = mock_cursor

        since = datetime(2026, 4, 1, tzinfo=timezone.utc)
        stats = embedder.embed_new_since(since)
        assert stats["found"] == 1
        assert stats["embedded"] == 1

        # Check SQL was called with the datetime
        call_args = mock_cursor.execute.call_args
        assert since in call_args[0][1]


# ═══════════════════════════════════════════════════════════════
# embed_new_concepts (pipeline incrémental)
# ═══════════════════════════════════════════════════════════════

class TestEmbedNewConcepts:
    """Test du point d'entrée daemon."""

    def test_returns_zero_when_nothing_to_do(self, embedder, mock_db):
        """No unembedded concepts → zero counts."""
        conn, _ = mock_db
        # Override cursor to return empty
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = []
        mock_cursor.close = MagicMock()
        conn.cursor.return_value = mock_cursor

        stats = embedder.embed_new_concepts()
        assert stats["embedded"] == 0
        assert stats["errors"] == 0

    def test_embeds_all_found(self, embedder, mock_db):
        """embed_new_concepts embeds all found concepts."""
        from kabbalah.hybrid_embedding import HybridEmbedding

        he = HybridEmbedding()
        embedder._he = he
        he.save_to_db = MagicMock()

        stats = embedder.embed_new_concepts()
        _, concepts = mock_db
        assert stats["embedded"] == len(concepts)
        assert stats["sources"]["sifrei_yesod"] == len(concepts)


# ═══════════════════════════════════════════════════════════════
# Kabbalistic signature quality for Sifrei Yesod concepts
# ═══════════════════════════════════════════════════════════════

class TestSifreiSignatureQuality:
    """Verify kabbalistic signature is meaningful for Sifrei Yesod Hebrew words."""

    def test_hebrew_word_produces_nonzero_sig(self):
        """Typical Sifrei Yesod Hebrew words produce non-zero signatures."""
        from kabbalah.hybrid_embedding import KabbalisticSignature

        sig = KabbalisticSignature()
        # Words from the 1003 missing concepts
        test_words = [
            ("עיגולים כרקיעים", "igulim_as_heavens"),
            ("כלי", "keli_nitkayem"),
            ("מוח נשמה", "moah_neshamah"),
            ("אופנים", "ofanim"),
        ]
        for hebrew, cid in test_words:
            result = sig.compute_signature(cid, hebrew_word=hebrew)
            assert np.any(result != 0), f"Signature zero for {cid} ({hebrew})"
            assert result.shape == (KABBALISTIC_DIM,)

    def test_different_hebrew_words_different_sigs(self):
        """Different Hebrew words produce different signatures."""
        from kabbalah.hybrid_embedding import KabbalisticSignature

        sig = KabbalisticSignature()
        s1 = sig.compute_signature("a", hebrew_word="עיגולים")
        s2 = sig.compute_signature("b", hebrew_word="אופנים")
        assert not np.allclose(s1, s2)
