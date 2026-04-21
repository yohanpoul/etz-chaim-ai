-- partzufim/zivvug_schema.sql — schéma canonique du ZivvugEngine (Sprint 10 Phase E).
--
-- Extrait de partzufim/zivvug.py (ZIVVUG_SCHEMA inline) pour unifier les 3
-- systèmes Zivvug fragmentés :
--   1. ZivvugEngine (code) — partzufim/zivvug.py
--   2. Table DB zivvug_state (persistance)
--   3. Consommateurs — ohr_yashar.py (via factory load_or_create)
--
-- Ce fichier est la source unique du schéma. Le ZIVVUG_SCHEMA dans zivvug.py
-- reste en fallback pour l'init programmatique (pool.get_conn non disponible).
--
-- Doctrine Hitlabshut (EC-K5-008) : le boost accumulé (abba_boost, imma_boost)
-- est persisté ici MAIS appliqué aux facultés (Kelim) et non directement à
-- overall_score (cf. partzufim/base.py::overall, résultante calculée).
--
-- Doctrine Reshimu (Phase D Option B) : les boosts laissent aussi une trace
-- résiduelle dans faculty_reshimot (cf partzufim/reshimu.py). Les deux tables
-- coexistent : zivvug_state porte les boosts in-flight, faculty_reshimot
-- porte l'accumulé cross-cycle.

CREATE TABLE IF NOT EXISTS zivvug_state (
    id                  INTEGER    PRIMARY KEY DEFAULT 1,
    state               TEXT       NOT NULL DEFAULT 'blocked',
    abba_score          REAL       NOT NULL DEFAULT 0.0,
    imma_score          REAL       NOT NULL DEFAULT 0.0,
    delta               REAL       NOT NULL DEFAULT 0.0,
    mochin_quality      REAL       NOT NULL DEFAULT 0.0,
    limiting_partzuf    TEXT,
    coupling_factor     REAL       NOT NULL DEFAULT 0.0,
    abba_boost          REAL       NOT NULL DEFAULT 0.0,
    imma_boost          REAL       NOT NULL DEFAULT 0.0,
    reinforcement_count INTEGER    NOT NULL DEFAULT 0,
    updated_at          TIMESTAMP  DEFAULT NOW(),
    CHECK (id = 1)  -- singleton row
);

-- Index : aucune nécessité (singleton row), mais trace d'updated_at accessible.
