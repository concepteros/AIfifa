# Predict Odds Bot Operations

This guide covers local and container runs for the football odds bot. Keep real API keys in `.env`; do not paste them into scripts, Docker files, or docs.

## Local Setup

From `predict-odds-python`:

```powershell
$env:PYTHON="C:\Users\erosone\AppData\Local\Python\bin\python.exe"
python -m pip install -e .
```

Required `.env` values:

```text
PREDICT_API_KEY=replace-with-your-predict-key
THE_ODDS_API_KEY=replace-with-your-odds-key
POLYMARKET_API_URL=https://gamma-api.polymarket.com
SPORTMONKS_API_KEY=replace-with-your-sportmonks-key
TELEGRAM_BOT_TOKEN=replace-with-your-telegram-token
TELEGRAM_CHAT_ID=replace-with-your-chat-id
```

`TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are only required when Telegram notifications are enabled in the config.
`POLYMARKET_API_URL` defaults to `https://gamma-api.polymarket.com` and only needs to be set when you want to override it.
`SPORTMONKS_API_KEY` is only required when running Sportmonks fixture detail commands.

## Demo Run

Generate sample data, scan, settle, calculate CLV, and write a report without external APIs:

```powershell
.\scripts\run-demo.ps1 -Output .\demo-out
```

If Windows blocks local scripts, run the same command through a bypassed process:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run-demo.ps1 -Output .\demo-out
```

## Health Check

Check local config, data paths, output paths, database path, and environment variables:

```powershell
.\scripts\run-doctor.ps1 -Config .\data\bot-scan.json -EnvFile .\.env
```

Run network probes only when you want to verify live API connectivity:

```powershell
.\scripts\run-doctor.ps1 -Config .\data\bot-scan.json -EnvFile .\.env -WithNetwork
```

## One-Off Scan

Scan upcoming matches from The Odds API, predict.fun, and Polymarket, build features, predict probabilities, create value-bet decisions, save SQLite history, and send Telegram summaries if enabled:

```powershell
.\scripts\run-scan.ps1 -Config .\data\bot-scan.json -EnvFile .\.env
```

## Telegram Control Panel

Start the interactive Telegram panel:

```powershell
.\scripts\run-telegram-panel.ps1 -Config .\data\telegram-panel.example.json -EnvFile .\.env
```

Supported commands:

```text
/dashboard
/upcoming
/scan
/approve
/history
/set_limit daily_stake 250
```

Before running it, create a Telegram bot with BotFather, put `TELEGRAM_BOT_TOKEN` in `.env`, then set your numeric Telegram chat id in `allowed_chat_ids` inside `data/telegram-panel.example.json` or a copied production config. Keep `allowed_chat_ids` non-empty for live usage.

Fetch a Sportmonks fixture detail payload for enrichment or debugging:

```powershell
$env:PYTHONPATH="src"
python -m predict_odds --env-file .\.env sportmonks-fixture --fixture-id 19102725
```

## Daily Schedule

Run the full scan pipeline every day at the configured local time:

```powershell
.\scripts\run-schedule.ps1 -Config .\data\bot-scan.json -Time 09:00 -Timezone Asia/Shanghai -EnvFile .\.env
```

Leave the terminal or service process running. Use a VPS process manager or Windows Task Scheduler if you need the scheduler to survive reboots.

## Settlement And Reports

After matches finish, import results and closing odds:

```powershell
$env:PYTHONPATH="src"
python -m predict_odds settle --database .\out\bot.sqlite --results .\data\results.csv --closing-odds .\data\closing_odds.csv
python -m predict_odds report --database .\out\bot.sqlite
```

Replay stored recommendations with different value-bet thresholds:

```powershell
python -m predict_odds backtest --database .\out\bot.sqlite --results .\data\results.csv --bankroll 1000 --min-edge 0.04 --fractional-kelly 0.25 --max-stake-fraction 0.05
```

Use the returned `max_drawdown`, `hit_rate`, and `equity_curve` fields to reject settings that look profitable only because of a small or volatile sample.

Search several risk settings at once:

```powershell
python -m predict_odds optimize --database .\out\bot.sqlite --results .\data\results.csv --bankroll 1000 --min-edges 0.02,0.03,0.05 --fractional-kellies 0.1,0.25,0.5 --max-stake-fractions 0.02,0.05 --min-bets 10
```

Before adopting optimized settings, validate them on a later date range:

```powershell
python -m predict_odds validate --database .\out\bot.sqlite --results .\data\results.csv --bankroll 1000 --min-edges 0.02,0.03,0.05 --fractional-kellies 0.1,0.25 --max-stake-fractions 0.02,0.05 --train-start-date 2026-06-01 --train-end-date 2026-06-15 --validation-start-date 2026-06-16 --validation-end-date 2026-06-30 --min-bets 10
```

For a more realistic rolling evaluation, run repeated walk-forward folds:

```powershell
python -m predict_odds walk-forward --database .\out\bot.sqlite --results .\data\results.csv --bankroll 1000 --min-edges 0.02,0.03,0.05 --fractional-kellies 0.1,0.25 --max-stake-fractions 0.02,0.05 --window 2026-06-01:2026-06-15:2026-06-16:2026-06-30 --window 2026-06-16:2026-06-30:2026-07-01:2026-07-15 --min-bets 10
```

Promote settings into a bot `decision` config only when validation risk gates pass:

```powershell
python -m predict_odds promote --report .\out\walk-forward.json --min-bets 30 --min-roi 0.03 --min-profit 25 --max-drawdown-pct 0.15 --bankroll 1000
```

Apply approved settings, then run safety checks before scheduling:

```powershell
python -m predict_odds apply-config --config .\data\bot-scan.json --promotion .\out\promotion.json
python -m predict_odds safety --report .\out\report.json --max-daily-stake 100 --max-drawdown-pct 0.15 --max-consecutive-losses 3
python -m predict_odds digest --scan .\out\scan.json --report .\out\report.json
python -m predict_odds migrate-db --database .\out\bot.sqlite
```

## Docker

Build the image:

```powershell
docker build -t predict-odds-bot .
```

Run the safe health-check command from the compose example:

```powershell
docker compose -f docker-compose.example.yml up --build
```

Override the command for a one-off scan:

```powershell
docker compose -f docker-compose.example.yml run --rm predict-odds predict-odds scan --config /app/data/bot-scan.json
```

Override the command for scheduling:

```powershell
docker compose -f docker-compose.example.yml run --rm predict-odds predict-odds schedule --config /app/data/bot-scan.json --time 09:00 --timezone Asia/Shanghai
```

## Troubleshooting

If `python` opens the Windows Store alias, set `$env:PYTHON` to the full interpreter path before running the scripts. If `doctor` reports missing API keys, check `.env` and confirm the script uses `-EnvFile .\.env`. If live requests fail, first run `doctor` without `-WithNetwork` to separate local configuration problems from external API or network problems.
