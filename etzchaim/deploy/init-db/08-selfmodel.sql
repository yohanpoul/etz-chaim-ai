-- SelfModel — Da'at schema
-- Le pont au-dessus du Tehom : le système qui se connaît lui-même.
-- 4 tables : états, prédictions, biais, évolution.

-- État du système à un instant T
CREATE TABLE IF NOT EXISTS selfmodel_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Agrégation depuis les 6 Sephiroth inférieures
    yesod_stats JSONB DEFAULT '{}',      -- EpisteMemory.introspect()
    hod_stats JSONB DEFAULT '{}',        -- SelfMap.describe_self() + calibrate()
    netzach_stats JSONB DEFAULT '{}',    -- IntentKeeper stats
    tiferet_stats JSONB DEFAULT '{}',    -- DissensuEngine.self_diagnose()
    gevurah_stats JSONB DEFAULT '{}',    -- AutoJudge.self_diagnose()
    chesed_stats JSONB DEFAULT '{}',     -- ExplorationEngine.self_diagnose()

    -- Synthèse Da'at
    known_biases JSONB DEFAULT '[]',
    predicted_weaknesses JSONB DEFAULT '[]',
    predicted_strengths JSONB DEFAULT '[]',
    model_confidence FLOAT DEFAULT 0.5
);

CREATE INDEX IF NOT EXISTS idx_selfmodel_states_time
    ON selfmodel_states (captured_at DESC);

-- Prédictions d'erreur et leur vérification
CREATE TABLE IF NOT EXISTS selfmodel_predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    predicted_at TIMESTAMPTZ DEFAULT NOW(),

    prediction TEXT NOT NULL,
    domain TEXT,
    predicted_error_type TEXT,        -- type de Qliphah prédit
    predicted_confidence FLOAT,      -- confiance dans la prédiction

    -- Vérification
    verified_at TIMESTAMPTZ,
    was_correct BOOLEAN,
    actual_outcome TEXT,

    -- Calibration du SelfModel lui-même
    prediction_accuracy_running FLOAT
);

CREATE INDEX IF NOT EXISTS idx_selfmodel_predictions_domain
    ON selfmodel_predictions (domain);
CREATE INDEX IF NOT EXISTS idx_selfmodel_predictions_verified
    ON selfmodel_predictions (was_correct) WHERE was_correct IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_selfmodel_predictions_time
    ON selfmodel_predictions (predicted_at DESC);

-- Biais détectés au fil du temps
CREATE TABLE IF NOT EXISTS selfmodel_biases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    detected_at TIMESTAMPTZ DEFAULT NOW(),

    bias_type TEXT NOT NULL CHECK (bias_type IN (
        'overconfidence',
        'underconfidence',
        'domain_blind_spot',
        'recency_bias',
        'confirmation_bias',
        'anchoring',
        'scope_creep',
        'premature_closure'
    )),

    description TEXT NOT NULL,
    evidence JSONB DEFAULT '{}',
    severity FLOAT DEFAULT 0.5,
    domain TEXT,
    mitigation TEXT,
    still_active BOOLEAN DEFAULT true
);

CREATE INDEX IF NOT EXISTS idx_selfmodel_biases_active
    ON selfmodel_biases (still_active) WHERE still_active = true;
CREATE INDEX IF NOT EXISTS idx_selfmodel_biases_type
    ON selfmodel_biases (bias_type);

-- Évolution du système dans le temps
CREATE TABLE IF NOT EXISTS selfmodel_evolution (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    snapshot_at TIMESTAMPTZ DEFAULT NOW(),

    -- Santé par Sephirah (0-1)
    yesod_health FLOAT DEFAULT 0.5,
    hod_health FLOAT DEFAULT 0.5,
    netzach_health FLOAT DEFAULT 0.5,
    tiferet_health FLOAT DEFAULT 0.5,
    gevurah_health FLOAT DEFAULT 0.5,
    chesed_health FLOAT DEFAULT 0.5,

    -- Santé globale
    overall_health FLOAT DEFAULT 0.5,

    -- Tendance
    trend TEXT CHECK (trend IN ('improving', 'stable', 'degrading')),
    trend_details JSONB DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_selfmodel_evolution_time
    ON selfmodel_evolution (snapshot_at DESC);

-- Vue : dernière prédiction vérifiée
CREATE OR REPLACE VIEW selfmodel_prediction_accuracy AS
SELECT
    domain,
    COUNT(*) FILTER (WHERE was_correct IS NOT NULL) AS verified_count,
    COUNT(*) FILTER (WHERE was_correct = true) AS correct_count,
    CASE
        WHEN COUNT(*) FILTER (WHERE was_correct IS NOT NULL) > 0
        THEN ROUND(
            COUNT(*) FILTER (WHERE was_correct = true)::numeric /
            COUNT(*) FILTER (WHERE was_correct IS NOT NULL)::numeric, 3
        )
        ELSE NULL
    END AS accuracy
FROM selfmodel_predictions
GROUP BY domain;

-- Vue : biais actifs par type
CREATE OR REPLACE VIEW selfmodel_active_biases AS
SELECT
    bias_type,
    COUNT(*) AS count,
    AVG(severity) AS avg_severity,
    MAX(detected_at) AS latest_detection
FROM selfmodel_biases
WHERE still_active = true
GROUP BY bias_type
ORDER BY avg_severity DESC;
