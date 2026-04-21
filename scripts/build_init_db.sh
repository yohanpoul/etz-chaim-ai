#!/usr/bin/env bash
# scripts/build_init_db.sh — copy module schema.sql files into etzchaim/deploy/init-db/
# with numeric prefix. PostgreSQL docker-entrypoint-initdb.d runs them in alphanumeric order.
#
# Source of truth for ordering : init_db.py SCHEMA_ORDER (FK dependency aware).
# Run this whenever a new module schema is added.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/etzchaim/deploy/init-db"

# Rebuild clean
mkdir -p "$OUT"
rm -f "$OUT"/*.sql

# pgvector extension must exist before any CREATE TABLE with vector column
cat > "$OUT/00-extensions.sql" <<'EOF'
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
EOF

# Order from init_db.py SCHEMA_ORDER — FK dependencies respected
ORDER=(
  "epistememory"
  "selfmap"
  "intentkeeper"
  "failuretoinsight"
  "dissensuengine"
  "autojudge"
  "explorationengine"
  "selfmodel"
  "causalengine"
  "insightforge"
  "omer"
  "partzufim"
  "tanya"
  "sifrei_yesod"
  "kabbalah"
  "masakh"
  "gematria"
  "chat"
  "malakhim"
)

i=1
missing=()
for mod in "${ORDER[@]}"; do
  src="$ROOT/$mod/schema.sql"
  if [ ! -f "$src" ]; then
    missing+=("$mod")
    continue
  fi
  dst=$(printf "%s/%02d-%s.sql" "$OUT" "$i" "$mod")
  cp "$src" "$dst"
  i=$((i+1))
done

# Partzufim has a second schema (zivvug)
if [ -f "$ROOT/partzufim/zivvug_schema.sql" ]; then
  dst=$(printf "%s/%02d-partzufim-zivvug.sql" "$OUT" "$i")
  cp "$ROOT/partzufim/zivvug_schema.sql" "$dst"
  i=$((i+1))
fi

# Kabbalah has a second schema (hybrid embeddings)
if [ -f "$ROOT/kabbalah/schema_hybrid.sql" ]; then
  dst=$(printf "%s/%02d-kabbalah-hybrid.sql" "$OUT" "$i")
  cp "$ROOT/kabbalah/schema_hybrid.sql" "$dst"
  i=$((i+1))
fi

echo "Built $((i-1)) schemas into $OUT"
ls -1 "$OUT"

if [ ${#missing[@]} -gt 0 ]; then
  echo ""
  echo "WARNING : these modules had no schema.sql, skipped :"
  printf '  - %s\n' "${missing[@]}"
fi
