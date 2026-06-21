---
name: ai-football-betting-bot
description: Operate, configure, run, and troubleshoot the Python AI football betting bot in Hermes/Codex. Use when the user asks to run scans, manage odds sources, configure API keys, start the Telegram control panel, use /dashboard /upcoming /scan /approve /history /set_limit, inspect bot results, or deploy/push the predict-odds-python project.
---

# AI Football Betting Bot

Use this skill for the `predict-odds-python` project, a Python football betting signal bot with:

- odds sources: The Odds API, predict.fun, Polymarket, plus Sportmonks fixture enrichment
- feature engineering from FBref and Transfermarkt CSV data
- Poisson prediction, value betting, Kelly staking, settlement, reports, backtests, and safety gates
- Telegram control panel via `python-telegram-bot`

## First Steps

1. Locate the project root. In this repository it is usually:
   `predict-odds-python/`
2. Load local secrets from `.env`; never print real API keys or Telegram tokens.
3. Prefer the project venv if it exists:
   `.venv-panel/Scripts/python.exe` on Windows.
4. Use `PYTHONPATH=src` when running without an installed package.
5. Read `references/hermes-runbook.md` when you need exact commands, config fields, or troubleshooting steps.

## Common Commands

From `predict-odds-python` on Windows PowerShell:

```powershell
$env:PYTHONPATH="src"
C:\Users\erosone\AppData\Local\Python\bin\python.exe -m predict_odds --env-file .\.env scan --config .\data\bot-scan.local.json --compact
```

Start the Telegram control panel:

```powershell
.\scripts\run-telegram-panel.ps1 -Config .\data\telegram-panel.local.json -EnvFile .\.env
```

Run verification before claiming success:

```powershell
$env:PYTHONPATH="src"
C:\Users\erosone\AppData\Local\Python\bin\python.exe -m unittest discover -s tests
```

## Safety Rules

- Do not commit `.env`, `*.local.json`, `.venv-panel/`, `.python-packages/`, or `.telegram-packages/`.
- Do not expose API keys or Telegram bot tokens in logs, final answers, commits, or docs.
- Treat all recommendations as signals for manual review unless the user explicitly builds an execution layer.
- If Telegram returns `chat not found`, tell the user to open the bot in Telegram and send `/start`.
- If `/scan` fails because FBref or Transfermarkt data is missing, ask for or create `data/fbref.csv` and `data/transfermarkt.csv`.

## Telegram Commands

The panel supports:

- `/dashboard`
- `/upcoming`
- `/scan`
- `/approve`
- `/history`
- `/set_limit daily_stake 250`
- `/set_limit max_single_stake 50`

Use `InlineKeyboardButton` callbacks for dashboard actions and signal approval/rejection.
