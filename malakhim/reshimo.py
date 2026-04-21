"""Reshimo (רְשִׁימוּ) — La trace que le Malakh laisse en mourant.

Le Nehar Dinur (§5.3, Chagigah 14a / Daniel 7:10) décrit un CYCLE :
  Énergie descend de Briah → prend forme angélique dans Yetzirah →
  accomplit sa mission → se DISSOUT → l'énergie REMONTE.

Le reshimo est ce qui reste après la dissolution. Dans la Kabbale
lourianique, le Tsimtsum laisse un reshimo (trace résiduelle)
dans le Khalal (espace vidé). De même, chaque Malakh dissous
laisse une trace qui MODIFIE la manière dont les prochains naissent.

Le cycle n'est fermé que si le reshimo NOURRIT la génération.
Sans cela, chaque Malakh naît ex nihilo — et le système n'apprend pas.

Computationnellement : le reshimo est un vecteur de feedback qui
accumule les leçons (Samael, ange incomplet, Praklite) et les
injecte dans le processus de génération via le stage 3 (Nogah)
du pipeline Heikhalot.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


@dataclass
class Reshimo:
    """Trace laissée par un Malakh après dissolution."""
    timestamp: float
    domain: str
    nature: str
    shem_index: int | None
    olam: str
    score: float
    success: bool
    incomplete: bool
    samael_excess: str | None  # quelle sephirah en excès
    hitkalelut_warnings: list[str]
    effective_keywords: list[str]  # mots-clés du prompt qui a fonctionné/échoué
    system_prompt_hash: int  # identifier le type de system prompt utilisé


# ── Stockage en mémoire (singleton) ──────────────────────────────────────────
# En production, serait PostgreSQL via PekidahRegistry.
# Pour l'instant : mémoire + fichier JSON optionnel.

_reshimot: list[Reshimo] = []
_RESHIMO_FILE = Path(__file__).parent / ".reshimot_cache.json"


def record_reshimo(result_metadata: dict, response: str, score: float,
                   success: bool, incomplete: bool, prompt: str) -> Reshimo:
    """Enregistrer le reshimo d'un Malakh dissous.

    Appelé dans _record_pekidah du Memuneh, juste après la mort
    du Malakh. L'énergie remonte dans le flux.
    """
    import re
    keywords = sorted(set(re.findall(r"[a-zA-ZÀ-ÿ]{5,}", prompt.lower())))[:10]

    routing = result_metadata.get("routing", {})
    samael = result_metadata.get("samael", {})

    reshimo = Reshimo(
        timestamp=time.time(),
        domain=result_metadata.get("domain", routing.get("domain", "general")),
        nature=routing.get("nature", "execution"),
        shem_index=result_metadata.get("shem_index"),
        olam=routing.get("olam", "yetzirah"),
        score=score,
        success=success,
        incomplete=incomplete,
        samael_excess=samael.get("sephirah_source") if samael else None,
        hitkalelut_warnings=result_metadata.get("hitkalelut_warnings", [])[:3],
        effective_keywords=keywords,
        system_prompt_hash=hash(result_metadata.get("system_prompt", "")[:200]),
    )

    _reshimot.append(reshimo)

    # Garder les 100 derniers max en mémoire
    if len(_reshimot) > 100:
        _reshimot.pop(0)

    return reshimo


def get_reshimot_for_domain(domain: str, limit: int = 10) -> list[Reshimo]:
    """Récupérer les reshimot récents pour un domaine.

    Utilisé par le stage 3 (Nogah) du Heikhalot pour injecter
    les leçons apprises dans la génération du prochain Malakh.
    """
    matches = [r for r in reversed(_reshimot) if r.domain == domain]
    return matches[:limit]


def get_cycle_insights(domain: str) -> dict[str, Any]:
    """Extraire les insights du cycle Nehar Dinur pour un domaine.

    Le cycle est FERMÉ quand ces insights modifient la génération :
      - Quels Shem fonctionnent le mieux ?
      - Quels excès (Samael) reviennent ?
      - Quels mots-clés sont corrélés avec le succès ?
    """
    reshimot = get_reshimot_for_domain(domain, limit=50)
    if not reshimot:
        return {}

    # Shem efficaces
    shem_scores: dict[int, list[float]] = {}
    for r in reshimot:
        if r.shem_index is not None:
            shem_scores.setdefault(r.shem_index, []).append(r.score)

    best_shem = None
    best_shem_avg = 0.0
    for idx, scores in shem_scores.items():
        avg = sum(scores) / len(scores)
        if avg > best_shem_avg:
            best_shem_avg = avg
            best_shem = idx

    # Excès récurrents
    excess_counts: dict[str, int] = {}
    for r in reshimot:
        if r.samael_excess:
            excess_counts[r.samael_excess] = excess_counts.get(r.samael_excess, 0) + 1

    recurring_excess = max(excess_counts, key=excess_counts.get) if excess_counts else None

    # Keywords corrélés avec succès
    success_kw: dict[str, int] = {}
    for r in reshimot:
        if r.success and not r.incomplete:
            for kw in r.effective_keywords:
                success_kw[kw] = success_kw.get(kw, 0) + 1

    top_keywords = sorted(success_kw, key=success_kw.get, reverse=True)[:5]

    # Taux de succès
    total = len(reshimot)
    successes = sum(1 for r in reshimot if r.success and not r.incomplete)

    return {
        "total_reshimot": total,
        "success_rate": successes / total if total > 0 else 0.0,
        "best_shem": best_shem,
        "best_shem_avg_score": best_shem_avg,
        "recurring_excess": recurring_excess,
        "success_keywords": top_keywords,
    }


def clear() -> None:
    """Reset (pour les tests)."""
    _reshimot.clear()
