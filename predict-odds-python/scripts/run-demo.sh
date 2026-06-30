#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
OUTPUT="${1:-$PROJECT_ROOT/demo-out}"
PYTHON="${PYTHON:-python3}"
export PYTHONPATH="$PROJECT_ROOT/src"
cd "$PROJECT_ROOT"
exec "$PYTHON" -m predict_odds demo --output "$OUTPUT"
