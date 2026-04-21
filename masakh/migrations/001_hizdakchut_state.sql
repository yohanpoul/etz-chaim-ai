-- Hizdakchut state persistence (audit F06, recommendation R4)
--
-- Le dict _HIZDAKCHUT_LEVELS etait volatile (memoire seule).
-- Cette table persiste les niveaux ajustes par hizdakchut entre
-- les redemarrages du processus.

CREATE TABLE IF NOT EXISTS hizdakchut_state (
    olam TEXT PRIMARY KEY CHECK (olam IN (
        'atziluth', 'briah', 'yetzirah', 'assiah'
    )),
    level TEXT NOT NULL DEFAULT 'bet' CHECK (level IN (
        'dalet', 'gimel', 'bet', 'aleph', 'shoresh'
    )),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed with defaults (OLAM_DEFAULT_LEVEL mapping)
INSERT INTO hizdakchut_state (olam, level) VALUES
    ('atziluth', 'dalet'),
    ('briah', 'gimel'),
    ('yetzirah', 'bet'),
    ('assiah', 'aleph')
ON CONFLICT (olam) DO NOTHING;
