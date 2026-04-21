-- Partzufim — Persistance des 6 configurations matures de l'Arbre.
--
-- Dans le Tikkun, chaque Sephirah isolée (Nekudah) est reconstruite
-- comme un Partzuf — un organisme complet avec ses propres 10 Sephiroth
-- internes (Hitkalelut). Cette table persiste leur état entre redémarrages.

CREATE TABLE IF NOT EXISTS partzufim_state (
    name TEXT PRIMARY KEY,           -- atik_yomin, arikh_anpin, abba, imma, zeir_anpin, nukva
    overall_score FLOAT DEFAULT 0.0,
    mochin_state TEXT DEFAULT 'katnut'
        CHECK (mochin_state IN ('katnut', 'transitional', 'gadlut')),
    orientation TEXT DEFAULT 'akhor'
        CHECK (orientation IN ('panim', 'akhor')),
    faculties JSONB DEFAULT '{}',    -- Les 10 facultés internes {keter: 0.0, ...}
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_partzufim_state_updated
    ON partzufim_state (updated_at DESC);
