# ⚽ AIfifa — AI Football Prediction Bot

> Poisson xG + tactical analysis + Kelly betting + Predict.fun on-chain execution

Production-grade AI football prediction system. Live World Cup 2026 trading. Runs standalone or as a [Hermes Agent](https://github.com/nousresearch/hermes-agent) skill.

---

## 🚀 Quick Start

```bash
git clone https://github.com/concepteros/AIfifa.git
cd AIfifa/predict-odds-python
python3 -m venv .venv && .venv/bin/pip install -e .
cp .env.example .env   # edit → add THE_ODDS_API_KEY
.venv/bin/python -m predict_odds scan --config data/bot-scan.json --summary
```

---

## 🧠 Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌──────────────┐
│  ESPN API   │───▶│ Poisson v2  │───▶│  Tactical   │───▶│   Referee    │
│  (fixtures) │    │  (xG model) │    │  Analysis   │    │  Assessment  │
└─────────────┘    └─────────────┘    └─────────────┘    └──────────────┘
                                                                  │
┌──────────────┐    ┌──────────────┐                              │
│ Predict.fun  │◀───│    Kelly     │◀─────── The Odds API ◀────────┘
│  (execute)   │    │  (position)  │        (market odds)
└──────────────┘    └──────────────┘
```

---

## 📦 Core Modules

### `prediction.py` — Poisson v2 Model

The heart of the system. Takes engineered features and outputs:

```python
{
  "expected_goals": {"home": 3.07, "away": 1.46},
  "probabilities": {
    "home_win": 0.69, "draw": 0.16, "away_win": 0.16,
    "over_2_5": 0.82, "under_2_5": 0.18
  },
  "most_likely_scores": [("3-0", 0.079), ("3-1", 0.077), ("2-0", 0.061)]
}
```

- Pure data-driven: `market_weight=0`, no odds calibration
- λ search grid: 0.02–5.00, ±20% cap
- Integrated referee modifier: adjusts λ by strictness, card tendency, VAR usage, home bias

### `feature_pipeline.py` — Feature Engineering

Builds 25+ features per match from raw data:

| Category | Features |
|----------|----------|
| Recent form | Goals for/against (3/5/10 game windows), results string |
| xG metrics | xG/xGA averages, xG delta, xG trend |
| Head-to-head | Historical matchups between the two teams |
| Injuries | Injured player count, total market value lost |
| Referee | 7-dimension profile (strictness, cards, VAR, bias...) |

Auto-assigns referees via deterministic hash (neutral continent principle, 15 referees, same pairing always gets same ref).

### `tactics.py` — Tactical Analysis (59 Teams)

Profiles 59 national teams with detailed tactical attributes:

```
France:
  Style: possession
  Formation: 4-3-3
  Strengths: pace on counter, midfield creativity, defensive depth
  Weaknesses: occasional complacency, Mbappe-dependence
  Key Player: Kylian Mbappe
  Coach: Didier Deschamps — pragmatic winner, blends possession + counters
  FIFA Rank: #2
```

The matchup analyzer computes a `tactical_advantage` score by comparing playing styles, formation compatibility, and strength/weakness overlaps between any two teams.

### `supplementary.py` — Match Context Data

Three data layers for contextualizing predictions:

| Layer | Source | Details |
|-------|--------|---------|
| **Referee** | 15 FIFA referees | Strictness, card tendency, VAR usage, home bias — adjusts λ multipliers |
| **Weather** | Venue-based | Temperature, humidity, wind — can suppress high-scoring predictions |
| **Injuries** | Transfermarkt-style CSV | ⚠️ Currently synthetic — marked clearly in output |

### `bot_scanner.py` — Scan + Kelly Pipeline

The main orchestrator. Single command end-to-end:

```bash
.venv/bin/python -m predict_odds scan --config data/bot-scan.json --summary
```

Pipeline:
1. Fetch fixtures from The Odds API
2. For each match: load data → build features → run Poisson → run tactics → run referee
3. Compare model probabilities vs market implied probabilities
4. Apply Kelly Criterion for position sizing
5. Output human-readable recommendations with Edge/EV/Kelly breakdown

### `ml_model.py` — XGBoost Ensemble

25-feature XGBoost classifier + regressor ensemble. Trained on historical match data, outputs win/draw/loss probabilities alongside Poisson predictions for cross-validation. 63.9% accuracy on test set.

### `the_odds_api.py` — The Odds API Client

Python SDK for [The Odds API](https://the-odds-api.com). Fetches real-time odds across bookmakers:

```python
from predict_odds.the_odds_api import TheOddsAPIClient
client = TheOddsAPIClient.from_env()
odds = client.get_odds(sport="soccer_fifa_world_cup", regions="eu",
                       markets=["h2h", "totals", "spreads"])
```

- Best-price aggregation across bookmakers (Pinnacle, Bet365, Betfair, William Hill...)
- Supports: h2h (1X2), totals (Over/Under), spreads (Asian handicap)
- Free tier: 500 requests/month

### `predict_fun_betting.py` — On-Chain Betting (BNB Chain)

Executes bets directly on [Predict.fun](https://predict.fun) prediction markets via BNB Chain:

```bash
# Dry-run
.venv/bin/python -m predict_odds bet \
  --match-slug fifwc-tun-jpn-2026-06-21 \
  --bet-type away --amount 10 --dry-run -y

# Live
.venv/bin/python -m predict_odds bet ... --live -y
```

Supported bet types: `home`, `draw`, `away`, `over_2_5`, `under_2_5`, `exact_score_X-Y`

Safety gates:
- $50 max per single bet
- $200 daily limit
- Default dry-run mode
- Requires BNB Chain USDC + BNB gas

### `predict_fun_sell.py` — Take-Profit Module

Three-tier auto take-profit system:

| Trigger | Action |
|---------|--------|
| +25% profit | Sell 33% of position |
| +50% profit | Sell another 33% |
| +100% profit | Close remaining |

Tracks positions in `out/positions.json`. Manual activation only — no auto-trigger.

### `predict_fun_odds.py` — Predict.fun Market Data

Fetches prediction market odds from Predict.fun. Each World Cup match has 4 slugs:
- Main: moneyline (Win/Draw/Win)
- `-exact-score`: 17 score outcomes
- `-halftime-result`: HT markets
- `-more-markets`: spreads, O/U, BTTS (11 markets)

### `data_enrichment.py` — Data Enrichment Pipeline

Enriches raw match data with 48-team statistics. Uses FotMob for real match results + FIFA ranking-based xG estimation. Merges real results with synthetic placeholders for teams with sparse data.

### `sentiment.py` — Social Sentiment Analysis

Web-scrapes and analyzes social media sentiment for teams. Outputs -1.0 to +1.0 sentiment scores. Lexical analysis + search-based data collection.

### `backtest.py` — Backtesting Engine

Replay stored predictions against historical results:

```bash
.venv/bin/python -m predict_odds backtest \
  --database out/bot.sqlite --results data/results.csv \
  --bankroll 1000 --min-edge 0.04 --fractional-kelly 0.25
```

Outputs: profit, ROI, hit rate, max drawdown, equity curve per bet.

### `settlement.py` — Results Settlement

Import final scores and grade all predictions:

```bash
.venv/bin/python -m predict_odds settle \
  --database out/bot.sqlite --results data/results.csv
```

Grades: Win / Loss / Push / Void. Tracks by market family (1X2, totals, spreads).

### `repository.py` — SQLite Storage

Persistent SQLite database (`out/bot.sqlite`) for all predictions, odds snapshots, settlements, and CLV tracking. Powers backtesting and reporting.

### `cli.py` — Command-Line Interface

Comprehensive CLI with subcommands:

```
scan        Full scan → predict → Kelly pipeline
bet         Place Predict.fun orders (BNB Chain)
analyze     Deep match analysis with LLM prompt
settle      Import results and grade predictions
report      Performance dashboard
backtest    Replay historical predictions
optimize    Grid-search Kelly parameters
walk-forward  Walk-forward validation
demo        Offline demo mode
doctor      Health check
schedule    APScheduler cron setup
```

### `telegram_panel.py` — Telegram Bot Panel

Interactive Telegram bot with commands:

```
/dashboard   Live position overview
/upcoming    Today's fixtures
/scan        Trigger full scan
/approve     Review and approve bets
/history     Recent bet history
/set_limit   Adjust limits on the fly
```

### Data Sources Module

| Source | Module | Data | Auth |
|--------|--------|------|:---:|
| ESPN API | `data_sources.py` | Fixtures + results | ❌ |
| The Odds API | `the_odds_api.py` | Live odds (h2h/totals/spreads) | ✅ |
| Predict.fun | `predict_fun_odds.py` | Prediction market odds | ✅ |
| api-football | `client.py` | Bet365 odds, lineups, stats | ⚠️ |
| Polymarket | `polymarket.py` | Event discovery | ❌ |
| Sportmonks | `sportmonks.py` | Fixture details | ⚠️ |

---

## 📊 Betting Frameworks

Proven patterns from live World Cup 2026:

| Framework | Rule | Example |
|-----------|------|---------|
| **3-Tier Odds** | 1.06-1.18 steamroll / 1.35-1.45 danger / 1.48-1.60 gray | France 1.30 → steamroll ✅ |
| **Counter-Attack Check** | Favorites only steamroll if opponent lacks PL/LaLiga anchors | England vs Ghana (Partey) → 0-0 ❌ |
| **Star Premium** | Haaland-effect inflates odds. Check R1 stats before fading | Norway (#44) at 2.15 vs Senegal (#20) |
| **Knockout Draw Bias** | R16+ draws spike → conservative on ML | 2/3 R16 matches to pens |
| **xG Conversion Gap** | Favorites vs low-blocks: high xG, low conversion | Belgium xG 1.80 → 0 goals |

Full analysis in [`references/`](references/) (23 framework documents).

---

## 🎯 Track Record

| Match | Prediction | Actual | Result |
|-------|-----------|--------|--------|
| Ecuador vs Curaçao | 0-0 (70% draw) | 0-0 | ✅ Score + direction |
| France vs Iraq | Over 2.5 + 3-0 | 3-0 | ✅ Exact score |
| Tunisia vs Japan | Away 81% | 0-4 | ✅ Direction |
| Portugal vs Uzbekistan | Steamroll | 5-0 | ✅ |
| Panama vs Croatia | Gray zone ✅ | 0-1 | ✅ |
| Colombia vs Congo DR | Gray zone ✅ | 1-0 | ✅ |

---

## 🤖 Hermes Agent Integration

```bash
mkdir -p ~/.hermes/skills/crypto/football-bot/
cp SKILL.md ~/.hermes/skills/crypto/football-bot/SKILL.md
cp -r references/ ~/.hermes/skills/crypto/football-bot/references/
```

Commands in Hermes: `足球` `fb` `⚽` `足球分析` `比分预测` `下注`

Cron example:
```bash
hermes cron create --name "足球每日赛程" --schedule "0 8 * * *" \
  --skill football-bot --prompt "扫描今日赛事，输出Kelly仓位摘要"
```

---

## 📁 Project Layout

```
predict-odds-python/
├── src/predict_odds/
│   ├── prediction.py          # Poisson v2: xG + score distribution
│   ├── feature_pipeline.py    # 25+ features engine
│   ├── tactics.py             # 59-team tactical profiles
│   ├── supplementary.py       # Referees (15), weather, injuries
│   ├── bot_scanner.py         # Scan → predict → Kelly pipeline
│   ├── ml_model.py            # XGBoost classifier + regressor
│   ├── the_odds_api.py        # The Odds API client (best-price)
│   ├── predict_fun_betting.py # BNB Chain order execution
│   ├── predict_fun_sell.py    # 3-tier take-profit
│   ├── predict_fun_odds.py    # Predict.fun market data
│   ├── predict_fun_trade.py   # Low-level trading utils
│   ├── predict_fun_wallet.py  # BNB Chain wallet ops
│   ├── sentiment.py           # Social sentiment analysis
│   ├── data_enrichment.py     # 48-team stats enrichment
│   ├── backtest.py            # Historical replay engine
│   ├── settlement.py          # Results settlement + grading
│   ├── repository.py          # SQLite persistence
│   ├── cli.py                 # Full CLI interface
│   ├── telegram_panel.py      # Telegram bot control panel
│   └── ...                    # + 20 more modules
├── data/                      # CSV data + config
├── scripts/                   # 10 data pipeline scripts
├── references/                # 23 analysis framework docs
├── tests/                     # 23 test files
├── SKILL.md                   # Hermes Agent skill
└── README.md                  # ← You are here
```

---

## 🔑 API Keys

| Service | Env Variable | Free Tier | Sign Up |
|---------|-------------|-----------|---------|
| The Odds API | `THE_ODDS_API_KEY` | 500 req/mo | [the-odds-api.com](https://the-odds-api.com) |
| Predict.fun | `PREDICTFUN_API_KEY` | — | [predict.fun](https://predict.fun) |
| api-football | `API_FOOTBALL_KEY` | 100 req/day | [api-football.com](https://www.api-football.com) |

Only `THE_ODDS_API_KEY` is required. ESPN data is free.

---

## 📄 License

MIT
