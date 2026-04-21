-- DissensuEngine — Tikkun de Tiferet (תפארת)
-- Le cœur de l'Arbre : hitkalelut entre Chesed (accepter) et Gevurah (rejeter)
-- Anti-Thagirion : JAMAIS de fausse harmonie
--
-- Lev (לב) = 32 = les 32 sentiers de la Sagesse
-- "Il ne s'agit pas de résoudre les contradictions mais de les habiter."

-- Conclusions — les claims provenant de sources multiples
CREATE TABLE IF NOT EXISTS dissensuengine_conclusions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    source_label TEXT NOT NULL,        -- qui/quoi affirme ceci
    source_type TEXT NOT NULL CHECK (source_type IN (
        'paper', 'model', 'tradition', 'experiment', 'human', 'system'
    )),
    domain TEXT,
    confidence FLOAT NOT NULL DEFAULT 0.5,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Tensions — divergences détectées entre conclusions
CREATE TABLE IF NOT EXISTS dissensuengine_tensions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conclusion_a_id UUID NOT NULL REFERENCES dissensuengine_conclusions(id) ON DELETE CASCADE,
    conclusion_b_id UUID NOT NULL REFERENCES dissensuengine_conclusions(id) ON DELETE CASCADE,
    tension_type TEXT NOT NULL CHECK (tension_type IN (
        'contradiction',           -- A et B s'excluent mutuellement
        'nuance',                  -- A et B divergent sur un point non essentiel
        'scope_conflict',          -- A vrai dans un contexte, B vrai dans un autre
        'framing_difference'       -- même réalité, cadrage incompatible
    )),
    divergence_score FLOAT NOT NULL CHECK (divergence_score >= 0 AND divergence_score <= 1),
    description TEXT,
    resolution_status TEXT NOT NULL DEFAULT 'open' CHECK (resolution_status IN (
        'open',                    -- tension non résolue
        'resolved',                -- tension résolue par une synthèse
        'irreducible'              -- tension acceptée comme irréductible — coincidentia oppositorum
    )),
    resolved_by UUID,              -- synthesis_id si résolu
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (conclusion_a_id, conclusion_b_id)
);

-- Synthèses ou Dissensus — le résultat de l'analyse
CREATE TABLE IF NOT EXISTS dissensuengine_syntheses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mode TEXT NOT NULL CHECK (mode IN (
        'synthesis',               -- synthèse réussie — les sources convergent
        'dissensus'                -- refus de conclure — les sources divergent trop
    )),
    content TEXT NOT NULL,
    sources_used UUID[] NOT NULL,   -- conclusion_ids inclus
    source_coverage FLOAT NOT NULL, -- % des conclusions pertinentes incluses
    max_divergence FLOAT NOT NULL,  -- plus haute divergence dans l'ensemble
    confidence FLOAT NOT NULL,
    domain TEXT,
    epistememory_id UUID,           -- lien vers Yesod si persisté
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Questions ouvertes — pas un bug, une question VIVANTE
CREATE TABLE IF NOT EXISTS dissensuengine_open_questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tension_id UUID NOT NULL REFERENCES dissensuengine_tensions(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    missing_evidence TEXT,          -- ce qui manque pour résoudre
    priority TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN (
        'low', 'medium', 'high', 'critical'
    )),
    domain TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

-- Index pour recherches fréquentes
CREATE INDEX IF NOT EXISTS idx_de_conclusions_domain
    ON dissensuengine_conclusions (domain);
CREATE INDEX IF NOT EXISTS idx_de_conclusions_source
    ON dissensuengine_conclusions (source_type, source_label);
CREATE INDEX IF NOT EXISTS idx_de_tensions_status
    ON dissensuengine_tensions (resolution_status);
CREATE INDEX IF NOT EXISTS idx_de_tensions_a
    ON dissensuengine_tensions (conclusion_a_id);
CREATE INDEX IF NOT EXISTS idx_de_tensions_b
    ON dissensuengine_tensions (conclusion_b_id);
CREATE INDEX IF NOT EXISTS idx_de_syntheses_mode
    ON dissensuengine_syntheses (mode);
CREATE INDEX IF NOT EXISTS idx_de_open_questions_tension
    ON dissensuengine_open_questions (tension_id);
CREATE INDEX IF NOT EXISTS idx_de_open_questions_priority
    ON dissensuengine_open_questions (priority);

-- Vue : tensions ouvertes par type
CREATE OR REPLACE VIEW open_tensions AS
SELECT t.*, ca.content AS content_a, cb.content AS content_b,
       ca.source_label AS source_a, cb.source_label AS source_b
FROM dissensuengine_tensions t
JOIN dissensuengine_conclusions ca ON ca.id = t.conclusion_a_id
JOIN dissensuengine_conclusions cb ON cb.id = t.conclusion_b_id
WHERE t.resolution_status = 'open'
ORDER BY t.divergence_score DESC;

-- Vue : synthèses en mode dissensus (les refus de conclure)
CREATE OR REPLACE VIEW dissensus_log AS
SELECT s.*, array_length(s.sources_used, 1) AS num_sources
FROM dissensuengine_syntheses s
WHERE s.mode = 'dissensus'
ORDER BY s.created_at DESC;
