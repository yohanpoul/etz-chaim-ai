"""Sprint 5.6 — task_validate_orphan_candidates.

Ferme la boucle Chokmah → Binah → Da'at : aucune candidate hitbonenut
ne reste orpheline en ``status='pending'``. Retro-patch
``connects_domains`` si vide, puis exerce
``InsightValidator.validate`` (Sprint 5.2/5.3) et met à jour le statut.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest

from daemon_tasks.orphan_validation import (
    ORPHAN_BATCH_LIMIT,
    _infer_connects_domains,
    task_validate_orphan_candidates,
)
from insightforge.models import CandidateInsight, InsightValidation


# --- Helpers ----------------------------------------------------------------


def _insert_candidate(
    db,
    *,
    description: str = "Q: Test ?\nA: # Synthèse — Un claim causal substantiel qui dépasse trente caractères.",
    source_module: str = "hitbonenut",
    domain: str = "physics",
    connects_domains: list[str] | None = None,
    status: str = "pending",
) -> CandidateInsight:
    """Insérer une candidate directement en DB sans transit par InsightForge."""
    candidate = CandidateInsight(
        description=description,
        source_module=source_module,
        domain=domain,
        connects_domains=connects_domains if connects_domains is not None else [],
        status=status,
        novelty_score=0.5,
        confidence=0.5,
    )
    candidate = db.save_candidate(candidate)
    return candidate


def _fetch(db, cid):
    """Re-lire la candidate depuis la DB après la task (raw SQL)."""
    import psycopg2.extras

    from insightforge.db import _row_to_candidate
    with db._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT * FROM candidate_insights WHERE id = %s", (cid,))
        row = cur.fetchone()
        return _row_to_candidate(row) if row else None


# --- Tests ------------------------------------------------------------------


def test_scan_targets_hitbonenut_only(db):
    """Test 1 — scan ne traite que ``source_module='hitbonenut'``.

    Autres sources restent intactes en pending.
    """
    hitbo_candidates = [
        _insert_candidate(db, source_module="hitbonenut", domain=f"d{i}")
        for i in range(3)
    ]
    other_candidates = [
        _insert_candidate(db, source_module="autojudge", domain="x"),
        _insert_candidate(db, source_module="chesed", domain="y"),
    ]

    validator = _mock_validator(is_valid=True)
    report = task_validate_orphan_candidates(db=db, validator=validator)

    assert report["scanned"] == 3  # hitbonenut uniquement
    assert report["processed"] == 3

    # Les autres sources inchangées
    for c in other_candidates:
        refreshed = _fetch(db, c.id)
        assert refreshed.status == "pending", (
            f"{c.source_module} candidate muted by orphan task"
        )


def test_retropatch_empty_connects_domains(db):
    """Test 2 — ``connects_domains=[]`` retro-patché avec [domain, "hitbonenut"]."""
    candidate = _insert_candidate(
        db,
        domain="kabbalah_lurianique",
        connects_domains=[],
    )

    validator = _mock_validator(is_valid=True)
    task_validate_orphan_candidates(db=db, validator=validator)

    refreshed = _fetch(db, candidate.id)
    assert refreshed is not None
    assert "kabbalah_lurianique" in refreshed.connects_domains
    assert "hitbonenut" in refreshed.connects_domains


def test_retropatch_crossdomain_colon_split(db):
    """Test 2b — domain ``"olamot:biologie_evo"`` split en deux domains."""
    candidate = _insert_candidate(
        db,
        domain="olamot:biologie_evo",
        connects_domains=[],
    )

    validator = _mock_validator(is_valid=True)
    task_validate_orphan_candidates(db=db, validator=validator)

    refreshed = _fetch(db, candidate.id)
    assert "olamot" in refreshed.connects_domains
    assert "biologie_evo" in refreshed.connects_domains
    assert "hitbonenut" in refreshed.connects_domains


def test_preserve_existing_connects_domains(db):
    """Test 3 — ``connects_domains`` non vide préservé tel quel."""
    candidate = _insert_candidate(
        db,
        domain="physics",
        connects_domains=["kabbalah", "hitbonenut"],
    )

    validator = _mock_validator(is_valid=True)
    task_validate_orphan_candidates(db=db, validator=validator)

    refreshed = _fetch(db, candidate.id)
    # Préservation : aucun élément ajouté, aucun retiré
    assert sorted(refreshed.connects_domains) == sorted(["kabbalah", "hitbonenut"])


def test_validation_success_updates_to_insight(db):
    """Test 4 — ``is_valid=True`` → ``status='insight'`` + flags triple."""
    candidate = _insert_candidate(db, domain="physics", connects_domains=[])

    validator = _mock_validator(is_valid=True)
    task_validate_orphan_candidates(db=db, validator=validator)

    refreshed = _fetch(db, candidate.id)
    assert refreshed.status == "insight"
    assert refreshed.binah_validated is True
    assert refreshed.gevurah_validated is True
    assert refreshed.daat_validated is True
    assert refreshed.rejection_reason in ("", None)


def test_validation_failure_updates_to_rejected(db):
    """Test 5 — ``is_valid=False`` → ``status='rejected'`` + reason populée."""
    candidate = _insert_candidate(db, domain="physics", connects_domains=[])

    validator = _mock_validator(
        is_valid=False,
        binah_ok=False,
        binah_detail="question_deferred (not a causal claim)",
        gevurah_ok=True,
        daat_ok=True,
    )
    task_validate_orphan_candidates(db=db, validator=validator)

    refreshed = _fetch(db, candidate.id)
    assert refreshed.status == "rejected"
    assert refreshed.rejection_reason
    assert "Binah" in refreshed.rejection_reason
    assert "question_deferred" in refreshed.rejection_reason


def test_batch_limit_enforced(db):
    """Test 6 — au-delà de ``ORPHAN_BATCH_LIMIT``, le reste est ignoré."""
    total = ORPHAN_BATCH_LIMIT + 7
    for i in range(total):
        _insert_candidate(db, domain=f"d{i}", connects_domains=[])

    validator = _mock_validator(is_valid=True)
    report = task_validate_orphan_candidates(db=db, validator=validator)

    assert report["scanned"] == ORPHAN_BATCH_LIMIT
    assert report["processed"] == ORPHAN_BATCH_LIMIT
    assert report["skipped_over_limit"] == 7


def test_exception_continues_batch(db):
    """Test 7 — si validator lève, la task log WARNING et continue."""
    candidates = [
        _insert_candidate(db, domain=f"d{i}", connects_domains=[])
        for i in range(3)
    ]

    validator = MagicMock()
    # 1er crash, les 2 suivants OK
    validator.validate.side_effect = [
        RuntimeError("binah instanciation échouée"),
        InsightValidation(is_valid=True, binah_ok=True, gevurah_ok=True,
                          daat_ok=True, confidence=0.7),
        InsightValidation(is_valid=True, binah_ok=True, gevurah_ok=True,
                          daat_ok=True, confidence=0.7),
    ]

    report = task_validate_orphan_candidates(db=db, validator=validator)

    assert report["processed"] == 2  # 2 succès
    assert report["errors"] == 1
    # Les 2 candidates qui ont passé le validator sont maintenant insight
    non_errored = [
        c for c in candidates
        if _fetch(db, c.id).status == "insight"
    ]
    assert len(non_errored) == 2


def test_infer_connects_domains_handles_formats():
    """Test helper — ``_infer_connects_domains`` couvre mono, cross, vide."""
    assert sorted(_infer_connects_domains("physics")) == ["hitbonenut", "physics"]
    assert sorted(_infer_connects_domains("olamot:biologie_evo")) == (
        sorted(["olamot", "biologie_evo", "hitbonenut"])
    )
    # Doublons éliminés
    assert _infer_connects_domains("hitbonenut") == ["hitbonenut"]
    # Vide → hitbonenut seul
    assert _infer_connects_domains("") == ["hitbonenut"]
    assert _infer_connects_domains(None) == ["hitbonenut"]


# --- Validator stub helper --------------------------------------------------


def _mock_validator(
    *,
    is_valid: bool = True,
    binah_ok: bool | None = None,
    binah_detail: str = "Causal check passed",
    gevurah_ok: bool | None = None,
    gevurah_detail: str = "Quality check passed",
    daat_ok: bool | None = None,
    daat_detail: str = "No error predicted",
    confidence: float = 0.7,
):
    """Construire un mock validator qui retourne une InsightValidation fixe."""
    if binah_ok is None:
        binah_ok = is_valid
    if gevurah_ok is None:
        gevurah_ok = is_valid
    if daat_ok is None:
        daat_ok = is_valid
    result = InsightValidation(
        is_valid=is_valid,
        binah_ok=binah_ok,
        gevurah_ok=gevurah_ok,
        daat_ok=daat_ok,
        binah_detail=binah_detail,
        gevurah_detail=gevurah_detail,
        daat_detail=daat_detail,
        confidence=confidence,
    )
    mock = MagicMock()
    mock.validate = MagicMock(return_value=result)
    return mock
