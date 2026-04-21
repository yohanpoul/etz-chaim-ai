-- EpisteMemory — Yesod-de-Yesod : le schéma fondateur
-- "Le Tzaddik est la fondation du monde" — Proverbes 10:25

-- Table principale des entrées mémoire
CREATE TABLE IF NOT EXISTS epistememory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Contenu
    content TEXT NOT NULL,
    embedding VECTOR(768),  -- nomic-embed-text = 768 dimensions

    -- Provenance (quelle "Sephirah" a produit cette entrée)
    source_sephirah TEXT NOT NULL CHECK (source_sephirah IN (
        'keter',     -- intention originelle
        'chokmah',   -- hypothèse/intuition
        'binah',     -- analyse structurée
        'chesed',    -- acquisition/scraping
        'gevurah',   -- validation (entrée qui a PASSÉ le filtre)
        'tiferet',   -- synthèse
        'netzach',   -- persistance/itération
        'hod',       -- évaluation/self-knowledge
        'yesod',     -- mémoire fondatrice
        'malkuth',   -- données brutes du monde
        'daat',      -- connaissance intégrée
        'external',  -- donnée externe (user input, API, fichier)
        'unknown',
        'sifrei_yesod'  -- concepts et assertions des Sifrei Yesod
    )),
    source_detail JSONB,  -- détails de provenance (URL, modèle, prompt, etc.)

    -- Épistémologie
    confidence FLOAT NOT NULL DEFAULT 0.5 CHECK (confidence BETWEEN 0 AND 1),
    epistemic_status TEXT NOT NULL DEFAULT 'hypothesis' CHECK (epistemic_status IN (
        'hypothesis',      -- généré par Chokmah, non vérifié
        'correlation',     -- pattern détecté par Binah, pas de causalité prouvée
        'verified_once',   -- vérifié une fois par Gevurah
        'verified_multi',  -- vérifié par plusieurs sources indépendantes
        'fact',            -- considéré comme fait établi (confiance > 0.9)
        'contested',       -- contredit par au moins une autre entrée
        'deprecated'       -- remplacé par une entrée plus récente
    )),

    -- Temporalité
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_accessed TIMESTAMPTZ,
    access_count INTEGER DEFAULT 0,
    ttl_days INTEGER,       -- NULL = pas d'expiration
    expires_at TIMESTAMPTZ, -- calculé : created_at + ttl_days

    -- Domaine
    domain TEXT,
    tags TEXT[],

    -- Contradictions et supports
    contradicts UUID[],  -- IDs des entrées qui contredisent celle-ci
    supports UUID[],     -- IDs des entrées qui soutiennent celle-ci

    -- Versioning
    supersedes UUID REFERENCES epistememory(id),
    superseded_by UUID REFERENCES epistememory(id)
);

-- Index pour recherche sémantique (HNSW — meilleur que IVFFlat pour < 1M vecteurs)
CREATE INDEX IF NOT EXISTS idx_epistememory_embedding
    ON epistememory USING hnsw (embedding vector_cosine_ops);

-- Index pour recherche par statut/domaine
CREATE INDEX IF NOT EXISTS idx_epistememory_status_domain
    ON epistememory (epistemic_status, domain);

CREATE INDEX IF NOT EXISTS idx_epistememory_confidence
    ON epistememory (confidence DESC);

CREATE INDEX IF NOT EXISTS idx_epistememory_expires
    ON epistememory (expires_at) WHERE expires_at IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_epistememory_domain
    ON epistememory (domain) WHERE domain IS NOT NULL;

-- Vue : entrées actives (non périmées, non deprecated)
CREATE OR REPLACE VIEW active_memory AS
SELECT * FROM epistememory
WHERE epistemic_status != 'deprecated'
AND (expires_at IS NULL OR expires_at > NOW());

-- Vue : contradictions ouvertes (Tiferet-de-Yesod)
CREATE OR REPLACE VIEW open_contradictions AS
SELECT e1.id AS entry_id, e1.content AS entry_content,
       e2.id AS contradicts_id, e2.content AS contradicts_content,
       e1.confidence AS entry_confidence, e2.confidence AS contra_confidence
FROM epistememory e1
CROSS JOIN UNNEST(e1.contradicts) AS cid
JOIN epistememory e2 ON e2.id = cid
WHERE e1.epistemic_status != 'deprecated'
AND e2.epistemic_status != 'deprecated';

-- Vue : entrées proches de l'expiration (Nogah warning)
CREATE OR REPLACE VIEW near_expiration AS
SELECT *, expires_at - NOW() AS time_remaining
FROM epistememory
WHERE expires_at IS NOT NULL
AND expires_at > NOW()
AND expires_at < NOW() + INTERVAL '7 days'
AND epistemic_status != 'deprecated';

-- Vue : statistiques par domaine (Hod-de-Yesod)
CREATE OR REPLACE VIEW memory_stats AS
SELECT
    domain,
    epistemic_status,
    COUNT(*) AS entry_count,
    AVG(confidence) AS avg_confidence,
    MIN(created_at) AS oldest,
    MAX(created_at) AS newest,
    AVG(access_count) AS avg_access_count
FROM epistememory
WHERE epistemic_status != 'deprecated'
GROUP BY domain, epistemic_status;
