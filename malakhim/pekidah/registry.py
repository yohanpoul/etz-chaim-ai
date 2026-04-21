"""PekidahRegistry — Registre de compétence avec maturation IYM.

פְּקִידָה — La Pekidah est la « visite divine » qui évalue l'état d'un être.
Ici : chaque agent est visité, son stade (Ibur/Yenikah/Mochin) réévalué,
ses échecs (Kategor) et réussites (Praklite) enregistrés.

Symétrie Kategor/Praklite :
  - Le Kategor (accusateur) enregistre les patterns d'échec actifs.
    Un tikkun (réparation) désactive le pattern.
  - Le Praklite (défenseur) enregistre les stratégies réussies,
    réutilisables par d'autres agents sur le même domaine.

Maturation IYM réversible (Hizdakchut) :
  Un agent peut régresser de Yenikah vers Ibur si ses scores chutent.
  Le Mochin n'est atteint qu'après suffisamment de tâches ET de compétence.

Persistence PostgreSQL (opt-in) :
  Si db_url est fourni au constructeur, les données sont persistées en
  PostgreSQL (tables pekidah_agents, pekidah_scores, kategor_patterns,
  praklite_patterns). Sinon, le registre fonctionne en mémoire pure.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from malakhim.models import (
    AgentProfile,
    FailurePattern,
    MalakhStage,
    SuccessPattern,
)

# ── Seuils IYM (redéfinis localement, pas de couplage avec masakh) ──────────
IBUR_RESHIMOT_MAX = 10       # < 10 tâches → ibur
MOCHIN_RESHIMOT_MIN = 50     # >= 50 tâches → candidat mochin
IBUR_SCORE_MAX = 0.3         # score < 0.3 → régression en ibur
MOCHIN_SCORE_MIN = 0.6       # score >= 0.6 → candidat mochin
SCORE_EMA_ALPHA = 0.2        # exponential moving average

# ── SQL DDL (identique à malakhim/schema.sql, sans hypertable) ──────────────
_DDL = """
CREATE TABLE IF NOT EXISTS pekidah_agents (
    id          BIGSERIAL PRIMARY KEY,
    agent_id    TEXT UNIQUE NOT NULL,
    domains     TEXT[] DEFAULT '{}',
    stage       TEXT DEFAULT 'ibur' CHECK (stage IN ('ibur', 'yenikah', 'mochin')),
    total_tasks INTEGER DEFAULT 0,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pekidah_scores (
    id         BIGSERIAL PRIMARY KEY,
    agent_id   TEXT NOT NULL REFERENCES pekidah_agents(agent_id) ON DELETE CASCADE,
    domain     TEXT NOT NULL,
    score      REAL DEFAULT 0.5 CHECK (score >= 0 AND score <= 1),
    executions INTEGER DEFAULT 0,
    successes  INTEGER DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (agent_id, domain)
);

CREATE TABLE IF NOT EXISTS kategor_patterns (
    id                  BIGSERIAL PRIMARY KEY,
    agent_id            TEXT,
    domain              TEXT NOT NULL,
    error_type          TEXT NOT NULL,
    prompt_keywords     TEXT[] DEFAULT '{}',
    prompt_excerpt      TEXT,
    score               REAL,
    active              BOOLEAN DEFAULT TRUE,
    occurrences         INTEGER DEFAULT 1,
    tikkun_description  TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    last_seen           TIMESTAMPTZ,
    resolved_at         TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS praklite_patterns (
    id             BIGSERIAL PRIMARY KEY,
    agent_id       TEXT,
    domain         TEXT NOT NULL,
    strategy_used  TEXT,
    kavvanah       JSONB,
    score          REAL NOT NULL,
    reuse_count    INTEGER DEFAULT 0,
    created_at     TIMESTAMPTZ DEFAULT NOW(),
    last_reused    TIMESTAMPTZ
);
"""


class PekidahRegistry:
    """Registre de compétence des agents — évaluation, maturation, mémoire.

    Si ``db_url`` est fourni, les données sont persistées en PostgreSQL
    (write-through : mémoire + DB). Sinon, mémoire pure (comportement originel).
    """

    def __init__(self, db_url: str | None = None) -> None:
        self._agents: dict[str, AgentProfile] = {}
        self._failures: dict[int, FailurePattern] = {}
        self._successes: dict[int, SuccessPattern] = {}
        self._next_failure_id = 1
        self._next_success_id = 1
        self._conn = None

        if db_url is not None:
            from pool import get_pool, init_pool
            init_pool(db_url)  # idempotent
            self._pool = get_pool()
            # Emprunter une conn pour toute la durée de vie de ce registry
            # (semantique transactionnelle préservée : autocommit=False,
            # commit/rollback explicites). Rendue au pool dans close().
            self._conn = self._pool.getconn()
            self._conn.autocommit = False
            self._ensure_tables()
            self._load_from_db()
        else:
            self._pool = None

    # ── DB bootstrap ───────────────────────────────────────────────────────

    def _ensure_tables(self) -> None:
        """Crée les tables si elles n'existent pas."""
        with self._conn.cursor() as cur:
            cur.execute(_DDL)
        self._conn.commit()

    def _load_from_db(self) -> None:
        """Charge l'état complet depuis PostgreSQL dans les dicts mémoire."""
        with self._conn.cursor() as cur:
            # ── agents ──
            cur.execute(
                "SELECT agent_id, domains, stage, total_tasks FROM pekidah_agents"
            )
            for row in cur.fetchall():
                agent_id, domains, stage, total_tasks = row
                profile = AgentProfile(
                    agent_id=agent_id,
                    domains=list(domains or []),
                    stage=MalakhStage(stage),
                    total_tasks=total_tasks or 0,
                    scores={},
                )
                self._agents[agent_id] = profile

            # ── scores ──
            cur.execute("SELECT agent_id, domain, score FROM pekidah_scores")
            for row in cur.fetchall():
                agent_id, domain, score = row
                if agent_id in self._agents:
                    self._agents[agent_id].scores[domain] = float(score)

            # ── kategor ──
            cur.execute(
                "SELECT id, agent_id, domain, error_type, prompt_keywords, "
                "prompt_excerpt, score, active, occurrences, tikkun_description, "
                "created_at, last_seen, resolved_at "
                "FROM kategor_patterns"
            )
            for row in cur.fetchall():
                fp = FailurePattern(
                    pattern_id=row[0],
                    agent_id=row[1],
                    domain=row[2],
                    error_type=row[3],
                    prompt_keywords=list(row[4] or []),
                    prompt_excerpt=row[5],
                    score=row[6],
                    active=row[7],
                    occurrences=row[8] or 1,
                    tikkun_description=row[9],
                    created_at=row[10],
                    last_seen=row[11],
                    resolved_at=row[12],
                )
                self._failures[fp.pattern_id] = fp
                if fp.pattern_id >= self._next_failure_id:
                    self._next_failure_id = fp.pattern_id + 1

            # ── praklite ──
            cur.execute(
                "SELECT id, agent_id, domain, strategy_used, kavvanah, "
                "score, reuse_count, created_at, last_reused "
                "FROM praklite_patterns"
            )
            for row in cur.fetchall():
                sp = SuccessPattern(
                    pattern_id=row[0],
                    agent_id=row[1],
                    domain=row[2],
                    strategy_used=row[3],
                    kavvanah=row[4],
                    score=float(row[5]),
                    reuse_count=row[6] or 0,
                    created_at=row[7],
                    last_reused=row[8],
                )
                self._successes[sp.pattern_id] = sp
                if sp.pattern_id >= self._next_success_id:
                    self._next_success_id = sp.pattern_id + 1

    # ── Registration ────────────────────────────────────────────────────────

    def register(self, agent_id: str, domains: list[str]) -> AgentProfile:
        """Enregistre un agent. Si déjà connu, retourne l'existant."""
        if agent_id in self._agents:
            return self._agents[agent_id]

        profile = AgentProfile(
            agent_id=agent_id,
            domains=list(domains),
            stage=MalakhStage.IBUR,
            total_tasks=0,
            scores={d: 0.5 for d in domains},
        )
        self._agents[agent_id] = profile

        if self._conn:
            self._db_register(agent_id, domains)

        return profile

    def _db_register(self, agent_id: str, domains: list[str]) -> None:
        with self._conn.cursor() as cur:
            cur.execute(
                "INSERT INTO pekidah_agents (agent_id, domains) VALUES (%s, %s) "
                "ON CONFLICT (agent_id) DO NOTHING",
                (agent_id, domains),
            )
            for d in domains:
                cur.execute(
                    "INSERT INTO pekidah_scores (agent_id, domain) VALUES (%s, %s) "
                    "ON CONFLICT (agent_id, domain) DO NOTHING",
                    (agent_id, d),
                )
        self._conn.commit()

    # ── Compétence ──────────────────────────────────────────────────────────

    def get_score(self, agent_id: str, domain: str) -> float:
        """Score de l'agent pour un domaine. 0.0 si inconnu."""
        profile = self._agents.get(agent_id)
        if profile is None:
            return 0.0
        return profile.scores.get(domain, 0.0)

    def can_handle(
        self, agent_id: str, domain: str, min_score: float = 0.3
    ) -> bool:
        """L'agent peut-il traiter ce domaine au-dessus du seuil ?"""
        profile = self._agents.get(agent_id)
        if profile is None:
            return False
        if domain not in profile.scores:
            return False
        return profile.scores[domain] >= min_score

    def record_outcome(
        self,
        agent_id: str,
        domain: str,
        score: float,
        error_type: str | None = None,
    ) -> None:
        """Enregistre le résultat d'une tâche. Met à jour score EMA + stade."""
        profile = self._agents.get(agent_id)
        if profile is None:
            return

        # Ajouter le domaine s'il est nouveau
        if domain not in profile.scores:
            profile.scores[domain] = 0.5
            if domain not in profile.domains:
                profile.domains.append(domain)

        # EMA update
        old = profile.scores[domain]
        profile.scores[domain] = (
            SCORE_EMA_ALPHA * score + (1 - SCORE_EMA_ALPHA) * old
        )

        profile.total_tasks += 1

        # Réévaluer le stade IYM
        profile.stage = self.assess_stage(agent_id)

        if self._conn:
            self._db_record_outcome(agent_id, domain, profile)

    def _db_record_outcome(
        self, agent_id: str, domain: str, profile: AgentProfile
    ) -> None:
        with self._conn.cursor() as cur:
            # Upsert score
            cur.execute(
                "INSERT INTO pekidah_scores (agent_id, domain, score, updated_at) "
                "VALUES (%s, %s, %s, NOW()) "
                "ON CONFLICT (agent_id, domain) DO UPDATE "
                "SET score = EXCLUDED.score, "
                "    executions = pekidah_scores.executions + 1, "
                "    updated_at = NOW()",
                (agent_id, domain, profile.scores[domain]),
            )
            # Update agent stage + total_tasks
            cur.execute(
                "UPDATE pekidah_agents SET stage = %s, total_tasks = %s, "
                "updated_at = NOW() WHERE agent_id = %s",
                (profile.stage.value, profile.total_tasks, agent_id),
            )
            # Ensure domain in domains array
            cur.execute(
                "UPDATE pekidah_agents "
                "SET domains = array_append(domains, %s) "
                "WHERE agent_id = %s AND NOT (%s = ANY(domains))",
                (domain, agent_id, domain),
            )
        self._conn.commit()

    # ── Maturation IYM (réversible — Hizdakchut) ───────────────────────────

    def assess_stage(self, agent_id: str) -> MalakhStage:
        """Évalue le stade IYM. Régression possible."""
        profile = self._agents.get(agent_id)
        if profile is None:
            return MalakhStage.IBUR

        avg_score = self._avg_score(profile)

        # Régression : score trop bas → ibur
        if avg_score < IBUR_SCORE_MAX:
            return MalakhStage.IBUR

        # Pas assez de tâches → ibur
        if profile.total_tasks < IBUR_RESHIMOT_MAX:
            return MalakhStage.IBUR

        # Assez de tâches ET bon score → mochin
        if (
            profile.total_tasks >= MOCHIN_RESHIMOT_MIN
            and avg_score >= MOCHIN_SCORE_MIN
        ):
            return MalakhStage.MOCHIN

        # Entre les deux → yenikah
        return MalakhStage.YENIKAH

    # ── Kategor (dette active) ──────────────────────────────────────────────

    def record_failure(
        self,
        agent_id: str,
        domain: str,
        error_type: str,
        prompt: str,
        score: float,
    ) -> FailurePattern:
        """Enregistre un pattern d'échec (Kategor actif)."""
        keywords = self._extract_keywords(prompt)
        now = datetime.now(timezone.utc)

        pattern = FailurePattern(
            pattern_id=self._next_failure_id,
            agent_id=agent_id,
            domain=domain,
            error_type=error_type,
            prompt_keywords=keywords,
            prompt_excerpt=prompt[:200] if prompt else None,
            score=score,
            active=True,
            occurrences=1,
            created_at=now,
            last_seen=now,
        )
        self._failures[self._next_failure_id] = pattern
        self._next_failure_id += 1

        if self._conn:
            self._db_record_failure(pattern)

        return pattern

    def _db_record_failure(self, pattern: FailurePattern) -> None:
        with self._conn.cursor() as cur:
            cur.execute(
                "INSERT INTO kategor_patterns "
                "(agent_id, domain, error_type, prompt_keywords, "
                "prompt_excerpt, score, active, occurrences, "
                "created_at, last_seen) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                "RETURNING id",
                (
                    pattern.agent_id,
                    pattern.domain,
                    pattern.error_type,
                    pattern.prompt_keywords,
                    pattern.prompt_excerpt,
                    pattern.score,
                    pattern.active,
                    pattern.occurrences,
                    pattern.created_at,
                    pattern.last_seen,
                ),
            )
            db_id = cur.fetchone()[0]
            # Sync the in-memory pattern_id with the DB-generated id
            old_id = pattern.pattern_id
            pattern.pattern_id = db_id
            del self._failures[old_id]
            self._failures[db_id] = pattern
            self._next_failure_id = db_id + 1
        self._conn.commit()

    def check_failures(
        self, agent_id: str, domain: str, prompt: str
    ) -> list[FailurePattern]:
        """Cherche les patterns d'échec actifs qui matchent le prompt.

        Match si >= 50% des keywords du prompt apparaissent dans le pattern.
        """
        keywords = set(self._extract_keywords(prompt))
        if not keywords:
            return []

        matches: list[FailurePattern] = []
        for pattern in self._failures.values():
            if not pattern.active:
                continue
            if pattern.agent_id != agent_id:
                continue
            if pattern.domain != domain:
                continue

            pattern_kw = set(pattern.prompt_keywords)
            if not pattern_kw:
                continue

            overlap = keywords & pattern_kw
            ratio = len(overlap) / len(keywords)
            if ratio >= 0.5:
                matches.append(pattern)

        return matches

    def resolve_failure(
        self, pattern_id: int, tikkun_description: str
    ) -> None:
        """Résout un pattern d'échec (tikkun)."""
        pattern = self._failures.get(pattern_id)
        if pattern is None:
            return
        pattern.active = False
        pattern.tikkun_description = tikkun_description
        pattern.resolved_at = datetime.now(timezone.utc)

        if self._conn:
            self._db_resolve_failure(pattern)

    def _db_resolve_failure(self, pattern: FailurePattern) -> None:
        with self._conn.cursor() as cur:
            cur.execute(
                "UPDATE kategor_patterns SET active = FALSE, "
                "tikkun_description = %s, resolved_at = %s "
                "WHERE id = %s",
                (
                    pattern.tikkun_description,
                    pattern.resolved_at,
                    pattern.pattern_id,
                ),
            )
        self._conn.commit()

    # ── Praklite (mérite réutilisable) ──────────────────────────────────────

    def record_success(
        self,
        agent_id: str,
        domain: str,
        strategy: str,
        kavvanah: dict | None,
        score: float,
    ) -> SuccessPattern:
        """Enregistre un pattern de réussite (Praklite)."""
        now = datetime.now(timezone.utc)

        pattern = SuccessPattern(
            pattern_id=self._next_success_id,
            agent_id=agent_id,
            domain=domain,
            strategy_used=strategy,
            kavvanah=kavvanah,
            score=score,
            reuse_count=0,
            created_at=now,
        )
        self._successes[self._next_success_id] = pattern
        self._next_success_id += 1

        if self._conn:
            self._db_record_success(pattern)

        return pattern

    def _db_record_success(self, pattern: SuccessPattern) -> None:
        with self._conn.cursor() as cur:
            cur.execute(
                "INSERT INTO praklite_patterns "
                "(agent_id, domain, strategy_used, kavvanah, score, "
                "reuse_count, created_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s) "
                "RETURNING id",
                (
                    pattern.agent_id,
                    pattern.domain,
                    pattern.strategy_used,
                    json.dumps(pattern.kavvanah) if pattern.kavvanah else None,
                    pattern.score,
                    pattern.reuse_count,
                    pattern.created_at,
                ),
            )
            db_id = cur.fetchone()[0]
            old_id = pattern.pattern_id
            pattern.pattern_id = db_id
            del self._successes[old_id]
            self._successes[db_id] = pattern
            self._next_success_id = db_id + 1
        self._conn.commit()

    def get_best_strategies(
        self, domain: str, limit: int = 5
    ) -> list[SuccessPattern]:
        """Retourne les meilleures stratégies pour un domaine, par score desc."""
        candidates = [
            p for p in self._successes.values() if p.domain == domain
        ]
        candidates.sort(key=lambda p: p.score, reverse=True)
        return candidates[:limit]

    # ── Lifecycle ──────────────────────────────────────────────────────────

    def close(self) -> None:
        """Rend la connexion empruntée au pool (ou la ferme si autonome)."""
        if self._conn and not self._conn.closed:
            if self._pool is not None:
                self._pool.putconn(self._conn)
            else:
                self._conn.close()
            self._conn = None

    # ── Helpers ─────────────────────────────────────────────────────────────

    @staticmethod
    def _extract_keywords(prompt: str) -> list[str]:
        """Extrait les mots de 4+ caractères, triés, 20 max."""
        words = re.findall(r"[a-zA-Z\u00C0-\u024F]{4,}", prompt.lower())
        unique = sorted(set(words))
        return unique[:20]

    @staticmethod
    def _avg_score(profile: AgentProfile) -> float:
        """Score moyen sur tous les domaines."""
        if not profile.scores:
            return 0.0
        return sum(profile.scores.values()) / len(profile.scores)
