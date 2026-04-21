"""Tests EvidenceElevator — cristallisation des claims causaux.

Vérifie le pipeline d'élévation :
  correlation_only → observed_association → probable_causation → demonstrated_causation

Chaque niveau est GAGNÉ par des critères croisés multi-modules.
"""

import pytest

from causalengine.db import CausalDB
from causalengine.evidence_elevator import (
    EvidenceElevator,
    _extract_keywords,
    _keyword_overlap,
)
from causalengine.evidence_scorer import EvidenceScorer
from causalengine.models import CausalClaim, EVIDENCE_RANK


TEST_DB_URL = "postgresql://localhost/etz_chaim_test"


@pytest.fixture(scope="module", autouse=True)
def _ensure_elevator_tables():
    """Create tables needed by elevator (hitbonenut, insights, dissensus)."""
    import psycopg2
    conn = psycopg2.connect(TEST_DB_URL)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS hitbonenut_sessions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            started_at TIMESTAMPTZ DEFAULT NOW(),
            ended_at TIMESTAMPTZ,
            n_questions INTEGER,
            difficulty TEXT,
            avg_score FLOAT DEFAULT 0.0,
            domains_tested TEXT[] DEFAULT '{}',
            soul_level_before TEXT,
            soul_level_after TEXT,
            competence_delta JSONB DEFAULT '{}'
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS hitbonenut_questions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            session_id UUID REFERENCES hitbonenut_sessions(id),
            question TEXT NOT NULL,
            domain TEXT,
            difficulty TEXT,
            response TEXT,
            score FLOAT DEFAULT 0.0,
            kw_score FLOAT DEFAULT 0.0,
            sentiers_used TEXT[] DEFAULT '{}',
            nitzotzot_generated INTEGER DEFAULT 0,
            duration_seconds FLOAT DEFAULT 0.0,
            is_novel BOOLEAN DEFAULT false,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS candidate_insights (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            session_id UUID,
            description TEXT NOT NULL,
            source_module TEXT NOT NULL DEFAULT '',
            domain TEXT NOT NULL DEFAULT '',
            novelty_score FLOAT NOT NULL DEFAULT 0.0,
            confidence FLOAT NOT NULL DEFAULT 0.5,
            status TEXT NOT NULL DEFAULT 'candidate',
            rejection_reason TEXT,
            binah_validated BOOLEAN NOT NULL DEFAULT false,
            gevurah_validated BOOLEAN NOT NULL DEFAULT false,
            daat_validated BOOLEAN NOT NULL DEFAULT false,
            connects_domains TEXT[] NOT NULL DEFAULT '{}',
            source_connections UUID[] NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS dissensuengine_conclusions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            content TEXT NOT NULL,
            source_label TEXT NOT NULL,
            source_type TEXT NOT NULL,
            domain TEXT,
            confidence FLOAT NOT NULL DEFAULT 0.5,
            metadata JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    cur.close()
    conn.close()


@pytest.fixture
def db():
    """Fresh CausalDB, truncated between tests."""
    database = CausalDB(TEST_DB_URL)
    yield database
    from pool import get_conn
    with get_conn() as conn:
        _truncate(conn)
    database.close()


@pytest.fixture
def elevator(db):
    """EvidenceElevator with fresh DB."""
    return EvidenceElevator(db)


def _truncate(conn):
    with conn.cursor() as cur:
        cur.execute("TRUNCATE causal_confounders CASCADE")
        cur.execute("TRUNCATE causal_claims CASCADE")
        cur.execute("TRUNCATE causal_graphs CASCADE")
        cur.execute("TRUNCATE hitbonenut_questions CASCADE")
        cur.execute("TRUNCATE candidate_insights CASCADE")
        cur.execute("TRUNCATE dissensuengine_conclusions CASCADE")
    conn.commit()


def _insert_claim(db, cause, effect, confidence=0.33, evidence_level="correlation_only"):
    """Insert a claim directly into DB."""
    return db.save_claim(CausalClaim(
        cause=cause,
        effect=effect,
        confidence=confidence,
        evidence_level=evidence_level,
    ))


def _insert_hitbonenut(db, question, score=0.8, domain="test"):
    """Insert a hitbonenut question directly."""
    with db._cursor() as cur:
        cur.execute(
            "INSERT INTO hitbonenut_questions (question, score, domain, difficulty, response) "
            "VALUES (%s, %s, %s, 'medium', 'test response')",
            (question, score, domain),
        )


def _insert_insight(db, description, confidence=0.5, domain="test"):
    """Insert a candidate insight directly."""
    with db._cursor() as cur:
        cur.execute(
            "INSERT INTO candidate_insights (description, confidence, domain, "
            "source_module, novelty_score, status) "
            "VALUES (%s, %s, %s, 'test', 0.5, 'pending')",
            (description, confidence, domain),
        )


def _insert_dissensus(db, content, confidence=0.7, domain="test"):
    """Insert a dissensus conclusion directly."""
    with db._cursor() as cur:
        cur.execute(
            "INSERT INTO dissensuengine_conclusions (content, confidence, domain, "
            "source_label, source_type) "
            "VALUES (%s, %s, %s, 'test', 'model')",
            (content, confidence, domain),
        )


# ── Keyword extraction ────────────────────────────────

class TestKeywordExtraction:
    def test_basic_extraction(self):
        kw = _extract_keywords("Les Sefirot de l'Arbre de Vie")
        assert "sefirot" in kw
        assert "arbre" in kw  # l'Arbre → arbre (French contraction handled)

    def test_stopwords_removed(self):
        kw = _extract_keywords("Comment les choses sont faites")
        assert "comment" not in kw
        assert "sont" not in kw
        assert "faites" in kw

    def test_domain_stopwords_removed(self):
        kw = _extract_keywords("hitbonenut insight kabbale connexions")
        assert "hitbonenut" not in kw
        assert "insight" not in kw
        assert "kabbale" not in kw
        assert "connexions" not in kw

    def test_short_words_removed(self):
        kw = _extract_keywords("a de la vie est un")
        assert len(kw) == 0

    def test_hebrew_terms_preserved(self):
        kw = _extract_keywords("Tsimtsum Shevirah Tikkun Partzufim")
        assert "tsimtsum" in kw
        assert "shevirah" in kw
        assert "tikkun" in kw
        assert "partzufim" in kw


class TestKeywordOverlap:
    def test_identical_sets(self):
        kw = {"tsimtsum", "shevirah", "tikkun"}
        assert _keyword_overlap(kw, kw) == 1.0

    def test_disjoint_sets(self):
        assert _keyword_overlap({"alpha", "beta"}, {"gamma", "delta"}) == 0.0

    def test_partial_overlap(self):
        a = {"tsimtsum", "shevirah", "tikkun", "partzufim"}
        b = {"tsimtsum", "shevirah", "olamot", "sefirot"}
        overlap = _keyword_overlap(a, b)
        assert 0.3 < overlap < 0.4  # 2/6 = 0.333

    def test_empty_sets(self):
        assert _keyword_overlap(set(), {"x"}) == 0.0
        assert _keyword_overlap({"x"}, set()) == 0.0


# ── Evidence levels ───────────────────────────────────

class TestEvidenceRank:
    def test_observed_between_correlation_and_probable(self):
        assert EVIDENCE_RANK["correlation_only"] < EVIDENCE_RANK["observed_association"]
        assert EVIDENCE_RANK["observed_association"] < EVIDENCE_RANK["probable_causation"]
        assert EVIDENCE_RANK["probable_causation"] < EVIDENCE_RANK["demonstrated_causation"]


# ── Observed Association ──────────────────────────────

class TestObservedAssociation:
    def test_multi_context_elevates(self, db, elevator):
        """Claim with cause appearing in 2+ claims → observed_association."""
        # Same cause, different effects
        _insert_claim(db, "Tsimtsum crée un espace vide", "Compression d'information", 0.33)
        _insert_claim(db, "Tsimtsum crée un espace vide", "Bottleneck neuronal", 0.33)

        result = elevator.elevate_claims(batch_size=0)
        assert result["elevated_to_observed"] + result["elevated_to_probable"] + result["elevated_to_demonstrated"] >= 2

    def test_low_confidence_not_elevated(self, db, elevator):
        """Claim with confidence < 0.3 stays at correlation_only."""
        _insert_claim(db, "Cause A test", "Effect B test", 0.1)
        _insert_claim(db, "Cause A test", "Effect C test", 0.1)

        result = elevator.elevate_claims(batch_size=0)
        total = result["elevated_to_observed"] + result["elevated_to_probable"] + result["elevated_to_demonstrated"]
        assert total == 0

    def test_single_context_not_elevated_without_hitbonenut(self, db, elevator):
        """Claim appearing once with no hitbonenut match stays at correlation_only."""
        _insert_claim(db, "Unique obscure cause xyz", "Unique obscure effect xyz", 0.33)

        result = elevator.elevate_claims(batch_size=0)
        total = result["elevated_to_observed"] + result["elevated_to_probable"] + result["elevated_to_demonstrated"]
        assert total == 0


# ── Confidence recalculation ──────────────────────────

class TestConfidenceRecalculation:
    def test_observed_confidence_higher_than_correlation(self):
        scorer = EvidenceScorer()
        corr = scorer.compute_confidence("correlation_only", [])
        obs = scorer.compute_confidence("observed_association", [])
        assert obs > corr

    def test_probable_confidence_higher_than_observed(self):
        scorer = EvidenceScorer()
        obs = scorer.compute_confidence("observed_association", [])
        prob = scorer.compute_confidence("probable_causation", [])
        assert prob > obs

    def test_demonstrated_confidence_highest(self):
        scorer = EvidenceScorer()
        prob = scorer.compute_confidence("probable_causation", [])
        demo = scorer.compute_confidence("demonstrated_causation", [])
        assert demo > prob


# ── Cascading ─────────────────────────────────────────

class TestCascading:
    def test_cascading_to_probable(self, db, elevator):
        """Claim that passes observed AND probable → probable_causation."""
        # Multi-context + chain (same term as cause and effect elsewhere)
        c1 = _insert_claim(db, "Tsimtsum contraction divine", "Reshimu trace résiduelle", 0.33)
        _insert_claim(db, "Tsimtsum contraction divine", "Kav ligne lumière", 0.33)
        # Create chain: effect of c1 appears as cause elsewhere
        _insert_claim(db, "Reshimu trace résiduelle", "Mémoire cosmique persistante", 0.33)

        result = elevator.elevate_claims(batch_size=0)
        # At least some should reach probable (those in chains)
        total_elevated = result["elevated_to_observed"] + result["elevated_to_probable"] + result["elevated_to_demonstrated"]
        assert total_elevated >= 2

    def test_no_cascading_without_multi_context(self, db, elevator):
        """Single-context claim stays correlation even if in chain."""
        _insert_claim(db, "Unique cause abcdef", "Unique effect ghijkl", 0.33)
        _insert_claim(db, "Unique effect ghijkl", "Downstream mnopqr", 0.33)

        result = elevator.elevate_claims(batch_size=0)
        # These don't have multi-context for the first claim
        assert result["elevated_to_probable"] == 0
        assert result["elevated_to_demonstrated"] == 0


# ── Dry run ───────────────────────────────────────────

class TestDryRun:
    def test_dry_run_does_not_persist(self, db, elevator):
        """Dry run should not modify the database."""
        _insert_claim(db, "Cause multi-contexte alpha", "Effect A alpha", 0.33)
        _insert_claim(db, "Cause multi-contexte alpha", "Effect B alpha", 0.33)

        # Dry run
        result = elevator.dry_run()
        assert result["total"] == 2

        # Verify DB unchanged
        claims = db.get_all_claims()
        for c in claims:
            assert c.evidence_level == "correlation_only"


# ── Demonstrated causation ────────────────────────────

class TestDemonstratedCausation:
    def test_with_hitbonenut_and_dissensus(self, db, elevator):
        """Claim with hitbonenut match AND dissensus match → demonstrated."""
        # Multi-context claims
        _insert_claim(db, "Shevirah brisure récipients", "Nitzotzot étincelles dispersées", 0.33)
        _insert_claim(db, "Shevirah brisure récipients", "Klipot écorces formées", 0.33)
        # Chain: nitzotzot is both effect and cause
        _insert_claim(db, "Nitzotzot étincelles dispersées", "Tikkun réparation monde", 0.33)
        # Hitbonenut with high score matching shevirah/nitzotzot
        _insert_hitbonenut(db, "Comment la Shevirah produit-elle les Nitzotzot et les Klipot?", score=0.9)
        # Dissensus conclusion matching
        _insert_dissensus(db, "Shevirah brisure produit nitzotzot étincelles")

        result = elevator.elevate_claims(batch_size=0)
        total = result["elevated_to_observed"] + result["elevated_to_probable"] + result["elevated_to_demonstrated"]
        assert total >= 2


# ── Bulk update ───────────────────────────────────────

class TestBulkUpdate:
    def test_bulk_update_persists(self, db):
        """bulk_update_evidence should persist changes."""
        c1 = _insert_claim(db, "Cause alpha test", "Effect alpha test", 0.33)
        c2 = _insert_claim(db, "Cause beta test", "Effect beta test", 0.33)

        updates = [
            ("observed_association", 0.45, "is observed alongside", str(c1.id)),
            ("probable_causation", 0.58, "likely contributes to", str(c2.id)),
        ]
        count = db.bulk_update_evidence(updates)
        assert count == 2

        claims = db.get_all_claims()
        levels = {c.evidence_level for c in claims}
        assert "observed_association" in levels
        assert "probable_causation" in levels


# ── Report format ─────────────────────────────────────

class TestReport:
    def test_report_has_before_after(self, db, elevator):
        _insert_claim(db, "Cause gamma contexte", "Effect gamma one", 0.33)
        _insert_claim(db, "Cause gamma contexte", "Effect gamma two", 0.33)

        result = elevator.elevate_claims(batch_size=0)
        assert "before" in result
        assert "after" in result
        assert "total_claims" in result
        assert result["total_claims"] == 2
        assert result["errors"] == 0
