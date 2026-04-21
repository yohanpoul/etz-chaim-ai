-- Sefirat haOmer — Table d'historique des calibrations
-- ספירת העומר — 49 jours de raffinement, un paramètre par jour.
--
-- Chaque modification de paramètre est loggée ici.
-- L'Omer est le tuning fin de l'Arbre — la trace de son évolution.

CREATE TABLE IF NOT EXISTS omer_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    param_key TEXT NOT NULL,          -- ex: "gevurah_dans_gevurah"
    param_name TEXT NOT NULL,         -- ex: "quality_threshold"
    sephirah TEXT NOT NULL CHECK (sephirah IN (
        'keter', 'chokmah', 'binah',
        'chesed', 'gevurah', 'tiferet', 'netzach', 'hod', 'yesod', 'malkuth'
    )),
    inner_midah TEXT NOT NULL CHECK (inner_midah IN (
        'keter', 'chokmah', 'binah',
        'chesed', 'gevurah', 'tiferet', 'netzach', 'hod', 'yesod', 'malkuth'
    )),
    module TEXT NOT NULL,             -- ex: "autojudge"
    old_value TEXT,                   -- valeur avant modification (sérialisée)
    new_value TEXT NOT NULL,          -- nouvelle valeur (sérialisée)
    reason TEXT NOT NULL,             -- justification de la modification
    source TEXT NOT NULL DEFAULT 'tune' CHECK (source IN (
        'tune',      -- suggestion automatique via etz omer tune
        'manual',    -- modification manuelle
        'reset'      -- retour aux défauts
    )),
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_omer_history_param
    ON omer_history (param_key, applied_at DESC);
CREATE INDEX IF NOT EXISTS idx_omer_history_sephirah
    ON omer_history (sephirah, applied_at DESC);
CREATE INDEX IF NOT EXISTS idx_omer_history_applied
    ON omer_history (applied_at DESC);

-- Vue : valeur courante de chaque paramètre (dernière modification)
CREATE OR REPLACE VIEW omer_current AS
SELECT DISTINCT ON (param_key)
       param_key, param_name, sephirah, inner_midah, module,
       new_value AS current_value, reason AS last_reason,
       applied_at AS last_modified
FROM omer_history
ORDER BY param_key, applied_at DESC;

-- Vue : nombre de modifications par Sephirah
CREATE OR REPLACE VIEW omer_activity AS
SELECT sephirah,
       COUNT(*) AS total_changes,
       COUNT(DISTINCT param_key) AS params_touched,
       MAX(applied_at) AS last_change
FROM omer_history
GROUP BY sephirah
ORDER BY last_change DESC;
