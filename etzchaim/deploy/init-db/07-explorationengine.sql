-- ExplorationEngine — Tikkun de Chesed
-- Exploration inter-domaines avec sérendipité structurée.

-- Explorations lancées
CREATE TABLE IF NOT EXISTS explorationengine_explorations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    seed_query TEXT NOT NULL,
    seed_domain TEXT NOT NULL,
    target_domains TEXT[] DEFAULT '{}',

    -- Résultats
    connections_found INTEGER DEFAULT 0,
    novel_connections INTEGER DEFAULT 0,

    -- Budget (anti-Gamchicoth)
    max_connections INTEGER DEFAULT 50,
    max_duration_seconds INTEGER DEFAULT 600,
    novelty_threshold FLOAT DEFAULT 0.3,

    -- Statut
    status TEXT CHECK (status IN (
        'running',
        'completed',
        'stopped_novelty',
        'stopped_budget'
    )) DEFAULT 'running',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Connexions inter-domaines trouvées
CREATE TABLE IF NOT EXISTS explorationengine_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    exploration_id UUID REFERENCES explorationengine_explorations(id),

    -- Les deux concepts connectés
    concept_a TEXT NOT NULL,
    domain_a TEXT NOT NULL,
    concept_b TEXT NOT NULL,
    domain_b TEXT NOT NULL,

    -- La connexion
    connection_type TEXT CHECK (connection_type IN (
        'analogy',
        'causal',
        'contradicts',
        'complements',
        'pattern_shared',
        'gematria_equivalence'
    )),
    description TEXT NOT NULL,

    -- Qualité
    novelty_score FLOAT,
    relevance_score FLOAT,
    confidence FLOAT,

    -- Persistance dans EpisteMemory
    epistememory_id UUID,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_explorationengine_explorations_status
    ON explorationengine_explorations(status);
CREATE INDEX IF NOT EXISTS idx_explorationengine_explorations_seed
    ON explorationengine_explorations(seed_domain);
CREATE INDEX IF NOT EXISTS idx_explorationengine_connections_exploration
    ON explorationengine_connections(exploration_id);
CREATE INDEX IF NOT EXISTS idx_explorationengine_connections_domains
    ON explorationengine_connections(domain_a, domain_b);
CREATE INDEX IF NOT EXISTS idx_explorationengine_connections_type
    ON explorationengine_connections(connection_type);
CREATE INDEX IF NOT EXISTS idx_explorationengine_connections_novelty
    ON explorationengine_connections(novelty_score DESC)
    WHERE novelty_score IS NOT NULL;

-- Vue : explorations avec taux de nouveauté (anti-Gamchicoth)
CREATE OR REPLACE VIEW explorationengine_novelty_rates AS
SELECT e.id,
       e.seed_query,
       e.seed_domain,
       e.status,
       e.connections_found,
       e.novel_connections,
       ROUND(e.novel_connections::numeric / NULLIF(e.connections_found, 0), 3) as novelty_rate,
       AVG(c.novelty_score) as avg_novelty_score
FROM explorationengine_explorations e
LEFT JOIN explorationengine_connections c ON c.exploration_id = e.id
GROUP BY e.id;

-- Vue : connexions les plus nouvelles (sérendipité)
CREATE OR REPLACE VIEW explorationengine_top_connections AS
SELECT c.*,
       e.seed_query,
       e.seed_domain
FROM explorationengine_connections c
JOIN explorationengine_explorations e ON e.id = c.exploration_id
WHERE c.novelty_score IS NOT NULL
ORDER BY c.novelty_score DESC;

-- Analogies cross-domain — Chesed extrait les patterns récurrents
-- entre connexions passées et génère des analogies structurelles.
CREATE TABLE IF NOT EXISTS explorationengine_analogies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Les deux domaines mis en relation
    domain_a TEXT NOT NULL,
    domain_b TEXT NOT NULL,

    -- L'analogie elle-même
    pattern TEXT NOT NULL,         -- le pattern structurel identifié
    explanation TEXT NOT NULL,     -- explication détaillée
    strength FLOAT DEFAULT 0.5,   -- force de l'analogie (0-1)

    -- Provenance
    source_connection_ids UUID[] DEFAULT '{}',  -- connexions qui l'ont inspirée
    generated_by TEXT NOT NULL DEFAULT 'heuristic',  -- 'heuristic' ou 'llm'

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_explorationengine_analogies_domains
    ON explorationengine_analogies(domain_a, domain_b);
CREATE INDEX IF NOT EXISTS idx_explorationengine_analogies_strength
    ON explorationengine_analogies(strength DESC);
CREATE INDEX IF NOT EXISTS idx_explorationengine_analogies_created
    ON explorationengine_analogies(created_at DESC);
