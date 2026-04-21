"""daemon_tasks/orphan_validation.py — Sprint 5.6.

``task_validate_orphan_candidates`` ferme la boucle Chokmah → Binah → Da'at :
aucune candidate hitbonenut ne reste orpheline en ``status='pending'``
éternellement.

Workflow
--------

1. Scan ``candidate_insights WHERE status='pending' AND source_module='hitbonenut'``
   (LIMIT ``ORPHAN_BATCH_LIMIT``).
2. Pour chaque candidate :

   a. Retro-patch ``connects_domains`` si vide : pose
      ``[*domain_split_colon, "hitbonenut"]`` (ex. ``"olamot:biologie_evo"``
      → ``["olamot", "biologie_evo", "hitbonenut"]``). Ce fix lève le
      blocage Sprint 5.5 (Gevurah ``_local_quality_check`` rejetait sur
      ``"no connected domains"`` les candidates créées avant le patch).

   b. Appelle ``InsightValidator.validate(candidate)`` — exerce
      Sprint 5.2 (em-dash) et Sprint 5.3 (format Q/A) pour extraire la
      synthèse et la soumettre à Binah au lieu de déférer sur la forme
      interrogative.

   c. Met à jour la DB :

      - ``is_valid=True`` → ``status='insight'``, flags triple à True
      - ``is_valid=False`` → ``status='rejected'`` + ``rejection_reason``
        consolidée depuis les détails des 3 gates.

3. Logge un récapitulatif : N scannés / M traités / X validés / Y rejetés
   / Z erreurs.

Scope Sprint 5.6
----------------

- **Uniquement** ``source_module='hitbonenut'`` (les autres sources
  transitent par ``InsightForge.forge()`` et sont déjà validées).
- Batch limit : ``ORPHAN_BATCH_LIMIT = 50`` par invocation (évite
  de bloquer le daemon si 1000 pending).
- Gevurah laissé à ``None`` : ``_check_gevurah`` applique toujours le
  ``_local_quality_check`` interne — pas besoin d'instance AutoJudge.
"""
from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from insightforge.db import InsightDB
    from insightforge.insight_validator import InsightValidator
    from insightforge.models import CandidateInsight


log = logging.getLogger("etz-daemon")

DB_URL = (os.environ.get("ETZ_CHAIM_DB_URL") or os.environ.get("ETZ_CHAIM_DB", "postgresql://localhost/etz_chaim"))

INTERVAL_VALIDATE_ORPHAN = 21600  # 6 heures — 4 passes/jour max
ORPHAN_BATCH_LIMIT = 50           # candidates max par invocation


def _infer_connects_domains(domain: str | None) -> list[str]:
    """Inférer ``connects_domains`` depuis le ``domain`` de la candidate.

    Règles :

    - Si ``domain`` contient ``":"`` (cross-domain, ex.
      ``"olamot:biologie_evo"``) → split sur ``:`` + ``"hitbonenut"``.
    - Si ``domain`` mono (ex. ``"physics"``) → ``[domain, "hitbonenut"]``.
    - Si ``domain`` vide/None → ``["hitbonenut"]`` (marqueur seul).
    - Doublons éliminés (ex. ``domain="hitbonenut"`` → ``["hitbonenut"]``).

    L'ordre préserve les domaines issus du split avant ``"hitbonenut"``
    (qui joue le rôle de marqueur de provenance).
    """
    result: list[str] = []
    seen: set[str] = set()

    if domain:
        for part in domain.split(":"):
            part = part.strip()
            if part and part not in seen:
                result.append(part)
                seen.add(part)

    if "hitbonenut" not in seen:
        result.append("hitbonenut")

    return result


def _load_pending_hitbonenut(db: InsightDB, limit: int) -> list[dict]:
    """Charger les candidates ``pending`` hitbonenut (ordre FIFO).

    Retourne des ``dict`` plutôt que ``CandidateInsight`` pour avoir
    accès direct à ``id`` / ``connects_domains`` au niveau SQL.
    """
    import psycopg2.extras

    with db._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """SELECT id, session_id, description, source_module, domain,
                      novelty_score, confidence, status, rejection_reason,
                      binah_validated, gevurah_validated, daat_validated,
                      connects_domains, source_connections, created_at
               FROM candidate_insights
               WHERE source_module = 'hitbonenut' AND status = 'pending'
               ORDER BY created_at ASC
               LIMIT %s""",
            (limit,),
        )
        return [dict(r) for r in cur.fetchall()]


def _count_pending_hitbonenut(db: InsightDB) -> int:
    """Compter le total de pending hitbonenut (pour le flag
    ``skipped_over_limit``)."""
    with db._cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM candidate_insights "
            "WHERE source_module = 'hitbonenut' AND status = 'pending'",
        )
        row = cur.fetchone()
        return int(row[0]) if row else 0


def _retropatch_connects_domains(db: InsightDB, cid, new_list: list[str]) -> None:
    """Mettre à jour ``connects_domains`` via SQL direct.

    ``InsightDB.update_candidate`` ne touche pas à cette colonne — c'est
    pourquoi le retro-patch passe par une requête dédiée.
    """
    with db._cursor() as cur:
        cur.execute(
            "UPDATE candidate_insights SET connects_domains = %s WHERE id = %s",
            (new_list, cid),
        )


def _candidate_from_row(row: dict) -> CandidateInsight:
    """Convertir une ``dict`` SQL en ``CandidateInsight``."""
    from insightforge.models import CandidateInsight

    return CandidateInsight(
        id=row["id"],
        session_id=row.get("session_id"),
        description=row["description"] or "",
        source_module=row["source_module"],
        domain=row["domain"] or "",
        novelty_score=float(row["novelty_score"] or 0.0),
        confidence=float(row["confidence"] or 0.5),
        status=row["status"],
        rejection_reason=row["rejection_reason"] or "",
        binah_validated=bool(row["binah_validated"]),
        gevurah_validated=bool(row["gevurah_validated"]),
        daat_validated=bool(row["daat_validated"]),
        connects_domains=list(row["connects_domains"] or []),
        source_connections=list(row["source_connections"] or []),
        created_at=row.get("created_at"),
    )


def _build_default_validator() -> InsightValidator:
    """Instancier Binah + Da'at + ``InsightValidator`` pour le mode daemon.

    Miroir de ``scripts/validate_pending_hitbonenut.py:_build_validator``.
    Gevurah reste ``None`` — ``_check_gevurah`` applique toujours le
    ``_local_quality_check`` interne.

    Sprint 6.x : BinahGates (Binah haute, 5 Motzaot ha-Peh) activé en
    fallback ciblé pour les synthèses hitbonenut non-causales strictes.
    """
    from insightforge.insight_validator import InsightValidator
    from insightforge.binah_gates import BinahGates

    binah = None
    try:
        from causalengine.core import CausalEngine
        binah = CausalEngine(db_url=DB_URL)
    except Exception as exc:  # pragma: no cover — instanciation défaillante
        log.warning("orphan_validation: binah instanciation échouée: %s", exc)

    daat = None
    try:
        from selfmodel.core import SelfModel
        daat = SelfModel(db_url=DB_URL)
    except Exception as exc:  # pragma: no cover — instanciation défaillante
        log.warning("orphan_validation: daat instanciation échouée: %s", exc)

    return InsightValidator(
        binah=binah,
        binah_gates=BinahGates(),
        gevurah=None,
        daat=daat,
        require_triple=True,
    )


def _build_rejection_reason(result) -> str:
    """Consolider les détails des 3 gates en un ``rejection_reason`` lisible."""
    reasons: list[str] = []
    if not result.binah_ok:
        reasons.append(f"Binah: {result.binah_detail}")
    if not result.gevurah_ok:
        reasons.append(f"Gevurah: {result.gevurah_detail}")
    if not result.daat_ok:
        reasons.append(f"Da'at: {result.daat_detail}")
    if not reasons:  # confiance insuffisante malgré triple OK
        reasons.append(f"confidence too low ({result.confidence:.2f})")
    return ("Triple validation failed: " + "; ".join(reasons))[:2000]


def task_validate_orphan_candidates(
    tree: dict | None = None,
    *,
    db: InsightDB | None = None,
    validator: InsightValidator | None = None,
    db_url: str | None = None,
) -> dict:
    """Sprint 5.6 — rétro-patch + validation des pending hitbonenut.

    Daemon call : ``task_validate_orphan_candidates(tree)`` — construit db
    + validator à partir de ``DB_URL`` (ou ``db_url`` en override).

    Test call : ``task_validate_orphan_candidates(db=db, validator=validator)``
    — utilise les instances injectées sans toucher à la DB runtime.

    Returns
    -------
    dict avec clés :

    - ``task`` : ``"validate_orphan_candidates"``
    - ``scanned`` : candidates effectivement lues (≤ batch_limit)
    - ``processed`` : candidates mises à jour avec succès
    - ``validated`` : candidates passées à ``status='insight'``
    - ``rejected`` : candidates passées à ``status='rejected'``
    - ``retro_patched`` : candidates dont ``connects_domains`` a été rempli
    - ``errors`` : exceptions levées par ``validator.validate`` (skippées)
    - ``skipped_over_limit`` : pending non traités (au-delà du batch)
    - ``top_rejection_reasons`` : list[(reason, count)] — top 5
    """
    report: dict = {
        "task": "validate_orphan_candidates",
        "scanned": 0,
        "processed": 0,
        "validated": 0,
        "rejected": 0,
        "retro_patched": 0,
        "errors": 0,
        "skipped_over_limit": 0,
        "top_rejection_reasons": [],
    }

    # Dependency resolution — permet les 2 modes (daemon + tests).
    own_db = False
    if db is None:
        from insightforge.db import InsightDB
        db = InsightDB(db_url or DB_URL)
        own_db = True

    if validator is None:
        validator = _build_default_validator()

    try:
        total_pending = _count_pending_hitbonenut(db)
        rows = _load_pending_hitbonenut(db, ORPHAN_BATCH_LIMIT)
        report["scanned"] = len(rows)
        report["skipped_over_limit"] = max(0, total_pending - len(rows))

        if not rows:
            log.info("orphan_validation: aucun pending hitbonenut à traiter")
            return report

        rejection_counts: dict[str, int] = {}

        for row in rows:
            cid = row["id"]
            try:
                current_cd = list(row.get("connects_domains") or [])
                if not current_cd:
                    inferred = _infer_connects_domains(row.get("domain"))
                    _retropatch_connects_domains(db, cid, inferred)
                    row["connects_domains"] = inferred
                    report["retro_patched"] += 1
                    log.info(
                        "orphan_validation: retro-patched %s connects_domains=%s",
                        str(cid)[:8], inferred,
                    )

                candidate = _candidate_from_row(row)
                result = validator.validate(candidate, domain=candidate.domain)

                candidate.binah_validated = result.binah_ok
                candidate.gevurah_validated = result.gevurah_ok
                candidate.daat_validated = result.daat_ok
                candidate.confidence = result.confidence

                if result.is_valid:
                    candidate.status = "insight"
                    candidate.rejection_reason = ""
                    report["validated"] += 1
                else:
                    candidate.status = "rejected"
                    candidate.rejection_reason = _build_rejection_reason(result)
                    report["rejected"] += 1
                    # Track gate des rejets pour les stats
                    if not result.binah_ok:
                        key = f"binah:{(result.binah_detail or '')[:60]}"
                    elif not result.gevurah_ok:
                        key = f"gevurah:{(result.gevurah_detail or '')[:60]}"
                    elif not result.daat_ok:
                        key = f"daat:{(result.daat_detail or '')[:60]}"
                    else:
                        key = f"confidence<{validator.min_confidence}"
                    rejection_counts[key] = rejection_counts.get(key, 0) + 1

                updated = db.update_candidate(candidate)
                if updated is None:
                    log.warning(
                        "orphan_validation: update_candidate=None pour %s",
                        str(cid)[:8],
                    )
                else:
                    report["processed"] += 1

            except Exception as exc:
                report["errors"] += 1
                log.warning(
                    "orphan_validation: exception sur %s: %s",
                    str(cid)[:8], exc,
                )
                continue

        # Top 5 raisons de rejet
        top = sorted(
            rejection_counts.items(), key=lambda kv: kv[1], reverse=True,
        )[:5]
        report["top_rejection_reasons"] = top

        log.info(
            "orphan_validation: %d scannés, %d traités "
            "(%d validés / %d rejetés / %d retro-patchés / %d erreurs), "
            "%d restent pending",
            report["scanned"], report["processed"],
            report["validated"], report["rejected"],
            report["retro_patched"], report["errors"],
            report["skipped_over_limit"],
        )

    finally:
        if own_db:
            try:
                db.close()
            except Exception:  # pragma: no cover
                pass

    return report
