"""
Predict.fun 持仓止盈模块 — 自动监控并挂单卖出。

止盈策略：
  - +25% → 卖出 33% 持仓（保本锁利）
  - +50% → 卖出 33% 持仓（放大利润）
  - +100% → 卖出剩余全部（清仓）

用法：
  python -m predict_odds sell-track --position-file out/positions.json
  python -m predict_odds sell-check --all  # 检查所有持仓是否需要止盈
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from predict_sdk.constants import ChainId, Side
from predict_sdk.order_builder import OrderBuilder
from predict_sdk.types import BuildOrderInput, LimitHelperInput

# ── Data structures ──────────────────────────────────────────────────────────


@dataclass
class Position:
    """A single Predict.fun position."""

    market_id: str  # e.g. "163338"
    token_id: str  # on-chain token ID
    side: str  # "buy" or "sell"
    entry_price: float  # price per share in cents (0.01-0.99)
    shares: float  # number of shares owned
    entry_time: str  # ISO timestamp
    match_name: str = ""  # human-readable
    outcome: str = ""  # "Yes" or "No"

    # Sell tracking
    sold_25: bool = False
    sold_50: bool = False
    sold_100: bool = False

    def profit_pct(self, current_price: float) -> float:
        """Current unrealized profit percentage."""
        if self.entry_price <= 0:
            return 0.0
        return (current_price / self.entry_price - 1) * 100


@dataclass
class PositionTracker:
    """Tracks all open positions."""

    file_path: Path
    positions: list[Position] = field(default_factory=list)

    def save(self) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        data = []
        for p in self.positions:
            data.append({
                "market_id": p.market_id,
                "token_id": p.token_id,
                "side": p.side,
                "entry_price": p.entry_price,
                "shares": p.shares,
                "entry_time": p.entry_time,
                "match_name": p.match_name,
                "outcome": p.outcome,
                "sold_25": p.sold_25,
                "sold_50": p.sold_50,
                "sold_100": p.sold_100,
            })
        self.file_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    @classmethod
    def load(cls, path: str | Path) -> "PositionTracker":
        file_path = Path(path)
        tracker = cls(file_path=file_path)
        if file_path.exists():
            raw = json.loads(file_path.read_text())
            tracker.positions = [Position(**r) for r in raw]
        return tracker

    def add_position(self, position: Position) -> None:
        self.positions.append(position)
        self.save()

    def open_positions(self) -> list[Position]:
        return [p for p in self.positions if not p.sold_100]

    def mark_sold(self, market_id: str, tier: str) -> None:
        for p in self.positions:
            if p.market_id == market_id:
                if tier == "25":
                    p.sold_25 = True
                elif tier == "50":
                    p.sold_50 = True
                elif tier == "100":
                    p.sold_100 = True
        self.save()


# ── Sell logic ───────────────────────────────────────────────────────────────


def get_current_price(market_id: str, api_key: str) -> float | None:
    """Fetch the current bestAsk price for a market from Predict.fun API.

    Returns price in cents (0.01-0.99), or None if unavailable.
    """
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError

    url = f"https://api.predict.fun/v1/markets/{market_id}"
    try:
        req = Request(url, headers={"x-api-key": api_key, "User-Agent": "hermes-football-bot"})
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except (HTTPError, OSError) as e:
        print(f"  ⚠️ 获取价格失败: {e}")
        return None

    # Extract bestAsk from outcomes (handles both Yes/No tokens)
    outcomes = data.get("outcomes", [])
    for o in outcomes:
        ask = o.get("bestAsk")
        if ask and ask.get("price"):
            return float(ask["price"])
    return None


def _sell_order(
    position: Position,
    sell_pct: float,
    current_price: float,
    private_key: str,
    fee_rate_bps: int = 200,
) -> dict[str, Any]:
    """Execute a sell order for a portion of the position.

    Args:
        position: The position to sell from.
        sell_pct: Fraction of shares to sell (0.0-1.0).
        current_price: Current market price in cents.
        private_key: Wallet private key for signing.
        fee_rate_bps: Fee in basis points.

    Returns:
        Dict with sell result details.
    """
    from eth_account import Account

    shares_to_sell = int(position.shares * sell_pct * 1e6)  # Convert to wei (6 decimal)

    if shares_to_sell < int(1e16):
        return {"status": "skip", "reason": f"卖出量太小 ({shares_to_sell} wei)"}

    # Build the order
    builder = OrderBuilder.make(
        chain_id=ChainId.BNB_MAINNET,
        signer=private_key,
    )

    # Price in wei (6 decimal precision)
    price_wei = int(current_price * 1e6)

    amounts = builder.get_limit_order_amounts(
        LimitHelperInput(
            side=Side.SELL,
            price_per_share_wei=price_wei,
            quantity_wei=shares_to_sell,
        )
    )

    order = builder.build_order(
        strategy="LIMIT",
        data=BuildOrderInput(
            side=Side.SELL,
            token_id=position.token_id,
            maker_amount=amounts.maker_amount,
            taker_amount=amounts.taker_amount,
            fee_rate_bps=fee_rate_bps,
        ),
    )

    # Sign and submit
    typed_data = builder.build_typed_data(
        order,
        is_neg_risk=True,
        is_yield_bearing=True,
    )

    signature = builder.sign_typed_data(typed_data)

    # Submit to the orderbook API
    result = _submit_order(order, signature)

    return {
        "status": "submitted" if result else "failed",
        "order": order,
        "shares_sold": sell_pct * position.shares,
        "price": current_price,
        "pnl_pct": position.profit_pct(current_price),
    }


def _submit_order(order: Any, signature: str) -> bool:
    """Submit a signed order to the Predict.fun API."""
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError

    api_key = os.getenv("PREDICTFUN_API_KEY", "")
    order_dict = {
        "order": {
            "salt": order.salt,
            "maker": order.maker,
            "signer": order.signer,
            "taker": order.taker,
            "tokenId": order.token_id,
            "makerAmount": order.maker_amount,
            "takerAmount": order.taker_amount,
            "expiration": order.expiration,
            "nonce": order.nonce,
            "feeRateBps": order.fee_rate_bps,
            "side": int(order.side),
            "signatureType": int(order.signature_type),
        },
        "signature": signature,
    }

    try:
        req = Request(
            "https://api.predict.fun/v1/orders",
            data=json.dumps(order_dict).encode(),
            headers={
                "x-api-key": api_key,
                "Content-Type": "application/json",
                "User-Agent": "hermes-football-bot",
            },
        )
        with urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode())
            print(f"  ✅ 订单已提交: {result}")
            return True
    except HTTPError as e:
        body = e.read().decode() if e.fp else ""
        print(f"  ❌ 订单提交失败 ({e.code}): {body[:200]}")
        return False


def check_and_sell(
    tracker: PositionTracker,
    private_key: str,
    api_key: str,
    *,
    dry_run: bool = True,
) -> list[dict[str, Any]]:
    """Check all open positions and execute take-profit sells.

    Args:
        tracker: PositionTracker with open positions.
        private_key: Wallet private key.
        api_key: Predict.fun API key.
        dry_run: If True, don't actually submit sell orders.

    Returns:
        List of sell actions taken.
    """
    results = []
    for pos in tracker.open_positions():
        price = get_current_price(pos.market_id, api_key)
        if price is None:
            continue

        pnl = pos.profit_pct(price)

        # Determine which tier to sell at
        if pnl >= 100 and not pos.sold_100:
            sell_pct = 1.0  # sell all remaining
            tier = "100%"
        elif pnl >= 50 and not pos.sold_50:
            sell_pct = 0.33  # sell 1/3 of original
            tier = "50%"
        elif pnl >= 25 and not pos.sold_25:
            sell_pct = 0.33  # sell 1/3 of original
            tier = "25%"
        else:
            continue  # No sell needed

        action = {
            "position": pos,
            "tier": tier,
            "sell_pct": sell_pct,
            "current_price": price,
            "entry_price": pos.entry_price,
            "pnl_pct": round(pnl, 1),
        }

        if dry_run:
            action["status"] = "dry_run"
            print(f"🔍 [DRY-RUN] {pos.match_name} {pos.outcome}: "
                  f"{pos.entry_price:.2f}¢ → {price:.2f}¢ (+{pnl:.0f}%) → 触发 {tier} 止盈")
        else:
            result = _sell_order(pos, sell_pct, price, private_key)
            action.update(result)
            if result["status"] == "submitted":
                # Map tier to tracker field
                tier_key = {"25%": "25", "50%": "50", "100%": "100"}[tier]
                tracker.mark_sold(pos.market_id, tier_key)
                print(f"📤 [SELL] {pos.match_name} {pos.outcome}: "
                      f"+{pnl:.0f}% → 卖出 {sell_pct*100:.0f}% @ {price:.2f}¢")

        results.append(action)

    return results


# ── CLI helpers ──────────────────────────────────────────────────────────────


def sell_now_cli(
    position_file: str,
    market_id: str,
    pct: int,
    *,
    dry_run: bool = True,
    limit_price: float | None = None,
) -> str:
    """CLI entry point: manually sell pct% of a specific position.

    Args:
        position_file: Path to positions JSON.
        market_id: Market ID to sell.
        pct: Percentage to sell (25, 50, or 100).
        dry_run: If True, simulate only.
        limit_price: Optional limit price override.
    """
    from .env_loader import load_env_file

    load_env_file()
    pk = os.getenv("PREDICTFUN_WALLET_PRIVATE_KEY", "")
    api_key = os.getenv("PREDICTFUN_API_KEY", "")

    if not pk or not api_key:
        return "❌ 缺少 PREDICTFUN_WALLET_PRIVATE_KEY 或 PREDICTFUN_API_KEY"

    tracker = PositionTracker.load(position_file)

    # Find the position
    pos = None
    for p in tracker.positions:
        if p.market_id == market_id and not p.sold_100:
            pos = p
            break

    if pos is None:
        return f"❌ 未找到持仓 market_id={market_id}（或已全部卖出）"

    # Get current price
    price = limit_price or get_current_price(market_id, api_key)
    if price is None:
        return f"❌ 无法获取 {market_id} 当前价格"

    pnl = pos.profit_pct(price)
    sell_pct = pct / 100.0

    mode = "DRY-RUN" if dry_run else "实盘"
    lines = [
        f"📤 主动卖出 — {mode}",
        f"   持仓: {pos.match_name} {pos.outcome}",
        f"   入场: {pos.entry_price}¢ → 当前: {price}¢ (+{pnl:.1f}%)",
        f"   卖出: {pct}% × {pos.shares:.0f} shares = {pos.shares * sell_pct:.0f} shares",
    ]

    if dry_run:
        lines.append(f"\n   🔍 未实际执行（移除 --live 来实盘卖出）")
    else:
        result = _sell_order(pos, sell_pct, price, pk)
        if result["status"] == "submitted":
            if pct == 100:
                tracker.mark_sold(market_id, "100")
            elif pct == 50:
                tracker.mark_sold(market_id, "50")
            elif pct == 25:
                tracker.mark_sold(market_id, "25")
            lines.append(f"   ✅ 卖单已提交")
        else:
            lines.append(f"   ❌ 卖单失败: {result.get('reason', '未知错误')}")

    return "\n".join(lines)


def sell_check_cli(position_file: str, *, dry_run: bool = True) -> str:
    """CLI entry point: check all positions and sell if targets hit."""
    from .env_loader import load_env_file

    load_env_file()
    pk = os.getenv("PREDICTFUN_WALLET_PRIVATE_KEY", "")
    api_key = os.getenv("PREDICTFUN_API_KEY", "")

    if not pk or not api_key:
        return "❌ 缺少 PREDICTFUN_WALLET_PRIVATE_KEY 或 PREDICTFUN_API_KEY"

    tracker = PositionTracker.load(position_file)
    open_pos = tracker.open_positions()

    if not open_pos:
        return "📭 无持仓"

    mode = "DRY-RUN" if dry_run else "实盘"
    lines = [f"📊 持仓止盈检查 — {mode}", f"持仓 {len(open_pos)} 个", ""]

    for p in open_pos:
        price = get_current_price(p.market_id, api_key) if not dry_run else None
        pnl = p.profit_pct(price) if price else 0
        lines.append(
            f"{p.match_name} {p.outcome}: "
            f"{p.entry_price:.2f}¢ → {price:.2f}¢ (+{pnl:.0f}%)"
            if price
            else f"{p.match_name} {p.outcome}: 入场 {p.entry_price:.2f}¢ (价格获取失败)"
        )

    if not dry_run:
        results = check_and_sell(tracker, pk, api_key, dry_run=False)
        for r in results:
            if r["status"] == "submitted":
                lines.append(f"  → 已卖出 {r['tier']} 档")

    return "\n".join(lines)
