-- CausalEngine — Binah schema
-- L'Intelligence qui distingue corrélation de causalité.
-- 3 tables : graphes causaux, claims causales, confounders.

-- Graphes causaux (DAGs)
CREATE TABLE IF NOT EXISTS causal_graphs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    domain TEXT,
    description TEXT,

    -- Le graphe (JSON adjacency list)
    nodes JSONB NOT NULL DEFAULT '[]',   -- [{id, name, type, domain}]
    edges JSONB NOT NULL DEFAULT '[]',   -- [{source, target, edge_type, confidence, evidence_level}]

    -- Qualité
    confounders_checked BOOLEAN DEFAULT false,
    evidence_level TEXT CHECK (evidence_level IN (
        'association',       -- Pearl niveau 1 : corrélation observée
        'intervention',      -- Pearl niveau 2 : effet d'une intervention testé
        'counterfactual'     -- Pearl niveau 3 : "que serait-il arrivé si..."
    )),

    -- Provenance
    source_data JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_causal_graphs_domain
    ON causal_graphs (domain);
CREATE INDEX IF NOT EXISTS idx_causal_graphs_evidence
    ON causal_graphs (evidence_level);
CREATE INDEX IF NOT EXISTS idx_causal_graphs_time
    ON causal_graphs (created_at DESC);

-- Affirmations causales individuelles
CREATE TABLE IF NOT EXISTS causal_claims (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    graph_id UUID REFERENCES causal_graphs(id) ON DELETE CASCADE,

    cause TEXT NOT NULL,
    effect TEXT NOT NULL,

    -- Niveau de preuve
    evidence_level TEXT NOT NULL CHECK (evidence_level IN (
        'correlation_only',       -- "A est associé à B"
        'observed_association',   -- "A est observé avec B" (2+ contextes)
        'probable_causation',     -- "A cause probablement B" (confounders vérifiés)
        'demonstrated_causation'  -- "A cause B" (intervention ou RCT)
    )),

    -- Confounders
    known_confounders TEXT[] DEFAULT '{}',
    confounders_controlled BOOLEAN DEFAULT false,

    -- Direction
    direction_verified BOOLEAN DEFAULT false,
    reverse_plausible BOOLEAN,

    -- Langage approprié
    appropriate_language TEXT,

    confidence FLOAT DEFAULT 0.5,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_causal_claims_graph
    ON causal_claims (graph_id);
CREATE INDEX IF NOT EXISTS idx_causal_claims_evidence
    ON causal_claims (evidence_level);
CREATE INDEX IF NOT EXISTS idx_causal_claims_time
    ON causal_claims (created_at DESC);

-- Variables confondantes détectées
CREATE TABLE IF NOT EXISTS causal_confounders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id UUID REFERENCES causal_claims(id) ON DELETE CASCADE,

    confounder_name TEXT NOT NULL,
    confounder_domain TEXT,
    plausibility FLOAT DEFAULT 0.5,
    controlled BOOLEAN DEFAULT false,
    how_controlled TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_causal_confounders_claim
    ON causal_confounders (claim_id);
CREATE INDEX IF NOT EXISTS idx_causal_confounders_plausibility
    ON causal_confounders (plausibility DESC);

-- Vue : claims avec nombre de confounders
CREATE OR REPLACE VIEW causal_claims_summary AS
SELECT
    c.id,
    c.cause,
    c.effect,
    c.evidence_level,
    c.confidence,
    c.direction_verified,
    c.appropriate_language,
    g.name AS graph_name,
    g.domain,
    (SELECT COUNT(*) FROM causal_confounders cf WHERE cf.claim_id = c.id) AS confounder_count,
    (SELECT COUNT(*) FROM causal_confounders cf
     WHERE cf.claim_id = c.id AND cf.controlled = true) AS confounders_controlled_count
FROM causal_claims c
LEFT JOIN causal_graphs g ON c.graph_id = g.id;
