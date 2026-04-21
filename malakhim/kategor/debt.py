"""Kategor — Gestion de la dette technique vivante.

קָטֵגוֹר — L'accusateur persiste tant que l'erreur n'est pas réparée.
"Ein kategor na'aseh sanegor" — un accusateur ne peut devenir défenseur.

Ce module fournit des vues sur la dette active du système.
Les données vivent dans PekidahRegistry (_failures : dict[int, FailurePattern]).
"""

from __future__ import annotations

from dataclasses import dataclass

from malakhim.models import FailurePattern
from malakhim.pekidah.registry import PekidahRegistry


@dataclass
class DebtReport:
    """Rapport de dette technique — les Kategorim actifs."""

    total_active: int
    by_domain: dict[str, int]
    by_error_type: dict[str, int]
    oldest_unresolved: FailurePattern | None
    most_frequent: FailurePattern | None


def get_debt_report(registry: PekidahRegistry) -> DebtReport:
    """Générer un rapport de dette à partir du registre."""
    active = [f for f in registry._failures.values() if f.active]

    by_domain: dict[str, int] = {}
    by_error_type: dict[str, int] = {}

    for f in active:
        by_domain[f.domain] = by_domain.get(f.domain, 0) + 1
        by_error_type[f.error_type] = by_error_type.get(f.error_type, 0) + 1

    oldest = (
        min(active, key=lambda f: f.created_at or f.pattern_id)
        if active
        else None
    )
    most_frequent = (
        max(active, key=lambda f: f.occurrences) if active else None
    )

    return DebtReport(
        total_active=len(active),
        by_domain=by_domain,
        by_error_type=by_error_type,
        oldest_unresolved=oldest,
        most_frequent=most_frequent,
    )


def purge_resolved(registry: PekidahRegistry) -> int:
    """Purger les patterns résolus du registre. Retourne le nombre purgé."""
    before = len(registry._failures)
    registry._failures = {
        pid: f for pid, f in registry._failures.items() if f.active
    }
    return before - len(registry._failures)
