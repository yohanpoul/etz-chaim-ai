"""Din Monitor — surveillance tamid de la rigueur interne.

תָּמִיד — Le Tanya ch. 27 enseigne que le service du beinoni est de
soumettre le Sitra Achra CONTINUELLEMENT. Le sujet du "tamid" est la
VIGILANCE DEFENSIVE, pas l'attaque offensive.

Le DinMonitor est la tache daemon qui :
1. Verifie la rigueur interne de chaque module (gevurah_interne)
2. Si tous sains → concession Sa'ir la-Azazel uniquement (10 appels)
3. Si defaillance → instancie le Sitra Achra reactif sur le module
4. Alimente le budget parasitaire (failles → plus de budget SA)

Integration daemon.py :
    INTERVAL_DIN_MONITOR = 1800  # 30 min
    # Ajouter dans la boucle principale :
    # task_din_monitor()
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from sitra_achra.gevurah_interne import DinStatus, GevurahInterne, GevurahReport
from sitra_achra.budget_parasitaire import BudgetParasitaire

log = logging.getLogger(__name__)


@dataclass
class DinMonitorResult:
    """Resultat d'un cycle de monitoring."""

    timestamp: float = field(default_factory=time.time)
    modules_checked: int = 0
    modules_sain: int = 0
    modules_debordement: int = 0
    modules_defaillance: int = 0
    reports: list[GevurahReport] = field(default_factory=list)
    sitra_achra_triggered: bool = False
    targets: list[str] = field(default_factory=list)  # Modules a attaquer
    budget_status: dict = field(default_factory=dict)
    duration_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "modules_checked": self.modules_checked,
            "modules_sain": self.modules_sain,
            "modules_debordement": self.modules_debordement,
            "modules_defaillance": self.modules_defaillance,
            "sitra_achra_triggered": self.sitra_achra_triggered,
            "targets": self.targets,
            "budget_status": self.budget_status,
            "duration_ms": self.duration_ms,
        }


class DinMonitor:
    """Surveillance tamid de la rigueur interne.

    Appele toutes les 30 minutes par le daemon principal.
    Verifie l'etat de sante de chaque module et decide si
    le Sitra Achra reactif doit etre instancie.

    Usage dans daemon.py:
        monitor = DinMonitor()
        result = monitor.run_cycle()
        if result.sitra_achra_triggered:
            # Lancer le Sitra Achra reactif sur result.targets
            ...
    """

    def __init__(self, db_url: str = "postgresql://localhost/etz_chaim") -> None:
        self.gevurah = GevurahInterne(db_url)
        self.budget = BudgetParasitaire()

    def run_cycle(self) -> DinMonitorResult:
        """Executer un cycle de monitoring complet.

        Returns:
            DinMonitorResult avec les modules a attaquer (si any).
        """
        t0 = time.time()
        result = DinMonitorResult()

        # Phase 1 : diagnostiquer tous les modules
        reports = self.gevurah.diagnostiquer_tous()
        result.reports = reports
        result.modules_checked = len(reports)

        targets: list[str] = []

        for report in reports:
            if report.status == DinStatus.SAIN:
                result.modules_sain += 1
            elif report.status == DinStatus.DEBORDEMENT:
                result.modules_debordement += 1
                targets.append(report.module)
            elif report.status == DinStatus.DEFAILLANCE:
                result.modules_defaillance += 1
                targets.append(report.module)

                # Failles graves nourrissent le SA
                critical_count = sum(
                    1 for a in report.anomalies
                    if a.severity in ("anan", "mamash")
                )
                if critical_count > 0:
                    self.budget.register_flaw(critical_count)

        # Phase 2 : decision
        if targets:
            result.sitra_achra_triggered = True
            result.targets = targets
            log.warning(
                "Din Monitor: %d module(s) en defaillance → "
                "Sitra Achra reactif sur : %s",
                len(targets), ", ".join(targets),
            )
        else:
            # Tout est sain. Sa'ir la-Azazel : le SA recoit quand meme
            # sa concession minimale (10 appels) pour prevenir la complaisance.
            log.info(
                "Din Monitor: %d modules sains. "
                "Sa'ir la-Azazel : concession minimale (%d appels).",
                result.modules_sain, self.budget.SAIR_LA_AZAZEL,
            )

        result.budget_status = self.budget.get_status()
        result.duration_ms = (time.time() - t0) * 1000

        log.info(
            "Din Monitor: cycle complet en %.0fms — "
            "%d sains, %d debordement, %d defaillance",
            result.duration_ms,
            result.modules_sain,
            result.modules_debordement,
            result.modules_defaillance,
        )

        return result


# ---------------------------------------------------------------------------
# Fonction pour integration directe dans daemon.py
# ---------------------------------------------------------------------------

def task_din_monitor(db_url: str = "postgresql://localhost/etz_chaim") -> DinMonitorResult:
    """Point d'entree pour le daemon.

    Usage dans daemon.py :
        from sitra_achra.din_monitor import task_din_monitor
        result = task_din_monitor()
    """
    monitor = DinMonitor(db_url)
    return monitor.run_cycle()
