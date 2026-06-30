#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIG="${1:-$PROJECT_ROOT/data/telegram-panel.example.json}"
ENV_FILE="${2:-$PROJECT_ROOT/.env}"

if [ -x "$PROJECT_ROOT/.venv/bin/python" ]; then
    PYTHON="$PROJECT_ROOT/.venv/bin/python"
else
    PYTHON="${PYTHON:-python3}"
fi

export PYTHONPATH="$PROJECT_ROOT/src"
cd "$PROJECT_ROOT"
exec "$PYTHON" -m predict_odds --env-file "$ENV_FILE" telegram-panel --config "$CONFIG"
