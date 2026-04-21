-- kabbalah/schema_hybrid.sql — Table des embeddings hybrides Cube+ML
-- Requiert l'extension pgvector

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS hybrid_embeddings (
    id SERIAL PRIMARY KEY,
    concept TEXT NOT NULL UNIQUE,
    hebrew_word TEXT,
    kabbalistic_signature vector(30),
    ml_embedding vector(768),
    hybrid_vector vector(798),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    status TEXT DEFAULT 'active',
    authority_olam FLOAT DEFAULT 0.5,
    source_module TEXT DEFAULT 'manual',
    harvested_at TIMESTAMPTZ DEFAULT NOW(),
    gematria_gadol INTEGER,
    gematria_siduri INTEGER,
    gematria_katan INTEGER,
    last_consumed_at TIMESTAMPTZ,
    consume_count INTEGER DEFAULT 0
);

-- Index pour recherche par similarité kabbalistique (30 dims — exact search OK)
CREATE INDEX IF NOT EXISTS idx_hybrid_kab_cosine
    ON hybrid_embeddings USING ivfflat (kabbalistic_signature vector_cosine_ops)
    WITH (lists = 10);

-- Index pour recherche par similarité ML (768 dims)
CREATE INDEX IF NOT EXISTS idx_hybrid_ml_cosine
    ON hybrid_embeddings USING ivfflat (ml_embedding vector_cosine_ops)
    WITH (lists = 20);

-- Index pour recherche hybride (798 dims)
CREATE INDEX IF NOT EXISTS idx_hybrid_full_cosine
    ON hybrid_embeddings USING ivfflat (hybrid_vector vector_cosine_ops)
    WITH (lists = 20);
