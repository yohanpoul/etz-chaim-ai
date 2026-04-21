-- malakhim/schema.sql
-- Registre des Malakhim — persistence PostgreSQL
-- Tables : pekidah_agents, pekidah_scores, kategor_patterns, praklite_patterns, malakh_log

-- 1. Registre des agents
CREATE TABLE IF NOT EXISTS pekidah_agents (
    id          BIGSERIAL PRIMARY KEY,
    agent_id    TEXT UNIQUE NOT NULL,
    domains     TEXT[] DEFAULT '{}',
    stage       TEXT DEFAULT 'ibur' CHECK (stage IN ('ibur', 'yenikah', 'mochin')),
    total_tasks INTEGER DEFAULT 0,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Scores par domaine
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

-- 3. Patterns d'échec (Kategor)
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

CREATE INDEX IF NOT EXISTS idx_kategor_active_domain
    ON kategor_patterns (active, domain);

-- 4. Patterns de succès (Praklite)
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

CREATE INDEX IF NOT EXISTS idx_praklite_domain_score
    ON praklite_patterns (domain, score DESC);

-- 5. Historique des exécutions (TimescaleDB hypertable)
CREATE TABLE IF NOT EXISTS malakh_log (
    id                   BIGSERIAL,
    mission              TEXT NOT NULL,
    kavvanah             JSONB,
    angel_order          TEXT NOT NULL,
    olam                 TEXT NOT NULL,
    success              BOOLEAN NOT NULL,
    score                REAL,
    latency_ms           REAL,
    hitkalelut_warnings  TEXT[],
    created_at           TIMESTAMPTZ DEFAULT NOW()
);

SELECT create_hypertable('malakh_log', 'created_at', if_not_exists => TRUE);
