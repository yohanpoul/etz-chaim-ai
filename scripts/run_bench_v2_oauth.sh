#!/usr/bin/env bash
# Enchaîne tous les arms × benches du plan v2 OAuth.
# Resume automatique via --run-id stable.
# Stop & resume safe : Ctrl+C → state persisté, relance reprend où on était.
#
# Usage :
#   ./scripts/run_bench_v2_oauth.sh           # full sweep
#   ./scripts/run_bench_v2_oauth.sh raw_cli   # only one arm
#   BENCH=truthfulqa ./scripts/run_bench_v2_oauth.sh   # only one bench
#
# Total estimé : ~5h30 wall-clock pour les 3 arms × 4 benches × 100 prompts.
set -e

cd "$(dirname "$0")/.."
source .venv/bin/activate

RUN_ID="${RUN_ID:-bench_v2_oauth}"
LIMIT="${LIMIT:-100}"
BUDGET="${BUDGET:-30}"
ARMS="${1:-raw_cli cot_cli etz_yosher}"
BENCHES="${BENCH:-truthfulqa harmbench xstest reasoning_hard}"

echo "==========================================================="
echo "  Bench v2 OAuth — RUN_ID=$RUN_ID  LIMIT=$LIMIT  BUDGET=\$$BUDGET/arm"
echo "  ARMS    = $ARMS"
echo "  BENCHES = $BENCHES"
echo "==========================================================="
echo ""

for arm in $ARMS; do
    for bench in $BENCHES; do
        echo ""
        echo "----- $arm × $bench -----"
        python3 -m benchmarks.cli run "$bench" "$arm" \
            --limit "$LIMIT" --budget "$BUDGET" \
            --run-id "$RUN_ID" --no-kill-daemon
        sleep 2  # let Claude CLI breathe between bench transitions
    done
done

echo ""
echo "==========================================================="
echo "  Done. Run analysis with:"
echo "    python -m benchmarks.analyze benchmarks/results/runs/$RUN_ID"
echo "==========================================================="
