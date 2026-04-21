-- IntentKeeper — Tikkun de Netzach
-- Schéma de données pour la persistance adaptative
--
-- Netzach = persistence qui sait mourir.
-- A'arab Zaraq = corbeaux de dispersion = retries infinis, zombies.

-- Table principale : intentions
CREATE TABLE IF NOT EXISTS intentkeeper_intentions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goal TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK (
        status IN ('active', 'completed', 'abandoned', 'paused')
    ),
    max_duration_days INTEGER NOT NULL DEFAULT 90,
    abandon_threshold FLOAT NOT NULL DEFAULT 0.2
        CHECK (abandon_threshold BETWEEN 0 AND 1),
    progress FLOAT NOT NULL DEFAULT 0.0
        CHECK (progress BETWEEN 0 AND 1),
    strategy TEXT,
    strategy_version INTEGER NOT NULL DEFAULT 1,
    total_subtasks INTEGER NOT NULL DEFAULT 0,
    completed_subtasks INTEGER NOT NULL DEFAULT 0,
    failed_subtasks INTEGER NOT NULL DEFAULT 0,
    abandon_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deadline_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Sous-tâches décomposées
CREATE TABLE IF NOT EXISTS intentkeeper_subtasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    intention_id UUID NOT NULL REFERENCES intentkeeper_intentions(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (
        status IN ('pending', 'in_progress', 'completed', 'failed', 'skipped')
    ),
    order_index INTEGER NOT NULL,
    strategy_version INTEGER NOT NULL DEFAULT 1,
    result TEXT,
    failure_reason TEXT,
    retries INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Heartbeat pour détection zombie (hypertable TimescaleDB)
CREATE TABLE IF NOT EXISTS intentkeeper_heartbeats (
    id UUID DEFAULT gen_random_uuid(),
    intention_id UUID NOT NULL REFERENCES intentkeeper_intentions(id) ON DELETE CASCADE,
    activity_type TEXT NOT NULL CHECK (
        activity_type IN (
            'subtask_start', 'subtask_complete', 'subtask_fail',
            'strategy_change', 'progress_check', 'checkpoint'
        )
    ),
    details JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, created_at)
);

DO $$
BEGIN
    PERFORM create_hypertable('intentkeeper_heartbeats', 'created_at',
                              if_not_exists => true, migrate_data => true);
EXCEPTION WHEN undefined_function OR OTHERS THEN
    RAISE NOTICE 'intentkeeper_heartbeats : skipping create_hypertable (timescaledb missing).';
END$$;

-- Vues

-- Intentions actives
CREATE OR REPLACE VIEW active_intentions AS
    SELECT * FROM intentkeeper_intentions WHERE status = 'active';

-- Intentions stale (sans activité depuis 7+ jours)
CREATE OR REPLACE VIEW stale_intentions AS
    SELECT i.*,
           EXTRACT(EPOCH FROM (NOW() - COALESCE(
               (SELECT MAX(h.created_at) FROM intentkeeper_heartbeats h
                WHERE h.intention_id = i.id),
               i.created_at
           ))) / 86400.0 AS days_since_activity
    FROM intentkeeper_intentions i
    WHERE i.status = 'active'
      AND EXTRACT(EPOCH FROM (NOW() - COALESCE(
              (SELECT MAX(h.created_at) FROM intentkeeper_heartbeats h
               WHERE h.intention_id = i.id),
              i.created_at
          ))) / 86400.0 > 7;

-- Vue progrès avec vélocité
CREATE OR REPLACE VIEW intention_progress AS
    SELECT i.id, i.goal, i.status, i.progress,
           i.total_subtasks, i.completed_subtasks, i.failed_subtasks,
           i.strategy_version,
           CASE WHEN i.deadline_at IS NOT NULL
                     AND i.deadline_at > i.created_at
                THEN 1.0 - EXTRACT(EPOCH FROM (i.deadline_at - NOW()))
                         / EXTRACT(EPOCH FROM (i.deadline_at - i.created_at))
                ELSE NULL
           END AS time_elapsed_ratio,
           (SELECT MAX(h.created_at) FROM intentkeeper_heartbeats h
            WHERE h.intention_id = i.id) AS last_heartbeat
    FROM intentkeeper_intentions i
    WHERE i.status = 'active';
