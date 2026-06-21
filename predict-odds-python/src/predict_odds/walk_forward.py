from __future__ import annotations

from pathlib import Path
from typing import Any

from .validation import validate_strategy


def parse_walk_forward_window(raw: str) -> dict[str, str]:
    parts = [part.strip() for part in raw.split(":")]
    if len(parts) != 4 or any(not part for part in parts):
        raise ValueError("window must use train_start:train_end:validation_start:validation_end")
    return {
        "train_start_date": parts[0],
        "train_end_date": parts[1],
        "validation_start_date": parts[2],
        "validation_end_date": parts[3],
    }


def run_walk_forward(
    database: str | Path,
    results_path: str | Path,
    *,
    bankroll: float,
    min_edges: list[float],
    fractional_kellies: list[float],
    max_stake_fractions: list[float],
    windows: list[dict[str, str]],
    min_bets: int = 1,
    league: str | None = None,
) -> dict[str, Any]:
    folds = []
    validations = []
    for index, window in enumerate(windows, start=1):
        fold = validate_strategy(
            database,
            results_path,
            bankroll=bankroll,
            min_edges=min_edges,
            fractional_kellies=fractional_kellies,
            max_stake_fractions=max_stake_fractions,
            min_bets=min_bets,
            league=league,
            train_start_date=window["train_start_date"],
            train_end_date=window["train_end_date"],
            validation_start_date=window["validation_start_date"],
            validation_end_date=window["validation_end_date"],
        )
        fold["fold"] = index
        folds.append(fold)
        if fold["validation"] is not None:
            validations.append(fold["validation"])
    return {
        "fold_count": len(folds),
        "summary": _summarize_validations(validations),
        "folds": folds,
    }


def _summarize_validations(validations: list[dict[str, Any]]) -> dict[str, Any]:
    total_bets = sum(int(item["total_bets"]) for item in validations)
    wins = sum(int(item["wins"]) for item in validations)
    pushes = sum(int(item["pushes"]) for item in validations)
    losses = sum(int(item["losses"]) for item in validations)
    stake = round(sum(float(item["stake"]) for item in validations), 2)
    profit = round(sum(float(item["profit"]) for item in validations), 2)
    drawdowns = [float(item["max_drawdown"]) for item in validations]
    return {
        "total_bets": total_bets,
        "wins": wins,
        "pushes": pushes,
        "losses": losses,
        "stake": stake,
        "profit": profit,
        "roi": round(profit / stake, 6) if stake else 0.0,
        "hit_rate": round(wins / total_bets, 6) if total_bets else 0.0,
        "avg_max_drawdown": round(sum(drawdowns) / len(drawdowns), 6) if drawdowns else 0.0,
    }
