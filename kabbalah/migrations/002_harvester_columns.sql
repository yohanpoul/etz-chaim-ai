-- Tikkun: extend hybrid_embeddings for ConceptHarvester pipeline
ALTER TABLE hybrid_embeddings ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'active';
ALTER TABLE hybrid_embeddings ADD COLUMN IF NOT EXISTS authority_olam FLOAT DEFAULT 0.5;
ALTER TABLE hybrid_embeddings ADD COLUMN IF NOT EXISTS source_module TEXT DEFAULT 'manual';
ALTER TABLE hybrid_embeddings ADD COLUMN IF NOT EXISTS harvested_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE hybrid_embeddings ADD COLUMN IF NOT EXISTS gematria_gadol INTEGER;
ALTER TABLE hybrid_embeddings ADD COLUMN IF NOT EXISTS gematria_siduri INTEGER;
ALTER TABLE hybrid_embeddings ADD COLUMN IF NOT EXISTS gematria_katan INTEGER;
ALTER TABLE hybrid_embeddings ADD COLUMN IF NOT EXISTS last_consumed_at TIMESTAMPTZ;
ALTER TABLE hybrid_embeddings ADD COLUMN IF NOT EXISTS consume_count INTEGER DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_hybrid_status ON hybrid_embeddings(status);
CREATE INDEX IF NOT EXISTS idx_hybrid_harvested ON hybrid_embeddings(harvested_at);
CREATE INDEX IF NOT EXISTS idx_hybrid_source ON hybrid_embeddings(source_module);
