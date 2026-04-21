-- InsightForge — Chokmah
-- Tables pour les sessions d'insight, candidats, et évaluations de nouveauté.

CREATE TABLE IF NOT EXISTS insight_sessions (
    id            UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    question      TEXT NOT NULL,
    domain        TEXT NOT NULL DEFAULT '',
    status        TEXT NOT NULL DEFAULT 'active'
                  CHECK (status IN ('active', 'completed', 'aborted')),
    modules_consulted TEXT[] NOT NULL DEFAULT '{}',
    total_candidates  INT NOT NULL DEFAULT 0,
    insights_found    INT NOT NULL DEFAULT 0,
    rejected_count    INT NOT NULL DEFAULT 0,
    pearl_level    TEXT NOT NULL DEFAULT 'association'
                  CHECK (pearl_level IN ('association', 'intervention', 'counterfactual')),
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    completed_at  TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS candidate_insights (
    id            UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    session_id    UUID REFERENCES insight_sessions(id) ON DELETE CASCADE,
    description   TEXT NOT NULL,
    source_module TEXT NOT NULL DEFAULT '',
    domain        TEXT NOT NULL DEFAULT '',
    novelty_score FLOAT NOT NULL DEFAULT 0.0
                  CHECK (novelty_score >= 0.0 AND novelty_score <= 1.0),
    confidence    FLOAT NOT NULL DEFAULT 0.5
                  CHECK (confidence >= 0.0 AND confidence <= 1.0),
    status        TEXT NOT NULL DEFAULT 'candidate'
                  CHECK (status IN ('candidate', 'validated', 'rejected', 'insight', 'pending', 'incubating')),
    rejection_reason TEXT,
    -- Triple validation
    binah_validated   BOOLEAN NOT NULL DEFAULT FALSE,
    gevurah_validated BOOLEAN NOT NULL DEFAULT FALSE,
    daat_validated    BOOLEAN NOT NULL DEFAULT FALSE,
    -- Liens
    connects_domains  TEXT[] NOT NULL DEFAULT '{}',
    source_connections UUID[] NOT NULL DEFAULT '{}',
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS novelty_assessments (
    id            UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    candidate_id  UUID REFERENCES candidate_insights(id) ON DELETE CASCADE,
    is_genuinely_new  BOOLEAN NOT NULL DEFAULT FALSE,
    already_known     BOOLEAN NOT NULL DEFAULT FALSE,
    is_reformulation  BOOLEAN NOT NULL DEFAULT FALSE,
    is_trivial        BOOLEAN NOT NULL DEFAULT FALSE,
    is_cross_domain   BOOLEAN NOT NULL DEFAULT FALSE,
    novelty_score     FLOAT NOT NULL DEFAULT 0.0,
    reasoning         TEXT NOT NULL DEFAULT '',
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

-- Index
CREATE INDEX IF NOT EXISTS idx_insight_sessions_status ON insight_sessions(status);
CREATE INDEX IF NOT EXISTS idx_insight_sessions_domain ON insight_sessions(domain);
CREATE INDEX IF NOT EXISTS idx_candidate_insights_session ON candidate_insights(session_id);
CREATE INDEX IF NOT EXISTS idx_candidate_insights_status ON candidate_insights(status);
CREATE INDEX IF NOT EXISTS idx_novelty_assessments_candidate ON novelty_assessments(candidate_id);

-- Vue résumé
CREATE OR REPLACE VIEW insight_sessions_summary AS
SELECT
    s.id,
    s.question,
    s.domain,
    s.status,
    s.total_candidates,
    s.insights_found,
    s.rejected_count,
    s.pearl_level,
    s.created_at,
    COALESCE(array_length(s.modules_consulted, 1), 0) AS modules_count,
    (SELECT COUNT(*) FROM candidate_insights ci WHERE ci.session_id = s.id AND ci.status = 'insight') AS actual_insights,
    (SELECT COUNT(*) FROM candidate_insights ci WHERE ci.session_id = s.id AND ci.binah_validated AND ci.gevurah_validated AND ci.daat_validated) AS triple_validated
FROM insight_sessions s;
