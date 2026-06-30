# Kelly Over/Under Betting Flow — End-to-End Example

Complete flow from market discovery to order placement, verified 2026-06-22.

## Prerequisites

```bash
cd /Users/macbook/AIfifa/predict-odds-python
export $(grep -v '^#' .env | xargs)
# Must use venv Python (has eth_account):
VPY=/Users/macbook/.hermes/hermes-agent/venv/bin/python
```

## Step 1: Discover More-Markets (O/U, Spreads, BTTS)

```python
from predict_odds.predict_fun_odds import _request_get

# Main slug only has moneyline (Win/Draw/Win)
# O/U lives under -more-markets sub-slug
data = _request_get("/v1/categories/fifwc-esp-ksa-2026-06-21-more-markets")
markets = data.get('data', {}).get('markets', [])

for m in markets:
    q = m.get('question', '')
    if 'O/U' in q and '2.5' in q:
        mid = m.get('id')  # e.g. 376983
        for o in m.get('outcomes', []):
            name = o.get('name', '?')  # "Over" / "Under" (NOT Yes/No!)
            ba = o.get('bestAsk') or {}
            print(f"{name}: ask={ba.get('price')} size={ba.get('size',0):.0f}")
```

## Step 2: Kelly Calculation

```python
bankroll = 100.0
fractional_kelly = 0.25
max_stake_pct = 0.05

market_price = 0.74       # Over 2.5 bestAsk
decimal_odds = 1 / market_price
our_prob = 0.78           # From exact-score synthesis or model

full_kelly = (our_prob * decimal_odds - 1) / (decimal_odds - 1)
kelly_amount = bankroll * full_kelly * fractional_kelly
stake = min(round(kelly_amount, 2), bankroll * max_stake_pct)
size = round(stake / market_price, 3)
```

## Step 3: Place Order

```python
from predict_odds.predict_fun_betting import place_bet, SafetyLimits

result = place_bet(
    market_id=376983,           # From Step 1
    side="buy",                 # BUY = Over, SELL = Under
    price=market_price,         # 0.74
    size=size,                  # 5.203 shares for $3.85 stake
    dry_run=False,
    safety=SafetyLimits(
        max_bet_usdc=10.0,
        daily_limit_usdc=50.0,
        confirm_before_execute=False,
    ),
)
```

## Critical: Outcome Names Vary by Sub-Slug

| Sub-slug | Outcome Names |
|----------|--------------|
| main (moneyline) | "Yes" / "No" |
| exact-score | "Yes" / "No" |
| more-markets O/U | **"Over" / "Under"** |
| more-markets Spread | **"ESP" / "KSA"** (team codes) |
| more-markets BTTS | "Yes" / "No" |

Always check `outcomes[].name` before hardcoding.

## Wallet Requirement

⚠️ Predict.fun = **BNB Chain only** (ChainId 56).
- USDC must be on BNB Chain (BEP-20)
- Need ~0.01 BNB for gas
- Same EVM address works: `0x9E47a2103B7039A97C41892653F880c077503eaD`
- Polygon funds NOT visible to Predict.fun
