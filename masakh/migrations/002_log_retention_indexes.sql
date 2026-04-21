-- Migration 002: Index pour la rétention des logs (F404 — FATAL)
-- Trois tables à INSERT sans DELETE grandissent de ~525K rows/an chacune.
-- Ces index accélèrent le DELETE périodique par date dans task_log_retention().
--
-- Note : masakh_log a déjà idx_masakh_log_created (created_at DESC) dans schema.sql,
-- mais un index ASC dédié est plus efficace pour DELETE ... WHERE created_at < X.

-- context_monitor_log — rétention 30 jours
CREATE INDEX IF NOT EXISTS idx_context_monitor_log_retention
    ON context_monitor_log (created_at);

-- masakh_log — rétention 30 jours
CREATE INDEX IF NOT EXISTS idx_masakh_log_retention
    ON masakh_log (created_at);

-- hitbonenut_questions — rétention 90 jours
CREATE INDEX IF NOT EXISTS idx_hitbonenut_questions_retention
    ON hitbonenut_questions (created_at);
