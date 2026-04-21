-- sifrei_yesod/schema.sql — Tables de la Bibliothèque Sacrée
-- 9 tables : sefarim, heikhalot, shaarim, perakim, assertions, concepts, relations, principes, cross_refs

-- ═══════════════════════════════════════════════════════════════
-- Table 1 : Registre des Sefarim (livres)
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS sifrei_yesod_sefarim (
    id SERIAL PRIMARY KEY,
    sefer_id VARCHAR(50) UNIQUE NOT NULL,
    titre_he TEXT NOT NULL,
    titre_fr TEXT NOT NULL,
    auteur TEXT NOT NULL,
    maitre TEXT,
    edition_base TEXT NOT NULL,
    date_composition TEXT,
    structure_type VARCHAR(50),
    nombre_shaarim INTEGER,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ═══════════════════════════════════════════════════════════════
-- Table 2 : Heikhalot (palais — niveau intermédiaire optionnel)
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS sifrei_yesod_heikhalot (
    id SERIAL PRIMARY KEY,
    sefer_id VARCHAR(50) NOT NULL REFERENCES sifrei_yesod_sefarim(sefer_id),
    heikhal_number INTEGER NOT NULL,
    heikhal_name_he TEXT NOT NULL,
    heikhal_name_fr TEXT NOT NULL,
    nombre_shaarim INTEGER,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(sefer_id, heikhal_number)
);

-- ═══════════════════════════════════════════════════════════════
-- Table 3 : Sha'arim (portes / sections)
-- heikhal_number = 0 → sha'ar standalone (ex: Sha'ar HaKlalim)
-- heikhal_number >= 1 → sha'ar dans un heikhal
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS sifrei_yesod_shaarim (
    id SERIAL PRIMARY KEY,
    sefer_id VARCHAR(50) NOT NULL REFERENCES sifrei_yesod_sefarim(sefer_id),
    heikhal_number INTEGER NOT NULL DEFAULT 0,
    shaar_number INTEGER NOT NULL,
    shaar_name_he TEXT NOT NULL,
    shaar_name_fr TEXT NOT NULL,
    nombre_perakim INTEGER,
    sujet_principal TEXT,
    concepts_cles TEXT[],
    connexions_modules TEXT[],
    connexions_domaines TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(sefer_id, heikhal_number, shaar_number)
);

-- ═══════════════════════════════════════════════════════════════
-- Table 4 : Perakim (chapitres)
-- heikhal_number = 0 → perek dans un sha'ar standalone
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS sifrei_yesod_perakim (
    id SERIAL PRIMARY KEY,
    sefer_id VARCHAR(50) NOT NULL,
    heikhal_number INTEGER NOT NULL DEFAULT 0,
    shaar_number INTEGER NOT NULL,
    perek_number INTEGER NOT NULL,
    source_edition TEXT NOT NULL,
    transposed_by TEXT NOT NULL,
    version INTEGER DEFAULT 1,
    strates TEXT[] DEFAULT ARRAY['base'],
    yaml_hash VARCHAR(64),
    ingested_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(sefer_id, heikhal_number, shaar_number, perek_number),
    FOREIGN KEY (sefer_id, heikhal_number, shaar_number)
        REFERENCES sifrei_yesod_shaarim(sefer_id, heikhal_number, shaar_number)
);

-- ═══════════════════════════════════════════════════════════════
-- Table 5 : Assertions — Couche Peshat-Machine
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS sifrei_yesod_assertions (
    id SERIAL PRIMARY KEY,
    assertion_id VARCHAR(20) UNIQUE NOT NULL,
    perek_id INTEGER NOT NULL REFERENCES sifrei_yesod_perakim(id),
    source_he TEXT NOT NULL,
    source_ref TEXT NOT NULL,
    assertion TEXT NOT NULL,
    assertion_type VARCHAR(30) NOT NULL,
    concepts JSONB NOT NULL DEFAULT '[]',
    mapping_modules TEXT[],
    mapping_tables TEXT[],
    mapping_partzufim TEXT[],
    mapping_relevance TEXT,
    strate VARCHAR(30) DEFAULT 'base',
    embedding vector(768),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sy_assertions_embedding
    ON sifrei_yesod_assertions USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 20);

CREATE INDEX IF NOT EXISTS idx_sy_assertions_concepts
    ON sifrei_yesod_assertions USING GIN (concepts);

CREATE INDEX IF NOT EXISTS idx_sy_assertions_type
    ON sifrei_yesod_assertions (assertion_type);

-- ═══════════════════════════════════════════════════════════════
-- Table 6 : Concepts — Registre des Concepts Kabbalistiques
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS sifrei_yesod_concepts (
    id SERIAL PRIMARY KEY,
    concept_id VARCHAR(100) UNIQUE NOT NULL,
    nom_he TEXT,
    nom_fr TEXT,
    description TEXT,
    domaine VARCHAR(50),
    premiere_apparition VARCHAR(20),
    embedding vector(768),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sy_concepts_embedding
    ON sifrei_yesod_concepts USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 20);

CREATE INDEX IF NOT EXISTS idx_sy_concepts_domaine
    ON sifrei_yesod_concepts (domaine);

-- ═══════════════════════════════════════════════════════════════
-- Table 7 : Relations — Couche Remez-Relational
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS sifrei_yesod_relations (
    id SERIAL PRIMARY KEY,
    relation_id VARCHAR(20) UNIQUE NOT NULL,
    perek_id INTEGER NOT NULL REFERENCES sifrei_yesod_perakim(id),
    relation_type VARCHAR(30) NOT NULL,
    concept_from VARCHAR(100) REFERENCES sifrei_yesod_concepts(concept_id),
    concept_to VARCHAR(100) REFERENCES sifrei_yesod_concepts(concept_id),
    paire TEXT[],
    via TEXT[],
    nature TEXT NOT NULL,
    pattern VARCHAR(100),
    assertions_source TEXT[] NOT NULL,
    bidirectionnel BOOLEAN DEFAULT FALSE,
    strate VARCHAR(30) DEFAULT 'base',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sy_relations_from
    ON sifrei_yesod_relations (concept_from);
CREATE INDEX IF NOT EXISTS idx_sy_relations_to
    ON sifrei_yesod_relations (concept_to);
CREATE INDEX IF NOT EXISTS idx_sy_relations_type
    ON sifrei_yesod_relations (relation_type);

-- ═══════════════════════════════════════════════════════════════
-- Table 8 : Principes Génératifs — Couche Sod-Generative
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS sifrei_yesod_principes (
    id SERIAL PRIMARY KEY,
    principe_id VARCHAR(20) UNIQUE NOT NULL,
    perek_id INTEGER NOT NULL REFERENCES sifrei_yesod_perakim(id),
    nom TEXT NOT NULL,
    source_assertions TEXT[] NOT NULL,
    formalisation TEXT NOT NULL,
    applications_ia TEXT[] NOT NULL,
    questions_ouvertes TEXT[],
    strate VARCHAR(30) DEFAULT 'base',
    embedding vector(768),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sy_principes_embedding
    ON sifrei_yesod_principes USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 20);

-- ═══════════════════════════════════════════════════════════════
-- Table 9 : Cross-Références Inter-Sefarim
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS sifrei_yesod_cross_refs (
    id SERIAL PRIMARY KEY,
    source_assertion_id VARCHAR(20) NOT NULL,
    target_assertion_id VARCHAR(20),
    target_sefer VARCHAR(50) NOT NULL,
    target_ref TEXT NOT NULL,
    relation_type VARCHAR(30) NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sy_crossrefs_source
    ON sifrei_yesod_cross_refs (source_assertion_id);
CREATE INDEX IF NOT EXISTS idx_sy_crossrefs_target
    ON sifrei_yesod_cross_refs (target_sefer);
