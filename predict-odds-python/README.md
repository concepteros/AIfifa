# ⚽ AIfifa — AI Football Prediction Bot

> Poisson xG + tactical analysis + Kelly betting + Predict.fun on-chain execution

A production-grade AI system that predicts football matches, sizes bets with Kelly Criterion, and executes on-chain via Predict.fun (BNB Chain). Powers live World Cup 2026 predictions. Runs standalone or as a [Hermes Agent](https://github.com/nousresearch/hermes-agent) skill.

---

## 🚀 Quick Start (2 min)

```bash
# 1. Clone
git clone https://github.com/concepteros/AIfifa.git
cd AIfifa/predict-odds-python

# 2. Setup venv
python3 -m venv .venv
.venv/bin/pip install -e .

# 3. Configure
cp .env.example .env
# Edit .env → add THE_ODDS_API_KEY (free tier: https://the-odds-api.com)

# 4. Run
TODAY=$(date +%Y-%m-%d)
python3 -c "import json; c=json.load(open('data/bot-scan.json')); c['scan']['date']='$TODAY'; json.dump(c,open('data/bot-scan.json','w'),indent=2)"
.venv/bin/python -m predict_odds scan --config data/bot-scan.json --summary
```

**That's it.** The scanner will find today's matches, run Poisson predictions, compare against market odds, and output Kelly-sized bet recommendations.

---

## 🧠 How It Works

```
ESPN API ──→ Poisson xG ──→ Tactical ──→ Referee ──→ Market Odds ──→ Kelly Bet
(fixtures)   (scores)     (matchups)   (profile)    (The Odds API)   (position)
```

| Step | Component | What It Does |
|------|-----------|-------------|
| 1 | ESPN API | Grab fixtures + results (free, no API key) |
| 2 | Poisson v2 | Expected goals + score distribution |
| 3 | Tactical Analysis | 59 team profiles, style matchups |
| 4 | Referee Assessment | Strictness, cards, VAR, home bias |
| 5 | The Odds API | Real-time Bet365 / Pinnacle odds |
| 6 | Kelly Criterion | Optimal bet size (1/4 Kelly, 5% cap) |

---

## 📊 Betting Frameworks

Battle-tested patterns from live World Cup 2026 trading:

| Framework | Rule | Example |
|-----------|------|---------|
| **3-Tier Odds** | 1.06-1.18 steamroll / 1.35-1.45 danger / 1.48-1.60 gray | France 1.30 → steamroll ✅ |
| **Counter-Attack Check** | Favorites only steamroll if opponent lacks PL/LaLiga anchors | England 1.18 vs Ghana (Partey) → 0-0 ❌ |
| **Star Premium** | Haaland-effect inflates odds. Check R1 stats before fading | Norway (#44) lines at 2.15 vs Senegal (#20) |
| **Knockout Draw Bias** | R16+ draws spike. Conservative on ML | 2/3 R16 matches → pens |
| **xG Conversion Gap** | Favorites vs low-blocks: high xG, low conversion | Belgium xG 1.80 → 0 goals |

Full analysis frameworks in [`references/`](references/).

---

## 🎯 Verified Track Record

| Match | Prediction | Actual | Result |
|-------|-----------|--------|--------|
| Ecuador vs Curaçao | 0-0 (70% draw) | 0-0 | ✅ Score + direction |
| France vs Iraq | Over 2.5 + 3-0 | 3-0 | ✅ Exact score |
| Tunisia vs Japan | Away 81% | 0-4 | ✅ Direction |
| Portugal vs Uzbekistan | Steamroll | 5-0 | ✅ |
| Panama vs Croatia | Gray zone Croatia | 0-1 | ✅ |
| Colombia vs Congo DR | Gray zone Colombia | 1-0 | ✅ |

---

## 🔗 Predict.fun On-Chain Betting

Execute bets directly on BNB Chain:

```bash
# Dry-run first (always safe)
.venv/bin/python -m predict_odds bet \
  --match-slug fifwc-tun-jpn-2026-06-21 \
  --bet-type away --amount 10 --dry-run -y

# Live
.venv/bin/python -m predict_odds bet ... --live -y

# Available bet types: home / draw / away / over_2_5 / under_2_5 / exact_score_1-0
```

Safety gates: $50 max per bet, $200 daily limit. Requires BNB Chain USDC + BNB gas.

---

## 🤖 Hermes Agent Integration

Drop into Hermes for natural-language control:

```bash
mkdir -p ~/.hermes/skills/crypto/football-bot/
cp SKILL.md ~/.hermes/skills/crypto/football-bot/SKILL.md
cp -r references/ ~/.hermes/skills/crypto/football-bot/references/
```

Then just say **"⚽ 分析今天比赛"** in your Hermes chat. Cron-ready for daily schedules.

---

## 📁 Project Layout

```
predict-odds-python/
├── src/predict_odds/          # Core engine
│   ├── prediction.py          # Poisson xG model
│   ├── feature_pipeline.py    # Feature engineering
│   ├── tactics.py             # Team profiles
│   ├── supplementary.py       # Referee/weather data
│   ├── bot_scanner.py         # Scan → predict → Kelly
│   ├── predict_fun_betting.py # BNB Chain orders
│   └── the_odds_api.py        # Odds API client
├── data/                      # CSVs + config
├── references/                # Analysis docs (23 files)
├── scripts/                   # Data pipelines
├── tests/                     # Test suite
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
