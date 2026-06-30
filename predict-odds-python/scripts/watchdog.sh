#!/usr/bin/env bash
# Football bot panel watchdog — auto-restart if dead
set -euo pipefail

PROJECT=/Users/macbook/AIfifa/predict-odds-python
PIDFILE=/tmp/football-panel.pid
LOGFILE=/tmp/football-panel.log

# Check if already running
if [ -f "$PIDFILE" ]; then
    pid=$(cat "$PIDFILE")
    if kill -0 "$pid" 2>/dev/null; then
        exit 0  # alive
    fi
fi

# Start
cd "$PROJECT"
source .venv/bin/activate
export PYTHONPATH=src
nohup python -m predict_odds --env-file .env telegram-panel \
    --config data/telegram-panel.local.json \
    >> "$LOGFILE" 2>&1 &

echo $! > "$PIDFILE"
echo "Panel started PID=$!"
