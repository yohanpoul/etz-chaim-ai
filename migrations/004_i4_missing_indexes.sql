-- Migration 004 : indexes manquants identifiés par l'audit cycle 4 (I4)
--
-- 4 tables avec seq_scan élevé / idx_scan = 0 dans pg_stat_user_tables.
-- Avec n_live_tup = 0 actuellement, aucun impact ; mais les seq_scans
-- exploseront en latence dès accumulation. Indexer en préventif.
--
-- Choix des colonnes basé sur grep des WHERE / ORDER BY effectifs :
--   - intentkeeper_intentions : `WHERE status = 'active'|'completed'|...`
--     très fréquent (omer/core.py:568-570, gevurah_interne.py, etc.)
--   - dissensuengine_syntheses : pas encore de pattern hot, mais le
--     ORDER BY created_at est attendu pour les listings dashboard.
--   - partzufim_state : `WHERE name = %s` (lookup) +
--     `WHERE orientation = 'panim'` (governors.py:230).
--   - failuretoinsight_insights : `ORDER BY created_at DESC LIMIT 20`
--     dans insightforge/orchestrator.py:204-208.

-- intentkeeper_intentions ── status le plus filtré
CREATE INDEX IF NOT EXISTS idx_intentkeeper_intentions_status
    ON intentkeeper_intentions (status);

-- dissensuengine_syntheses ── tri chronologique
CREATE INDEX IF NOT EXISTS idx_dissensuengine_syntheses_created_at
    ON dissensuengine_syntheses (created_at DESC);

-- partzufim_state ── lookup nom + orientation
CREATE INDEX IF NOT EXISTS idx_partzufim_state_name
    ON partzufim_state (name);
CREATE INDEX IF NOT EXISTS idx_partzufim_state_orientation
    ON partzufim_state (orientation);

-- failuretoinsight_insights ── ORDER BY created_at DESC LIMIT
CREATE INDEX IF NOT EXISTS idx_fti_insights_created_at_desc
    ON failuretoinsight_insights (created_at DESC);
