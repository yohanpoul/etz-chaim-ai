"""Omer Tuner — Apprentissage de seuils par feedback de qualité.

Lit les outcomes récents (outcome_quality dans selfmap_routing_log),
calcule pour chaque seuil ciblé si l'ajustement améliore la qualité,
et applique des micro-corrections ±0.02 max par cycle via l'Omer.

Trois seuils ciblés (Tier 1) :
  - autojudge QUALITY_THRESHOLD (0.6)
  - tzimtzum CONTRACTION_THRESHOLD (0.7)
  - selfmap decline_threshold (0.3)

Le tuner ne modifie PAS les seuils directement — il produit des
Suggestions que le DailyInfluence peut appliquer.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

MAX_ADJUSTMENT = 0.02
MIN_SAMPLES = 20


@dataclass
class ThresholdState:
    """État courant d'un seuil suivi."""
    name: str
    module: str
    attr: str
    current: float
    floor: float
    ceiling: float


@dataclass
class TuneResult:
    """Résultat d'un cycle de tuning."""
    threshold: str
    old_value: float
    new_value: float
    direction: str       # "up", "down", "stable"
    reason: str
    n_samples: int
    avg_quality: float


# Les 3 seuils Tier 1
TRACKED_THRESHOLDS = [
    ThresholdState(
        name="quality_threshold",
        module="autojudge",
        attr="quality_threshold",
        current=0.6,
        floor=0.4,
        ceiling=0.85,
    ),
    ThresholdState(
        name="contraction_threshold",
        module="tzimtzum",
        attr="CONTRACTION_THRESHOLD",
        current=0.7,
        floor=0.5,
        ceiling=0.9,
    ),
    ThresholdState(
        name="decline_threshold",
        module="selfmap",
        attr="decline_threshold",
        current=0.3,
        floor=0.1,
        ceiling=0.5,
    ),
]


def compute_adjustment(
    outcomes: list[dict],
    threshold: ThresholdState,
) -> TuneResult:
    """Calcule l'ajustement pour un seuil donné.

    Logique :
    - Si la qualité moyenne des outcomes est basse (<0.5) ET le seuil
      est élevé → le seuil rejette trop → baisser
    - Si la qualité moyenne est haute (>0.7) ET le seuil est bas →
      le seuil laisse passer trop → monter
    - Sinon → stable

    Args:
        outcomes: liste de dicts avec au minimum {"quality": float}
        threshold: état du seuil à ajuster

    Returns:
        TuneResult avec la direction et la nouvelle valeur proposée
    """
    n = len(outcomes)
    if n < MIN_SAMPLES:
        return TuneResult(
            threshold=threshold.name,
            old_value=threshold.current,
            new_value=threshold.current,
            direction="stable",
            reason=f"Pas assez de samples ({n}/{MIN_SAMPLES})",
            n_samples=n,
            avg_quality=0.0,
        )

    avg_q = sum(o["quality"] for o in outcomes) / n

    direction = "stable"
    delta = 0.0
    reason = "Qualité dans la plage normale"

    if avg_q < 0.5 and threshold.current > threshold.floor + MAX_ADJUSTMENT:
        # Trop restrictif — baisser le seuil
        direction = "down"
        delta = -MAX_ADJUSTMENT
        reason = f"Qualité basse ({avg_q:.2f}) — seuil trop restrictif"
    elif avg_q > 0.7 and threshold.current < threshold.ceiling - MAX_ADJUSTMENT:
        # Trop permissif — monter le seuil
        direction = "up"
        delta = MAX_ADJUSTMENT
        reason = f"Qualité haute ({avg_q:.2f}) — seuil peut monter"

    new_value = round(
        max(threshold.floor, min(threshold.ceiling, threshold.current + delta)),
        4,
    )

    return TuneResult(
        threshold=threshold.name,
        old_value=threshold.current,
        new_value=new_value,
        direction=direction,
        reason=reason,
        n_samples=n,
        avg_quality=round(avg_q, 4),
    )


def read_recent_outcomes(
    db_url: str = "postgresql://localhost/etz_chaim",
    limit: int = 100,
) -> list[dict]:
    """Lit les derniers outcomes depuis selfmap_routing_log.

    Returns:
        liste de dicts {"quality": float, "domain": str, "timestamp": str}
    """
    try:
        from pool import get_conn, init_pool
        init_pool(db_url)
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT outcome_quality, domain, created_at
                       FROM selfmap_routing_log
                       WHERE outcome_quality IS NOT NULL
                       ORDER BY created_at DESC
                       LIMIT %s""",
                    (limit,),
                )
                rows = cur.fetchall()
        return [
            {"quality": float(r[0]), "domain": r[1], "timestamp": str(r[2])}
            for r in rows
        ]
    except Exception as e:
        logger.warning("Tuner: impossible de lire les outcomes — %s", e)
        return []


def write_outcome_quality(
    db_url: str,
    routing_log_id: int,
    quality: float,
) -> bool:
    """Écrit outcome_quality dans selfmap_routing_log.

    Returns:
        True si l'écriture a réussi.
    """
    try:
        from pool import get_conn, init_pool
        init_pool(db_url)
        with get_conn(autocommit=False) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE selfmap_routing_log
                       SET outcome_quality = %s
                       WHERE id = %s""",
                    (quality, routing_log_id),
                )
            conn.commit()
        return True
    except Exception as e:
        logger.warning("Tuner: impossible d'écrire outcome — %s", e)
        return False


def run_tuning_cycle(
    outcomes: list[dict] | None = None,
    db_url: str = "postgresql://localhost/etz_chaim",
    thresholds: list[ThresholdState] | None = None,
) -> list[TuneResult]:
    """Exécute un cycle complet de tuning.

    Args:
        outcomes: si None, lit depuis la DB
        db_url: URL de la base
        thresholds: seuils à ajuster (défaut: TRACKED_THRESHOLDS)

    Returns:
        liste de TuneResult (un par seuil)
    """
    if outcomes is None:
        outcomes = read_recent_outcomes(db_url)

    if thresholds is None:
        thresholds = TRACKED_THRESHOLDS

    results = []
    for t in thresholds:
        result = compute_adjustment(outcomes, t)
        results.append(result)
        if result.direction != "stable":
            logger.info(
                "Tuner: %s %s→%s (%s)",
                result.threshold,
                result.old_value,
                result.new_value,
                result.reason,
            )

    return results


def apply_tune_results(
    tree: dict,
    results: list[TuneResult],
) -> list[str]:
    """Applique les résultats de tuning aux modules de l'arbre.

    Args:
        tree: dict des modules (clé=sephirah, valeur=instance)
        results: résultats de run_tuning_cycle

    Returns:
        liste de descriptions des changements appliqués
    """
    changes = []
    module_map = {
        "autojudge": "gevurah",
        "tzimtzum": "tzimtzum",
        "selfmap": "hod",
    }

    for r in results:
        if r.direction == "stable":
            continue

        tree_key = module_map.get(r.threshold.split("_")[0], None)
        # Find the right module
        for key, mod in tree.items():
            attr = None
            if r.threshold == "quality_threshold" and hasattr(mod, "quality_threshold"):
                attr = "quality_threshold"
            elif r.threshold == "contraction_threshold" and hasattr(mod, "CONTRACTION_THRESHOLD"):
                attr = "CONTRACTION_THRESHOLD"
            elif r.threshold == "decline_threshold" and hasattr(mod, "decline_threshold"):
                attr = "decline_threshold"

            if attr:
                setattr(mod, attr, r.new_value)
                changes.append(
                    f"{r.threshold}: {r.old_value}→{r.new_value} ({r.reason})"
                )
                break

    return changes
