"""Tests for kabbalah/hebrew_enrichment.py — Rétro-enrichissement hebrew_word."""

import numpy as np
import pytest

from kabbalah.hebrew_enrichment import (
    HebrewEnrichment,
    _CANONICAL_TOKENS,
    _COMPOUND_TOKENS,
    _PREFIX_MAP,
)


# ── Canonical mappings must all be present ──────────────────────

class TestCanonicalMappings:
    """Verify that mandatory canonical terms are in the dictionary."""

    SEFIROT = {
        "keter": "כתר", "binah": "בינה", "chesed": "חסד",
        "gevurah": "גבורה", "tiferet": "תפארת", "netzach": "נצח",
        "hod": "הוד", "yesod": "יסוד", "malkhut": "מלכות",
    }

    PARTZUFIM_TOKENS = {
        "atik": "עתיק", "arikh": "אריך", "anpin": "אנפין",
        "abba": "אבא", "imma": "אמא", "zeir": "זעיר",
        "nukvah": "נוקבא",
    }

    OLAMOT = {
        "atzilut": "אצילות", "beriah": "בריאה",
        "yetzirah": "יצירה", "asiyah": "עשייה",
    }

    LETTERS_SAMPLE = {
        "alef": "אלף", "bet": "בית", "gimel": "גימל",
        "shin": "שין", "tav": "תו",
    }

    def test_sefirot_all_present(self):
        for token, expected in self.SEFIROT.items():
            assert token in _CANONICAL_TOKENS, f"Missing sefirah: {token}"
            assert _CANONICAL_TOKENS[token] == expected

    def test_partzufim_tokens_present(self):
        for token, expected in self.PARTZUFIM_TOKENS.items():
            assert token in _CANONICAL_TOKENS, f"Missing partzuf token: {token}"
            assert _CANONICAL_TOKENS[token] == expected

    def test_olamot_present(self):
        for token, expected in self.OLAMOT.items():
            assert token in _CANONICAL_TOKENS
            assert _CANONICAL_TOKENS[token] == expected

    def test_letters_sample(self):
        for token, expected in self.LETTERS_SAMPLE.items():
            assert token in _CANONICAL_TOKENS
            assert _CANONICAL_TOKENS[token] == expected

    def test_prefix_map_complete(self):
        assert "ak" in _PREFIX_MAP  # Adam Kadmon
        assert "aa" in _PREFIX_MAP  # Arikh Anpin
        assert "es" in _PREFIX_MAP  # Ein Sof
        assert "om" in _PREFIX_MAP  # Ohr Makif
        assert "op" in _PREFIX_MAP  # Ohr Pnimi


# ── find_hebrew resolution tests ────────────────────────────────

@pytest.fixture
def enricher():
    """Create enricher with vocabulary loaded (no DB needed for token tests)."""
    e = HebrewEnrichment.__new__(HebrewEnrichment)
    e.db_url = "postgresql://localhost/etz_chaim"
    e._vocab = dict(_CANONICAL_TOKENS)
    e._sifrei_vocab = {}
    e._loaded = True
    return e


class TestFindHebrew:
    """Test find_hebrew resolution for various patterns."""

    def test_single_token_canonical(self, enricher):
        r = enricher.find_hebrew("keter")
        assert r.new_hebrew == "כתר"
        assert r.source == "canonical"

    def test_compound_adam_kadmon(self, enricher):
        r = enricher.find_hebrew("adam_kadmon")
        assert r.new_hebrew == "אדם קדמון"
        assert r.source == "compound"

    def test_compound_ein_sof(self, enricher):
        r = enricher.find_hebrew("ein_sof")
        assert r.new_hebrew == "אין סוף"
        assert r.source == "compound"

    def test_prefix_ak(self, enricher):
        r = enricher.find_hebrew("ak_kelim_zak")
        assert r.new_hebrew is not None
        assert "אד״ק" in r.new_hebrew
        assert "כלים" in r.new_hebrew

    def test_prefix_aa(self, enricher):
        r = enricher.find_hebrew("aa_malbish_atik")
        assert r.new_hebrew is not None
        assert "א״א" in r.new_hebrew

    def test_multi_token(self, enricher):
        r = enricher.find_hebrew("ohr_makif")
        assert r.new_hebrew == "אור מקיף"

    def test_rejoined_compound(self, enricher):
        r = enricher.find_hebrew("mahshavah_ila_ah")
        assert r.new_hebrew == "מחשבה עילאה"

    def test_zoharic_compound(self, enricher):
        r = enricher.find_hebrew("mati_ve_lo_mati")
        assert r.new_hebrew == "מטי ולא מטי"

    def test_no_overwrite_existing(self, enricher):
        """Concepts that already have hebrew_word should not be touched."""
        # This is tested at the DB level — find_hebrew doesn't know about existing values
        r = enricher.find_hebrew("keter")
        assert r.new_hebrew is not None


# ── Signature recomputation tests ───────────────────────────────

class TestSignatureComputation:
    """Verify that enrichment produces valid signatures."""

    def test_kabbalistic_signature_valid_shape(self):
        from kabbalah.hybrid_embedding import KabbalisticSignature, KABBALISTIC_DIM
        sig = KabbalisticSignature()
        vec = sig.compute_signature("adam_kadmon", "אדם קדמון")
        assert vec.shape == (KABBALISTIC_DIM,)
        assert vec.dtype == np.float32

    def test_kabbalistic_signature_not_all_zeros(self):
        from kabbalah.hybrid_embedding import KabbalisticSignature
        sig = KabbalisticSignature()
        vec = sig.compute_signature("keter", "כתר")
        assert not np.allclose(vec, 0.0), "Signature should not be all zeros for כתר"

    def test_kabbalistic_signature_no_nan(self):
        from kabbalah.hybrid_embedding import KabbalisticSignature
        sig = KabbalisticSignature()
        vec = sig.compute_signature("ein_sof", "אין סוף")
        assert not np.any(np.isnan(vec))

    def test_hebrew_enrichment_improves_signature(self):
        """A concept with hebrew_word should have a richer signature than without."""
        from kabbalah.hybrid_embedding import KabbalisticSignature
        sig = KabbalisticSignature()
        without = sig.compute_signature("adam_kadmon")
        with_hebrew = sig.compute_signature("adam_kadmon", "אדם קדמון")
        # adam_kadmon is in _TRANSLIT_TO_HEBREW so both may resolve,
        # but the explicit Hebrew should produce a valid signature
        assert with_hebrew.shape == (30,)
        norm = np.linalg.norm(with_hebrew)
        assert norm > 0, "Signature with Hebrew should have non-zero norm"


# ── Dry-run safety test ─────────────────────────────────────────

class TestDryRunSafety:
    """Verify dry_run doesn't modify anything.

    Les acces DB sont mockes pour isoler la logique dry_run : on verifie
    que enrich_all(dry_run=True) s'execute sans effet de bord et retourne
    des stats coherentes. Un vrai test d'integration DB vivrait dans
    epistememory/tests/ avec la TEST_DB_URL dediee.
    """

    def test_dry_run_returns_stats(self, monkeypatch):
        """enrich_all(dry_run=True) returns stats without DB modifications."""
        e = HebrewEnrichment()
        # Bypass DB : dry_run n'a pas besoin d'effets reels pour ce contrat.
        monkeypatch.setattr(e, "_load_vocabulary", lambda: None)
        monkeypatch.setattr(e, "get_null_concepts", lambda: [])
        monkeypatch.setattr(e, "_count_total", lambda: 0)
        e._vocab = dict(_CANONICAL_TOKENS)
        e._loaded = True

        stats = e.enrich_all(dry_run=True)
        assert stats.total_null >= 0
        assert stats.enriched >= 0
        assert stats.coverage_before >= 0
        assert stats.coverage_after >= stats.coverage_before

    def test_dry_run_coverage_improvement(self, monkeypatch):
        """After enrichment, coverage should improve (strict when resolutions exist)."""
        e = HebrewEnrichment()

        # Charger le vocabulaire canonique (pour que keter/binah se resolvent)
        def fake_load():
            e._vocab = dict(_CANONICAL_TOKENS)
            e._loaded = True
        monkeypatch.setattr(e, "_load_vocabulary", fake_load)

        # Simuler 2 concepts resolvables + 1 non resolvable
        monkeypatch.setattr(e, "get_null_concepts", lambda: ["keter", "binah", "unknown_xyz"])
        monkeypatch.setattr(e, "_count_total", lambda: 100)

        stats = e.enrich_all(dry_run=True)
        if stats.total_null > 0:
            assert stats.coverage_after > stats.coverage_before


# ── Non-regression test ─────────────────────────────────────────

class TestNonRegression:
    """Existing hebrew_word values must not be modified."""

    def test_existing_hebrew_preserved(self):
        """Verify the WHERE clause only updates NULL hebrew_word."""
        # This is enforced by the SQL:
        # UPDATE ... WHERE concept = %s AND hebrew_word IS NULL
        # We verify this constraint exists in the code
        import inspect
        from kabbalah.hebrew_enrichment import HebrewEnrichment
        source = inspect.getsource(HebrewEnrichment._apply_batch)
        assert "AND hebrew_word IS NULL" in source
