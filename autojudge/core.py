"""AutoJudge — Le cœur de Gevurah.

Le Karpathy Loop généralisé avec :
- Évaluation multi-sephirothique (5 axes)
- Sentier Lamed branché (rejets → FailureToInsight → Nitzotzot)
- Anti-Golachab (surveillance du sur-filtrage)
- 7 paramètres Omer de Gevurah

Connexions sephirothiques :
  - Gevurah → Yesod (Tsadi) : persistance des résultats
  - Gevurah → Hod (Peh) : SelfMap consulté avant chaque loop
  - Gevurah → Netzach (Kaph) : IntentKeeper gère les loops longues
  - Gevurah → Tiferet (Lamed) : rejets → FailureToInsight → DissensuEngine
"""

from __future__ import annotations

from collections.abc import Callable

from autojudge.db import AutoJudgeDB
from autojudge.domains.base import DomainJudge
from autojudge.evaluator import MultiSephirothEvaluator
from autojudge.lamed_bridge import LamedBridge
from autojudge.loop import LoopRunner
from autojudge.models import IterationResult, LoopResult
from omer import get_param

# Omer de Gevurah — 7 paramètres de calibration (hardcoded defaults as fallback)
DEFAULT_QUARANTINE_THRESHOLD = 0.4       # Chesed-dans-Gevurah
DEFAULT_QUALITY_THRESHOLD = 0.6          # Gevurah-dans-Gevurah
DEFAULT_TENSION_CHECK_ENABLED = True     # Tiferet-dans-Gevurah
DEFAULT_MAX_ITERATIONS = 50              # Netzach-dans-Gevurah
DEFAULT_EXPLAIN_REJECTIONS = True        # Hod-dans-Gevurah
DEFAULT_PERSIST_ALL_EXPERIMENTS = True   # Yesod-dans-Gevurah
DEFAULT_REPORT_FORMAT = "summary"        # Malkuth-dans-Gevurah

_MODULE = "autojudge"
_UNSET = object()  # sentinel for "caller didn't provide a value"


class AutoJudge:
    """Le Tikkun de Gevurah — auto-jugement generalisé.

    Orchestre le Karpathy Loop pour n'importe quel domaine,
    avec évaluation multi-sephirothique et sentier Lamed branché.
    """

    def __init__(
        self,
        db_url: str,
        memory=None,
        selfmap=None,
        intentkeeper=None,
        failuretoinsight=None,
        quarantine_threshold: float = _UNSET,
        quality_threshold: float = _UNSET,
        tension_check_enabled: bool = _UNSET,
        max_iterations: int = _UNSET,
        explain_rejections: bool = _UNSET,
        persist_all_experiments: bool = _UNSET,
        report_format: str = _UNSET,
    ):
        self.db = AutoJudgeDB(db_url)
        self.memory = memory
        self.selfmap = selfmap
        self.intentkeeper = intentkeeper
        self.failuretoinsight = failuretoinsight
        self.dissensus = None                     # Tiferet (injection tardive)

        # Omer — DB overrides when caller uses default, explicit values preserved.
        self.quarantine_threshold = quarantine_threshold if quarantine_threshold is not _UNSET else get_param(_MODULE, "quarantine_threshold", DEFAULT_QUARANTINE_THRESHOLD)
        self.quality_threshold = quality_threshold if quality_threshold is not _UNSET else get_param(_MODULE, "quality_threshold", DEFAULT_QUALITY_THRESHOLD)
        self.tension_check_enabled = tension_check_enabled if tension_check_enabled is not _UNSET else get_param(_MODULE, "tension_check_enabled", DEFAULT_TENSION_CHECK_ENABLED)
        self.max_iterations = max_iterations if max_iterations is not _UNSET else get_param(_MODULE, "max_iterations", DEFAULT_MAX_ITERATIONS)
        self.explain_rejections = explain_rejections if explain_rejections is not _UNSET else get_param(_MODULE, "explain_rejections", DEFAULT_EXPLAIN_REJECTIONS)
        self.persist_all_experiments = persist_all_experiments if persist_all_experiments is not _UNSET else get_param(_MODULE, "persist_all_experiments", DEFAULT_PERSIST_ALL_EXPERIMENTS)
        self.report_format = report_format if report_format is not _UNSET else get_param(_MODULE, "report_format", DEFAULT_REPORT_FORMAT)

        # Evaluator (uses resolved Omer values)
        self.evaluator = MultiSephirothEvaluator(
            quality_threshold=self.quality_threshold,
            quarantine_threshold=self.quarantine_threshold,
            tension_check_enabled=self.tension_check_enabled,
        )

        # Lamed bridge
        self.lamed = LamedBridge(failure_to_insight=failuretoinsight)

    def register_domain(
        self,
        domain_id: str,
        display_name: str,
        loss_function: str,
        config: dict | None = None,
    ):
        """Enregistrer un domaine d'auto-jugement."""
        return self.db.upsert_domain(domain_id, display_name, loss_function, config)

    def run_loop(
        self,
        domain_judge: DomainJudge,
        content: str,
        domain_id: str = "default",
        n_iterations: int | None = None,
        budget_seconds: float = 300.0,
        on_iteration: Callable[[IterationResult], None] | None = None,
    ) -> LoopResult:
        """Exécuter le Karpathy Loop pour un domaine donné.

        Le cœur de Gevurah : hypothèse → modification → test → évaluer
        → garder ou rejeter. Chaque rejet passe par le sentier Lamed.
        """
        n = n_iterations or self.max_iterations

        runner = LoopRunner(
            domain=domain_judge,
            evaluator=self.evaluator,
            lamed_bridge=self.lamed,
            domain_id=domain_id,
            on_iteration=on_iteration,
        )

        result = runner.run(content, n_iterations=n, budget_seconds=budget_seconds)

        # Persister les expériences en DB
        if self.persist_all_experiments:
            self._persist_loop(domain_id, result)

        # Persister en EpisteMemory si connecté
        if self.memory and result.accepted > 0:
            self.memory.remember(
                content=f"AutoJudge loop completed: {result.accepted} accepted, "
                        f"{result.rejected} rejected out of {result.total} iterations "
                        f"in domain '{domain_id}'",
                source_sephirah="gevurah",
                confidence=0.6,
                domain=domain_id,
                tags=["autojudge", "loop_result"],
                ttl_days=180,
            )

        return result

    def _persist_loop(self, domain_id: str, result: LoopResult):
        """Persister toutes les itérations d'un loop en DB."""
        for it in result.iterations:
            self.db.create_experiment(
                domain_id=domain_id,
                hypothesis=it.hypothesis,
                score_gevurah=it.multi_score.gevurah,
                score_chesed=it.multi_score.chesed,
                score_tiferet=it.multi_score.tiferet,
                score_hod=it.multi_score.hod,
                score_yesod=it.multi_score.yesod,
                score_overall=it.multi_score.overall,
                decision=it.decision,
                failure_analysis_id=it.failure_analysis_id,
                nitzotzot_extracted=it.nitzotzot_extracted,
                loop_iteration=it.iteration,
            )

    def self_diagnose(self) -> dict:
        """Auto-diagnostic de Gevurah — les 4 niveaux de Golachab.

        Golachab (les Incendiaires) : Gevurah qui détruit au lieu de filtrer.
        """
        diagnostics = {"level": "healthy", "issues": []}

        all_decisions = self.db.count_by_decision()
        total = sum(all_decisions.values())

        if total == 0:
            return diagnostics

        rejected = all_decisions.get("rejected", 0)
        accepted = all_decisions.get("accepted", 0)
        rejection_rate = rejected / total

        # Nogah : taux de rejet élevé mais résultats OK
        if rejection_rate > 0.7:
            diagnostics["issues"].append(
                f"Nogah: taux de rejet élevé ({rejection_rate:.0%}), "
                f"vérifier si les critères sont trop stricts"
            )
            diagnostics["level"] = "nogah"

        # Ruach : rejets non analysés (Nitzotzot perdues)
        unanalyzed = self.db.get_unanalyzed_rejections()
        if unanalyzed:
            diagnostics["issues"].append(
                f"Ruach: {len(unanalyzed)} rejets sans analyse Lamed "
                f"(Nitzotzot perdues)"
            )
            if diagnostics["level"] == "healthy":
                diagnostics["level"] = "ruach"

        # Anan : 0 acceptés sur 10+ itérations sans alerte
        if total >= 10 and accepted == 0:
            diagnostics["issues"].append(
                "Anan: 0 expériences acceptées sur "
                f"{total} itérations — Gevurah est devenu destructeur"
            )
            diagnostics["level"] = "anan"

        # Mamash : le critère de rejet rejette aussi ses propres corrections
        # Détecté quand les expériences avec les meilleurs scores sont rejetées
        experiments = self.db.get_experiments(limit=20)
        rejected_with_ok_score = [
            e for e in experiments
            if e.decision == "rejected" and e.score_overall
            and e.score_overall > self.quality_threshold
        ]
        if rejected_with_ok_score:
            diagnostics["issues"].append(
                f"Mamash: {len(rejected_with_ok_score)} expériences rejetées "
                f"malgré score > seuil ({self.quality_threshold}) — "
                f"le juge se juge lui-même à tort"
            )
            diagnostics["level"] = "mamash"

        return diagnostics

    def report(self, domain_id: str | None = None) -> str:
        """Rapport lisible — Malkhut de Gevurah."""
        decisions = self.db.count_by_decision(domain_id)
        total = sum(decisions.values())
        diag = self.self_diagnose()

        lines = [
            "=== AutoJudge Report (Gevurah) ===",
            f"Total experiments: {total}",
        ]

        for d in ["accepted", "rejected", "quarantined", "tension_detected"]:
            count = decisions.get(d, 0)
            pct = f" ({count/total:.0%})" if total > 0 else ""
            lines.append(f"  {d}: {count}{pct}")

        if domain_id:
            rate = self.db.get_rejection_rate(domain_id)
            lines.append(f"\nRejection rate ({domain_id}): {rate:.0%}")

        lines.append(f"\nSelf-diagnosis: {diag['level']}")
        if diag["issues"]:
            lines.append("Issues:")
            for issue in diag["issues"]:
                lines.append(f"  - {issue}")

        # Lamed status
        if self.failuretoinsight:
            unanalyzed = self.db.get_unanalyzed_rejections(domain_id)
            lines.append(f"\nSentier Lamed: connected")
            lines.append(f"  Unanalyzed rejections: {len(unanalyzed)}")
        else:
            lines.append(f"\nSentier Lamed: disconnected")

        return "\n".join(lines)
