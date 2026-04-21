-- Clustering dual Kabbale vs ML — Kibboutz (קִבּוּץ)
-- Compare les regroupements par structure kabbalistique (30D Cube)
-- vs par sémantique statistique (768D ML).
-- Les désaccords entre les deux = pistes d'investigation.

-- Résultats globaux d'un run de clustering
CREATE TABLE IF NOT EXISTS clustering_results (
    id SERIAL PRIMARY KEY,
    run_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    n_concepts INTEGER NOT NULL,
    n_clusters_kab INTEGER NOT NULL,
    n_clusters_ml INTEGER NOT NULL,
    n_disagreements INTEGER NOT NULL,
    agreement_ratio FLOAT NOT NULL,
    algorithm VARCHAR(50) NOT NULL DEFAULT 'kmeans',
    params JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Désaccords par paire : tradition vs statistique
CREATE TABLE IF NOT EXISTS clustering_disagreements (
    id SERIAL PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES clustering_results(id) ON DELETE CASCADE,
    concept_a VARCHAR(255) NOT NULL,
    concept_b VARCHAR(255) NOT NULL,
    same_cluster_kab BOOLEAN NOT NULL,
    same_cluster_ml BOOLEAN NOT NULL,
    kab_similarity FLOAT NOT NULL,
    ml_similarity FLOAT NOT NULL,
    gap FLOAT NOT NULL,
    disagreement_type VARCHAR(50) NOT NULL CHECK (disagreement_type IN (
        'kab_close_ml_far',   -- tradition dit proches, ML dit distants
        'ml_close_kab_far'    -- ML dit proches, tradition dit distants
    )),
    -- Suivi temporel
    first_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    times_seen INTEGER NOT NULL DEFAULT 1,
    -- Lien DissensuEngine
    dissensus_id UUID,
    routed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Unique sur paire ordonnée pour le suivi temporel (ON CONFLICT)
CREATE UNIQUE INDEX IF NOT EXISTS idx_clustering_pair
    ON clustering_disagreements (concept_a, concept_b);

CREATE INDEX IF NOT EXISTS idx_clustering_run
    ON clustering_disagreements (run_id);
CREATE INDEX IF NOT EXISTS idx_clustering_gap
    ON clustering_disagreements (gap DESC);
CREATE INDEX IF NOT EXISTS idx_clustering_unrouted
    ON clustering_disagreements (gap DESC) WHERE dissensus_id IS NULL;
CREATE INDEX IF NOT EXISTS idx_clustering_persistent
    ON clustering_disagreements (times_seen DESC);
