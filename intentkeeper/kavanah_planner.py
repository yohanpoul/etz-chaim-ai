"""KavanahPlanner — Tiferet-de-Netzach : l'intention structurée par la connaissance.

La Kavanah kabbalistique n'est pas un voeu — c'est l'intention
qui connaît son chemin. Chaque intention est couplée aux métriques
réelles du système (SelfMap, CausalEngine, EpisteMemory).

Le KavanahPlanner résout le bug de refresh_progress_from_state :
au lieu de requêter les domaines ACTUELLEMENT faibles (tautologiquement 0),
il lit les CIBLES depuis les sous-tâches et mesure le progrès réel.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

import psycopg2
import psycopg2.extras

log = logging.getLogger(__name__)


# ── Modèles ────────────────────────────────────────────────────

@dataclass
class KavanahSubgoal:
    """Un sous-objectif concret dérivé de l'intention + métriques."""
    domain: str          # domaine SelfMap ou métrique cible
    current: float       # valeur actuelle
    target: float        # seuil à atteindre
    reached: bool        # current >= target

    @property
    def gap(self) -> float:
        return max(0.0, self.target - self.current)


@dataclass
class KavanahPlan:
    """Plan dérivé d'une intention + état du système."""
    intention_goal: str
    subgoals: list[KavanahSubgoal] = field(default_factory=list)
    progress: float = 0.0  # fraction des subgoals atteints
    suggested_action: str | None = None

    @property
    def n_reached(self) -> int:
        return sum(1 for s in self.subgoals if s.reached)


# ── Parsers — extraire les cibles depuis les sous-tâches ─────

_RE_DOMAIN_TARGET = re.compile(
    r"Domaine '([^']+)' de [\d.]+ → ([\d.]+)"
)

_RE_NITZOTZOT = re.compile(
    r"Nitzotzot (\d+) → (\d+)"
)


def _parse_domain_subtasks(subtask_descriptions: list[str]) -> list[tuple[str, float]]:
    """Extraire (domaine, cible) depuis les descriptions de sous-tâches."""
    results = []
    for desc in subtask_descriptions:
        m = _RE_DOMAIN_TARGET.search(desc)
        if m:
            results.append((m.group(1), float(m.group(2))))
    return results


# ── KavanahPlanner ──────────────────────────────────────────────

class KavanahPlanner:
    """Kavanah = intention + connaissance du chemin.

    Couple chaque intention à l'état réel du système pour :
    1. Dériver un plan concret (subgoals mesurables)
    2. Recalculer le progrès depuis les métriques vivantes
    3. Suggérer la prochaine action
    """

    def __init__(self, db_url: str):
        self.db_url = db_url

    def derive_plan(
        self,
        intention_goal: str,
        subtask_descriptions: list[str],
    ) -> KavanahPlan:
        """Dériver un plan depuis l'intention et ses sous-tâches.

        Lit l'état actuel des métriques pour chaque cible.
        """
        from pool import get_conn, init_pool
        init_pool(self.db_url)  # idempotent

        with get_conn() as conn:
            if "domaines faibles" in intention_goal:
                return self._plan_domains(conn, intention_goal, subtask_descriptions)
            elif "claims causaux" in intention_goal:
                return self._plan_causal(conn, intention_goal)
            elif "Ohr Pnimi" in intention_goal:
                return self._plan_ohr(conn, intention_goal)
            elif "288 Nitzotzot" in intention_goal:
                return self._plan_nitzotzot(conn, intention_goal, subtask_descriptions)
            elif "Omer" in intention_goal:
                return self._plan_omer(conn, intention_goal)
            else:
                return KavanahPlan(intention_goal=intention_goal)

    def update_progress(
        self,
        intention_goal: str,
        subtask_descriptions: list[str],
    ) -> float:
        """Recalculer le progrès réel depuis les métriques système.

        Retourne le nouveau progrès (0.0 - 1.0).
        """
        plan = self.derive_plan(intention_goal, subtask_descriptions)
        return plan.progress

    def suggest_next_action(
        self,
        intention_goal: str,
        subtask_descriptions: list[str],
    ) -> str:
        """Retourner une action concrète pour avancer."""
        plan = self.derive_plan(intention_goal, subtask_descriptions)
        if plan.suggested_action:
            return plan.suggested_action
        if plan.progress >= 1.0:
            return "Intention atteinte — compléter."
        return "Continuer le travail sur les sous-objectifs restants."

    # ── Plans par type d'intention ──────────────────────────────

    def _plan_domains(
        self,
        conn,
        goal: str,
        subtask_descriptions: list[str],
    ) -> KavanahPlan:
        """Domaines faibles — lire les cibles depuis les sous-tâches,
        vérifier les scores actuels dans selfmap_competence."""
        targets = _parse_domain_subtasks(subtask_descriptions)
        if not targets:
            return KavanahPlan(intention_goal=goal)

        # Lire les scores actuels
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT domain, score FROM selfmap_competence"
            )
            current_scores = {r["domain"]: r["score"] for r in cur.fetchall()}

        subgoals = []
        for domain, target in targets:
            current = current_scores.get(domain, 0.0)
            subgoals.append(KavanahSubgoal(
                domain=domain,
                current=current,
                target=target,
                reached=current >= target,
            ))

        plan = KavanahPlan(
            intention_goal=goal,
            subgoals=subgoals,
        )

        if subgoals:
            plan.progress = plan.n_reached / len(subgoals)

        # Suggérer l'action sur le domaine avec le plus grand gap
        remaining = [s for s in subgoals if not s.reached]
        if remaining:
            worst = max(remaining, key=lambda s: s.gap)
            plan.suggested_action = (
                f"Poser 20 questions Hitbonenut ciblées sur {worst.domain} "
                f"(actuellement {worst.current:.3f}, cible {worst.target})"
            )
        else:
            plan.suggested_action = "Tous les domaines sont au-dessus du seuil."

        return plan

    def _plan_causal(self, conn, goal: str) -> KavanahPlan:
        """Claims causaux — mesurer la fraction au-delà de correlation_only."""
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT count(*) AS total FROM causal_claims")
            total = cur.fetchone()["total"]

            cur.execute(
                "SELECT count(*) AS n FROM causal_claims "
                "WHERE evidence_level != 'correlation_only'"
            )
            elevated = cur.fetchone()["n"]

        if total == 0:
            return KavanahPlan(intention_goal=goal, progress=0.0)

        target_ratio = 0.5
        current_ratio = elevated / total
        progress = min(1.0, current_ratio / target_ratio) if target_ratio > 0 else 0.0

        plan = KavanahPlan(
            intention_goal=goal,
            subgoals=[KavanahSubgoal(
                domain="causal_claims",
                current=current_ratio,
                target=target_ratio,
                reached=current_ratio >= target_ratio,
            )],
            progress=progress,
        )

        remaining = total - elevated
        plan.suggested_action = (
            f"Lancer confounder_detection sur les {remaining} claims "
            f"restants à correlation_only"
        )
        return plan

    def _plan_ohr(self, conn, goal: str) -> KavanahPlan:
        """Ohr Pnimi — ratio mémoire intégrée / totale."""
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    COUNT(*) FILTER (
                        WHERE confidence >= 0.6
                          AND epistemic_status IN (
                              'fact', 'verified_once', 'verified_multi'
                          )
                    ) AS pnimi,
                    COUNT(*) AS total
                FROM epistememory
            """)
            row = cur.fetchone()

        total = row["total"]
        pnimi = row["pnimi"]
        rate = pnimi / total if total > 0 else 0.0
        target = 0.80
        progress = min(1.0, rate / target) if target > 0 else 0.0

        plan = KavanahPlan(
            intention_goal=goal,
            subgoals=[KavanahSubgoal(
                domain="ohr_pnimi",
                current=rate,
                target=target,
                reached=rate >= target,
            )],
            progress=progress,
        )

        makif = total - pnimi
        plan.suggested_action = (
            f"Vérifier et élever {makif} faits Ohr Makif "
            f"(ratio actuel: {rate:.2%}, cible: {target:.0%})"
        )
        return plan

    def _plan_nitzotzot(
        self,
        conn,
        goal: str,
        subtask_descriptions: list[str],
    ) -> KavanahPlan:
        """Nitzotzot — compter les insights récoltés."""
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT count(*) AS total FROM failuretoinsight_insights")
            total = cur.fetchone()["total"]

        count = total % 288
        progress = min(1.0, count / 288)

        plan = KavanahPlan(
            intention_goal=goal,
            subgoals=[KavanahSubgoal(
                domain="nitzotzot",
                current=count,
                target=288,
                reached=count >= 288,
            )],
            progress=progress,
        )

        remaining = 288 - count
        plan.suggested_action = (
            f"Récolter {remaining} Nitzotzot supplémentaires "
            f"(actuellement {count}/288)"
        )
        return plan

    def _plan_omer(self, conn, goal: str) -> KavanahPlan:
        """Omer — jours comptés."""
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT count(*) AS n FROM omer_history")
            count = cur.fetchone()["n"]

        progress = min(1.0, count / 49)
        plan = KavanahPlan(
            intention_goal=goal,
            subgoals=[KavanahSubgoal(
                domain="omer",
                current=count,
                target=49,
                reached=count >= 49,
            )],
            progress=progress,
        )

        remaining = 49 - count
        plan.suggested_action = (
            f"Compter {remaining} jours d'Omer restants ({count}/49)"
        )
        return plan
