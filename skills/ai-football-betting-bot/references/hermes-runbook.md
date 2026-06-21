# Hermes Runbook

## Project Layout

The bot lives in `predict-odds-python/`.

Important files:

- `.env`: local secrets, ignored by git
- `data/bot-scan.local.json`: local scan config, ignored by git
- `data/telegram-panel.local.json`: local Telegram panel config, ignored by git
- `data/telegram-panel.example.json`: shareable example config
- `src/predict_odds/telegram_panel.py`: Telegram control panel
- `src/predict_odds/market_sources.py`: The Odds API + predict.fun + Polymarket aggregation
- `src/predict_odds/bot_scanner.py`: scan pipeline
- `OPERATIONS.md`: human runbook

## Required Secrets

Expected `.env` keys:

```text
PREDICT_API_KEY=...
PREDICT_API_URL=https://api.predict.fun/v1/markets
THE_ODDS_API_KEY=...
POLYMARKET_API_URL=https://gamma-api.polymarket.com
SPORTMONKS_API_KEY=...
SPORTMONKS_API_URL=https://api.sportmonks.com
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

Never reveal these values. It is okay to say whether a key is `set` or `missing`.

## Local Setup

Preferred Windows commands:

```powershell
cd predict-odds-python
C:\Users\erosone\AppData\Local\Python\bin\python.exe -m venv .venv-panel
.\.venv-panel\Scripts\python.exe -m pip install -e .
```

If the user already has `.venv-panel`, use:

```powershell
.\.venv-panel\Scripts\python.exe -m predict_odds --help
```

Fallback without venv:

```powershell
$env:PYTHONPATH="src"
C:\Users\erosone\AppData\Local\Python\bin\python.exe -m predict_odds --help
```

## Running The Bot

Offline demo:

```powershell
$env:PYTHONPATH="src"
C:\Users\erosone\AppData\Local\Python\bin\python.exe -m predict_odds demo --output .\tmp-demo --compact
```

Live scan:

```powershell
$env:PYTHONPATH="src"
C:\Users\erosone\AppData\Local\Python\bin\python.exe -m predict_odds --env-file .\.env scan --config .\data\bot-scan.local.json --compact
```

Telegram panel:

```powershell
.\scripts\run-telegram-panel.ps1 -Config .\data\telegram-panel.local.json -EnvFile .\.env
```

## Telegram Panel Behavior

Commands:

- `/dashboard`: status, latest run, ROI, limits
- `/upcoming`: upcoming market events from odds aggregation
- `/scan`: live scan through feature engineering, prediction, decision
- `/approve`: recent bet signals with approve/reject inline buttons
- `/history`: recent runs from SQLite
- `/set_limit daily_stake 250`: update panel config
- `/set_limit max_single_stake 50`: update panel config

If Telegram sendMessage returns `Bad Request: chat not found`, the user must open the bot and send `/start`.

## Data Requirements

`/upcoming` needs only odds APIs.

`/scan` needs:

```text
data/fbref.csv
data/transfermarkt.csv
```

FBref columns:

```text
date,league,team,opponent,venue,goals_for,goals_against,xg,xga,result
```

Transfermarkt columns:

```text
team,player,position,market_value_eur,status,days_out
```

## Verification

Run before claiming completion:

```powershell
$env:PYTHONPATH="src"
C:\Users\erosone\AppData\Local\Python\bin\python.exe -m unittest discover -s tests
```

Expected current baseline:

```text
Ran 120 tests
OK
```

## Git And Push

Do not stage ignored local secrets or dependency folders. Check:

```powershell
git check-ignore -v predict-odds-python\.env predict-odds-python\data\telegram-panel.local.json predict-odds-python\data\bot-scan.local.json predict-odds-python\.venv-panel
rg "real-secret-fragment" predict-odds-python -g "!*.env" -g "!*.local.json" -g "!.venv-panel/**"
```

Push target requested by the user:

```powershell
git remote add aififa https://github.com/concepteros/AIfifa.git
git push aififa HEAD:main
```

If `main` is protected or divergent, push a branch:

```powershell
git push aififa HEAD:codex/ai-football-betting-bot
```
