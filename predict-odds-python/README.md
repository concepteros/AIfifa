# Predict Odds Python

Python module for fetching football odds from the Predict markets API.

It supports:

- league and date filters
- API key lookup from environment variables
- structured JSON output for win/draw/win, handicap, and totals markets
- FBref/Transfermarkt data integration for form, xG, and injury features
- request, authentication, response, and validation errors
- dependency-free standard library HTTP client

## Setup

```powershell
cd predict-odds-python
$env:PREDICT_API_KEY="your-api-key"
```

The default endpoint is:

```text
https://api.predict.fun/v1/markets
```

Override it with:

```powershell
$env:PREDICT_API_URL="https://api.predict.fun/v1/markets"
```

You can also keep local credentials in `.env`; this file is ignored by git:

```text
PREDICT_API_KEY=your-predict-api-key
THE_ODDS_API_KEY=your-odds-api-key
POLYMARKET_API_URL=https://gamma-api.polymarket.com
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_CHAT_ID=your-chat-id
```

## CLI

```powershell
python -m pip install -e .
predict-odds odds --league "Premier League" --date 2026-06-20
```

Without installing:

```powershell
$env:PYTHONPATH="src"
python -m predict_odds odds --league "Premier League" --date 2026-06-20
```

The old form still works:

```powershell
python -m predict_odds --league "Premier League" --date 2026-06-20
```

## Offline Demo

Run the full bot locally without external APIs:

```powershell
$env:PYTHONPATH="src"
python -m predict_odds demo --output .\demo-out
```

The demo writes sample FBref, Transfermarkt, The Odds API event, result, and closing odds files, then runs scan, settlement, CLV tracking, and reporting.

## Python API

```python
from predict_odds import PredictOddsClient

client = PredictOddsClient.from_env()
payload = client.get_football_odds(league="Premier League", date="2026-06-20")
print(payload.to_json())
```

## Feature Engineering

Use FBref-style match exports and Transfermarkt-style injury exports:

```powershell
$env:PYTHONPATH="src"
python -m predict_odds features `
  --league "Premier League" `
  --date 2026-06-20 `
  --home-team "Arsenal" `
  --away-team "Chelsea" `
  --fbref .\data\fbref.csv `
  --transfermarkt .\data\transfermarkt.csv
```

Expected match CSV columns:

```text
date,league,team,opponent,venue,goals_for,goals_against,xg,xga,result
```

Expected injury CSV columns:

```text
team,player,position,market_value_eur,status,days_out
```

Feature output includes recent form, goal difference, xG/xGA averages, xG deltas, injured player counts, injured market value, and injury impact deltas.

## Prediction Model

Run a Poisson score model on top of the engineered features:

```powershell
$env:PYTHONPATH="src"
python -m predict_odds predict `
  --league "Premier League" `
  --date 2026-06-20 `
  --home-team "Arsenal" `
  --away-team "Chelsea" `
  --fbref .\data\fbref.csv `
  --transfermarkt .\data\transfermarkt.csv
```

The prediction output includes expected goals, win/draw/loss probabilities, over/under 2.5, both-teams-to-score, most likely scores, and rule-based reasoning.

## Decision Engine

Find value bets and stake sizes from a prediction JSON file and decimal odds:

```powershell
$env:PYTHONPATH="src"
python -m predict_odds decide `
  --prediction .\data\prediction.json `
  --odds .\data\odds.json `
  --bankroll 1000 `
  --min-edge 0.03 `
  --fractional-kelly 0.25 `
  --max-stake-fraction 0.05
```

Odds JSON should be keyed by prediction market:

```json
{
  "home_win": 2.1,
  "draw": 3.4,
  "away_win": 3.2,
  "over_2_5": 1.9,
  "under_2_5": 1.95
}
```

The engine calculates implied probability, model edge, expected value, Kelly fraction, capped stake fraction, and stake amount.

## Scheduled Workflow

Run the full feature, prediction, decision, file-output, and optional Telegram notification workflow once:

```powershell
$env:PYTHONPATH="src"
python -m predict_odds run --config .\data\workflow.json
```

Schedule it daily with APScheduler:

```powershell
$env:PYTHONPATH="src"
python -m predict_odds schedule --config .\data\workflow.json --time 09:00 --timezone Asia/Shanghai
```

Workflow config example:

```json
{
  "fixture": {
    "league": "Premier League",
    "date": "2026-06-20",
    "home_team": "Arsenal",
    "away_team": "Chelsea"
  },
  "data": {
    "fbref": "./data/fbref.csv",
    "transfermarkt": "./data/transfermarkt.csv",
    "odds": "./data/odds.json"
  },
  "decision": {
    "bankroll": 1000,
    "min_edge": 0.03,
    "fractional_kelly": 0.25,
    "max_stake_fraction": 0.05
  },
  "output": {"directory": "./out"},
  "telegram": {"enabled": true}
}
```

Telegram notifications read credentials from environment variables:

```powershell
$env:TELEGRAM_BOT_TOKEN="your-bot-token"
$env:TELEGRAM_CHAT_ID="your-chat-id"
```

## Telegram Control Panel

Run an interactive Telegram control panel with `/dashboard`, `/upcoming`, `/scan`, `/approve`, `/history`, and `/set_limit` commands:

```powershell
$env:PYTHONPATH="src"
python -m predict_odds --env-file .\.env telegram-panel --config .\data\telegram-panel.example.json
```

The panel uses `python-telegram-bot` and reads the bot token from `TELEGRAM_BOT_TOKEN` by default. Set `allowed_chat_ids` to your Telegram chat id to restrict access:

```json
{
  "telegram_panel": {
    "bot_token_env": "TELEGRAM_BOT_TOKEN",
    "allowed_chat_ids": ["123456789"],
    "scan_config": "./bot-scan.json",
    "database": "../out/bot.sqlite",
    "approvals": "../out/telegram-approvals.json",
    "limits": {
      "daily_stake": 100,
      "max_single_stake": 25
    }
  }
}
```

Limit changes can be made from Telegram:

```text
/set_limit daily_stake 250
/set_limit max_single_stake 50
```

## Bot Scanner

Scan upcoming matches through The Odds API, predict.fun, and Polymarket, normalize all markets into one odds board, run predictions and decisions, save SQLite history, and optionally send Telegram summaries:

```powershell
$env:THE_ODDS_API_KEY="your-odds-api-key"
$env:PREDICT_API_KEY="your-predict-api-key"
$env:POLYMARKET_API_URL="https://gamma-api.polymarket.com"
$env:SPORTMONKS_API_KEY="your-sportmonks-api-key"
$env:PYTHONPATH="src"
python -m predict_odds scan --config .\data\bot-scan.json
```

The scanner uses these odds sources by default:

```json
["the_odds_api", "predict_fun", "polymarket"]
```

If one source fails, the scanner continues with the remaining sources. If multiple sources quote the same match and market, the bot keeps the best decimal price and records the contributing `sources` in the match output.

Fetch a rich Sportmonks fixture detail payload with participants, scores, venue, state, events, statistics, lineups, and league:

```powershell
$env:SPORTMONKS_API_KEY="your-sportmonks-api-key"
$env:PYTHONPATH="src"
python -m predict_odds sportmonks-fixture --fixture-id 19102725
```

The default Sportmonks includes are:

```text
participants;scores;venue;state;events;statistics;lineups;league
```

Scanner config example:

```json
{
  "odds_sources": ["the_odds_api", "predict_fun", "polymarket"],
  "scan": {
    "sport": "soccer_epl",
    "regions": "eu",
    "markets": ["h2h", "totals", "spreads"],
    "league": "Premier League",
    "date": "2026-06-20"
  },
  "polymarket": {
    "query": "Premier League Arsenal Chelsea",
    "limit": 100,
    "active": true,
    "closed": false
  },
  "data": {
    "fbref": "./data/fbref.csv",
    "transfermarkt": "./data/transfermarkt.csv"
  },
  "decision": {
    "bankroll": 1000,
    "min_edge": 0.03,
    "fractional_kelly": 0.25,
    "max_stake_fraction": 0.05
  },
  "output": {"directory": "./out"},
  "database": {"path": "./out/bot.sqlite"},
  "telegram": {"enabled": true}
}
```

## Production Checks

Run a local health check before scheduling the bot:

```powershell
$env:PYTHONPATH="src"
python -m predict_odds --env-file .\.env doctor --config .\data\bot-scan.json --mode scan --skip-network
```

The doctor checks config structure, required files, output/database paths, environment variables, and optional network probes. Workflow and scanner runs send a Telegram error summary when `telegram.enabled` is true and a run fails.

For repeatable local scripts, Docker commands, and operations guidance, see [OPERATIONS.md](OPERATIONS.md).

## Settlement and Reporting

Import final scores and settle stored `home_win`, `draw`, `away_win`, totals, and spread recommendations:

```powershell
$env:PYTHONPATH="src"
python -m predict_odds settle --database .\out\bot.sqlite --results .\data\results.csv
python -m predict_odds report --database .\out\bot.sqlite
```

Track closing line value by adding closing odds:

```powershell
python -m predict_odds settle --database .\out\bot.sqlite --results .\data\results.csv --closing-odds .\data\closing_odds.csv
```

Results CSV format:

```text
date,league,home_team,away_team,home_goals,away_goals
```

Closing odds CSV format:

```text
date,league,home_team,away_team,market,closing_odds
```

The report includes total bets, wins/losses/pushes, stake, profit, ROI, average CLV, positive CLV rate, market-level breakdowns, and family breakdowns for `1x2`, `totals`, and `spreads`.

## Backtesting

Replay stored recommendations against historical results with different value and Kelly settings:

```powershell
$env:PYTHONPATH="src"
python -m predict_odds backtest --database .\out\bot.sqlite --results .\data\results.csv --bankroll 1000 --min-edge 0.04 --fractional-kelly 0.25 --max-stake-fraction 0.05
```

Backtest output includes profit, ROI, hit rate, starting and ending bankroll, maximum drawdown, and an equity curve for each replayed bet.

Filter by league and date range:

```powershell
python -m predict_odds backtest --database .\out\bot.sqlite --results .\data\results.csv --bankroll 1000 --league "Premier League" --start-date 2026-06-01 --end-date 2026-06-30
```

Grid-search risk parameters and sort runs by ROI, profit, and bet count:

```powershell
python -m predict_odds optimize --database .\out\bot.sqlite --results .\data\results.csv --bankroll 1000 --min-edges 0.02,0.03,0.05 --fractional-kellies 0.1,0.25,0.5 --max-stake-fractions 0.02,0.05 --min-bets 10
```

Optimize on one historical window and validate on a later window:

```powershell
python -m predict_odds validate --database .\out\bot.sqlite --results .\data\results.csv --bankroll 1000 --min-edges 0.02,0.03,0.05 --fractional-kellies 0.1,0.25 --max-stake-fractions 0.02,0.05 --train-start-date 2026-06-01 --train-end-date 2026-06-15 --validation-start-date 2026-06-16 --validation-end-date 2026-06-30 --min-bets 10
```

Run repeated walk-forward folds:

```powershell
python -m predict_odds walk-forward --database .\out\bot.sqlite --results .\data\results.csv --bankroll 1000 --min-edges 0.02,0.03,0.05 --fractional-kellies 0.1,0.25 --max-stake-fractions 0.02,0.05 --window 2026-06-01:2026-06-15:2026-06-16:2026-06-30 --window 2026-06-16:2026-06-30:2026-07-01:2026-07-15 --min-bets 10
```

Promote validated settings only when risk gates pass:

```powershell
python -m predict_odds promote --report .\out\walk-forward.json --min-bets 30 --min-roi 0.03 --min-profit 25 --max-drawdown-pct 0.15 --bankroll 1000
```

Apply promoted settings to the scanner config with a backup:

```powershell
python -m predict_odds apply-config --config .\data\bot-scan.json --promotion .\out\promotion.json
```

Evaluate model probabilities, safety gates, and operator digests:

```powershell
python -m predict_odds evaluate-probs --input .\out\predictions.json
python -m predict_odds safety --report .\out\report.json --max-daily-stake 100 --max-drawdown-pct 0.15 --max-consecutive-losses 3
python -m predict_odds digest --scan .\out\scan.json --report .\out\report.json
```

Generate an LLM-ready match analysis prompt and apply database migrations:

```powershell
python -m predict_odds llm-prompt --input .\out\2026-06-20-arsenal-vs-chelsea.json
python -m predict_odds migrate-db --database .\out\bot.sqlite
```

## Output Shape

```json
{
  "league": "Premier League",
  "date": "2026-06-20",
  "source": "https://api.predict.fun/v1/markets",
  "fetched_at": "2026-06-20T10:00:00Z",
  "raw_count": 3,
  "markets": {
    "win_draw_win": [],
    "handicap": [],
    "totals": [],
    "other": []
  }
}
```

## Tests

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests
```
