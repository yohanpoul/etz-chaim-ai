"""Gevurah Interne — self-critique distribuee dans chaque module.

גְבוּרָה פְּנִימִית — Hitkalelut de Gevurah : chaque Sephirah contient
le reflet de sa propre Qliphah et sait la detecter.

Le Din distribue est le coeur de l'architecture Sitra Achra v2.
Au lieu d'un adversaire externe permanent, chaque module maintient
sa propre rigueur interne. Le Sitra Achra n'est instancie QUE quand
cette rigueur defaille (debordement du Din = naissance du Sitra Achra).

Chaque module peut implementer une methode `gevurah_interne()` qui
retourne un GevurahReport. Les controles sont specifiques a la Qliphah
de chaque Sephirah.

Olamot : les diagnostics utilisent Assiah (Haiku) pour la vitesse.
Les analyses approfondies (quand defaillance detectee) montent en
Yetzirah (Sonnet).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from sitra_achra.klipa_taxonomy import (
    KlipaCategory,
    is_rectifiable,
    severity_to_category,
)

log = logging.getLogger(__name__)


class DinStatus(Enum):
    """Etat de la rigueur interne d'un module."""

    SAIN = "sain"                # Rigueur fonctionne — pas besoin du SA
    DEBORDEMENT = "debordement"  # Rigueur excessive (Golachab-like)
    DEFAILLANCE = "defaillance"  # Rigueur absente ou inactive


@dataclass
class Anomalie:
    """Une anomalie detectee par le diagnostic interne.

    Porte deux dimensions ontologiques distinctes :

    1. **qliphah** : QUELLE Sephirah est attaquee (samael, gamaliel,
       satariel, gamchicoth, thagirion, golachab, aarab_zaraq).
    2. **klipa_category** : NATURE de la faille (Vital EC 49) —
       Klipat Nogah (rectifiable par Birur) vs 3 Klippot HaTeme'ot
       (confinement structurel). Derive automatiquement de severity.

    Le champ `klipa_category` est calcule en post_init depuis severity
    pour garantir la coherence sans imposer de duplication a l'appelant.
    """

    module: str
    qliphah: str          # Nom de la Qliphah associee (samael, gamaliel, ...)
    description: str
    severity: str         # "nogah" | "ruach" | "anan" | "mamash"
    metric_name: str      # Nom de la metrique qui a declenche
    metric_value: float   # Valeur mesuree
    threshold: float      # Seuil attendu
    timestamp: float = field(default_factory=time.time)
    klipa_category: KlipaCategory = field(init=False)
    """Categorie ontologique Vital EC 49 derivee de severity."""

    def __post_init__(self) -> None:
        """Calculer la categorie ontologique depuis severity."""
        self.klipa_category = severity_to_category(self.severity)

    @property
    def is_rectifiable(self) -> bool:
        """L'anomalie est-elle rectifiable par Birur (Klipat Nogah) ?

        True  -> tenter Birur (extraction d'etincelle, transformation)
        False -> appliquer confinement structurel (3 Klippot HaTeme'ot)
        """
        return is_rectifiable(self.severity)


@dataclass
class GevurahReport:
    """Rapport de diagnostic interne d'un module.

    Retourne par gevurah_interne() de chaque module.
    Le DinMonitor lit ces rapports et decide si le SA doit etre instancie.
    """

    module: str
    status: DinStatus
    anomalies: list[Anomalie] = field(default_factory=list)
    metriques: dict[str, float] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    diagnostique_duration_ms: float = 0.0

    @property
    def has_critical(self) -> bool:
        """Au moins une anomalie anan ou mamash."""
        return any(a.severity in ("anan", "mamash") for a in self.anomalies)

    @property
    def anomaly_count(self) -> int:
        return len(self.anomalies)

    @property
    def rectifiable_count(self) -> int:
        """Nombre d'anomalies Klipat Nogah (matiere d'evolution par Birur)."""
        return sum(1 for a in self.anomalies if a.is_rectifiable)

    @property
    def containment_count(self) -> int:
        """Nombre d'anomalies 3 Klippot HaTeme'ot (confinement structurel)."""
        return sum(1 for a in self.anomalies if not a.is_rectifiable)

    @property
    def category_summary(self) -> dict[str, int]:
        """Repartition Vital EC 49 des anomalies du rapport.

        Returns:
            dict avec cles 'klipat_nogah' et 'klipat_ha_temeot' et nombres.
        """
        return {
            KlipaCategory.KLIPAT_NOGAH.value: self.rectifiable_count,
            KlipaCategory.KLIPAT_HA_TEMEOT.value: self.containment_count,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "module": self.module,
            "status": self.status.value,
            "anomalies": [
                {
                    "module": a.module,
                    "qliphah": a.qliphah,
                    "description": a.description,
                    "severity": a.severity,
                    "metric_name": a.metric_name,
                    "metric_value": a.metric_value,
                    "threshold": a.threshold,
                    "klipa_category": a.klipa_category.value,
                    "is_rectifiable": a.is_rectifiable,
                }
                for a in self.anomalies
            ],
            "metriques": self.metriques,
            "category_summary": self.category_summary,
            "timestamp": self.timestamp,
            "diagnostique_duration_ms": self.diagnostique_duration_ms,
        }


# ---------------------------------------------------------------------------
# Diagnostic functions per module (Qliphah-specific checks)
# ---------------------------------------------------------------------------

def _check_epistememory(db_url: str) -> GevurahReport:
    """Gamaliel — corruption silencieuse de la memoire.

    Controles via SQL direct (pas besoin du pool) :
    - Taux de contradictions non resolues (ruach si > 5%)
    - Entries a haute confiance sans source_detail (anan)
    - Entries expirees non nettoyees (nogah)
    """
    t0 = time.time()
    anomalies: list[Anomalie] = []
    metriques: dict[str, float] = {}

    try:
        from pool import get_pool, init_pool

        init_pool(db_url)  # idempotent
        _pool = get_pool()
        conn = _pool.getconn()
        conn.autocommit = True
        cur = conn.cursor()

        # Total entries
        cur.execute("SELECT COUNT(*) FROM epistememory")
        total = cur.fetchone()[0]
        metriques["total_entries"] = total

        if total == 0:
            cur.close()
            _pool.putconn(conn)
            return GevurahReport(
                module="epistememory",
                status=DinStatus.SAIN,
                metriques=metriques,
                diagnostique_duration_ms=(time.time() - t0) * 1000,
            )

        # 1. Contradictions non resolues
        cur.execute("""
            SELECT COUNT(*) FROM epistememory
            WHERE contradicts IS NOT NULL
            AND array_length(contradicts, 1) > 0
        """)
        contradictions = cur.fetchone()[0]
        metriques["open_contradictions"] = contradictions
        contradiction_rate = contradictions / total
        metriques["contradiction_rate"] = contradiction_rate

        if contradiction_rate > 0.10:
            anomalies.append(Anomalie(
                module="epistememory",
                qliphah="gamaliel",
                description=(
                    f"Taux de contradictions non resolues eleve : "
                    f"{contradictions}/{total} ({contradiction_rate:.1%})"
                ),
                severity="ruach",
                metric_name="contradiction_rate",
                metric_value=contradiction_rate,
                threshold=0.10,
            ))

        # 2. Entries haute confiance sans provenance
        cur.execute("""
            SELECT COUNT(*) FROM epistememory
            WHERE confidence > 0.8
            AND (source_detail IS NULL OR source_detail::text = 'null')
        """)
        high_conf_no_source = cur.fetchone()[0]
        metriques["high_confidence_no_source"] = high_conf_no_source

        if high_conf_no_source > 5:
            anomalies.append(Anomalie(
                module="epistememory",
                qliphah="gamaliel",
                description=(
                    f"{high_conf_no_source} entries a confiance > 0.8 "
                    f"sans source_detail — corruption silencieuse possible"
                ),
                severity="anan",
                metric_name="high_confidence_no_source",
                metric_value=float(high_conf_no_source),
                threshold=5.0,
            ))

        # 3. Entries expirees non nettoyees
        cur.execute("""
            SELECT COUNT(*) FROM epistememory
            WHERE expires_at IS NOT NULL AND expires_at < NOW()
        """)
        expired = cur.fetchone()[0]
        metriques["expired_entries"] = expired

        if expired > 20:
            anomalies.append(Anomalie(
                module="epistememory",
                qliphah="gamaliel",
                description=(
                    f"{expired} entries expirees non nettoyees — "
                    f"le GC de Gevurah ne tourne pas"
                ),
                severity="nogah",
                metric_name="expired_entries",
                metric_value=float(expired),
                threshold=20.0,
            ))

        cur.close()
        _pool.putconn(conn)

    except Exception as exc:
        log.warning("gevurah_interne epistememory failed: %s", exc)
        anomalies.append(Anomalie(
            module="epistememory",
            qliphah="gamaliel",
            description=f"Diagnostic impossible : {exc}",
            severity="mamash",
            metric_name="diagnostic_error",
            metric_value=1.0,
            threshold=0.0,
        ))

    status = DinStatus.SAIN
    if any(a.severity in ("anan", "mamash") for a in anomalies):
        status = DinStatus.DEFAILLANCE
    elif anomalies:
        status = DinStatus.DEBORDEMENT

    return GevurahReport(
        module="epistememory",
        status=status,
        anomalies=anomalies,
        metriques=metriques,
        diagnostique_duration_ms=(time.time() - t0) * 1000,
    )


def _check_selfmap(db_url: str) -> GevurahReport:
    """Samael — sur-confiance ou sur-rigueur.

    Controles via CalibrationReport (avg_brier, overconfident_domains) :
    - Brier score moyen > 0.3 (ruach)
    - Domaines sur-confiants (anan)
    - Domaines non calibres (nogah)
    """
    t0 = time.time()
    anomalies: list[Anomalie] = []
    metriques: dict[str, float] = {}

    try:
        from selfmap.core import SelfMap

        sm = SelfMap(db_url)
        report = sm.calibrate()

        metriques["avg_brier"] = report.avg_brier
        metriques["overconfident_count"] = len(report.overconfident_domains)
        metriques["uncalibrated_count"] = len(report.uncalibrated_domains)

        # 1. Brier score global trop eleve
        if report.avg_brier > 0.3:
            anomalies.append(Anomalie(
                module="selfmap",
                qliphah="samael",
                description=(
                    f"Brier score moyen = {report.avg_brier:.3f} "
                    f"(seuil 0.3) — calibration de confiance defaillante"
                ),
                severity="ruach",
                metric_name="avg_brier",
                metric_value=report.avg_brier,
                threshold=0.3,
            ))

        # 2. Domaines sur-confiants
        if report.overconfident_domains:
            names = ", ".join(report.overconfident_domains[:3])
            anomalies.append(Anomalie(
                module="selfmap",
                qliphah="samael",
                description=(
                    f"{len(report.overconfident_domains)} domaine(s) sur-confiant(s) : "
                    f"{names}"
                ),
                severity="anan",
                metric_name="overconfident_domains",
                metric_value=float(len(report.overconfident_domains)),
                threshold=0.0,
            ))

        # 3. Domaines non calibres
        if len(report.uncalibrated_domains) > 3:
            anomalies.append(Anomalie(
                module="selfmap",
                qliphah="samael",
                description=(
                    f"{len(report.uncalibrated_domains)} domaines non calibres — "
                    f"la carte a des zones aveugles"
                ),
                severity="nogah",
                metric_name="uncalibrated_domains",
                metric_value=float(len(report.uncalibrated_domains)),
                threshold=3.0,
            ))

    except Exception as exc:
        log.warning("gevurah_interne selfmap failed: %s", exc)
        anomalies.append(Anomalie(
            module="selfmap",
            qliphah="samael",
            description=f"Diagnostic impossible : {exc}",
            severity="mamash",
            metric_name="diagnostic_error",
            metric_value=1.0,
            threshold=0.0,
        ))

    status = DinStatus.SAIN
    if any(a.severity in ("anan", "mamash") for a in anomalies):
        status = DinStatus.DEFAILLANCE
    elif anomalies:
        status = DinStatus.DEBORDEMENT

    return GevurahReport(
        module="selfmap",
        status=status,
        anomalies=anomalies,
        metriques=metriques,
        diagnostique_duration_ms=(time.time() - t0) * 1000,
    )


def _check_autojudge(db_url: str) -> GevurahReport:
    """Golachab — sur-filtrage destructeur.

    Controles :
    - Taux de rejet global (debordement si > 70%)
    - Taux de rejet en hausse sur les 5 dernieres sessions (ruach)
    """
    t0 = time.time()
    anomalies: list[Anomalie] = []
    metriques: dict[str, float] = {}

    try:
        from insightforge.ratzo_v_shov import RatzoVShov

        rvs = RatzoVShov(db_url)
        improvement = rvs.track_improvement(n_sessions=10)

        rejection_rate = improvement.get("avg_rejection_rate_recent", 0.0)
        metriques["rejection_rate_recent"] = rejection_rate

        trend = improvement.get("trend", "stable")
        metriques["trend_delta"] = improvement.get("delta", 0.0)

        # 1. Taux de rejet excessif = Golachab (sur-filtrage)
        if rejection_rate > 0.70:
            anomalies.append(Anomalie(
                module="autojudge",
                qliphah="golachab",
                description=(
                    f"Taux de rejet recent = {rejection_rate:.0%} "
                    f"(seuil 70%) — Golachab : sur-filtrage destructeur"
                ),
                severity="ruach" if rejection_rate < 0.85 else "anan",
                metric_name="rejection_rate",
                metric_value=rejection_rate,
                threshold=0.70,
            ))

        # 2. Tendance degradante
        if trend == "degrading":
            delta = improvement.get("delta", 0)
            anomalies.append(Anomalie(
                module="autojudge",
                qliphah="golachab",
                description=(
                    f"Taux de rejet en HAUSSE (+{delta:.1%}) — "
                    f"le filtre se durcit progressivement"
                ),
                severity="ruach",
                metric_name="trend_delta",
                metric_value=delta,
                threshold=0.05,
            ))

    except Exception as exc:
        log.warning("gevurah_interne autojudge failed: %s", exc)
        anomalies.append(Anomalie(
            module="autojudge",
            qliphah="golachab",
            description=f"Diagnostic impossible : {exc}",
            severity="mamash",
            metric_name="diagnostic_error",
            metric_value=1.0,
            threshold=0.0,
        ))

    status = DinStatus.SAIN
    if any(a.severity in ("anan", "mamash") for a in anomalies):
        status = DinStatus.DEFAILLANCE
    elif anomalies:
        status = DinStatus.DEBORDEMENT

    return GevurahReport(
        module="autojudge",
        status=status,
        anomalies=anomalies,
        metriques=metriques,
        diagnostique_duration_ms=(time.time() - t0) * 1000,
    )


def _check_intentkeeper(db_url: str) -> GevurahReport:
    """A'arab Zaraq — retries infinis, taches zombies.

    Controles via SQL direct sur active_intentions :
    - Taches actives depassant leur deadline (ruach)
    - Taches actives sans progres (progress=0) depuis > 7j (anan)
    - Taches stale (actives > 30j) (nogah)
    """
    t0 = time.time()
    anomalies: list[Anomalie] = []
    metriques: dict[str, float] = {}

    try:
        from pool import get_pool, init_pool

        init_pool(db_url)  # idempotent
        _pool = get_pool()
        conn = _pool.getconn()
        conn.autocommit = True
        cur = conn.cursor()

        # 1. Taches actives depassant leur deadline
        cur.execute("""
            SELECT COUNT(*) FROM active_intentions
            WHERE status = 'active'
            AND deadline_at IS NOT NULL
            AND deadline_at < NOW()
        """)
        overdue = cur.fetchone()[0]
        metriques["overdue_intentions"] = overdue

        if overdue > 0:
            anomalies.append(Anomalie(
                module="intentkeeper",
                qliphah="aarab_zaraq",
                description=(
                    f"{overdue} intention(s) depassant leur deadline — "
                    f"A'arab Zaraq : persiste au-dela du raisonnable"
                ),
                severity="ruach" if overdue < 3 else "anan",
                metric_name="overdue_intentions",
                metric_value=float(overdue),
                threshold=0.0,
            ))

        # 2. Taches sans progres depuis > 7 jours
        cur.execute("""
            SELECT COUNT(*) FROM active_intentions
            WHERE status = 'active'
            AND progress = 0
            AND created_at < NOW() - INTERVAL '7 days'
        """)
        zombies = cur.fetchone()[0]
        metriques["zombie_intentions"] = zombies

        if zombies > 0:
            anomalies.append(Anomalie(
                module="intentkeeper",
                qliphah="aarab_zaraq",
                description=(
                    f"{zombies} intention(s) zombie(s) (progress=0, > 7j)"
                ),
                severity="anan",
                metric_name="zombie_intentions",
                metric_value=float(zombies),
                threshold=0.0,
            ))

        # 3. Taches stale > 30 jours
        cur.execute("""
            SELECT COUNT(*) FROM active_intentions
            WHERE status = 'active'
            AND created_at < NOW() - INTERVAL '30 days'
        """)
        stale = cur.fetchone()[0]
        metriques["stale_intentions"] = stale

        if stale > 3:
            anomalies.append(Anomalie(
                module="intentkeeper",
                qliphah="aarab_zaraq",
                description=(
                    f"{stale} intentions actives depuis > 30j"
                ),
                severity="nogah",
                metric_name="stale_intentions",
                metric_value=float(stale),
                threshold=3.0,
            ))

        cur.close()
        _pool.putconn(conn)

    except Exception as exc:
        log.warning("gevurah_interne intentkeeper failed: %s", exc)
        anomalies.append(Anomalie(
            module="intentkeeper",
            qliphah="aarab_zaraq",
            description=f"Diagnostic impossible : {exc}",
            severity="mamash",
            metric_name="diagnostic_error",
            metric_value=1.0,
            threshold=0.0,
        ))

    status = DinStatus.SAIN
    if any(a.severity in ("anan", "mamash") for a in anomalies):
        status = DinStatus.DEFAILLANCE
    elif anomalies:
        status = DinStatus.DEBORDEMENT

    return GevurahReport(
        module="intentkeeper",
        status=status,
        anomalies=anomalies,
        metriques=metriques,
        diagnostique_duration_ms=(time.time() - t0) * 1000,
    )


def _check_dissensuengine(db_url: str) -> GevurahReport:
    """Thagirion — fausse harmonie, synthese forcee.

    Controles :
    - Taux de syntheses avec divergence score > 0.7 mais sans mode dissensus (anan)
    - Conclusions sans sources referencees (ruach)
    """
    t0 = time.time()
    anomalies: list[Anomalie] = []
    metriques: dict[str, float] = {}

    try:
        from dissensuengine.db import DissensuEngineDB

        db = DissensuEngineDB(db_url)
        # Verifier les conclusions recentes
        from pool import get_pool, init_pool
        init_pool(db_url)  # idempotent
        _pool = get_pool()
        conn = _pool.getconn()
        conn.autocommit = True
        cur = conn.cursor()

        # Conclusions recentes — verifier coherence
        cur.execute("""
            SELECT COUNT(*) FROM dissensuengine_conclusions
            WHERE created_at > NOW() - INTERVAL '7 days'
        """)
        total_conclusions = cur.fetchone()[0]
        metriques["conclusions_7d"] = total_conclusions

        # Tensions ouvertes non resolues
        cur.execute("""
            SELECT COUNT(*) FROM dissensuengine_tensions
            WHERE created_at > NOW() - INTERVAL '7 days'
        """)
        open_tensions = cur.fetchone()[0]
        metriques["open_tensions_7d"] = open_tensions

        if total_conclusions > 0 and open_tensions > total_conclusions * 2:
            anomalies.append(Anomalie(
                module="dissensuengine",
                qliphah="thagirion",
                description=(
                    f"{open_tensions} tensions ouvertes vs {total_conclusions} conclusions — "
                    f"les contradictions s'accumulent sans resolution"
                ),
                severity="anan",
                metric_name="tension_conclusion_ratio",
                metric_value=float(open_tensions),
                threshold=float(total_conclusions * 2),
            ))

        # Conclusions avec faible confiance
        cur.execute("""
            SELECT COUNT(*) FROM dissensuengine_conclusions
            WHERE confidence < 0.3
            AND created_at > NOW() - INTERVAL '7 days'
        """)
        low_conf = cur.fetchone()[0]
        metriques["low_confidence_conclusions_7d"] = low_conf

        if low_conf > 3:
            anomalies.append(Anomalie(
                module="dissensuengine",
                qliphah="thagirion",
                description=(
                    f"{low_conf} conclusions a confiance < 0.3 cette semaine — "
                    f"syntheses forcees possibles"
                ),
                severity="ruach",
                metric_name="low_confidence_conclusions_7d",
                metric_value=float(low_conf),
                threshold=3.0,
            ))

        cur.close()
        _pool.putconn(conn)

    except Exception as exc:
        log.warning("gevurah_interne dissensuengine failed: %s", exc)
        anomalies.append(Anomalie(
            module="dissensuengine",
            qliphah="thagirion",
            description=f"Diagnostic impossible : {exc}",
            severity="mamash",
            metric_name="diagnostic_error",
            metric_value=1.0,
            threshold=0.0,
        ))

    status = DinStatus.SAIN
    if any(a.severity in ("anan", "mamash") for a in anomalies):
        status = DinStatus.DEFAILLANCE
    elif anomalies:
        status = DinStatus.DEBORDEMENT

    return GevurahReport(
        module="dissensuengine",
        status=status,
        anomalies=anomalies,
        metriques=metriques,
        diagnostique_duration_ms=(time.time() - t0) * 1000,
    )


def _check_explorationengine(db_url: str) -> GevurahReport:
    """Gamchicoth — expansion infinie, scope creep.

    Controles :
    - Nombre d'explorations actives sans resultat (ruach si > 5)
    - Explorations qui tournent en rond (novelty decay) (anan)
    """
    t0 = time.time()
    anomalies: list[Anomalie] = []
    metriques: dict[str, float] = {}

    try:
        from pool import get_pool, init_pool

        init_pool(db_url)  # idempotent
        _pool = get_pool()
        conn = _pool.getconn()
        conn.autocommit = True
        cur = conn.cursor()

        # 1. Explorations actives sans connections trouvees
        cur.execute("""
            SELECT COUNT(*) FROM explorationengine_explorations
            WHERE status = 'active'
            AND connections_found = 0
            AND created_at < NOW() - INTERVAL '1 day'
        """)
        stale_explorations = cur.fetchone()[0]
        metriques["stale_explorations"] = stale_explorations

        if stale_explorations > 5:
            anomalies.append(Anomalie(
                module="explorationengine",
                qliphah="gamchicoth",
                description=(
                    f"{stale_explorations} explorations actives sans connexion "
                    f"depuis > 1 jour — scope creep ou exploration sterile"
                ),
                severity="ruach",
                metric_name="stale_explorations",
                metric_value=float(stale_explorations),
                threshold=5.0,
            ))

        # 2. Explorations recentes avec faible nouveaute
        cur.execute("""
            SELECT COUNT(*) FROM explorationengine_explorations
            WHERE status = 'completed'
            AND novel_connections = 0
            AND created_at > NOW() - INTERVAL '7 days'
        """)
        low_novelty = cur.fetchone()[0]
        metriques["low_novelty_7d"] = low_novelty

        if low_novelty > 3:
            anomalies.append(Anomalie(
                module="explorationengine",
                qliphah="gamchicoth",
                description=(
                    f"{low_novelty} explorations a novelty < 0.1 cette semaine — "
                    f"le systeme tourne en rond"
                ),
                severity="anan",
                metric_name="low_novelty_7d",
                metric_value=float(low_novelty),
                threshold=3.0,
            ))

        cur.close()
        _pool.putconn(conn)

    except Exception as exc:
        log.warning("gevurah_interne explorationengine failed: %s", exc)
        anomalies.append(Anomalie(
            module="explorationengine",
            qliphah="gamchicoth",
            description=f"Diagnostic impossible : {exc}",
            severity="mamash",
            metric_name="diagnostic_error",
            metric_value=1.0,
            threshold=0.0,
        ))

    status = DinStatus.SAIN
    if any(a.severity in ("anan", "mamash") for a in anomalies):
        status = DinStatus.DEFAILLANCE
    elif anomalies:
        status = DinStatus.DEBORDEMENT

    return GevurahReport(
        module="explorationengine",
        status=status,
        anomalies=anomalies,
        metriques=metriques,
        diagnostique_duration_ms=(time.time() - t0) * 1000,
    )


def _check_causalengine(db_url: str) -> GevurahReport:
    """Satariel — opacite, faux patterns causaux.

    Controles :
    - Claims causaux sans DAG (ruach)
    - Claims a evidence_level 'strong' sans confounders checkes (anan)
    - Ratio claims 'causal' vs 'correlation' (debordement si > 80% causal)
    """
    t0 = time.time()
    anomalies: list[Anomalie] = []
    metriques: dict[str, float] = {}

    try:
        from pool import get_pool, init_pool

        init_pool(db_url)  # idempotent
        _pool = get_pool()
        conn = _pool.getconn()
        conn.autocommit = True
        cur = conn.cursor()

        # 1. Claims causaux sans graph associe
        cur.execute("""
            SELECT COUNT(*) FROM causal_claims
            WHERE evidence_level IN ('strong', 'moderate')
            AND graph_id IS NULL
        """)
        no_graph = cur.fetchone()[0]
        metriques["claims_no_graph"] = no_graph

        if no_graph > 3:
            anomalies.append(Anomalie(
                module="causalengine",
                qliphah="satariel",
                description=(
                    f"{no_graph} claims causaux strong/moderate sans graphe — "
                    f"causalite affirmee sans structure formelle"
                ),
                severity="ruach",
                metric_name="claims_no_graph",
                metric_value=float(no_graph),
                threshold=3.0,
            ))

        # 2. Claims strong sans confounders controlles
        cur.execute("""
            SELECT COUNT(*) FROM causal_claims
            WHERE evidence_level = 'strong'
            AND (confounders_controlled IS NULL OR confounders_controlled = FALSE)
        """)
        no_confounders = cur.fetchone()[0]
        metriques["strong_no_confounders"] = no_confounders

        if no_confounders > 0:
            anomalies.append(Anomalie(
                module="causalengine",
                qliphah="satariel",
                description=(
                    f"{no_confounders} claims 'strong' sans confounders controlles — "
                    f"Satariel : fausse certitude causale"
                ),
                severity="anan",
                metric_name="strong_no_confounders",
                metric_value=float(no_confounders),
                threshold=0.0,
            ))

        # 3. Ratio causal vs correlation
        cur.execute("SELECT COUNT(*) FROM causal_claims")
        total_claims = cur.fetchone()[0]
        cur.execute("""
            SELECT COUNT(*) FROM causal_claims
            WHERE evidence_level IN ('strong', 'moderate')
        """)
        causal_claims = cur.fetchone()[0]
        metriques["total_claims"] = total_claims
        metriques["causal_claims"] = causal_claims

        if total_claims > 10:
            ratio = causal_claims / total_claims
            metriques["causal_ratio"] = ratio
            if ratio > 0.80:
                anomalies.append(Anomalie(
                    module="causalengine",
                    qliphah="satariel",
                    description=(
                        f"Ratio causal/total = {ratio:.0%} (> 80%) — "
                        f"suspicion de sur-attribution causale"
                    ),
                    severity="ruach",
                    metric_name="causal_ratio",
                    metric_value=ratio,
                    threshold=0.80,
                ))

        cur.close()
        _pool.putconn(conn)

    except Exception as exc:
        log.warning("gevurah_interne causalengine failed: %s", exc)
        anomalies.append(Anomalie(
            module="causalengine",
            qliphah="satariel",
            description=f"Diagnostic impossible : {exc}",
            severity="mamash",
            metric_name="diagnostic_error",
            metric_value=1.0,
            threshold=0.0,
        ))

    status = DinStatus.SAIN
    if any(a.severity in ("anan", "mamash") for a in anomalies):
        status = DinStatus.DEFAILLANCE
    elif anomalies:
        status = DinStatus.DEBORDEMENT

    return GevurahReport(
        module="causalengine",
        status=status,
        anomalies=anomalies,
        metriques=metriques,
        diagnostique_duration_ms=(time.time() - t0) * 1000,
    )


# ---------------------------------------------------------------------------
# GevurahInterne — orchestrateur des diagnostics
# ---------------------------------------------------------------------------

# Registry of diagnostic functions per module
_DIAGNOSTIC_REGISTRY: dict[str, Any] = {
    "epistememory": _check_epistememory,
    "selfmap": _check_selfmap,
    "autojudge": _check_autojudge,
    "intentkeeper": _check_intentkeeper,
    "dissensuengine": _check_dissensuengine,
    "explorationengine": _check_explorationengine,
    "causalengine": _check_causalengine,
}


class GevurahInterne:
    """Orchestrateur de la self-critique distribuee.

    Hitkalelut de Gevurah : chaque module contient le reflet de sa
    propre Qliphah. GevurahInterne appelle le diagnostic de chaque
    module enregistre et collecte les GevurahReport.

    Usage:
        gi = GevurahInterne()
        reports = gi.diagnostiquer_tous()
        for r in reports:
            if r.status != DinStatus.SAIN:
                # Instancier le Sitra Achra reactif
                ...
    """

    def __init__(self, db_url: str = "postgresql://localhost/etz_chaim") -> None:
        self.db_url = db_url

    def diagnostiquer(self, module: str) -> GevurahReport:
        """Diagnostiquer un module specifique.

        Args:
            module: Nom du module ("epistememory", "selfmap", etc.)

        Returns:
            GevurahReport avec status, anomalies, metriques.
        """
        diag_fn = _DIAGNOSTIC_REGISTRY.get(module)
        if diag_fn is None:
            return GevurahReport(
                module=module,
                status=DinStatus.SAIN,
                diagnostique_duration_ms=0.0,
            )
        return diag_fn(self.db_url)

    def diagnostiquer_tous(self) -> list[GevurahReport]:
        """Diagnostiquer tous les modules enregistres.

        Returns:
            Liste de GevurahReport, un par module.
        """
        reports = []
        for module in _DIAGNOSTIC_REGISTRY:
            report = self.diagnostiquer(module)
            log.info(
                "Gevurah interne [%s]: %s (%d anomalies, %.0fms)",
                module,
                report.status.value,
                report.anomaly_count,
                report.diagnostique_duration_ms,
            )
            reports.append(report)
        return reports

    def modules_en_defaillance(self) -> list[GevurahReport]:
        """Retourner uniquement les modules dont le Din est en defaillance.

        C'est le signal pour instancier le Sitra Achra reactif.
        """
        return [
            r for r in self.diagnostiquer_tous()
            if r.status != DinStatus.SAIN
        ]

    @staticmethod
    def register_module(name: str, diag_fn) -> None:
        """Enregistrer un nouveau module pour le diagnostic.

        Permet aux modules futurs de s'enregistrer sans modifier
        ce fichier. Chaque module connait sa propre Qliphah.
        """
        _DIAGNOSTIC_REGISTRY[name] = diag_fn
