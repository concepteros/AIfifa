# ⚽ AIfifa — AI Football Prediction Bot

> Poisson xG + tactical analysis + Kelly betting + Predict.fun on-chain execution

[![Python](https://img.shields.io/badge/Python-3.9+-blue)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![BNB Chain](https://img.shields.io/badge/Chain-BNB-yellow)](https://www.bnbchain.org)

AI-powered football prediction system running live World Cup 2026 predictions. Combines Poisson models, tactical analysis, referee profiling, and real-time market odds with Kelly-optimal position sizing. Executes on-chain via Predict.fun (BNB Chain).

## What's Inside

| Component | Description |
|-----------|-------------|
| [🔮 **predict-odds-python**](predict-odds-python/) | Core prediction engine — 30+ Python modules, CLI, tests |
| [🤖 **Skill**](predict-odds-python/SKILL.md) | Hermes Agent integration — natural-language football commands |
| [📚 **References**](predict-odds-python/references/) | 23 betting framework docs from live trading experience |

## Quick Start

```bash
git clone https://github.com/concepteros/AIfifa.git
cd AIfifa/predict-odds-python
python3 -m venv .venv && .venv/bin/pip install -e .
cp .env.example .env   # add THE_ODDS_API_KEY
.venv/bin/python -m predict_odds scan --config data/bot-scan.json --summary
```

## Six-Step Pipeline

```
ESPN API → Poisson xG → Tactical → Referee → Market Odds → Kelly Bet
```

## Verified Predictions

| Match | Prediction | Result |
|-------|-----------|--------|
| France vs Iraq | Over 2.5 + 3-0 | 3-0 ✅ |
| Ecuador vs Curaçao | 0-0 (70% draw) | 0-0 ✅ |
| Portugal vs Uzbekistan | Steamroll | 5-0 ✅ |
| Tunisia vs Japan | Away 81% | 0-4 ✅ |

## Betting Frameworks

- **3-Tier Odds** — steamroll vs danger vs gray zones
- **Counter-Attack Check** — structural defense profile before betting favorites
- **Star Premium** — Haaland-effect odds inflation detection
- **Knockout Draw Bias** — R16+ draw probability spike
- **xG Conversion Asymmetry** — favorites vs low blocks ≠ auto-Over

## On-Chain Trading

Execute bets on BNB Chain via Predict.fun:

```bash
.venv/bin/python -m predict_odds bet \
  --match-slug fifwc-tun-jpn-2026-06-21 \
  --bet-type away --amount 10 --live -y
```

Safety: $50 max/bet · $200 daily limit · dry-run default · 3-tier take-profit

## Hermes Agent

Drop into Hermes for voice/natural-language control:

```bash
cp predict-odds-python/SKILL.md ~/.hermes/skills/crypto/football-bot/SKILL.md
```

Then: `⚽` `足球分析` `下注 draw 10U`

---

📖 **Full docs:** [predict-odds-python/README.md](predict-odds-python/README.md) — complete module-by-module reference with architecture diagrams, API documentation, and 20+ module descriptions.
