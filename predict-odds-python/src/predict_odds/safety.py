from __future__ import annotations

from typing import Any


def evaluate_safety_gates(
    report: dict[str, Any],
    *,
    max_daily_stake: float | None = None,
    max_drawdown_pct: float | None = None,
    max_consecutive_losses: int | None = None,
    min_bankroll: float | None = None,
) -> dict[str, Any]:
    reasons = []
    stake = float(report.get("stake", 0) or 0)
    drawdown = float(report.get("max_drawdown_pct", 0) or 0)
    losses = int(report.get("losses", 0) or 0)
    wins = int(report.get("wins", 0) or 0)
    ending_bankroll = float(report.get("ending_bankroll", report.get("bankroll", 0)) or 0)
    if max_daily_stake is not None and stake > float(max_daily_stake):
        reasons.append(f"daily stake {stake} > limit {float(max_daily_stake)}")
    if max_drawdown_pct is not None and drawdown > float(max_drawdown_pct):
        reasons.append(f"drawdown {drawdown} > limit {float(max_drawdown_pct)}")
    if max_consecutive_losses is not None and losses >= int(max_consecutive_losses) and wins == 0:
        reasons.append(f"loss streak {losses} >= limit {int(max_consecutive_losses)}")
    if min_bankroll is not None and ending_bankroll < float(min_bankroll):
        reasons.append(f"bankroll {ending_bankroll} < minimum {float(min_bankroll)}")
    return {"allowed": not reasons, "reasons": reasons}
