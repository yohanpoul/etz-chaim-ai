-- SelfMap — Yesod-de-Hod : le schéma de la self-knowledge
-- "Aaron le prêtre qui nomme les choses pour ce qu'elles sont."

-- Table principale : compétence par domaine et modèle
CREATE TABLE IF NOT EXISTS selfmap_competence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain TEXT NOT NULL,
    model_id TEXT NOT NULL,
    score FLOAT NOT NULL CHECK (score BETWEEN 0 AND 1),
    brier_score FLOAT,            -- calibration quality (lower = better)
    n_evals INTEGER DEFAULT 0,
    last_eval TIMESTAMPTZ,
    eval_results JSONB,           -- questions posées et résultats détaillés
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE (domain, model_id)
);

CREATE INDEX IF NOT EXISTS idx_selfmap_domain
    ON selfmap_competence (domain);
CREATE INDEX IF NOT EXISTS idx_selfmap_model
    ON selfmap_competence (model_id);
CREATE INDEX IF NOT EXISTS idx_selfmap_score
    ON selfmap_competence (score DESC);

-- Table de log : chaque décision de routage
CREATE TABLE IF NOT EXISTS selfmap_routing_log (
    id UUID DEFAULT gen_random_uuid(),
    query TEXT NOT NULL,
    detected_domain TEXT,
    competence_score FLOAT,
    routed_to TEXT,                -- model_id choisi
    did_decline BOOLEAN DEFAULT false,
    decline_reason TEXT,
    outcome_quality FLOAT,        -- évaluation a posteriori (NULL = pas encore évalué)
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, created_at)
);

-- TimescaleDB : routing_log comme série temporelle
SELECT create_hypertable('selfmap_routing_log', 'created_at',
                         if_not_exists => true,
                         migrate_data => true);

CREATE INDEX IF NOT EXISTS idx_routing_domain
    ON selfmap_routing_log (detected_domain, created_at DESC);

-- Vue : domaines les plus faibles (Samael warning)
CREATE OR REPLACE VIEW weak_domains AS
SELECT domain, model_id, score, n_evals, last_eval
FROM selfmap_competence
WHERE score < 0.4
ORDER BY score ASC;

-- Vue : calibration par modèle
CREATE OR REPLACE VIEW model_calibration AS
SELECT model_id,
       COUNT(*) AS n_domains,
       AVG(score) AS avg_score,
       AVG(brier_score) AS avg_brier,
       MIN(score) AS worst_domain_score,
       MAX(last_eval) AS last_eval
FROM selfmap_competence
GROUP BY model_id;

-- Vue : taux de déclin (Gevurah-de-Hod)
CREATE OR REPLACE VIEW decline_stats AS
SELECT detected_domain,
       COUNT(*) AS total_queries,
       COUNT(*) FILTER (WHERE did_decline) AS declined,
       ROUND(100.0 * COUNT(*) FILTER (WHERE did_decline) / NULLIF(COUNT(*), 0), 1)
           AS decline_pct,
       AVG(outcome_quality) FILTER (WHERE NOT did_decline) AS avg_quality_when_answered
FROM selfmap_routing_log
GROUP BY detected_domain;
