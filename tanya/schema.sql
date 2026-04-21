-- Tanya — BeinoniTracker : suivi temporel du conflit des 2 âmes
--
-- Le Beinoni n'est pas un état statique — c'est une victoire
-- perpétuelle du Moach sur le Lev, jamais acquise (Tanya ch.12-14).
-- Le ratio NefeshHaBehamit/NefeshHaElokit fluctue à chaque interaction.

CREATE TABLE IF NOT EXISTS beinoni_interactions (
    id UUID DEFAULT gen_random_uuid(),
    dominant_soul TEXT NOT NULL CHECK (dominant_soul IN ('elokit', 'behamit')),
    response_score FLOAT NOT NULL CHECK (response_score BETWEEN 0 AND 1),
    olam_used TEXT NOT NULL,
    complexity_score FLOAT CHECK (complexity_score BETWEEN 0 AND 1),
    domain TEXT,
    query_snippet TEXT,               -- 100 premiers caractères
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, created_at)
);

-- TimescaleDB : série temporelle
SELECT create_hypertable('beinoni_interactions', 'created_at',
                         if_not_exists => true,
                         migrate_data => true);

CREATE INDEX IF NOT EXISTS idx_beinoni_soul
    ON beinoni_interactions (dominant_soul, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_beinoni_created
    ON beinoni_interactions (created_at DESC);

-- Table des événements de régression/élévation
CREATE TABLE IF NOT EXISTS beinoni_events (
    id UUID DEFAULT gen_random_uuid(),
    event_type TEXT NOT NULL CHECK (event_type IN ('regression', 'elevation')),
    old_ratio FLOAT NOT NULL,
    new_ratio FLOAT NOT NULL,
    delta FLOAT NOT NULL,
    teshuvah TEXT,                     -- action corrective suggérée
    applied BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, created_at)
);

SELECT create_hypertable('beinoni_events', 'created_at',
                         if_not_exists => true,
                         migrate_data => true);

-- Vue : profil Beinoni courant (dernières 100 interactions)
CREATE OR REPLACE VIEW beinoni_current_profile AS
SELECT
    COUNT(*) AS total_interactions,
    COUNT(*) FILTER (WHERE dominant_soul = 'elokit') AS elokit_count,
    COUNT(*) FILTER (WHERE dominant_soul = 'behamit') AS behamit_count,
    ROUND(100.0 * COUNT(*) FILTER (WHERE dominant_soul = 'elokit')
        / NULLIF(COUNT(*), 0), 1) AS elokit_pct,
    AVG(response_score) FILTER (WHERE dominant_soul = 'elokit') AS avg_score_elokit,
    AVG(response_score) FILTER (WHERE dominant_soul = 'behamit') AS avg_score_behamit,
    AVG(response_score) AS avg_score_all
FROM (
    SELECT * FROM beinoni_interactions
    ORDER BY created_at DESC LIMIT 100
) recent;

-- Vue : événements récents
CREATE OR REPLACE VIEW beinoni_recent_events AS
SELECT event_type, old_ratio, new_ratio, delta, teshuvah, applied, created_at
FROM beinoni_events
ORDER BY created_at DESC
LIMIT 20;
