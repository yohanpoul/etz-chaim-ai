-- Masakh — Reshimo de Aviut : trace du filtrage
-- "L'écran ne détruit pas la lumière — il la mesure"
--
-- Phase 2 : Masakh dynamique avec Kashiut + Aviut + Kavvanah + Reshimot

-- ── Table masakh_log — trace de chaque filtrage ────────────────

CREATE TABLE IF NOT EXISTS masakh_log (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Quel Olam a été appelé
    olam TEXT NOT NULL CHECK (olam IN (
        'atziluth', 'briah', 'yetzirah', 'assiah'
    )),

    -- Niveau d'Aviut appliqué (Phase 2 : ajout shoresh)
    aviut_level TEXT NOT NULL CHECK (aviut_level IN (
        'dalet', 'gimel', 'bet', 'aleph', 'shoresh'
    )),

    -- Phase 2 : double propriété Kashiut + Aviut
    kashiut REAL NOT NULL DEFAULT 0.0,
    aviut_mode TEXT NOT NULL DEFAULT 'unknown' CHECK (aviut_mode IN (
        'compression_forte', 'compression_moderee', 'resume',
        'troncation', 'aucune', 'unknown'
    )),

    -- Métriques du filtrage
    tokens_before INTEGER NOT NULL,
    tokens_after INTEGER NOT NULL,
    tokens_rejected INTEGER NOT NULL DEFAULT 0,

    -- Raison du filtrage (ou "within budget")
    rejection_reason TEXT,

    -- Phase 2 : Kavvanah associée à cet appel
    kavvanah JSONB
);

-- Index temporel pour les requêtes d'analyse
CREATE INDEX IF NOT EXISTS idx_masakh_log_created
    ON masakh_log (created_at DESC);

-- Index par olam pour les statistiques par monde
CREATE INDEX IF NOT EXISTS idx_masakh_log_olam
    ON masakh_log (olam);

-- Vue : statistiques de filtrage par olam et mode
CREATE OR REPLACE VIEW masakh_stats AS
SELECT
    olam,
    aviut_level,
    aviut_mode,
    COUNT(*) AS total_calls,
    SUM(CASE WHEN tokens_rejected > 0 THEN 1 ELSE 0 END) AS filtered_calls,
    AVG(kashiut) AS avg_kashiut,
    AVG(tokens_before) AS avg_tokens_before,
    AVG(tokens_after) AS avg_tokens_after,
    AVG(tokens_rejected) AS avg_tokens_rejected,
    MAX(tokens_rejected) AS max_tokens_rejected
FROM masakh_log
GROUP BY olam, aviut_level, aviut_mode;


-- ── Table reshimot — Double Reshimo (Phase 2c) ────────────────
--
-- Après chaque appel LLM, deux traces sont conservées :
--   reshimo_hitlabshut (רְשִׁימוֹ דְּהִתְלַבְּשׁוּת) = CE QUI a été fait
--   reshimo_aviut      (רְשִׁימוֹ דְּעָבִיוּת)       = COMMENT le filtrage a fonctionné
--
-- Le ContextAssembler futur utilisera ces Reshimot pour calibrer
-- le Masakh dès le départ de la prochaine session.

CREATE TABLE IF NOT EXISTS reshimot (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Quel Olam a produit ce Reshimo
    olam TEXT NOT NULL CHECK (olam IN (
        'atziluth', 'briah', 'yetzirah', 'assiah'
    )),

    -- Reshimo de Hitlabshut : CE QUI a été fait
    -- {result, decision, domain, response_length, ...}
    reshimo_hitlabshut JSONB NOT NULL DEFAULT '{}',

    -- Reshimo de Aviut : COMMENT le filtrage a fonctionné
    -- {masakh_level, tokens_before, tokens_after, kashiut, aviut_mode,
    --  kavvanah, score, sources_count, ...}
    reshimo_aviut JSONB NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_reshimot_created
    ON reshimot (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_reshimot_olam
    ON reshimot (olam);


-- ── Table context_monitor_log — état des 29 dimensions ────────
--
-- Après chaque appel LLM, le ContextMonitor évalue les 29 dimensions
-- du Kli et persiste l'état. Le score_global est le ratio de dimensions
-- opérantes (✓) sur les dimensions applicables.
-- PG-SHK-022 — Phase 3 (Sod HaKli).

CREATE TABLE IF NOT EXISTS context_monitor_log (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    olam TEXT NOT NULL CHECK (olam IN (
        'atziluth', 'briah', 'yetzirah', 'assiah', 'unknown'
    )),

    -- État des 29 dimensions : [{id, name, status}, ...]
    dimensions JSONB NOT NULL DEFAULT '[]',

    -- Score global : ✓ / (✓ + △ + ✗)
    score_global REAL NOT NULL DEFAULT 0.0
);

CREATE INDEX IF NOT EXISTS idx_context_monitor_log_created
    ON context_monitor_log (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_context_monitor_log_olam
    ON context_monitor_log (olam);


-- ── Table reshimot_archive — Reshimot purgés (Onesh) ─────────
--
-- Quand le Gilgul purge les Reshimot d'Onesh, ils ne sont pas
-- détruits — ils sont archivés ici pour analyse post-mortem.
-- EC-SHK-053, PG-SHK-020 — Phase 3 (Sod HaKli).

CREATE TABLE IF NOT EXISTS reshimot_archive (
    id BIGSERIAL PRIMARY KEY,
    archived_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    olam TEXT NOT NULL CHECK (olam IN (
        'atziluth', 'briah', 'yetzirah', 'assiah', 'unknown'
    )),

    reshimo_hitlabshut JSONB NOT NULL DEFAULT '{}',
    reshimo_aviut JSONB NOT NULL DEFAULT '{}',

    -- Catégorie au moment de l'archivage (toujours 'onesh' pour l'instant)
    category TEXT NOT NULL DEFAULT 'onesh' CHECK (category IN (
        'onesh', 'neutral', 'expired'
    ))
);

CREATE INDEX IF NOT EXISTS idx_reshimot_archive_olam
    ON reshimot_archive (olam);
