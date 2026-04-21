-- Tzeruf Spatial: geometric relationships between Hebrew words
CREATE TABLE IF NOT EXISTS tzeruf_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    word_a TEXT NOT NULL,
    word_b TEXT NOT NULL,
    relationship TEXT NOT NULL CHECK (relationship IN (
        'parallel', 'perpendicular', 'opposed', 'similar'
    )),
    angle FLOAT NOT NULL,
    geometric_similarity FLOAT,
    dominant_direction_a TEXT,
    dominant_direction_b TEXT,
    source TEXT DEFAULT 'daemon',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(word_a, word_b)
);

CREATE INDEX IF NOT EXISTS idx_tzeruf_relationship ON tzeruf_relationships(relationship);
CREATE INDEX IF NOT EXISTS idx_tzeruf_created ON tzeruf_relationships(created_at);
