-- AutoJudge — Tikkun de Gevurah
-- L'auto-jugement généralisé : le Karpathy Loop étendu.

-- Domaines d'auto-jugement
CREATE TABLE IF NOT EXISTS autojudge_domains (
    id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    loss_function TEXT NOT NULL,
    config JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Expériences (le Karpathy Loop)
CREATE TABLE IF NOT EXISTS autojudge_experiments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id TEXT REFERENCES autojudge_domains(id),

    -- Input
    hypothesis TEXT NOT NULL,
    original_content TEXT,
    modified_content TEXT,

    -- Évaluation multi-sephirothique
    score_gevurah FLOAT,
    score_chesed FLOAT,
    score_tiferet FLOAT,
    score_hod FLOAT,
    score_yesod FLOAT,
    score_overall FLOAT,

    -- Décision
    decision TEXT CHECK (decision IN (
        'accepted',
        'rejected',
        'quarantined',
        'tension_detected'
    )),

    -- Lien vers FailureToInsight (sentier Lamed)
    failure_analysis_id UUID,
    nitzotzot_extracted BOOLEAN DEFAULT false,

    -- Méta
    duration_seconds FLOAT,
    budget_seconds FLOAT DEFAULT 300,
    loop_iteration INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_autojudge_experiments_domain
    ON autojudge_experiments(domain_id);
CREATE INDEX IF NOT EXISTS idx_autojudge_experiments_decision
    ON autojudge_experiments(decision);
CREATE INDEX IF NOT EXISTS idx_autojudge_experiments_created
    ON autojudge_experiments(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_autojudge_experiments_failure
    ON autojudge_experiments(failure_analysis_id)
    WHERE failure_analysis_id IS NOT NULL;

-- Vue : taux de rejet par domaine (anti-Golachab)
CREATE OR REPLACE VIEW autojudge_rejection_rates AS
SELECT domain_id,
       COUNT(*) as total,
       COUNT(*) FILTER (WHERE decision = 'rejected') as rejected,
       COUNT(*) FILTER (WHERE decision = 'accepted') as accepted,
       COUNT(*) FILTER (WHERE decision = 'quarantined') as quarantined,
       ROUND(COUNT(*) FILTER (WHERE decision = 'rejected')::numeric /
             NULLIF(COUNT(*), 0), 3) as rejection_rate
FROM autojudge_experiments
GROUP BY domain_id;

-- Vue : expériences rejetées NON analysées (Nitzotzot perdues)
CREATE OR REPLACE VIEW autojudge_unanalyzed_rejections AS
SELECT * FROM autojudge_experiments
WHERE decision = 'rejected' AND nitzotzot_extracted = false;
