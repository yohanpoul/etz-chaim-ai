"""FailureToInsight — Sentier Lamed (ל).

Gevurah→Tiferet : transformer le jugement en compréhension.
Le Birur — extraire les Nitzotzot (étincelles) des Qliphoth (écorces).

"Même dans les Qliphoth les plus denses, des Nitzotzot attendent."
La seule lettre qui dépasse la ligne. Racine LMD = apprendre.

Sentiers connectés :
  - 23e Lamed ל (Gevurah→Tiferet)  : CE programme
  - Via Yesod (EpisteMemory)         : persiste les insights
  - Via Hod (SelfMap)                : vérifie la compétence
  - Via Netzach (IntentKeeper)       : source des subtasks failed
"""

from __future__ import annotations

import logging
from uuid import UUID

from failuretoinsight.classifier import classify_qliphah, classify_severity
from failuretoinsight.db import FailureToInsightDB
from failuretoinsight.models import (
    FailureAnalysis,
    FailureGraphEdge,
    FailureKnowledgeGraph,
    HypothesisGuidance,
    Insight,
)

log = logging.getLogger(__name__)

# Omer du sentier Lamed — 7 paramètres de calibration
DEFAULT_MIN_DESCRIPTION_LENGTH = 20    # analyse trop courte = Nogah (superficielle)
DEFAULT_MAX_UNKNOWN_RATIO = 0.3        # max 30% d'analyses "unknown"
DEFAULT_MIN_INSIGHTS_PER_ANALYSIS = 1  # au moins 1 nitzotz par analyse
DEFAULT_SIMILARITY_THRESHOLD = 0.7     # seuil pour edges "similar_failure"
DEFAULT_STALE_ANALYSIS_DAYS = 30       # analyses sans insights après N jours
DEFAULT_MAX_RECURRING_ROOT = 3         # max fois une root cause apparaît avant alerte
DEFAULT_MIN_GRAPH_CONNECTIVITY = 0.1   # ratio minimum edges/analyses


class FailureToInsight:
    """Le Birur computationnel — transformer l'échec en connaissance.

    Hitkalelut : la rigueur (Gevurah/classification) et la compréhension
    (Tiferet/insight) vivent dans le même programme.
    """

    def __init__(
        self,
        db_url: str,
        memory=None,
        selfmap=None,
        intentkeeper=None,
        min_description_length: int = DEFAULT_MIN_DESCRIPTION_LENGTH,
        max_unknown_ratio: float = DEFAULT_MAX_UNKNOWN_RATIO,
        min_insights_per_analysis: int = DEFAULT_MIN_INSIGHTS_PER_ANALYSIS,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        stale_analysis_days: int = DEFAULT_STALE_ANALYSIS_DAYS,
        max_recurring_root: int = DEFAULT_MAX_RECURRING_ROOT,
        min_graph_connectivity: float = DEFAULT_MIN_GRAPH_CONNECTIVITY,
    ):
        self.db = FailureToInsightDB(db_url)
        self.memory = memory            # Yesod — persist insights
        self.selfmap = selfmap          # Hod — competence check
        self.intentkeeper = intentkeeper  # Netzach — failed subtasks
        self.min_description_length = min_description_length
        self.max_unknown_ratio = max_unknown_ratio
        self.min_insights_per_analysis = min_insights_per_analysis
        self.similarity_threshold = similarity_threshold
        self.stale_analysis_days = stale_analysis_days
        self.max_recurring_root = max_recurring_root
        self.min_graph_connectivity = min_graph_connectivity

    # --- Gevurah du sentier : classification ---

    def analyze_failure(
        self,
        description: str,
        source_type: str = "external",
        source_id: UUID | None = None,
        context: dict | None = None,
        domain: str | None = None,
        qliphah_override: str | None = None,
        severity_override: str | None = None,
    ) -> FailureAnalysis:
        """Classifier un échec via la taxonomie des Qliphoth.

        Si qliphah_override ou severity_override sont fournis, les utiliser
        directement. Sinon, classifier automatiquement.
        """
        qliphah = qliphah_override or classify_qliphah(description, context)
        severity = severity_override or classify_severity(description, context)

        # Extraire une root_cause si possible
        root_cause = self._extract_root_cause(description, qliphah, context)

        analysis = self.db.create_analysis(
            source_type=source_type,
            description=description,
            qliphah=qliphah,
            severity=severity,
            source_id=source_id,
            root_cause=root_cause,
            context=context,
            domain=domain,
        )

        # Persister en EpisteMemory via Yesod
        if self.memory:
            self.memory.remember(
                content=f"Échec analysé [{qliphah}/{severity}]: {description}"
                        + (f" — cause: {root_cause}" if root_cause else ""),
                source_sephirah="gevurah",
                confidence=0.6,
                domain=domain or "failure_analysis",
                tags=["failure", qliphah, severity],
                ttl_days=365,
            )

        return analysis

    def analyze_subtask_failure(
        self,
        subtask_id: UUID,
        additional_context: dict | None = None,
    ) -> FailureAnalysis:
        """Analyser l'échec d'une sous-tâche IntentKeeper.

        Sentier Netzach→Lamed : les échecs de persistance alimentent
        l'apprentissage.
        """
        if not self.intentkeeper:
            raise ValueError("IntentKeeper non connecté — sentier Netzach absent")

        with self.intentkeeper.db._cursor() as cur:
            cur.execute(
                """SELECT id, intention_id, description, failure_reason
                   FROM intentkeeper_subtasks WHERE id = %s""",
                (subtask_id,),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Subtask {subtask_id} not found")

        description = f"Subtask failed: {row[2]}"
        if row[3]:
            description += f" — reason: {row[3]}"

        context = {"intention_id": str(row[1]), "subtask_id": str(row[0])}
        if additional_context:
            context.update(additional_context)

        return self.analyze_failure(
            description=description,
            source_type="subtask",
            source_id=subtask_id,
            context=context,
        )

    # --- Tiferet du sentier : extraction des Nitzotzot ---

    def extract_nitzotzot(
        self,
        analysis_id: UUID,
        insights_data: list[dict] | None = None,
    ) -> list[Insight]:
        """Extraire les étincelles de lumière d'un échec analysé.

        Si insights_data est fourni, utiliser ces données directement.
        Sinon, extraire automatiquement basé sur la classification.

        insights_data format: [{"content": str, "insight_type": str,
                                "confidence": float, "domain": str}]
        """
        analysis = self.db.get_analysis(analysis_id)
        if not analysis:
            raise ValueError(f"Analysis {analysis_id} not found")

        if insights_data:
            return self._store_insights(analysis, insights_data)

        # Extraction automatique basée sur la classification
        auto_insights = self._auto_extract(analysis)
        return self._store_insights(analysis, auto_insights)

    def _store_insights(
        self, analysis: FailureAnalysis, insights_data: list[dict]
    ) -> list[Insight]:
        """Stocker les insights et les persister en EpisteMemory.

        Sprint 8b fix 2 — Déduplication glissante 24h : les qliphah
        extractions contiennent des messages canned ("Boucle de retry
        détectée — adapter la stratégie…") qui sortaient identiques
        plusieurs fois par jour et alimentaient 31% du bruit rejeté par
        novelty_assessor dans candidate_insights. On skip si un insight
        avec exactement le même content existe depuis < 24h.
        """
        results = []
        for data in insights_data:
            domain = data.get("domain") or analysis.domain
            content = data["content"]

            # Déduplication glissante : skip si ce content a déjà été
            # persisté en failuretoinsight_insights dans les 24 dernières heures.
            try:
                if self.db.recent_insight_exists(content, hours=24):
                    log.info(
                        "FTI dedup skip (24h): %s",
                        content[:80],
                    )
                    continue
            except Exception as exc:
                # Ne jamais bloquer l'insertion sur une erreur de check
                log.debug("FTI dedup check failed, proceeding: %s", exc)

            # Persister en EpisteMemory si connecté
            epistememory_id = None
            if self.memory:
                epistememory_id = self.memory.remember(
                    content=f"Nitzotz [{analysis.qliphah}]: {content}",
                    source_sephirah="gevurah",
                    confidence=data.get("confidence", 0.5),
                    domain=domain or "failure_insight",
                    tags=["nitzotz", analysis.qliphah, data["insight_type"]],
                    ttl_days=365,
                )

            insight = self.db.create_insight(
                analysis_id=analysis.id,
                content=content,
                insight_type=data["insight_type"],
                confidence=data.get("confidence", 0.5),
                domain=domain,
                epistememory_id=epistememory_id,
            )
            results.append(insight)

        return results

    def _auto_extract(self, analysis: FailureAnalysis) -> list[dict]:
        """Extraction automatique d'insights basée sur la qliphah."""
        insights = []

        # Toujours extraire un anti-pattern de l'échec
        insights.append({
            "content": f"Anti-pattern [{analysis.qliphah}]: {analysis.description}",
            "insight_type": "anti_pattern",
            "confidence": 0.6,
        })

        # Si root_cause identifiée, extraire une contrainte
        if analysis.root_cause:
            insights.append({
                "content": f"Contrainte identifiée: {analysis.root_cause}",
                "insight_type": "constraint",
                "confidence": 0.5,
            })

        # Extractions spécifiques par qliphah
        qliphah_extractions = {
            "golachab": {
                "content": "Les critères de filtrage sont peut-être trop stricts "
                           "— envisager une approche graduée",
                "insight_type": "opportunity",
                "confidence": 0.4,
            },
            "gamchicoth": {
                "content": "Scope creep détecté — poser des limites fermes "
                           "avant la prochaine itération",
                "insight_type": "constraint",
                "confidence": 0.5,
            },
            "aarab_zaraq": {
                "content": "Boucle de retry détectée — adapter la stratégie "
                           "au lieu de persister",
                "insight_type": "warning",
                "confidence": 0.6,
            },
            "satariel": {
                "content": "Pattern possiblement fallacieux — vérifier la "
                           "direction causale et tester sur des données indépendantes",
                "insight_type": "warning",
                "confidence": 0.5,
            },
            "thagirion": {
                "content": "Synthèse forcée — les sources divergent, "
                           "exposer la tension au lieu de la résoudre",
                "insight_type": "pattern",
                "confidence": 0.5,
            },
        }

        if analysis.qliphah in qliphah_extractions:
            insights.append(qliphah_extractions[analysis.qliphah])

        return insights

    # --- Graphe de connaissance ---

    def build_failure_graph(
        self, domain: str | None = None
    ) -> FailureKnowledgeGraph:
        """Construire le graphe de connaissance des échecs.

        Lie les analyses entre elles :
        - same_root_cause : même cause racine
        - similar_failure : même qliphah + même domaine
        - escalation : sévérité croissante dans le même domaine
        """
        analyses = self.db.get_all_analyses(domain=domain)

        # Construire les edges automatiquement
        for i, a1 in enumerate(analyses):
            for a2 in analyses[i + 1:]:
                # Same root cause
                if (a1.root_cause and a2.root_cause
                        and a1.root_cause == a2.root_cause):
                    self.db.create_edge(
                        a1.id, a2.id, "same_root_cause", weight=1.0
                    )

                # Similar failure (même qliphah + même domaine)
                if (a1.qliphah == a2.qliphah
                        and a1.domain and a1.domain == a2.domain):
                    self.db.create_edge(
                        a1.id, a2.id, "similar_failure", weight=0.8
                    )

                # Escalation (même domaine, sévérité croissante)
                severity_order = {"nogah": 0, "ruach": 1, "anan": 2, "mamash": 3}
                if (a1.domain and a1.domain == a2.domain
                        and a1.qliphah == a2.qliphah):
                    s1 = severity_order.get(a1.severity, 0)
                    s2 = severity_order.get(a2.severity, 0)
                    if s2 > s1:
                        self.db.create_edge(
                            a1.id, a2.id, "escalation", weight=1.5
                        )

        edges = self.db.get_all_edges()
        all_insights = self.db.get_all_insights(domain=domain)
        qliphah_counts = self.db.count_by_qliphah()
        domains = sorted({a.domain for a in analyses if a.domain})
        most_common = max(qliphah_counts, key=qliphah_counts.get) if qliphah_counts else None

        return FailureKnowledgeGraph(
            analyses=analyses,
            edges=edges,
            patterns=qliphah_counts,
            domains_affected=domains,
            most_common_qliphah=most_common,
            total_insights=len(all_insights),
        )

    def guide_next_hypothesis(
        self, domain: str | None = None
    ) -> HypothesisGuidance:
        """Utiliser le graphe des échecs pour guider les explorations futures.

        Lamed pointe vers Tiferet — la guidance aide la synthèse.
        """
        graph = self.build_failure_graph(domain=domain)

        # Identifier les qliphoth récurrentes à éviter
        avoid = [q for q, c in graph.patterns.items()
                 if c >= self.max_recurring_root]

        # Root causes récurrentes
        root_causes: dict[str, int] = {}
        for a in graph.analyses:
            if a.root_cause:
                root_causes[a.root_cause] = root_causes.get(a.root_cause, 0) + 1
        recurring = [rc for rc, c in root_causes.items()
                     if c >= 2]

        # Directions prometteuses = domaines pas encore touchés par des échecs
        # (heuristique simple — à enrichir avec SelfMap)
        failed_domains = set(graph.domains_affected)
        promising = []
        if self.selfmap:
            try:
                all_domains = {
                    c.domain for c in self.selfmap.db.get_all_competences()
                }
                promising = sorted(all_domains - failed_domains)
            except Exception as _exc:

                import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

        confidence = 0.3
        if graph.total_insights > 5:
            confidence = 0.5
        if graph.total_insights > 20:
            confidence = 0.7

        return HypothesisGuidance(
            avoid_patterns=avoid,
            promising_directions=promising,
            recurring_root_causes=recurring,
            total_failures_analyzed=len(graph.analyses),
            confidence=confidence,
        )

    # --- Hod du sentier : auto-diagnostic ---

    def self_diagnose(self) -> dict:
        """Le sentier Lamed s'examine lui-même — les 4 Qliphoth du sentier.

        Retourne les défaillances détectées dans FailureToInsight lui-même.
        """
        analyses = self.db.get_all_analyses()
        all_insights = self.db.get_all_insights()
        unextracted = self.db.get_unextracted()

        diagnostics = {"level": "healthy", "issues": []}

        # Mamash : échecs non analysés du tout
        # (on ne peut pas détecter ça ici — c'est l'appelant qui doit
        #  s'assurer que les échecs sont envoyés à analyze_failure)

        # Anan : fausses leçons — insights avec confiance > 0.8 mais
        # dont l'analysis est "unknown"
        false_lessons = [
            ins for ins in all_insights
            if ins.confidence >= 0.8
        ]
        unknown_analyses = [a for a in analyses if a.qliphah == "unknown"]
        for ins in false_lessons:
            for ua in unknown_analyses:
                if ins.analysis_id == ua.id:
                    diagnostics["issues"].append(
                        f"Anan: insight haute confiance ({ins.confidence}) "
                        f"sur analyse non classifiée"
                    )
                    diagnostics["level"] = "anan"

        # Ruach : mauvaise classification — ratio "unknown" trop élevé
        if analyses:
            unknown_ratio = len(unknown_analyses) / len(analyses)
            if unknown_ratio > self.max_unknown_ratio:
                diagnostics["issues"].append(
                    f"Ruach: {unknown_ratio:.0%} des analyses sont 'unknown' "
                    f"(seuil: {self.max_unknown_ratio:.0%})"
                )
                if diagnostics["level"] == "healthy":
                    diagnostics["level"] = "ruach"

        # Nogah : analyses superficielles
        shallow = [
            a for a in analyses
            if len(a.description) < self.min_description_length
        ]
        if shallow:
            diagnostics["issues"].append(
                f"Nogah: {len(shallow)} analyses avec description < "
                f"{self.min_description_length} caractères"
            )
            if diagnostics["level"] == "healthy":
                diagnostics["level"] = "nogah"

        # Check unextracted failures
        if unextracted:
            diagnostics["issues"].append(
                f"{len(unextracted)} analyses sans insights extraits"
            )

        return diagnostics

    # --- Internal ---

    def _extract_root_cause(
        self, description: str, qliphah: str, context: dict | None
    ) -> str | None:
        """Tenter d'extraire une cause racine de la description."""
        desc_lower = description.lower()

        # Patterns simples pour extraction de root cause
        cause_markers = [
            "because", "parce que", "caused by", "causé par",
            "due to", "dû à", "reason:", "raison:", "cause:",
            "— reason:", "— cause:",
        ]
        for marker in cause_markers:
            idx = desc_lower.find(marker)
            if idx >= 0:
                cause = description[idx + len(marker):].strip()
                # Prendre jusqu'au prochain point ou fin
                end = cause.find(".")
                if end > 0:
                    cause = cause[:end]
                return cause.strip() if cause.strip() else None

        return None

    def report(self) -> str:
        """Rapport lisible — Malkhut du sentier Lamed."""
        analyses = self.db.get_all_analyses()
        insights = self.db.get_all_insights()
        edges = self.db.get_all_edges()
        qliphah_counts = self.db.count_by_qliphah()
        diag = self.self_diagnose()

        lines = [
            "=== FailureToInsight Report (Sentier Lamed) ===",
            f"Analyses: {len(analyses)}",
            f"Nitzotzot extraits: {len(insights)}",
            f"Liens dans le graphe: {len(edges)}",
            f"Self-diagnosis: {diag['level']}",
            "",
            "Qliphoth distribution:",
        ]
        for q, c in sorted(qliphah_counts.items(), key=lambda x: -x[1]):
            lines.append(f"  {q}: {c}")

        if diag["issues"]:
            lines.append("")
            lines.append("Issues:")
            for issue in diag["issues"]:
                lines.append(f"  - {issue}")

        return "\n".join(lines)
