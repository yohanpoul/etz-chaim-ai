"""LoopRunner — Le Karpathy Loop généralisé.

Le cycle autonome :
1. Lire l'état actuel
2. Former une hypothèse (guidée par le graphe d'échecs)
3. Modifier le contenu
4. Évaluer le résultat (multi-sephirothique)
5. Décider : accepted / rejected / quarantined / tension_detected
6. Si rejeté → sentier Lamed (FailureToInsight)
7. Boucler

"Le Karpathy Loop est du Gevurah pur : le jugement qui dit NON
à sa propre production quand elle n'est pas assez bonne."
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from difflib import SequenceMatcher

from autojudge.domains.base import DomainJudge
from autojudge.evaluator import MultiSephirothEvaluator
from autojudge.lamed_bridge import LamedBridge
from autojudge.models import IterationResult, LoopResult

log = logging.getLogger(__name__)


class LoopRunner:
    """Le Karpathy Loop généralisé — le cœur de Gevurah."""

    # Similarity above this threshold = "same hypothesis"
    SIMILARITY_THRESHOLD = 0.65
    # Max retries on the same theme before forcing skip
    MAX_THEME_RETRIES = 2

    def __init__(
        self,
        domain: DomainJudge,
        evaluator: MultiSephirothEvaluator,
        lamed_bridge: LamedBridge | None = None,
        domain_id: str = "default",
        on_iteration: Callable[[IterationResult], None] | None = None,
    ):
        self.domain = domain
        self.evaluator = evaluator
        self.lamed = lamed_bridge
        self.domain_id = domain_id
        self.on_iteration = on_iteration
        self._session_hypotheses: list[str] = []

    def run(
        self,
        content: str,
        n_iterations: int = 10,
        budget_seconds: float = 300.0,
    ) -> LoopResult:
        """Exécuter le Karpathy Loop.

        Boucle jusqu'à n_iterations ou épuisement du budget temps.
        Chaque itération : hypothèse → modification → évaluation → décision.
        """
        current = content
        iterations: list[IterationResult] = []
        start_time = time.time()

        for i in range(n_iterations):
            # Check budget
            elapsed = time.time() - start_time
            if elapsed >= budget_seconds:
                break

            result = self._run_iteration(current, i)
            iterations.append(result)

            if self.on_iteration:
                try:
                    self.on_iteration(result)
                except Exception as _exc:

                    import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

            if result.decision == "accepted":
                current = self._get_modified(current, result.hypothesis)

        return LoopResult(
            final_content=current,
            iterations=iterations,
        )

    def _is_duplicate_hypothesis(self, hypothesis: str) -> bool:
        """Check if this hypothesis is too similar to one already tested."""
        h_norm = hypothesis.strip().lower()
        for prev in self._session_hypotheses:
            ratio = SequenceMatcher(None, h_norm, prev.strip().lower()).ratio()
            if ratio >= self.SIMILARITY_THRESHOLD:
                return True
        return False

    def _count_theme_retries(self, hypothesis: str) -> int:
        """Count how many similar hypotheses were already tested."""
        h_norm = hypothesis.strip().lower()
        count = 0
        for prev in self._session_hypotheses:
            ratio = SequenceMatcher(None, h_norm, prev.strip().lower()).ratio()
            if ratio >= 0.45:  # looser threshold for "same theme"
                count += 1
        return count

    def _run_iteration(self, current: str, iteration: int) -> IterationResult:
        """Exécuter une seule itération du loop."""

        # 1. Chokmah : hypothèse (with diversity guard)
        hypothesis = self.domain.generate_hypothesis(current)

        # Anti-repetition: skip if too similar to already-tested
        retries = 0
        while self._is_duplicate_hypothesis(hypothesis) and retries < 3:
            log.info(
                "Loop iter %d: duplicate hypothesis detected (retry %d/3), "
                "regenerating", iteration, retries + 1,
            )
            hypothesis = self.domain.generate_hypothesis(
                current + f"\n[AVOID REPEATING: {hypothesis[:100]}]"
            )
            retries += 1

        # Theme saturation: if same theme hit MAX_THEME_RETRIES, force skip
        if self._count_theme_retries(hypothesis) >= self.MAX_THEME_RETRIES:
            log.info(
                "Loop iter %d: theme saturated (%d retries), skipping",
                iteration, self.MAX_THEME_RETRIES,
            )
            from autojudge.models import DomainScore, MultiScore
            self._session_hypotheses.append(hypothesis)
            return IterationResult(
                iteration=iteration,
                hypothesis=hypothesis,
                domain_score=DomainScore(
                    quality=0.0,
                    metrics={"novelty": 0.0, "skipped": True},
                    explanation="Theme saturated — skipped to force diversity",
                ),
                multi_score=MultiScore(
                    gevurah=0.0, chesed=0.0, tiferet=0.0, hod=0.0, yesod=0.0,
                ),
                decision="rejected",
                failure_analysis_id=None,
                nitzotzot_extracted=False,
                explanation="Theme saturated — skipped to force diversity",
            )

        self._session_hypotheses.append(hypothesis)

        # 2. Yetzirah : modification
        modified = self.domain.apply_modification(current, hypothesis)

        # 3. Gevurah : évaluation du domaine
        domain_score = self.domain.evaluate(current, modified)

        # 4. Évaluation multi-sephirothique
        multi_score = self.evaluator.evaluate(domain_score, current, modified)

        # 5. Taux de rejet récent (anti-Golachab)
        recent_rejected = sum(
            1 for it in self._recent_iterations(10)
            if it.decision == "rejected"
        )
        recent_total = len(self._recent_iterations(10))
        rejection_rate = recent_rejected / max(recent_total, 1)

        # 6. Tiferet : décision harmonisée
        decision = self.evaluator.holistic_decision(multi_score, rejection_rate)

        # 7. Sentier Lamed si rejeté
        failure_id = None
        nitzotzot = False
        if decision == "rejected" and self.lamed:
            failure_id, nitzotzot = self.lamed.process_rejection(
                domain_id=self.domain_id,
                hypothesis=hypothesis,
                original=current,
                modified=modified,
                multi_score=multi_score,
                explanation=domain_score.explanation,
            )
        elif decision == "quarantined" and self.lamed:
            failure_id, nitzotzot = self.lamed.process_quarantine(
                domain_id=self.domain_id,
                hypothesis=hypothesis,
                multi_score=multi_score,
            )

        result = IterationResult(
            iteration=iteration,
            hypothesis=hypothesis,
            domain_score=domain_score,
            multi_score=multi_score,
            decision=decision,
            failure_analysis_id=failure_id,
            nitzotzot_extracted=nitzotzot,
            explanation=domain_score.explanation,
        )

        self._iteration_history.append(result)
        return result

    def _get_modified(self, current: str, hypothesis: str) -> str:
        """Re-apply modification for accepted hypothesis."""
        return self.domain.apply_modification(current, hypothesis)

    def _recent_iterations(self, n: int) -> list[IterationResult]:
        """Get the last N iterations from history."""
        return self._iteration_history[-n:]

    @property
    def _iteration_history(self) -> list[IterationResult]:
        if not hasattr(self, "_history"):
            self._history: list[IterationResult] = []
        return self._history
