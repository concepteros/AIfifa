# AI Football Prediction Bot

> 世界杯足球 AI 预测 + 自动交易系统 | Poisson 模型 · 战术分析 · Kelly 仓位 · Predict.fun 链上下单

## Overview

Production-grade AI football prediction bot powering live World Cup 2026 betting. Runs inside [Hermes Agent](https://github.com/nousresearch/hermes-agent) as a skill-driven cron job.

**Core Pipeline:**
1. **ESPN API** → live fixtures & results (no API key needed)
2. **Poisson v2 Model** → xG prediction + score distribution
3. **Tactical Analysis** → 59-team profiles + style matchup
4. **Referee Assessment** → strictness/cards/VAR/home bias
5. **The Odds API** → real-time Bet365/Pinnacle odds
6. **Kelly Criterion** → 1/4 Kelly position sizing (5% cap)

## Verified Track Record

| Match | Prediction | Result | Status |
|-------|-----------|--------|--------|
| Ecuador vs Curaçao | 0-0 (70% draw) | 0-0 | ✅ Score + direction |
| Tunisia vs Japan | Away 81% / 0-2 | 0-4 | ✅ Direction |
| France vs Iraq | Over 2.5 + 3-0 | 3-0 | ✅ Exact score |
| Argentina vs Austria | Under 2.5 + 1-0 | 2-0 (U✅) | ⚠️ Half right |
| Portugal vs Uzbekistan | Steamroll | 5-0 | ✅ |
| Panama vs Croatia | Gray zone Croatia | 0-1 | ✅ |
| Colombia vs Congo DR | Gray zone Colombia | 1-0 | ✅ |

## Quick Start

```bash
git clone https://github.com/concepteros/AIfifa.git
cd predict-odds-python
python3 -m venv .venv
.venv/bin/pip install -e .

# Configure .env (see .env.example)
cp .env.example .env
# Edit .env with your API keys

# Scan today's World Cup matches
.venv/bin/python -m predict_odds scan --config data/bot-scan.json --summary
```

## Hermes Agent Integration

This repo includes a `SKILL.md` for Hermes Agent. Load it as:

```bash
cp SKILL.md ~/.hermes/skills/crypto/football-bot/SKILL.md
```

The skill enables natural-language commands:
- `足球` / `fb` — scan fixtures
- `⚽ 分析 France vs Sweden` — full pipeline analysis
- `下注 draw 10U` — place Predict.fun bets

Cron job delivers daily predictions to Telegram at 08:00 BJT.

## Project Structure

```
predict-odds-python/
├── src/predict_odds/
│   ├── prediction.py          # Poisson v2 model
│   ├── feature_pipeline.py    # Feature engineering + referee
│   ├── tactics.py             # 59-team tactical profiles
│   ├── supplementary.py       # Referee/weather/injury data
│   ├── ml_model.py            # XGBoost ensemble
│   ├── the_odds_api.py        # The Odds API client
│   ├── bot_scanner.py         # Scan + Kelly pipeline
│   ├── predict_fun_betting.py # On-chain betting (BNB Chain)
│   └── predict_fun_sell.py    # Take-profit module
├── data/                      # Data files
├── scripts/                   # Data pipelines
├── references/                # Analysis frameworks & lessons learned
├── tests/                     # Test suite
└── SKILL.md                   # Hermes Agent skill definition
```

## Data Sources

| Source | Purpose | Auth |
|--------|---------|------|
| ESPN API | Fixtures & results | None |
| The Odds API | Real-time odds (h2h/totals/spreads) | `THE_ODDS_API_KEY` |
| Predict.fun | Prediction market odds + on-chain trading | `PREDICTFUN_API_KEY` |
| api-football | Bet365 odds/lineups/corners | `API_FOOTBALL_KEY` |
| Polymarket | Event discovery | None (browser) |

## Betting Frameworks

- **3-Tier Odds Reliability**: 1.06-1.18 steamroll / 1.35-1.45 danger zone / 1.48-1.60 gray zone
- **Structured Counter-Attack Check**: Before betting steamroll favorites, verify opponent lacks PL/LaLiga midfield anchors + pace on wings
- **Star Premium Pattern**: Haaland-effect: markets inflate super-star teams. Verify round 1 stats before fading
- **Knockout Stage**: Draw probability spikes in R16+. Be conservative on ML bets.
- **xG Conversion Asymmetry**: Favorites vs low blocks → inflated xG, poor conversion. Don't blindly bet Over.

## Predict.fun Trading

On-chain betting via BNB Chain (ChainId 56):

```bash
# Dry-run (safe)
.venv/bin/python -m predict_odds bet \
  --match-slug fifwc-tun-jpn-2026-06-21 \
  --bet-type away --amount 10 --dry-run -y

# Live bet
.venv/bin/python -m predict_odds bet ... --live -y

# Bettable types: home / draw / away / over_2_5 / under_2_5 / exact_score_1-0
```

Safety gates: $50 max/single bet, $200 daily limit. Requires BNB Chain USDC + BNB for gas.

## Environment

- Python 3.9+
- macOS / Linux
- `.env` at project root (see `.env.example`)
- Virtual env: `.venv/`

## License

MIT
