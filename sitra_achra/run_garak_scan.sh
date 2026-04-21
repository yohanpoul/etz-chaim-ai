#!/bin/bash
# Scan hebdomadaire Garak — modele nu via Ollama
#
# Shevirah : chaos testing avec 150+ probes sur le modele brut.
# Le Sitra Achra teste le modele SANS le pipeline, pour trouver
# les faiblesses que le pipeline masque.
#
# Usage : bash sitra_achra/run_garak_scan.sh
# Prereqs : Ollama running, qwen3.5:9b loaded
#
# Probes selectionnees :
#   dan            — Do Anything Now jailbreaks
#   encoding       — Attaques par encodage (base64, ROT13, etc.)
#   knownbadsignatures — Patterns dangereux connus
#   lmrc           — Language Model Risk Cards (comprehensive)
#   continuation   — Continuation d'instructions malveillantes

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
GARAK_VENV="$PROJECT_DIR/.garak-venv"
CONFIG="$SCRIPT_DIR/garak_config.json"
RESULTS_DIR="$PROJECT_DIR/.etz-chaim/garak_results"

mkdir -p "$RESULTS_DIR"

echo "=== Garak Scan — $(date) ==="
echo "Modele : ollama/qwen3.5:9b"
echo "Config : $CONFIG"
echo "Resultats : $RESULTS_DIR"
echo ""

# Verifier qu'Ollama tourne
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "ERREUR : Ollama n'est pas en cours d'execution"
    echo "Lancer : ollama serve"
    exit 1
fi

# Verifier que le modele est disponible
if ! curl -s http://localhost:11434/api/tags | grep -q "qwen3.5:9b"; then
    echo "AVERTISSEMENT : qwen3.5:9b non trouve dans Ollama"
    echo "Lancer : ollama pull qwen3.5:9b"
fi

# Lancer le scan
"$GARAK_VENV/bin/python" -m garak \
    --target_type ollama \
    --target_name "qwen3.5:9b" \
    --probes dan,encoding,lmrc,promptinject \
    --report_prefix "$RESULTS_DIR/scan_$(date +%Y%m%d)" \
    2>&1 | tee "$RESULTS_DIR/scan_$(date +%Y%m%d).log"

echo ""
echo "=== Scan termine — $(date) ==="
echo "Resultats dans : $RESULTS_DIR"
