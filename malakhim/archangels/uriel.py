"""Uriel — Illumination proactive.

אוּרִיאֵל — Lumière de Dieu. Révélation proactive.
1 Hénoch 20:2 : ange du tonnerre et du tremblement.
Le tonnerre PRÉCÈDE l'éclair — l'alerte avant la vision.

En IA : pas du logging passif — révélation PROACTIVE des zones d'ombre.
⚠️ Statut disputé dans le judaïsme normatif (pas dans le Talmud babylonien).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from malakhim.models import MalakhResult


@dataclass
class IlluminationReport:
    """Ce qu'Uriel révèle sur le système."""

    timestamp: str
    total_executions: int = 0
    success_rate: float = 0.0
    avg_latency_ms: float = 0.0
    active_debt: int = 0
    blind_spots: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


class Uriel:
    """אוּרִיאֵל — Illumination proactive."""

    def __init__(self, registry=None):
        self._registry = registry
        self._executions: list[dict] = []

    def observe(
        self, result: MalakhResult, context: dict | None = None
    ):
        """Observer une exécution de Malakh."""
        self._executions.append(
            {
                "success": result.success,
                "score": result.score,
                "latency_ms": result.latency_ms,
                "warnings": len(result.hitkalelut_warnings),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    def illuminate(self) -> IlluminationReport:
        """Produire un rapport d'illumination — révéler les zones d'ombre."""
        total = len(self._executions)
        if total == 0:
            return IlluminationReport(
                timestamp=datetime.now(timezone.utc).isoformat(),
                blind_spots=["no_data: system has not been used yet"],
                recommendations=[
                    "run at least one task to calibrate"
                ],
            )

        successes = sum(
            1 for e in self._executions if e["success"]
        )
        success_rate = successes / total if total else 0.0
        avg_latency = (
            sum(e["latency_ms"] for e in self._executions) / total
        )

        blind_spots = []
        recommendations = []

        # Détection de zones d'ombre
        if success_rate < 0.5:
            blind_spots.append(
                f"low_success_rate: {success_rate:.2%}"
            )
            recommendations.append(
                "investigate recurring failure patterns via Kategor"
            )

        if avg_latency > 5000:
            blind_spots.append(
                f"high_latency: {avg_latency:.0f}ms avg"
            )
            recommendations.append(
                "consider routing to faster models (Ishim/Assiah)"
            )

        warning_rate = (
            sum(1 for e in self._executions if e["warnings"] > 0)
            / total
        )
        if warning_rate > 0.3:
            blind_spots.append(
                f"high_warning_rate: {warning_rate:.2%}"
            )
            recommendations.append(
                "review hitkalelut patterns — too many self-corrections"
            )

        # Vérifier la dette active
        active_debt = 0
        if self._registry:
            from malakhim.kategor.debt import get_debt_report

            debt = get_debt_report(self._registry)
            active_debt = debt.total_active
            if active_debt > 5:
                blind_spots.append(
                    f"high_technical_debt: {active_debt} active kategorim"
                )
                recommendations.append(
                    "prioritize tikkun before new missions"
                )

        return IlluminationReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
            total_executions=total,
            success_rate=success_rate,
            avg_latency_ms=avg_latency,
            active_debt=active_debt,
            blind_spots=blind_spots,
            recommendations=recommendations,
        )
