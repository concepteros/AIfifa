---
name: football-bot
description: "AI football prediction bot — Poisson xG model, tactical analysis, Kelly betting, Predict.fun on-chain execution"
version: 2.2.0
trigger:
  - "足球" "fb" "⚽" "足球分析" "比分预测" "scan football"
  - "下注" "买" "bet" + market name
  - "what matches today" "today's fixtures"
---

# ⚽ AI Football Prediction Bot

A production-grade football prediction system powered by Poisson models, tactical profiles, and real-time market odds. Works standalone or inside Hermes Agent as a skill.

## Quick Install (Standalone)

```bash
git clone https://github.com/concepteros/AIfifa.git
cd AIfifa/predict-odds-python
python3 -m venv .venv
.venv/bin/pip install -e .
cp .env.example .env
# Edit .env — at minimum set THE_ODDS_API_KEY
```

## Scan Today's Matches

```bash
# Update config date + scan (World Cup 2026)
TODAY=$(TZ='Asia/Shanghai' date +%Y-%m-%d)
python3 -c "import json; c=json.load(open('data/bot-scan.json')); c['scan']['date']='$TODAY'; json.dump(c,open('data/bot-scan.json','w'),indent=2)"
.venv/bin/python -m predict_odds scan --config data/bot-scan.json --summary
```

## Hermes Agent Integration

```bash
# Install as skill
mkdir -p ~/.hermes/skills/crypto/football-bot/
cp SKILL.md ~/.hermes/skills/crypto/football-bot/SKILL.md
cp -r references/ ~/.hermes/skills/crypto/football-bot/references/
```

Then in Hermes: `足球` or `scan football` triggers the full pipeline.

## Cron (Hermes Agent)

```bash
hermes cron create \
  --name "足球每日赛程" \
  --schedule "0 8 * * *" \
  --skill football-bot \
  --prompt "扫描今日世界杯赛事，输出 Kelly 仓位摘要。只显示北京时间当天比赛。"
```

## 6-Step Pipeline

1. **ESPN API** — fixtures/results (free, no key)
2. **Poisson v2** — xG + score distribution
3. **Tactical Analysis** — 59 team profiles + style matchup
4. **Referee Assessment** — strictness, cards, VAR, home bias
5. **The Odds API** — Bet365/Pinnacle real-time odds
6. **Kelly Criterion** — 1/4 Kelly, 5% cap per bet

## Data Sources

| Source | Provides | Key Required |
|--------|----------|:---:|
| ESPN API | Fixtures & results | ❌ |
| The Odds API | Live odds (h2h/totals/spreads) | ✅ |
| Predict.fun | Prediction markets + on-chain trading | ✅ |
| api-football | Bet365 odds / lineups / corn...| ⚠️ Optional |

## Predict.fun Betting (BNB Chain)

```bash
# Dry-run (safe)
.venv/bin/python -m predict_odds bet \
  --match-slug fifwc-tun-jpn-2026-06-21 \
  --bet-type away --amount 10 --dry-run -y

# Live trade
.venv/bin/python -m predict_odds bet ... --live -y

# Types: home / draw / away / over_2_5 / under_2_5 / exact_score_1-0
# Safety: $50 max/bet, $200 daily limit
# Chain: BNB Chain (56) — needs USDC + BNB for gas
```

## Key Frameworks (see references/)

- **3-Tier Odds**: 1.06-1.18 steamroll / 1.35-1.45 danger / 1.48-1.60 gray
- **Counter-Attack Check**: Before steamroll bets, verify opponent lacks PL/LaLiga midfield anchors + pace
- **Star Premium**: Haaland-effect inflates odds. Check R1 stats before fading
- **Knockout Draw Bias**: R16+ draw rates spike — conservative on ML
- **Model Overfit**: matches_used ≤2 → trust market odds, not Poisson

## Verified Predictions

| Match | Prediction | Result |
|-------|-----------|--------|
| Ecuador vs Curaçao | 0-0 (70% draw) | 0-0 ✅ |
| France vs Iraq | Over 2.5 + 3-0 | 3-0 ✅ |
| Tunisia vs Japan | Away 81% | 0-4 ✅ |
| Portugal vs Uzbekistan | Steamroll | 5-0 ✅ |
| Panama vs Croatia | Gray zone ✅ | 0-1 ✅ |
| Colombia vs Congo DR | Gray zone ✅ | 1-0 ✅ |

## Project Structure

```
predict-odds-python/
├── src/predict_odds/
│   ├── prediction.py          # Poisson v2 model
│   ├── feature_pipeline.py    # Features + referee integration
│   ├── tactics.py             # 59-team tactical profiles
│   ├── supplementary.py       # Referee/weather/injury data
│   ├── bot_scanner.py         # Scan + Kelly pipeline
│   ├── the_odds_api.py        # The Odds API client
│   ├── predict_fun_betting.py # On-chain betting (BNB Chain)
│   └── predict_fun_sell.py    # Take-profit module
├── data/                      # CSV data + config
├── scripts/                   # Data pipelines
├── references/                # Analysis frameworks
├── tests/                     # Test suite
├── SKILL.md                   # Hermes Agent skill
└── README.md                  # You are here
```

## Requirements

- Python 3.9+
- Virtual env: `.venv/`
- `.env` at project root (see `.env.example`)
- BNB Chain USDC + BNB (for Predict.fun trading only)
