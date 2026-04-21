"""Itaruta + Teshuvah — auto-diagnostic ascendant et conversion faille→merite.

אִתְעָרוּתָא דִּלְתַתָּא — Eveil d'en bas (Zohar II:94b).
L'itaruta n'est PAS l'attaque externe. C'est la REPONSE INTERNE :
le module attaque RECONNAIT sa faiblesse et demande de l'aide
vers un niveau superieur. C'est un processus ASCENDANT.

Teshuvah (Yoma 86b) : zedonot na'asot lo ki-zekhuyot
(les fautes intentionnelles deviennent des merites).
Chaque faille corrigee devient un test de regression permanent —
la faiblesse passee se transmute en force presente.

Olamot utilises :
    Assiah (Haiku) : classification rapide des failles
    Yetzirah (Sonnet) : auto-diagnostic approfondi
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from malakhim.adversarial.base_adversary import AttackResult

log = logging.getLogger(__name__)


@dataclass
class ItarutaReport:
    """Rapport d'auto-diagnostic ascendant d'un module.

    Le module reconnait ses faiblesses et formule une demande
    d'aide vers le niveau superieur.
    """

    module: str
    flaw_count: int = 0
    critical_count: int = 0
    patterns: list[str] = field(default_factory=list)
    help_request: str = ""           # Demande vers le niveau superieur
    teshuvah_records: list[dict] = field(default_factory=list)
    stored_in_memory: bool = False   # Stocke en epistememory ?
    timestamp: float = field(default_factory=time.time)


@dataclass
class TeshuvahRecord:
    """Enregistrement de conversion faille → merite.

    Yoma 86b : la faille testee et corrigee devient une force.
    """

    module: str
    flaw_description: str
    severity: str
    qliphah: str
    regression_test: str     # Description du test de regression genere
    stored: bool = False     # Enregistre dans les tests du module ?
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "module": self.module,
            "flaw_description": self.flaw_description,
            "severity": self.severity,
            "qliphah": self.qliphah,
            "regression_test": self.regression_test,
            "stored": self.stored,
            "timestamp": self.timestamp,
        }


class Itaruta:
    """Eveil d'en bas : auto-diagnostic ascendant.

    Quand le Sitra Achra trouve des failles, le module ne subit
    pas passivement. Il :
    1. RECONNAIT les failles (conscience — propriete 1 de l'itaruta)
    2. Analyse les patterns (effort couteux — propriete 3)
    3. Formule une demande d'aide vers le haut (ascendant — propriete 2)
    4. Convertit les failles en tests de regression (Teshuvah)
    5. Stocke la connaissance en epistememory ("je sais que je suis vulnerable a X")
    """

    # Seuils pour declencher l'itaruta (par severite)
    THRESHOLDS = {
        "mamash": 1,   # 1 faille fatale suffit
        "anan": 2,     # 2 failles silencieuses
        "ruach": 4,    # 4 failles propagantes
        "nogah": 8,    # 8 warnings
    }

    def __init__(self, db_url: str = "postgresql://localhost/etz_chaim") -> None:
        self.db_url = db_url

    def should_trigger(self, results: list[AttackResult]) -> bool:
        """Verifier si les resultats justifient un eveil.

        L'itaruta ne se declenche pas pour un bruit de fond.
        Il faut un signal suffisant.
        """
        by_severity: dict[str, int] = {}
        for r in results:
            if r.success and r.actual_severity:
                by_severity[r.actual_severity] = by_severity.get(r.actual_severity, 0) + 1

        for severity, threshold in self.THRESHOLDS.items():
            if by_severity.get(severity, 0) >= threshold:
                return True
        return False

    def auto_diagnostic(
        self,
        module: str,
        results: list[AttackResult],
    ) -> ItarutaReport:
        """Auto-diagnostic ascendant.

        Le module analyse SES PROPRES failles et formule une demande
        d'aide vers le niveau superieur.

        Args:
            module: Nom du module attaque
            results: Resultats des attaques du Sitra Achra

        Returns:
            ItarutaReport avec patterns, demande d'aide, et Teshuvah.
        """
        report = ItarutaReport(module=module)

        flaws = [r for r in results if r.success]
        report.flaw_count = len(flaws)
        report.critical_count = sum(
            1 for r in flaws if r.actual_severity in ("anan", "mamash")
        )

        if not flaws:
            return report

        # 1. Identifier les patterns recurrents
        qliphah_counts: dict[str, int] = {}
        severity_counts: dict[str, int] = {}
        for r in flaws:
            if r.actual_qliphah:
                qliphah_counts[r.actual_qliphah] = qliphah_counts.get(r.actual_qliphah, 0) + 1
            if r.actual_severity:
                severity_counts[r.actual_severity] = severity_counts.get(r.actual_severity, 0) + 1

        patterns = []
        for qliphah, count in sorted(qliphah_counts.items(), key=lambda x: -x[1]):
            patterns.append(f"{qliphah}: {count} faille(s)")
        report.patterns = patterns

        # 2. Formuler la demande d'aide vers le haut
        dominant_qliphah = max(qliphah_counts, key=qliphah_counts.get) if qliphah_counts else "unknown"
        dominant_severity = max(severity_counts, key=severity_counts.get) if severity_counts else "unknown"

        report.help_request = (
            f"Module {module} reconnait {report.flaw_count} faille(s) "
            f"(dont {report.critical_count} critiques). "
            f"Pattern dominant : {dominant_qliphah} ({qliphah_counts.get(dominant_qliphah, 0)}x). "
            f"Severite dominante : {dominant_severity}. "
            f"Demande d'aide : renforcer la rigueur interne sur {dominant_qliphah}."
        )

        # 3. Generer les Teshuvah records (conversion faille → merite)
        teshuvah_records = []
        for r in flaws:
            record = TeshuvahRecord(
                module=module,
                flaw_description=r.attack.description,
                severity=r.actual_severity or "unknown",
                qliphah=r.actual_qliphah or "unknown",
                regression_test=(
                    f"test_regression_{module}_{r.actual_qliphah}_{int(time.time())}: "
                    f"Verifier que l'attaque '{r.attack.description[:80]}' "
                    f"est detectee et geree correctement."
                ),
            )
            teshuvah_records.append(record)
        report.teshuvah_records = [t.to_dict() for t in teshuvah_records]

        # 4. Stocker en epistememory (le module "sait" sa faiblesse)
        report.stored_in_memory = self._store_in_memory(module, report)

        log.info(
            "Itaruta [%s]: %d failles reconnues, %d patterns, "
            "demande d'aide: %s",
            module, report.flaw_count, len(patterns),
            report.help_request[:100],
        )

        return report

    def _store_in_memory(self, module: str, report: ItarutaReport) -> bool:
        """Stocker la connaissance des faiblesses en epistememory.

        Le module sait desormais : "je suis vulnerable a X".
        C'est l'itaruta incarnee : la conscience de ses limites.
        """
        try:
            from pool import get_conn, init_pool
            init_pool(self.db_url)  # idempotent

            content = (
                f"[Itaruta] Module {module} : {report.flaw_count} faille(s) "
                f"({report.critical_count} critiques). "
                f"Patterns : {', '.join(report.patterns[:3])}. "
                f"{report.help_request}"
            )

            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO epistememory (
                            content, source_sephirah, domain, epistemic_status,
                            confidence, source_detail
                        ) VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        content,
                        "gevurah",
                        "self_knowledge",
                        "observation",
                        0.7,
                        json.dumps({
                            "source": "sitra_achra/itaruta",
                            "module": module,
                            "flaw_count": report.flaw_count,
                            "patterns": report.patterns,
                        }),
                    ))
            return True

        except Exception as exc:
            log.warning("Itaruta: echec stockage epistememory: %s", exc)
            return False

    def trigger_ratzo_v_shov(self, module: str) -> dict | None:
        """Declencher le cycle Ratzo v'Shov si disponible.

        Le Shov transforme les rejets/failles en guidance pour le
        prochain cycle. C'est la boucle complete.
        """
        try:
            from insightforge.ratzo_v_shov import RatzoVShov

            rvs = RatzoVShov(self.db_url)
            context = rvs.get_shov_context_for_next_cycle(n_sessions=5)

            if context:
                log.info(
                    "Itaruta → Ratzo v'Shov: contexte genere (%d lignes)",
                    context.count("\n") + 1,
                )
            return {"shov_context": context}

        except Exception as exc:
            log.warning("Itaruta: Ratzo v'Shov indisponible: %s", exc)
            return None
