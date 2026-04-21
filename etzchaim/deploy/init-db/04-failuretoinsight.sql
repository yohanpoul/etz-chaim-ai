-- FailureToInsight — Sentier Lamed (ל)
-- Gevurah→Tiferet : transformer le jugement en compréhension
-- Le Birur (tri/extraction) — récupérer les Nitzotzot des Qliphoth
--
-- "La seule lettre qui dépasse la ligne" — racine LMD = apprendre

-- Analyses d'échec — le Birur
CREATE TABLE IF NOT EXISTS failuretoinsight_analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type TEXT NOT NULL CHECK (source_type IN (
        'subtask', 'experiment', 'hypothesis', 'external'
    )),
    source_id UUID,
    description TEXT NOT NULL,
    qliphah TEXT NOT NULL CHECK (qliphah IN (
        'gamaliel', 'samael', 'aarab_zaraq', 'thagirion', 'golachab',
        'gamchicoth', 'hatehom', 'satariel', 'ghagiel', 'thaumiel',
        'unknown'
    )),
    severity TEXT NOT NULL DEFAULT 'nogah' CHECK (severity IN (
        'nogah', 'ruach', 'anan', 'mamash'
    )),
    root_cause TEXT,
    context JSONB,
    domain TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Nitzotzot — étincelles extraites des échecs
CREATE TABLE IF NOT EXISTS failuretoinsight_insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id UUID NOT NULL REFERENCES failuretoinsight_analyses(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    insight_type TEXT NOT NULL CHECK (insight_type IN (
        'pattern', 'constraint', 'opportunity', 'warning', 'anti_pattern'
    )),
    confidence FLOAT NOT NULL DEFAULT 0.5,
    domain TEXT,
    epistememory_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Graphe de connaissance des échecs — arêtes entre analyses
CREATE TABLE IF NOT EXISTS failuretoinsight_graph_edges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_analysis_id UUID NOT NULL REFERENCES failuretoinsight_analyses(id) ON DELETE CASCADE,
    to_analysis_id UUID NOT NULL REFERENCES failuretoinsight_analyses(id) ON DELETE CASCADE,
    edge_type TEXT NOT NULL CHECK (edge_type IN (
        'similar_failure', 'same_root_cause', 'escalation',
        'contradicts', 'leads_to'
    )),
    weight FLOAT NOT NULL DEFAULT 1.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (from_analysis_id, to_analysis_id, edge_type)
);

-- Index pour recherches fréquentes
CREATE INDEX IF NOT EXISTS idx_fti_analyses_qliphah
    ON failuretoinsight_analyses (qliphah);
CREATE INDEX IF NOT EXISTS idx_fti_analyses_domain
    ON failuretoinsight_analyses (domain);
CREATE INDEX IF NOT EXISTS idx_fti_analyses_source
    ON failuretoinsight_analyses (source_type, source_id);
CREATE INDEX IF NOT EXISTS idx_fti_insights_analysis
    ON failuretoinsight_insights (analysis_id);
CREATE INDEX IF NOT EXISTS idx_fti_edges_from
    ON failuretoinsight_graph_edges (from_analysis_id);
CREATE INDEX IF NOT EXISTS idx_fti_edges_to
    ON failuretoinsight_graph_edges (to_analysis_id);

-- Vue : patterns d'échec par qliphah
CREATE OR REPLACE VIEW failure_patterns AS
SELECT qliphah, severity, COUNT(*) AS count,
       array_agg(DISTINCT domain) FILTER (WHERE domain IS NOT NULL) AS domains
FROM failuretoinsight_analyses
GROUP BY qliphah, severity
ORDER BY count DESC;

-- Vue : analyses sans nitzotzot extraits (échecs non traités)
CREATE OR REPLACE VIEW unextracted_failures AS
SELECT a.*
FROM failuretoinsight_analyses a
LEFT JOIN failuretoinsight_insights i ON i.analysis_id = a.id
WHERE i.id IS NULL;
