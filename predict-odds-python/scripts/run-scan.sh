#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIG="${1:-$PROJECT_ROOT/data/bot-scan.json}"
ENV_FILE="${2:-$PROJECT_ROOT/.env}"
PYTHON="${PYTHON:-python3}"
export PYTHONPATH="$PROJECT_ROOT/src"
cd "$PROJECT_ROOT"
exec "$PYTHON" -m predict_odds --env-file "$ENV_FILE" scan --config "$CONFIG"
