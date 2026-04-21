-- Migration 001: table des signaux Beinoni (bridge I2 — audit Cycle 4)
-- BeinoniTracker (Tanya) agrège par domaine un signal de "qualité d'âme"
-- (elokit_ratio + avg response_score) que SelfMap utilise pour nuancer
-- ses scores de compétence sans les écraser.
--
-- Mise à jour : upsert par domaine (une ligne par domaine).

CREATE TABLE IF NOT EXISTS selfmap_beinoni_signals (
    domain             TEXT PRIMARY KEY,
    elokit_ratio       FLOAT NOT NULL CHECK (elokit_ratio BETWEEN 0 AND 1),
    avg_response_score FLOAT NOT NULL CHECK (avg_response_score BETWEEN 0 AND 1),
    n_interactions     INTEGER NOT NULL DEFAULT 0,
    regressions_count  INTEGER NOT NULL DEFAULT 0,
    elevations_count   INTEGER NOT NULL DEFAULT 0,
    window_seconds     INTEGER NOT NULL DEFAULT 3600,
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_selfmap_beinoni_updated
    ON selfmap_beinoni_signals (updated_at DESC);
