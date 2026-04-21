#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# Etz Chaim — Grafana Setup
# ═══════════════════════════════════════════════════════════════
# Installe Grafana (si nécessaire), crée les symlinks de
# provisioning, et démarre le service.
#
# ⚠ OPTIONAL DEV TOOL — not required for `etzchaim onboard` / `etzchaim start`.
#   The standard stack (web dashboard :8080 + Postgres + daemon) ships without
#   Grafana. Run this script ONLY if you want the maintainer-oriented
#   metrics dashboards for local development on macOS.
#
# Usage : bash grafana/setup.sh
# ═══════════════════════════════════════════════════════════════

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GRAFANA_HOME="/opt/homebrew/etc/grafana"

echo "╔═══════════════════════════════════════╗"
echo "║  Etz Chaim — Grafana Setup            ║"
echo "╚═══════════════════════════════════════╝"

# ─── 1. Installer Grafana si absent ────────────────────────────

if ! brew list grafana &>/dev/null; then
    echo "→ Grafana non installé. Installation via Homebrew..."
    brew install grafana
    echo "  ✓ Grafana installé"
else
    echo "→ Grafana déjà installé"
fi

# ─── 2. Créer les répertoires de provisioning ──────────────────

echo "→ Création des répertoires..."

mkdir -p "${GRAFANA_HOME}/provisioning/datasources"
mkdir -p "${GRAFANA_HOME}/provisioning/dashboards"
mkdir -p "${GRAFANA_HOME}/provisioning/plugins"
mkdir -p "${GRAFANA_HOME}/provisioning/alerting"
mkdir -p "${GRAFANA_HOME}/provisioning/access-control"
mkdir -p "${GRAFANA_HOME}/dashboards/etz-chaim"

echo "  ✓ Répertoires créés"

# ─── 2b. Configurer grafana.ini pour pointer vers notre provisioning ─

GRAFANA_INI="${GRAFANA_HOME}/grafana.ini"
if grep -q "^;provisioning = conf/provisioning" "$GRAFANA_INI" 2>/dev/null; then
    sed -i '' 's|^;provisioning = conf/provisioning|provisioning = /opt/homebrew/etc/grafana/provisioning|' "$GRAFANA_INI"
    echo "  ✓ grafana.ini : provisioning path configuré"
elif grep -q "^provisioning = /opt/homebrew/etc/grafana/provisioning" "$GRAFANA_INI" 2>/dev/null; then
    echo "  ✓ grafana.ini : provisioning path déjà configuré"
else
    echo "  ⚠ grafana.ini : vérifier manuellement le provisioning path"
fi

# ─── 3. Symlinks — datasources ─────────────────────────────────

DS_SRC="${SCRIPT_DIR}/provisioning/datasources/etz-chaim.yaml"
DS_DST="${GRAFANA_HOME}/provisioning/datasources/etz-chaim.yaml"

if [ -L "$DS_DST" ] || [ -f "$DS_DST" ]; then
    rm "$DS_DST"
fi
ln -s "$DS_SRC" "$DS_DST"
echo "  ✓ Datasource : $(basename "$DS_SRC") → $DS_DST"

# ─── 4. Symlinks — dashboard provider ──────────────────────────

DP_SRC="${SCRIPT_DIR}/provisioning/dashboards/etz-chaim.yaml"
DP_DST="${GRAFANA_HOME}/provisioning/dashboards/etz-chaim.yaml"

if [ -L "$DP_DST" ] || [ -f "$DP_DST" ]; then
    rm "$DP_DST"
fi
ln -s "$DP_SRC" "$DP_DST"
echo "  ✓ Dashboard provider : $(basename "$DP_SRC") → $DP_DST"

# ─── 5. Symlinks — dashboard JSON ──────────────────────────────

DB_SRC="${SCRIPT_DIR}/dashboards/etz-chaim.json"
DB_DST="${GRAFANA_HOME}/dashboards/etz-chaim/etz-chaim.json"

if [ -L "$DB_DST" ] || [ -f "$DB_DST" ]; then
    rm "$DB_DST"
fi
ln -s "$DB_SRC" "$DB_DST"
echo "  ✓ Dashboard JSON : $(basename "$DB_SRC") → $DB_DST"

# ─── 6. Démarrer Grafana ───────────────────────────────────────

echo "→ Démarrage de Grafana..."

if brew services list | grep -q "grafana.*started"; then
    brew services restart grafana
    echo "  ✓ Grafana redémarré"
else
    brew services start grafana
    echo "  ✓ Grafana démarré"
fi

echo ""
echo "═══════════════════════════════════════════"
echo "  Grafana accessible sur http://localhost:3000"
echo "  Login par défaut : admin / admin"
echo "  Dashboard : Etz Chaim → Etz Chaim — Arbre de Vie"
echo "═══════════════════════════════════════════"
