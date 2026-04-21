-- Migration 003: Hizdakchut transitions log (audit cycle 4, I3)
--
-- La table hizdakchut_state ne stocke que l'état courant (4 lignes max).
-- Sans log historique, impossible de prouver que la boucle d'auto-régulation
-- fonctionne en production. Cette table accumule chaque transition pour
-- traçabilité, debug, et métrique exposée via /api/state.

CREATE TABLE IF NOT EXISTS hizdakchut_transitions (
    id BIGSERIAL PRIMARY KEY,
    olam TEXT NOT NULL CHECK (olam IN (
        'atziluth', 'briah', 'yetzirah', 'assiah'
    )),
    from_level TEXT NOT NULL CHECK (from_level IN (
        'dalet', 'gimel', 'bet', 'aleph', 'shoresh'
    )),
    to_level TEXT NOT NULL CHECK (to_level IN (
        'dalet', 'gimel', 'bet', 'aleph', 'shoresh'
    )),
    quality_score REAL NOT NULL,
    reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Lookup par olam (les requêtes du dashboard filtrent souvent par monde).
CREATE INDEX IF NOT EXISTS idx_hizdakchut_transitions_olam_ts
    ON hizdakchut_transitions (olam, created_at DESC);

-- Comptage de fenêtre glissante (transitions/h) — exposé dans /api/state.
CREATE INDEX IF NOT EXISTS idx_hizdakchut_transitions_ts
    ON hizdakchut_transitions (created_at DESC);
