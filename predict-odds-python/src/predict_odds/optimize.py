from __future__ import annotations

from itertools import product
from pathlib import Path
from typing import Any

from .backtest import run_backtest


def optimize_parameters(
    database: str | Path,
    results_path: str | Path,
    *,
    bankroll: float,
    min_edges: list[float],
    fractional_kellies: list[float],
    max_stake_fractions: list[float],
    min_bets: int = 1,
    league: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    evaluated_runs = []
    accepted_runs = []
    for min_edge, fractional_kelly, max_stake_fraction in product(
        min_edges,
        fractional_kellies,
        max_stake_fractions,
    ):
        report = run_backtest(
            database,
            results_path,
            bankroll=bankroll,
            min_edge=min_edge,
            fractional_kelly=fractional_kelly,
            max_stake_fraction=max_stake_fraction,
            league=league,
            start_date=start_date,
            end_date=end_date,
        )
        evaluated_runs.append(report)
        if int(report["total_bets"]) >= int(min_bets):
            accepted_runs.append(report)
    accepted_runs.sort(key=_sort_key)
    return {
        "evaluated": len(evaluated_runs),
        "returned": len(accepted_runs),
        "min_bets": int(min_bets),
        "best": accepted_runs[0] if accepted_runs else None,
        "runs": accepted_runs,
    }


def parse_float_grid(raw: str) -> list[float]:
    values = []
    for part in raw.split(","):
        stripped = part.strip()
        if stripped:
            values.append(float(stripped))
    if not values:
        raise ValueError("grid must contain at least one numeric value")
    return values


def _sort_key(report: dict[str, Any]) -> tuple[float, float, int, float, float, float]:
    settings = report["settings"]
    return (
        -float(report["roi"]),
        -float(report["profit"]),
        -int(report["total_bets"]),
        float(settings["min_edge"]),
        float(settings["fractional_kelly"]),
        float(settings["max_stake_fraction"]),
    )
