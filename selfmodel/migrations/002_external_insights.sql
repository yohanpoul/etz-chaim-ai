-- Migration 002: table d'ingestion externe (bridge I2 — audit Cycle 4)
-- SelfModel (Da'at) doit pouvoir recevoir des insights validés par des
-- modules externes (InsightForge d'abord). Sans cette table, Da'at ne fait
-- que passivement agréger les stats des 6 Sephiroth.

CREATE TABLE IF NOT EXISTS selfmodel_external_insights (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_module  TEXT NOT NULL,               -- 'insightforge', futur : 'autojudge', ...
    source_id      UUID NOT NULL,               -- id de l'entrée source (dedup)
    description    TEXT NOT NULL,
    confidence     FLOAT NOT NULL DEFAULT 0.5,
    domain         TEXT,
    novelty_score  FLOAT,
    ingested_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (source_module, source_id)
);

CREATE INDEX IF NOT EXISTS idx_selfmodel_ext_insights_module
    ON selfmodel_external_insights (source_module, ingested_at DESC);
CREATE INDEX IF NOT EXISTS idx_selfmodel_ext_insights_domain
    ON selfmodel_external_insights (domain)
    WHERE domain IS NOT NULL;
