-- Required PostgreSQL extensions for Etz Chaim AI.
-- Runs before any module schema (prefix 01+).
CREATE EXTENSION IF NOT EXISTS vector;
-- timescaledb is optional (some dev hosts don't have it); guard with DO block.
DO $$
BEGIN
    CREATE EXTENSION IF NOT EXISTS timescaledb;
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'timescaledb not available, skipping (optional extension)';
END$$;
