#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIG="${1:-$PROJECT_ROOT/data/bot-scan.json}"
MODE="${2:-scan}"
ENV_FILE="${3:-$PROJECT_ROOT/.env}"
WITH_NETWORK="${4:-}"
PYTHON="${PYTHON:-python3}"
export PYTHONPATH="$PROJECT_ROOT/src"
cd "$PROJECT_ROOT"

if [ "$WITH_NETWORK" = "network" ]; then
    exec "$PYTHON" -m predict_odds --env-file "$ENV_FILE" doctor --config "$CONFIG" --mode "$MODE"
else
    exec "$PYTHON" -m predict_odds --env-file "$ENV_FILE" doctor --config "$CONFIG" --mode "$MODE" --skip-network
fi
