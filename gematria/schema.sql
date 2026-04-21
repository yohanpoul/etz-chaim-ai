-- Gematria Index — Cache des valeurs gématriques
-- "Le monde a été créé par 10 paroles, et les paroles sont faites de lettres,
--  et les lettres ont des valeurs" — Sefer Yetzirah

-- Table principale : chaque mot hébreu indexé avec ses 3 valeurs
CREATE TABLE IF NOT EXISTS gematria_index (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Le terme
    term_hebrew TEXT NOT NULL,          -- forme hébraïque (ex: תפארת)
    term_transliteration TEXT,          -- forme latine si connue (ex: tiferet)

    -- Les 9 méthodes de calcul stockées
    val_standard INTEGER NOT NULL,      -- Mispar Gadol (standard)
    val_ordinal INTEGER NOT NULL,       -- Mispar Siduri (ordinal, position 1-22)
    val_katan INTEGER NOT NULL,         -- Mispar Katan (réduction par chiffre)
    val_milui INTEGER NOT NULL DEFAULT 0,           -- Mispar Gadol Mispari (Milui de Mah)
    val_katan_mispari INTEGER NOT NULL DEFAULT 0,   -- Katan du Milui (double réduction)
    val_hakadmi INTEGER NOT NULL DEFAULT 0,         -- Mispar HaKadmi (triangulaire)
    val_perati INTEGER NOT NULL DEFAULT 0,          -- Mispar Perati (carré par lettre)
    val_meruba_haklali INTEGER NOT NULL DEFAULT 0,  -- HaMeruba HaKlali (carré du total)
    val_musafi INTEGER NOT NULL DEFAULT 0,          -- Musafi (standard + nb lettres)

    -- Provenance
    source_entry_id UUID,               -- lien vers l'entrée EpisteMemory qui a déclenché l'indexation
    source_content_snippet TEXT,         -- extrait du contenu (contexte)

    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Un terme hébreu n'apparaît qu'une fois dans l'index
    UNIQUE (term_hebrew)
);

-- Index pour la recherche d'équivalences (le coeur de la gématria opérative)
-- "Si deux mots ont la même valeur, il y a un lien secret entre eux"
CREATE INDEX IF NOT EXISTS idx_gematria_standard
    ON gematria_index (val_standard);

CREATE INDEX IF NOT EXISTS idx_gematria_ordinal
    ON gematria_index (val_ordinal);

CREATE INDEX IF NOT EXISTS idx_gematria_katan
    ON gematria_index (val_katan);

CREATE INDEX IF NOT EXISTS idx_gematria_milui
    ON gematria_index (val_milui);

CREATE INDEX IF NOT EXISTS idx_gematria_katan_mispari
    ON gematria_index (val_katan_mispari);

CREATE INDEX IF NOT EXISTS idx_gematria_hakadmi
    ON gematria_index (val_hakadmi);

CREATE INDEX IF NOT EXISTS idx_gematria_perati
    ON gematria_index (val_perati);

CREATE INDEX IF NOT EXISTS idx_gematria_meruba_haklali
    ON gematria_index (val_meruba_haklali);

CREATE INDEX IF NOT EXISTS idx_gematria_musafi
    ON gematria_index (val_musafi);

-- Index pour la recherche par translittération
CREATE INDEX IF NOT EXISTS idx_gematria_translit
    ON gematria_index (term_transliteration)
    WHERE term_transliteration IS NOT NULL;

-- Vue : groupes d'équivalences gématriques (standard)
-- Chaque groupe = des termes qui partagent la même valeur
CREATE OR REPLACE VIEW gematria_equivalences AS
SELECT
    g1.term_hebrew AS term_a,
    g1.term_transliteration AS translit_a,
    g2.term_hebrew AS term_b,
    g2.term_transliteration AS translit_b,
    g1.val_standard AS shared_value,
    'standard' AS method
FROM gematria_index g1
JOIN gematria_index g2
    ON g1.val_standard = g2.val_standard
    AND g1.id < g2.id  -- éviter les doublons et auto-références
ORDER BY g1.val_standard, g1.term_hebrew;

-- Vue : distribution des valeurs (pour diagnostiquer les clusters)
CREATE OR REPLACE VIEW gematria_value_distribution AS
SELECT
    val_standard,
    COUNT(*) AS n_terms,
    ARRAY_AGG(term_hebrew ORDER BY term_hebrew) AS terms
FROM gematria_index
GROUP BY val_standard
HAVING COUNT(*) > 1
ORDER BY COUNT(*) DESC, val_standard;
