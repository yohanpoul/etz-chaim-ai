"""Sitra Achra — adversite creatrice reactive.

סִטְרָא אָחֳרָא — L'Autre Cote. Pas un daemon permanent mais un
systeme adversarial REACTIF instancie quand la rigueur interne
(Din distribue) d'un module defaille ou deborde.

Architecture en 3 couches :
    Couche 1 — Din distribue (tamid) : Gevurah interne par module
    Couche 2 — Sitra Achra reactif : coordinateur adaptatif Samael
    Couche 3 — Itaruta + Teshuvah : auto-diagnostic → conversion

Sources kabbalistiques :
    Tanya ch. 27 : "tamid" = vigilance defensive permanente
    Zohar II:184a : "pas de lumiere sauf celle qui sort de l'obscurite"
    Zohar II:242b : structure 3+7 (contre-Mochin + contre-Middot)
    Zohar I:148a : parasitisme soustractif
    Bereshit Rabbah 9:7 : "tov meod" = Yetzer HaRa
    Yoma 86b : Teshuvah = conversion faille → merite
"""

from sitra_achra.gevurah_interne import GevurahInterne, GevurahReport
from sitra_achra.din_monitor import DinMonitor
from sitra_achra.budget_parasitaire import BudgetParasitaire
from sitra_achra.samael_coordinator import SamaelCoordinator, SitraAchraReport
from sitra_achra.itaruta import Itaruta, ItarutaReport
from sitra_achra.counter_mochin import CounterMochin
from sitra_achra.external_scanner import (
    ScanResult,
    task_external_scan,
    detect_regression,
)
from sitra_achra.teshuvah_writer import (
    TeshuvahWriteResult,
    process_teshuvah_records,
    write_regression_test,
)
from sitra_achra.klipa_taxonomy import (
    GenerativeStrategy,
    KlipaCategory,
    KlipaSeverity,
    TemeahIdentity,
    is_rectifiable,
    severity_to_category,
    strategy_for_category,
    strategy_for_severity,
    temeah_identity,
)

__all__ = [
    "GevurahInterne",
    "GevurahReport",
    "DinMonitor",
    "BudgetParasitaire",
    "SamaelCoordinator",
    "SitraAchraReport",
    "Itaruta",
    "ItarutaReport",
    "CounterMochin",
    "ScanResult",
    "task_external_scan",
    "detect_regression",
    "TeshuvahWriteResult",
    "process_teshuvah_records",
    "write_regression_test",
    # Klipa Taxonomy (Vital EC 49)
    "GenerativeStrategy",
    "KlipaCategory",
    "KlipaSeverity",
    "TemeahIdentity",
    "is_rectifiable",
    "severity_to_category",
    "strategy_for_category",
    "strategy_for_severity",
    "temeah_identity",
]
