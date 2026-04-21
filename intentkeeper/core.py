"""IntentKeeper — Tikkun de Netzach.

Moïse dans le désert 40 ans. Pas un sprint — une marche.
Le système qui maintient un but sur des semaines et sait quand abandonner.

Sentiers :
  - 28e Tsadi צ (Netzach→Yesod) : CheckpointWrite — persist to EpisteMemory
  - 27e Ayin ע (Netzach→Hod)    : StatusSync — check competence via SelfMap
"""

from __future__ import annotations

import logging
from uuid import UUID

from intentkeeper.db import IntentKeeperDB
from intentkeeper.models import (
    AbandonDecision,
    Intention,
    NewStrategy,
    ProgressReport,
    SubTask,
)

log = logging.getLogger(__name__)

# Omer de Netzach — 7 paramètres de calibration
DEFAULT_MAX_DURATION_DAYS = 90
DEFAULT_ABANDON_THRESHOLD = 0.2
DEFAULT_MAX_RETRIES = 3
DEFAULT_STALE_DAYS = 7       # jours sans activité avant warning
DEFAULT_ZOMBIE_DAYS = 180    # jours sans activité = Mamash
DEFAULT_MIN_PROGRESS_AT_QUARTER = 0.10  # progrès minimum à 25% du temps
DEFAULT_MAX_FAILED_RATIO = 0.6  # ratio max échecs/total avant Ruach


class IntentKeeper:
    """Persistance adaptative — Netzach avec critère d'abandon."""

    def __init__(
        self,
        db_url: str,
        selfmap=None,
        memory=None,
        stale_days: float = DEFAULT_STALE_DAYS,
        zombie_days: float = DEFAULT_ZOMBIE_DAYS,
        min_progress_at_quarter: float = DEFAULT_MIN_PROGRESS_AT_QUARTER,
        max_failed_ratio: float = DEFAULT_MAX_FAILED_RATIO,
    ):
        self.db = IntentKeeperDB(db_url)
        self.selfmap = selfmap   # Hod — sentier Ayin ע
        self.memory = memory     # Yesod — sentier Tsadi צ
        self.exploration = None  # Chesed (injection tardive)
        self.stale_days = stale_days
        self.zombie_days = zombie_days
        self.min_progress_at_quarter = min_progress_at_quarter
        self.max_failed_ratio = max_failed_ratio

    # --- Intention lifecycle ---

    def set_intention(
        self,
        goal: str,
        max_duration_days: int = DEFAULT_MAX_DURATION_DAYS,
        abandon_threshold: float = DEFAULT_ABANDON_THRESHOLD,
        strategy: str | None = None,
    ) -> Intention | None:
        """Créer une intention persistante.

        Sentier Ayin (Netzach→Hod) : vérifie la compétence via SelfMap.
        Sentier Tsadi (Netzach→Yesod) : persiste le checkpoint en mémoire.
        """
        # Garde Tzimtzum — Netzach dormant pendant la contraction
        try:
            from tzimtzum import is_module_active
            if not is_module_active("netzach"):
                log.info("Netzach dormant (Tzimtzum contraction) — set_intention() skipped")
                return None
        except Exception as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)  # Tzimtzum unavailable = module active

        intention = self.db.create_intention(
            goal=goal,
            max_duration_days=max_duration_days,
            abandon_threshold=abandon_threshold,
            strategy=strategy,
        )
        self.db.record_heartbeat(
            intention.id, "checkpoint", {"event": "intention_created", "goal": goal}
        )

        # Sentier Tsadi — checkpoint en EpisteMemory
        if self.memory:
            self.memory.remember(
                content=f"IntentKeeper: nouvelle intention '{goal}' "
                        f"(max {max_duration_days}j, abandon@{abandon_threshold})",
                source_sephirah="netzach",
                confidence=0.5,
                domain="intentkeeper",
                tags=["intention", "created"],
                ttl_days=max_duration_days,
            )

        return intention

    def add_subtask(
        self,
        intention_id: UUID,
        description: str,
        order_index: int,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> SubTask:
        """Ajouter une sous-tâche à une intention."""
        intention = self.db.get_intention(intention_id)
        if not intention:
            raise ValueError(f"Intention {intention_id} not found")
        return self.db.add_subtask(
            intention_id=intention_id,
            description=description,
            order_index=order_index,
            strategy_version=intention.strategy_version,
            max_retries=max_retries,
        )

    def start_subtask(self, subtask_id: UUID):
        """Démarrer une sous-tâche."""
        self.db.update_subtask_status(subtask_id, "in_progress")
        # Find intention_id for heartbeat
        with self.db._cursor() as cur:
            cur.execute(
                "SELECT intention_id FROM intentkeeper_subtasks WHERE id = %s",
                (subtask_id,),
            )
            row = cur.fetchone()
            if row:
                self.db.record_heartbeat(
                    row[0], "subtask_start", {"subtask_id": str(subtask_id)}
                )

    def complete_subtask(self, subtask_id: UUID, result: str | None = None):
        """Compléter une sous-tâche et recalculer le progrès."""
        self.db.update_subtask_status(subtask_id, "completed", result=result)
        with self.db._cursor() as cur:
            cur.execute(
                "SELECT intention_id FROM intentkeeper_subtasks WHERE id = %s",
                (subtask_id,),
            )
            row = cur.fetchone()
            if row:
                intention_id = row[0]
                self.db.record_heartbeat(
                    intention_id, "subtask_complete",
                    {"subtask_id": str(subtask_id)},
                )
                self._recalculate_progress(intention_id)

    def fail_subtask(self, subtask_id: UUID, reason: str | None = None):
        """Marquer une sous-tâche comme échouée."""
        retries = self.db.increment_retry(subtask_id)
        # Check max retries
        with self.db._cursor() as cur:
            cur.execute(
                "SELECT intention_id, max_retries FROM intentkeeper_subtasks WHERE id = %s",
                (subtask_id,),
            )
            row = cur.fetchone()
            if not row:
                return
            intention_id, max_retries = row
            if retries >= max_retries:
                self.db.update_subtask_status(
                    subtask_id, "failed", failure_reason=reason
                )
            else:
                # Reset to pending for retry
                self.db.update_subtask_status(subtask_id, "pending")
            self.db.record_heartbeat(
                intention_id, "subtask_fail",
                {"subtask_id": str(subtask_id), "reason": reason, "retry": retries},
            )

    def skip_subtask(self, subtask_id: UUID):
        """Passer une sous-tâche."""
        self.db.update_subtask_status(subtask_id, "skipped")

    # --- Progress & Monitoring ---

    def check_progress(self, intention_id: UUID) -> ProgressReport | None:
        """Évaluer le progrès — Hod-de-Netzach.

        Détecte le warning Nogah : progrès < min_progress_at_quarter à 25%+ du temps.
        """
        # Garde Tzimtzum — Netzach dormant pendant la contraction
        try:
            from tzimtzum import is_module_active
            if not is_module_active("netzach"):
                log.info("Netzach dormant (Tzimtzum contraction) — check_progress() skipped")
                return None
        except Exception as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)  # Tzimtzum unavailable = module active

        intention = self.db.get_intention(intention_id)
        if not intention:
            raise ValueError(f"Intention {intention_id} not found")

        time_ratio = self.db.get_time_elapsed_ratio(intention_id)
        days_inactive = self.db.days_since_activity(intention_id)

        # Qlipat Nogah : progrès lent
        warning = None
        is_on_track = True
        if time_ratio >= 0.25 and intention.progress < self.min_progress_at_quarter:
            warning = (
                f"Nogah: progrès {intention.progress:.0%} après "
                f"{time_ratio:.0%} du temps écoulé "
                f"(seuil: {self.min_progress_at_quarter:.0%} à 25%)"
            )
            is_on_track = False

        self.db.record_heartbeat(
            intention_id, "progress_check",
            {"progress": intention.progress, "time_ratio": time_ratio},
        )

        return ProgressReport(
            intention_id=intention.id,
            goal=intention.goal,
            progress=intention.progress,
            time_elapsed_ratio=time_ratio,
            subtasks_completed=intention.completed_subtasks,
            subtasks_total=intention.total_subtasks,
            subtasks_failed=intention.failed_subtasks,
            strategy_version=intention.strategy_version,
            is_on_track=is_on_track,
            warning=warning,
            days_since_activity=days_inactive,
        )

    def should_abandon(self, intention_id: UUID) -> AbandonDecision | None:
        """Le critère d'abandon — anti-A'arab Zaraq.

        4 niveaux (du plus grave au moins grave) :
        - Mamash : zombie — aucune activité depuis zombie_days
        - Anan : faux progrès — sous-tâches complétées mais progrès stagnant
        - Ruach : fuite de ressources — ratio échecs trop élevé
        - Nogah : progrès lent — warning seulement
        """
        # Garde Tzimtzum — Netzach dormant pendant la contraction
        try:
            from tzimtzum import is_module_active
            if not is_module_active("netzach"):
                log.info("Netzach dormant (Tzimtzum contraction) — should_abandon() skipped")
                return None
        except Exception as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)  # Tzimtzum unavailable = module active

        intention = self.db.get_intention(intention_id)
        if not intention:
            raise ValueError(f"Intention {intention_id} not found")

        time_ratio = self.db.get_time_elapsed_ratio(intention_id)
        days_inactive = self.db.days_since_activity(intention_id)

        # Mamash — zombie (le plus grave, vérifié en premier)
        if days_inactive >= self.zombie_days:
            return AbandonDecision(
                should_abandon=True,
                reason=f"Mamash: intention zombie — {days_inactive:.0f} jours "
                       f"sans activité (seuil: {self.zombie_days})",
                level="mamash",
                progress=intention.progress,
                time_elapsed_ratio=time_ratio,
                days_since_activity=days_inactive,
            )

        # Anan — faux progrès
        # Sous-tâches complétées mais progrès à 0 ou stagnant
        if (intention.completed_subtasks >= 3
                and intention.progress < 0.05
                and intention.total_subtasks > 0):
            return AbandonDecision(
                should_abandon=True,
                reason=f"Anan: faux progrès — {intention.completed_subtasks} "
                       f"sous-tâches complétées mais progrès = "
                       f"{intention.progress:.0%}",
                level="anan",
                progress=intention.progress,
                time_elapsed_ratio=time_ratio,
                days_since_activity=days_inactive,
            )

        # Ruach — fuite de ressources
        if intention.total_subtasks > 0:
            failed_ratio = intention.failed_subtasks / intention.total_subtasks
            if failed_ratio >= self.max_failed_ratio:
                return AbandonDecision(
                    should_abandon=True,
                    reason=f"Ruach: fuite de ressources — {intention.failed_subtasks}/"
                           f"{intention.total_subtasks} sous-tâches échouées "
                           f"({failed_ratio:.0%} >= {self.max_failed_ratio:.0%})",
                    level="ruach",
                    progress=intention.progress,
                    time_elapsed_ratio=time_ratio,
                    days_since_activity=days_inactive,
                )

        # Nogah — progrès lent (ne recommande pas l'abandon, juste le signale)
        if time_ratio >= 0.25 and intention.progress < self.min_progress_at_quarter:
            return AbandonDecision(
                should_abandon=False,
                reason=f"Nogah: progrès lent — {intention.progress:.0%} après "
                       f"{time_ratio:.0%} du temps",
                level="nogah",
                progress=intention.progress,
                time_elapsed_ratio=time_ratio,
                days_since_activity=days_inactive,
            )

        return AbandonDecision(
            should_abandon=False,
            reason=None,
            level="healthy",
            progress=intention.progress,
            time_elapsed_ratio=time_ratio,
            days_since_activity=days_inactive,
        )

    def abandon(self, intention_id: UUID, reason: str):
        """Abandonner une intention — l'acte de Gevurah-de-Netzach."""
        self.db.update_intention_status(intention_id, "abandoned", reason)

        # Sentier Tsadi — checkpoint
        if self.memory:
            intention = self.db.get_intention(intention_id)
            self.memory.remember(
                content=f"IntentKeeper: intention abandonnée — "
                        f"'{intention.goal}' — raison: {reason}",
                source_sephirah="netzach",
                confidence=0.7,
                domain="intentkeeper",
                tags=["intention", "abandoned"],
                ttl_days=365,
            )

    def complete(self, intention_id: UUID):
        """Compléter une intention — Netzach accompli."""
        self.db.update_intention_status(intention_id, "completed")
        self.db.update_progress(intention_id, 1.0)

        if self.memory:
            intention = self.db.get_intention(intention_id)
            self.memory.remember(
                content=f"IntentKeeper: intention complétée — '{intention.goal}'",
                source_sephirah="netzach",
                confidence=0.9,
                domain="intentkeeper",
                tags=["intention", "completed"],
                ttl_days=365,
            )

    # --- Adaptation ---

    def adapt_strategy(
        self,
        intention_id: UUID,
        failed_subtask_id: UUID,
        new_strategy: str,
        new_subtask_descriptions: list[str],
    ) -> NewStrategy | None:
        """Changer de stratégie après échec — pas retry, ADAPTATION.

        Skip les sous-tâches pending de l'ancienne stratégie.
        Crée de nouvelles sous-tâches pour la nouvelle stratégie.
        """
        # Garde Tzimtzum — Netzach dormant pendant la contraction
        try:
            from tzimtzum import is_module_active
            if not is_module_active("netzach"):
                log.info("Netzach dormant (Tzimtzum contraction) — adapt_strategy() skipped")
                return None
        except Exception as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)  # Tzimtzum unavailable = module active

        intention = self.db.get_intention(intention_id)
        if not intention:
            raise ValueError(f"Intention {intention_id} not found")

        old_strategy = intention.strategy
        old_version = intention.strategy_version
        new_version = old_version + 1

        # Skip les pending de l'ancienne stratégie
        self.db.skip_pending_subtasks(intention_id, old_version)

        # Mettre à jour la stratégie
        with self.db._cursor() as cur:
            cur.execute(
                """UPDATE intentkeeper_intentions
                   SET strategy = %s, strategy_version = %s, updated_at = NOW()
                   WHERE id = %s""",
                (new_strategy, new_version, intention_id),
            )

        # Créer les nouvelles sous-tâches
        for i, desc in enumerate(new_subtask_descriptions):
            self.db.add_subtask(
                intention_id=intention_id,
                description=desc,
                order_index=i,
                strategy_version=new_version,
            )

        self.db.record_heartbeat(
            intention_id, "strategy_change",
            {
                "old_version": old_version,
                "new_version": new_version,
                "reason": f"Failed subtask: {failed_subtask_id}",
            },
        )

        return NewStrategy(
            intention_id=intention_id,
            old_strategy=old_strategy,
            new_strategy=new_strategy,
            new_version=new_version,
            reason=f"Adaptation after subtask {failed_subtask_id} failed",
            new_subtasks=new_subtask_descriptions,
        )

    def report(self, intention_id: UUID) -> str:
        """Rapport lisible — Malkhut-de-Netzach."""
        intention = self.db.get_intention(intention_id)
        if not intention:
            return "Intention not found."

        time_ratio = self.db.get_time_elapsed_ratio(intention_id)
        days_inactive = self.db.days_since_activity(intention_id)
        abandon = self.should_abandon(intention_id)

        lines = [
            f"=== IntentKeeper Report ===",
            f"Goal: {intention.goal}",
            f"Status: {intention.status}",
            f"Progress: {intention.progress:.0%}",
            f"Time elapsed: {time_ratio:.0%}",
            f"Strategy v{intention.strategy_version}: {intention.strategy or 'N/A'}",
            f"Subtasks: {intention.completed_subtasks}/{intention.total_subtasks} "
            f"completed, {intention.failed_subtasks} failed",
            f"Days since activity: {days_inactive:.1f}",
            f"A'arab Zaraq level: {abandon.level}",
        ]
        if abandon.reason:
            lines.append(f"Warning: {abandon.reason}")
        return "\n".join(lines)

    # --- Internal ---

    def _recalculate_progress(self, intention_id: UUID):
        """Recalcule le progrès basé sur les sous-tâches."""
        intention = self.db.get_intention(intention_id)
        if not intention or intention.total_subtasks == 0:
            return
        # Progrès = sous-tâches terminées (completed + skipped) / total
        done = intention.completed_subtasks
        progress = done / intention.total_subtasks
        self.db.update_progress(intention_id, progress)

    # --- Auto-generation from system state ---

    def seed_system_intentions(self, db_url: str) -> list[Intention]:
        """Générer des intentions automatiques à partir de l'état du système.

        Netzach = endurance. Le gardien d'intention ne peut pas battre dans le vide.
        Il inspecte l'état réel du système et crée des intentions mesurables
        avec subtasks concrètes.

        Ne recrée PAS une intention dont le goal existe déjà (active ou completed).
        """
        # Garde Tzimtzum — Netzach dormant pendant la contraction
        try:
            from tzimtzum import is_module_active
            if not is_module_active("netzach"):
                log.info("Netzach dormant (Tzimtzum contraction) — seed_system_intentions() skipped")
                return []
        except Exception as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)  # Tzimtzum unavailable = module active

        import psycopg2.extras

        from pool import get_pool, init_pool

        # Emprunter au pool (via getconn/putconn) pour bénéficier du CB.
        # __init__ est idempotent. conn.close() plus bas sera intercepté
        # ci-dessous par un putconn pour retourner au pool.
        init_pool(db_url)
        _pool = get_pool()
        conn = _pool.getconn()
        conn.autocommit = True

        # Récupérer les goals existants pour éviter les doublons
        existing_goals = set()
        for intent in self.db.get_active_intentions():
            existing_goals.add(intent.goal)
        # Also check completed/abandoned to avoid re-seeding
        with self.db._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT goal FROM intentkeeper_intentions")
            for row in cur.fetchall():
                existing_goals.add(row["goal"])

        created = []
        metrics = _query_system_metrics(conn)

        # ── 1. Domaines faibles → score > 0.75 ──
        weak = metrics["weak_domains"]
        if weak:
            goal = "Maîtriser les domaines faibles — seuil 0.75"
            if goal not in existing_goals:
                intention = self.set_intention(
                    goal=goal,
                    max_duration_days=60,
                    abandon_threshold=0.15,
                    strategy="hitbonenut_ciblé",
                )
                for i, (domain, score) in enumerate(weak):
                    self.add_subtask(
                        intention.id,
                        f"Domaine '{domain}' de {score:.3f} → 0.75",
                        order_index=i,
                    )
                created.append(intention)
                log.info("Seeded intention: %s (%d subtasks)", goal, len(weak))

        # ── 2. Claims causaux → élever au-delà de correlation_only ──
        causal = metrics["causal_claims"]
        if causal["total"] > 0 and causal["correlation_ratio"] > 0.8:
            goal = "Élever 50% des claims causaux au-delà de correlation_only"
            if goal not in existing_goals:
                target = causal["total"] // 2
                intention = self.set_intention(
                    goal=goal,
                    max_duration_days=90,
                    abandon_threshold=0.2,
                    strategy="confounder_detection_+_evidence_scoring",
                )
                self.add_subtask(
                    intention.id,
                    f"Identifier confounders pour {min(target, 100)} claims",
                    order_index=0,
                )
                self.add_subtask(
                    intention.id,
                    f"Vérifier la direction causale pour {min(target, 100)} claims",
                    order_index=1,
                )
                self.add_subtask(
                    intention.id,
                    f"Élever {target} claims à probable_causation",
                    order_index=2,
                )
                created.append(intention)
                log.info("Seeded intention: %s", goal)

        # ── 3. Nitzotzot → compléter un cycle Tikkun (288) ──
        nitz = metrics["nitzotzot"]
        if nitz["cycle"] == 0:
            goal = "Récolter 288 Nitzotzot — premier cycle Tikkun"
            if goal not in existing_goals:
                remaining = 288 - nitz["count"]
                intention = self.set_intention(
                    goal=goal,
                    max_duration_days=120,
                    abandon_threshold=0.15,
                    strategy="auto_improve_loop",
                )
                # Subtasks par tranches de 50
                for i, start in enumerate(range(nitz["count"], 288, 50)):
                    end = min(start + 50, 288)
                    self.add_subtask(
                        intention.id,
                        f"Nitzotzot {start} → {end}",
                        order_index=i,
                    )
                created.append(intention)
                log.info("Seeded intention: %s (%d remaining)", goal, remaining)

        # ── 4. Mémoire → intégration (ratio Ohr Pnimi > 0.8) ──
        ohr = metrics["ohr_ratio"]
        if ohr["total"] > 50 and ohr["integration_rate"] < 0.8:
            goal = "Intégrer la mémoire — ratio Ohr Pnimi > 0.80"
            if goal not in existing_goals:
                intention = self.set_intention(
                    goal=goal,
                    max_duration_days=60,
                    abandon_threshold=0.2,
                    strategy="epistemic_verification",
                )
                self.add_subtask(
                    intention.id,
                    f"Vérifier {ohr['makif']} hypothèses en attente",
                    order_index=0,
                )
                self.add_subtask(
                    intention.id,
                    f"Élever le ratio d'intégration de {ohr['integration_rate']:.2f} → 0.80",
                    order_index=1,
                )
                created.append(intention)
                log.info("Seeded intention: %s", goal)

        # ── 5. Omer → compléter 49 jours ──
        omer = metrics["omer_count"]
        if omer < 49:
            goal = "Compléter le cycle Omer — 49 jours"
            if goal not in existing_goals:
                intention = self.set_intention(
                    goal=goal,
                    max_duration_days=90,
                    abandon_threshold=0.1,
                    strategy="daily_omer_count",
                )
                # Subtasks par semaine
                for i in range(7):
                    start_day = i * 7 + 1
                    end_day = min((i + 1) * 7, 49)
                    if start_day > 49:
                        break
                    status = "completed" if end_day <= omer else "pending"
                    st = self.add_subtask(
                        intention.id,
                        f"Semaine {i+1}: jours {start_day}-{end_day}",
                        order_index=i,
                    )
                    if status == "completed":
                        self.complete_subtask(st.id, result="déjà compté")
                created.append(intention)
                log.info("Seeded intention: %s (%d/49)", goal, omer)

        _pool.putconn(conn)
        return created

    def refresh_progress_from_state(self, db_url: str):
        """Met à jour le progrès des intentions actives depuis les métriques système.

        Utilise KavanahPlanner pour lire les cibles depuis les sous-tâches
        et mesurer le progrès réel (pas le tautologique 0 de l'ancienne version).
        """
        # Garde Tzimtzum — Netzach dormant pendant la contraction
        try:
            from tzimtzum import is_module_active
            if not is_module_active("netzach"):
                log.info("Netzach dormant (Tzimtzum contraction) — refresh_progress_from_state() skipped")
                return
        except Exception as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)  # Tzimtzum unavailable = module active

        from intentkeeper.kavanah_planner import KavanahPlanner

        planner = KavanahPlanner(db_url)

        for intention in self.db.get_active_intentions():
            subtasks = self.db.get_subtasks(intention.id)
            descriptions = [st.description for st in subtasks]

            new_progress = planner.update_progress(
                intention.goal, descriptions,
            )

            if new_progress != intention.progress:
                self.db.update_progress(intention.id, round(new_progress, 3))
                self.db.record_heartbeat(
                    intention.id, "progress_check",
                    {"old": intention.progress, "new": round(new_progress, 3),
                     "source": "kavanah_planner"},
                )


def _query_system_metrics(conn) -> dict:
    """Interroge la DB pour extraire les métriques système.

    Retourne un dict avec les clés :
    - weak_domains: list[(domain, score)] avec score < 0.75
    - causal_claims: {total, correlation_only, correlation_ratio}
    - nitzotzot: {count, cycle, total}
    - ohr_ratio: {pnimi, makif, total, integration_rate}
    - omer_count: int
    """
    import psycopg2.extras

    result = {
        "weak_domains": [],
        "causal_claims": {"total": 0, "correlation_only": 0, "correlation_ratio": 0.0},
        "nitzotzot": {"count": 0, "cycle": 0, "total": 0},
        "ohr_ratio": {"pnimi": 0, "makif": 0, "total": 0, "integration_rate": 0.0},
        "omer_count": 0,
    }

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        # 1. Domaines faibles (selfmap_competence)
        try:
            cur.execute(
                "SELECT domain, score FROM selfmap_competence "
                "WHERE score < 0.75 ORDER BY score"
            )
            result["weak_domains"] = [(r["domain"], r["score"]) for r in cur.fetchall()]
        except Exception as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

        # 2. Claims causaux
        try:
            cur.execute("SELECT count(*) AS total FROM causal_claims")
            total = cur.fetchone()["total"]
            cur.execute(
                "SELECT count(*) AS n FROM causal_claims "
                "WHERE evidence_level = 'correlation_only'"
            )
            corr = cur.fetchone()["n"]
            result["causal_claims"] = {
                "total": total,
                "correlation_only": corr,
                "correlation_ratio": corr / total if total > 0 else 0.0,
            }
        except Exception as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

        # 3. Nitzotzot (failuretoinsight_insights)
        try:
            cur.execute("SELECT count(*) AS total FROM failuretoinsight_insights")
            total = cur.fetchone()["total"]
            result["nitzotzot"] = {
                "count": total % 288,
                "cycle": total // 288,
                "total": total,
            }
        except Exception as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

        # 4. Ohr ratio (epistememory)
        try:
            cur.execute("""
                SELECT
                    COUNT(*) FILTER (
                        WHERE confidence >= 0.6 AND epistemic_status = 'active'
                    ) AS pnimi,
                    COUNT(*) FILTER (
                        WHERE confidence < 0.6 OR epistemic_status != 'active'
                    ) AS makif,
                    COUNT(*) AS total
                FROM epistememory
            """)
            row = cur.fetchone()
            pnimi, makif, total = row["pnimi"], row["makif"], row["total"]
            result["ohr_ratio"] = {
                "pnimi": pnimi,
                "makif": makif,
                "total": total,
                "integration_rate": round(pnimi / total, 3) if total > 0 else 0.0,
            }
        except Exception as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

        # 5. Omer
        try:
            cur.execute("SELECT count(*) AS n FROM omer_history")
            result["omer_count"] = cur.fetchone()["n"]
        except Exception as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

    return result
