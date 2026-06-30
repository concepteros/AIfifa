"""Predict.fun auto-betting execution — place bets on World Cup match markets.

Provides:
  place_bet()           — core order placement with EIP-712 wallet auth
  bet_on_match()        — convenience: resolve market by slug + bet type
  auto_bet_from_decisions() — integrate decision.py output

CLI:  python -m predict_odds bet --market-id 163340 --side buy --amount 10 [--dry-run]
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from .env_loader import load_env_file
from .errors import PredictAPIError, PredictConfigError, PredictValidationError

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_URL = "https://api.predict.fun"
BET_MARKET_TYPES = frozenset({
    "home_win", "away_win", "draw",
    "over_2_5", "under_2_5",
    "home", "away",  # aliases for home_win / away_win
})

# How we map bet_type strings to Predict.fun outcome names
# Predict.fun match markets use "Yes"/"No" outcomes for binary questions.
# e.g. "Will Japan win?" → Yes=Japan wins, No=Japan doesn't win
# e.g. "Will there be over 2.5 goals?" → Yes=Over, No=Under
BET_TYPE_TO_OUTCOME: dict[str, str] = {
    "home_win": "Yes",
    "home": "Yes",
    "away_win": "No",    # "Will HOME win?" → No means away wins or draw
    "away": "No",
    "draw": "No",         # "Will HOME win?" → No means draw or away win
    "over_2_5": "Yes",    # "Will there be over 2.5 goals?"
    "under_2_5": "No",
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class BetResult:
    success: bool
    market_id: int
    side: str          # BUY or SELL
    price: float
    size: float
    cost: float        # price * size in USDC
    order_id: str | None = None
    raw_response: dict[str, Any] | None = None
    error: str | None = None
    dry_run: bool = False


@dataclass
class SafetyLimits:
    max_bet_usdc: float = 50.0        # max single bet in USDC
    daily_limit_usdc: float = 200.0   # max total per day
    confirm_before_execute: bool = True
    daily_spent: float = 0.0
    last_reset_date: str = field(default_factory=lambda: datetime.utcnow().strftime("%Y-%m-%d"))


# ---------------------------------------------------------------------------
# API helpers (mirror predict_fun_wallet.py but self-contained for reliability)
# ---------------------------------------------------------------------------

def _get_api_key() -> str:
    key = os.getenv("PREDICTFUN_API_KEY", "")
    if not key:
        raise PredictConfigError("PREDICTFUN_API_KEY not set in environment")
    return key


def _request(method: str, path: str, body: dict | None = None, *, jwt: str | None = None) -> dict:
    url = f"{BASE_URL}{path}"
    h = {
        "x-api-key": _get_api_key(),
        "User-Agent": "predict-odds-bot/1.0",
        "Accept": "application/json",
    }
    if jwt:
        h["Authorization"] = f"Bearer {jwt}"
    data_bytes = json.dumps(body).encode() if body else None
    if data_bytes:
        h["Content-Type"] = "application/json"

    req = Request(url, data=data_bytes, headers=h)
    if method != "GET":
        req.method = method

    try:
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        body_text = e.read().decode()
        try:
            return json.loads(body_text)
        except json.JSONDecodeError:
            return {"error": str(e), "body": body_text[:500]}


# Global JWT cache
_jwt_token: str | None = None


def _authenticate() -> str:
    """Authenticate wallet using EIP-712 signature and return JWT token. Cached globally."""
    global _jwt_token
    if _jwt_token:
        return _jwt_token

    pk = os.getenv("PREDICTFUN_WALLET_PRIVATE_KEY", "")
    if not pk:
        raise PredictConfigError("PREDICTFUN_WALLET_PRIVATE_KEY not set")

    # 1. Get message to sign
    resp = _request("GET", "/v1/auth/message")
    if not resp.get("success"):
        raise PredictAPIError(f"Auth message request failed: {resp}")
    msg = resp["data"]["message"]

    # 2. Sign with eth_account
    from eth_account import Account
    from eth_account.messages import encode_defunct

    acct = Account.from_key(pk)
    signed = acct.sign_message(encode_defunct(text=msg))
    sig = f"0x{signed.signature.hex()}"

    # 3. Get JWT (retry once on 500)
    for attempt in range(2):
        resp = _request("POST", "/v1/auth", {
            "signer": acct.address,
            "signature": sig,
            "message": msg,
        })
        if resp.get("success"):
            _jwt_token = resp["data"]["token"]
            return _jwt_token
        if attempt == 0:
            time.sleep(1)

    raise PredictAPIError(f"Authentication failed after retry: {resp}")


# ---------------------------------------------------------------------------
# Market resolution
# ---------------------------------------------------------------------------

def lookup_market_by_slug(match_slug: str) -> dict[str, Any] | None:
    """Find a market on Predict.fun by its category slug.

    Args:
        match_slug: e.g. 'fifwc-tun-jpn-2026-06-21'

    Returns:
        Market dict with id, outcomes, bestAsk/bestBid, or None if not found.
    """
    return _lookup_market_by_slug(match_slug)


def lookup_markets_by_slug(match_slug: str) -> list[dict[str, Any]]:
    """Find ALL markets belonging to a match slug.

    Some matches have multiple markets (win/loss, draw) under the same slug.
    Uses /v1/search which returns match-specific categories.
    """
    # Strategy 1: /v1/search is the most reliable for match markets
    # Extract team names from slug patterns like 'fifwc-tun-jpn-2026-06-21'
    parts = match_slug.split("-")
    search_terms = []
    for part in parts:
        if len(part) == 3 and part.isalpha():  # team codes like tun, jpn
            search_terms.append(part)
    query = " ".join(search_terms) if search_terms else match_slug

    data = _request("GET", f"/v1/search?query={query.replace(' ', '%20')}")
    categories = data.get("data", {}).get("categories", [])
    all_markets: list[dict[str, Any]] = []
    for cat in categories:
        for m in cat.get("markets", []):
            if m.get("categorySlug", "") == match_slug:
                all_markets.append(m)

    if all_markets:
        return all_markets

    # Fallback: try direct markets search and categories
    data = _request("GET", f"/v1/markets?search={match_slug}")
    markets = data.get("data", [])
    matched = [m for m in markets if m.get("categorySlug", "") == match_slug]

    if not matched:
        data = _request("GET", "/v1/categories")
        events = data.get("data", [])
        for e in events:
            for m in e.get("markets", []):
                if m.get("categorySlug", "") == match_slug:
                    matched.append(m)

    return matched


def _lookup_market_by_slug(match_slug: str) -> dict[str, Any] | None:
    """Find first market matching the slug."""
    markets = lookup_markets_by_slug(match_slug)
    return markets[0] if markets else None


def _resolve_market_for_bet_type(
    all_markets: list[dict], match_slug: str, bet_type: str
) -> dict[str, Any]:
    """Find the specific market matching the bet type.

    Predict.fun match structure (e.g. fifwc-tun-jpn-2026-06-21):
      - "Will [HOME] win on YYYY-MM-DD?" → bet home_win/home here (BUY Yes)
      - "Will [HOME] vs. [AWAY] end in a draw?" → bet draw here (BUY Yes)
      - "Will [AWAY] win on YYYY-MM-DD?" → bet away_win/away here (BUY Yes)

    Strategy: parse team names from the draw market question, then match.
    """
    bet_type_lower = bet_type.lower().strip()

    # First, find the draw market to extract team names
    draw_market = None
    home_team_lower = ""
    away_team_lower = ""
    for m in all_markets:
        question = str(m.get("question", "")).lower()
        if "draw" in question:
            draw_market = m
            # Parse "Will X vs Y end in a draw?"
            # Split on " vs " or " vs. "
            for sep in (" vs. ", " vs "):
                if sep in question:
                    before, after = question.split(sep, 1)
                    # before: "will X" → extract X
                    home_part = before.replace("will ", "").strip()
                    # after: "Y end in a draw?" → extract Y
                    away_part = after.split(" end in")[0].strip()
                    home_team_lower = home_part
                    away_team_lower = away_part
                    break
            break

    # Match bet_type to the right market
    for m in all_markets:
        question = str(m.get("question", "")).lower()

        if bet_type_lower in ("home_win", "home"):
            # "Will [HOME] win on ...?"
            if "win on" in question and home_team_lower and home_team_lower in question:
                return m

        elif bet_type_lower in ("away_win", "away"):
            # "Will [AWAY] win on ...?" — but NOT the home team's win market
            if "win on" in question and away_team_lower and away_team_lower in question:
                return m

        elif bet_type_lower == "draw":
            if draw_market:
                return draw_market

        elif bet_type_lower == "over_2_5":
            if "over" in question and ("2.5" in question or "2_5" in question):
                return m

        elif bet_type_lower == "under_2_5":
            if "under" in question and ("2.5" in question or "2_5" in question):
                return m

        elif bet_type_lower.startswith("exact_score_"):
            score_str = bet_type_lower.replace("exact_score_", "").replace("_", "-")
            if "exact score" in question or score_str in question:
                return m

    # Fallback for over_2_5 / under_2_5: check all markets
    for m in all_markets:
        question = str(m.get("question", "")).lower()
        if bet_type_lower == "over_2_5" and "over" in question:
            return m
        if bet_type_lower == "under_2_5" and "over" in question:
            return m  # caller will handle SELL side

    # Broad fallback
    if all_markets:
        return all_markets[0]
    raise PredictValidationError(
        f"No market found for bet_type '{bet_type}' in slug '{match_slug}'"
    )


def _resolve_side_and_price(market: dict, bet_type: str) -> tuple[str, float]:
    """For a given market and bet_type, return (side: BUY/SELL, best_price).

    Most bets are BUY Yes. Exception: under_2_5 on a market that only has over.
    """
    outcomes = market.get("outcomes", [])
    yes_outcome = None
    no_outcome = None

    for o in outcomes:
        name = o.get("name", "").strip().lower()
        if name == "yes":
            yes_outcome = o
        elif name == "no":
            no_outcome = o

    bet_type_lower = bet_type.lower().strip()

    # Determine whether to BUY or SELL
    if bet_type_lower == "under_2_5":
        question = str(market.get("question", "")).lower()
        if "under" in question:
            # Direct under market exists — BUY Yes
            side = "BUY"
            outcome = yes_outcome
            price_key = "bestAsk"
        else:
            # Only over market exists — SELL No (bet against over)
            side = "SELL"
            outcome = no_outcome
            price_key = "bestBid"
    else:
        # All other bets: BUY Yes on the appropriate market
        side = "BUY"
        outcome = yes_outcome
        price_key = "bestAsk"

    if outcome is None:
        raise PredictValidationError(
            f"Could not find {'Yes' if side == 'BUY' else 'No'} outcome in market"
        )

    best = outcome.get(price_key)
    if isinstance(best, dict):
        price = float(best.get("price", 0))
    else:
        price = float(best) if best is not None else 0.0

    if price <= 0:
        raise PredictValidationError(
            f"No {price_key} price available for {bet_type} on market #{market.get('id')}"
        )

    return side, price


# ---------------------------------------------------------------------------
# Core betting function
# ---------------------------------------------------------------------------

def place_bet(
    market_id: int,
    side: str,
    price: float,
    size: float,
    *,
    dry_run: bool = False,
    safety: SafetyLimits | None = None,
) -> BetResult:
    """Place an order on Predict.fun.

    Authenticates with wallet (EIP-712 signature), then POSTs to /v1/orders.

    Args:
        market_id: Predict.fun market ID.
        side: 'buy' or 'sell' (case-insensitive). BUY = Yes, SELL = No.
        price: Price per share in USDC (0.00–1.00).
        size: Number of shares.
        dry_run: If True, simulate without placing order.
        safety: Optional SafetyLimits for pre-flight checks.

    Returns:
        BetResult with success status and order details.
    """
    side_upper = side.upper().strip()
    if side_upper not in ("BUY", "SELL"):
        return BetResult(
            success=False,
            market_id=market_id,
            side=side_upper,
            price=price,
            size=size,
            cost=price * size,
            error=f"Invalid side: {side}. Must be 'buy' or 'sell'.",
            dry_run=dry_run,
        )

    cost = round(price * size, 2)

    # --- Safety checks ---
    if safety is not None:
        # Reset daily counter if date changed
        today = datetime.utcnow().strftime("%Y-%m-%d")
        if safety.last_reset_date != today:
            safety.daily_spent = 0.0
            safety.last_reset_date = today

        if cost > safety.max_bet_usdc:
            return BetResult(
                success=False,
                market_id=market_id,
                side=side_upper,
                price=price,
                size=size,
                cost=cost,
                error=f"Bet cost ${cost:.2f} exceeds max single bet ${safety.max_bet_usdc:.2f}",
                dry_run=dry_run,
            )

        if safety.daily_spent + cost > safety.daily_limit_usdc:
            return BetResult(
                success=False,
                market_id=market_id,
                side=side_upper,
                price=price,
                size=size,
                cost=cost,
                error=(
                    f"Daily limit would be exceeded: "
                    f"already spent ${safety.daily_spent:.2f}, "
                    f"this bet ${cost:.2f}, "
                    f"limit ${safety.daily_limit_usdc:.2f}"
                ),
                dry_run=dry_run,
            )

        if safety.confirm_before_execute:
            # In CLI mode this is handled by the caller; in programmatic mode
            # we log a warning but proceed. The caller should check.
            pass  # Caller is responsible for confirmation

    # --- Dry run ---
    if dry_run:
        return BetResult(
            success=True,
            market_id=market_id,
            side=side_upper,
            price=price,
            size=size,
            cost=cost,
            order_id="DRY_RUN",
            dry_run=True,
        )

    # --- Authenticate and place order ---
    try:
        jwt = _authenticate()
    except Exception as e:
        return BetResult(
            success=False,
            market_id=market_id,
            side=side_upper,
            price=price,
            size=size,
            cost=cost,
            error=f"Authentication failed: {e}",
            dry_run=False,
        )

    try:
        resp = _request("POST", "/v1/orders", {
            "marketId": market_id,
            "side": side_upper,
            "price": str(price),
            "size": str(size),
        }, jwt=jwt)
    except Exception as e:
        return BetResult(
            success=False,
            market_id=market_id,
            side=side_upper,
            price=price,
            size=size,
            cost=cost,
            error=f"Order request failed: {e}",
            dry_run=False,
        )

    # Parse response
    if resp.get("success") or resp.get("data"):
        order_data = resp.get("data", resp)
        order_id = order_data.get("id") or order_data.get("orderId", "UNKNOWN")
        if safety is not None:
            safety.daily_spent += cost
        return BetResult(
            success=True,
            market_id=market_id,
            side=side_upper,
            price=price,
            size=size,
            cost=cost,
            order_id=str(order_id),
            raw_response=resp,
            dry_run=False,
        )

    # Error case
    error_msg = resp.get("error") or resp.get("message") or str(resp)
    return BetResult(
        success=False,
        market_id=market_id,
        side=side_upper,
        price=price,
        size=size,
        cost=cost,
        error=str(error_msg),
        raw_response=resp,
        dry_run=False,
    )


# ---------------------------------------------------------------------------
# Convenience: bet_on_match
# ---------------------------------------------------------------------------

def bet_on_match(
    match_slug: str,
    bet_type: str,
    amount: float,
    *,
    dry_run: bool = False,
    safety: SafetyLimits | None = None,
) -> BetResult:
    """Place a bet on a match by slug.

    Args:
        match_slug: e.g. 'fifwc-tun-jpn-2026-06-21'
        bet_type: 'home', 'away', 'draw', 'over_2_5', 'under_2_5', or 'exact_score_X-Y'
        amount: Total USDC to spend (size = amount / price)
        dry_run: If True, simulate without placing order.
        safety: Optional SafetyLimits.

    Returns:
        BetResult.
    """
    # Find ALL markets for this match slug
    all_markets = lookup_markets_by_slug(match_slug)
    if not all_markets:
        return BetResult(
            success=False,
            market_id=0,
            side="?",
            price=0,
            size=0,
            cost=0,
            error=f"No markets found for slug: {match_slug}",
            dry_run=dry_run,
        )

    # Find the specific market matching the bet type
    try:
        market = _resolve_market_for_bet_type(all_markets, match_slug, bet_type)
    except PredictValidationError as e:
        return BetResult(
            success=False, market_id=0, side="?", price=0, size=0, cost=0,
            error=str(e), dry_run=dry_run,
        )

    market_id = int(market["id"])
    question = market.get("question", "")

    # Resolve side and price
    try:
        side, price = _resolve_side_and_price(market, bet_type)
    except PredictValidationError as e:
        return BetResult(
            success=False,
            market_id=market_id,
            side="?",
            price=0,
            size=0,
            cost=0,
            error=str(e),
            dry_run=dry_run,
        )

    # Calculate size from amount
    if price <= 0:
        return BetResult(
            success=False,
            market_id=market_id,
            side=side,
            price=price,
            size=0,
            cost=0,
            error=f"No valid price for {bet_type} on market #{market_id}",
            dry_run=dry_run,
        )

    size = round(amount / price, 3)

    # Place the bet
    return place_bet(
        market_id=market_id,
        side=side.lower(),  # place_bet normalizes case
        price=price,
        size=size,
        dry_run=dry_run,
        safety=safety,
    )


# ---------------------------------------------------------------------------
# Integration with decision.py
# ---------------------------------------------------------------------------

def auto_bet_from_decisions(
    decisions: dict[str, Any],
    *,
    dry_run: bool = True,
    safety: SafetyLimits | None = None,
    match_slug: str | None = None,
    market_id_map: dict[str, int] | None = None,
) -> list[BetResult]:
    """Auto-place bets from decision.py recommendations.

    Args:
        decisions: Output of build_betting_decisions() — dict with 'recommendations' list.
        dry_run: Default True for safety — set False to actually place bets.
        safety: Optional SafetyLimits.
        match_slug: If provided, look up markets by this slug.
        market_id_map: Dict mapping market names to Predict.fun market IDs.

    Returns:
        List of BetResult for each recommendation with action='bet'.
    """
    results: list[BetResult] = []

    recommendations = decisions.get("recommendations", [])
    bets = [r for r in recommendations if r.get("action") == "bet"]

    if not bets:
        return results

    for rec in bets:
        market_name = rec["market"]
        stake = rec["stake"]

        # Determine the market_id and side
        market_id = None
        side = "buy"
        if market_id_map and market_name in market_id_map:
            market_id = market_id_map[market_name]
            side = "buy"  # assume we know the right market
        elif match_slug:
            # Find the right market for this bet type
            all_markets = lookup_markets_by_slug(match_slug)
            if all_markets:
                try:
                    market = _resolve_market_for_bet_type(all_markets, match_slug, market_name)
                    market_id = int(market["id"])
                    side, _ = _resolve_side_and_price(market, market_name)
                    side = side.lower()
                except PredictValidationError as e:
                    results.append(BetResult(
                        success=False, market_id=0, side="?", price=0, size=0, cost=0,
                        error=str(e), dry_run=dry_run,
                    ))
                    continue
            else:
                results.append(BetResult(
                    success=False, market_id=0, side="?", price=0, size=0, cost=0,
                    error=f"Cannot find markets for slug {match_slug} / bet {market_name}",
                    dry_run=dry_run,
                ))
                continue

        if market_id is None:
            results.append(BetResult(
                success=False, market_id=0, side="?", price=0, size=0, cost=0,
                error=f"No market_id mapping for '{market_name}'. Provide match_slug or market_id_map.",
                dry_run=dry_run,
            ))
            continue

        # Get price from the market's orderbook
        mkt_detail = _request("GET", f"/v1/markets/{market_id}")
        mkt = mkt_detail.get("data", mkt_detail)
        try:
            _, price = _resolve_side_and_price(mkt, market_name)
        except PredictValidationError as e:
            results.append(BetResult(
                success=False, market_id=market_id, side=side, price=0, size=0, cost=0,
                error=str(e), dry_run=dry_run,
            ))
            continue

        size = round(stake / price, 3) if price > 0 else 0

        result = place_bet(
            market_id=market_id,
            side=side,
            price=price,
            size=size,
            dry_run=dry_run,
            safety=safety,
        )
        results.append(result)

    return results


# ---------------------------------------------------------------------------
# Safety check helpers
# ---------------------------------------------------------------------------

def get_wallet_balance() -> float:
    """Get current wallet balance in USDC."""
    try:
        jwt = _authenticate()
    except Exception:
        return 0.0
    resp = _request("GET", "/v1/account", jwt=jwt)
    acc = resp.get("data", resp)
    balance_str = acc.get("balance", "0")
    try:
        return float(balance_str)
    except (ValueError, TypeError):
        return 0.0


def check_safety_gates(
    stake: float,
    *,
    safety: SafetyLimits | None = None,
) -> dict[str, Any]:
    """Check if a bet passes safety gates.

    Returns: {'allowed': bool, 'reasons': list[str]}
    """
    reasons: list[str] = []
    if safety is None:
        return {"allowed": True, "reasons": []}

    if stake > safety.max_bet_usdc:
        reasons.append(f"stake ${stake:.2f} exceeds max single bet ${safety.max_bet_usdc:.2f}")

    today = datetime.utcnow().strftime("%Y-%m-%d")
    current_daily = safety.daily_spent if safety.last_reset_date == today else 0.0
    if current_daily + stake > safety.daily_limit_usdc:
        reasons.append(
            f"daily total would be ${current_daily + stake:.2f} "
            f"(limit ${safety.daily_limit_usdc:.2f})"
        )

    # Check wallet balance
    balance = get_wallet_balance()
    if balance > 0 and stake > balance:
        reasons.append(f"stake ${stake:.2f} exceeds wallet balance ${balance:.2f}")

    return {"allowed": not reasons, "reasons": reasons}


# ---------------------------------------------------------------------------
# CLI support
# ---------------------------------------------------------------------------

def bet_cli(args: Any) -> int:
    """Handle the 'bet' CLI subcommand. Returns exit code."""
    load_env_file(args.env_file)

    safety = SafetyLimits(
        max_bet_usdc=args.max_bet if hasattr(args, 'max_bet') and args.max_bet else 50.0,
        daily_limit_usdc=args.daily_limit if hasattr(args, 'daily_limit') and args.daily_limit else 200.0,
        confirm_before_execute=not getattr(args, 'yes', False),
    )

    dry_run = getattr(args, 'dry_run', False)

    if hasattr(args, 'match_slug') and args.match_slug:
        # bet_on_match mode
        result = bet_on_match(
            match_slug=args.match_slug,
            bet_type=args.bet_type,
            amount=args.amount,
            dry_run=dry_run,
            safety=safety,
        )
    elif hasattr(args, 'market_id') and args.market_id:
        # Direct market bet
        if not hasattr(args, 'side') or not args.side:
            print("ERROR: --side is required (buy or sell)", flush=True)
            return 1

        price = args.price if hasattr(args, 'price') and args.price else 0
        if price <= 0:
            # Auto-fetch price from orderbook
            mkt_detail = _request("GET", f"/v1/markets/{args.market_id}")
            mkt = mkt_detail.get("data", mkt_detail)
            outcomes = mkt.get("outcomes", [])
            side_upper = args.side.upper()
            for o in outcomes:
                if side_upper == "BUY":
                    best = o.get("bestAsk")
                else:
                    best = o.get("bestBid")
                if best:
                    if isinstance(best, dict):
                        price = float(best.get("price", 0))
                    else:
                        price = float(best) if best else 0.0
                    break

        if price <= 0:
            print(f"ERROR: Could not determine price for market {args.market_id}", flush=True)
            return 1

        size = args.size if hasattr(args, 'size') and args.size else round(args.amount / price, 3)
        amount = args.amount if hasattr(args, 'amount') and args.amount else price * size

        # Confirmation
        if not dry_run and safety.confirm_before_execute:
            side_label = "YES (Buy)" if args.side.lower() == "buy" else "NO (Sell)"
            print(f"\n⚠️  CONFIRM LIVE BET:")
            print(f"   Market: #{args.market_id}")
            print(f"   Side: {side_label}")
            print(f"   Price: {price:.4f} USDC/share")
            print(f"   Size: {size:.3f} shares")
            print(f"   Total: ${amount:.2f} USDC")
            print()
            try:
                response = input("Place this bet? (yes/no): ").strip().lower()
                if response not in ("yes", "y"):
                    print("Bet cancelled.")
                    return 0
            except (EOFError, KeyboardInterrupt):
                print("\nBet cancelled.")
                return 0

        result = place_bet(
            market_id=args.market_id,
            side=args.side,
            price=price,
            size=size,
            dry_run=dry_run,
            safety=safety,
        )
    else:
        print("ERROR: Must specify either --market-id or --match-slug", flush=True)
        return 1

    # Output result
    if result.success:
        if dry_run:
            print(f"✅ DRY RUN — would place bet: #{result.market_id} {result.side} "
                  f"{result.size} shares @ {result.price} = ${result.cost:.2f}")
        else:
            print(f"✅ Bet placed! Order: {result.order_id}")
            print(f"   Market #{result.market_id} | {result.side} | "
                  f"{result.size} shares @ {result.price} | ${result.cost:.2f}")
    else:
        print(f"❌ Bet failed: {result.error}")

    # JSON output
    import json as _json
    print(_json.dumps({
        "success": result.success,
        "market_id": result.market_id,
        "side": result.side,
        "price": result.price,
        "size": result.size,
        "cost": result.cost,
        "order_id": result.order_id,
        "error": result.error,
        "dry_run": result.dry_run,
    }, indent=2))

    return 0 if result.success else 1
