from __future__ import annotations

from pathlib import Path
from typing import Any

from .backtest import run_backtest
from .optimize import optimize_parameters


def validate_strategy(
    database: str | Path,
    results_path: str | Path,
    *,
    bankroll: float,
    min_edges: list[float],
    fractional_kellies: list[float],
    max_stake_fractions: list[float],
    train_start_date: str,
    train_end_date: str,
    validation_start_date: str,
    validation_end_date: str,
    min_bets: int = 1,
    league: str | None = None,
) -> dict[str, Any]:
    train = optimize_parameters(
        database,
        results_path,
        bankroll=bankroll,
        min_edges=min_edges,
        fractional_kellies=fractional_kellies,
        max_stake_fractions=max_stake_fractions,
        min_bets=min_bets,
        league=league,
        start_date=train_start_date,
        end_date=train_end_date,
    )
    best = train["best"]
    if best is None:
        return {
            "selected_settings": None,
            "train": train,
            "validation": None,
            "windows": _windows(train_start_date, train_end_date, validation_start_date, validation_end_date),
        }
    settings = best["settings"]
    validation = run_backtest(
        database,
        results_path,
        bankroll=bankroll,
        min_edge=float(settings["min_edge"]),
        fractional_kelly=float(settings["fractional_kelly"]),
        max_stake_fraction=float(settings["max_stake_fraction"]),
        league=league,
        start_date=validation_start_date,
        end_date=validation_end_date,
    )
    return {
        "selected_settings": {
            "min_edge": float(settings["min_edge"]),
            "fractional_kelly": float(settings["fractional_kelly"]),
            "max_stake_fraction": float(settings["max_stake_fraction"]),
            "min_bets": int(min_bets),
        },
        "train": train,
        "validation": validation,
        "windows": _windows(train_start_date, train_end_date, validation_start_date, validation_end_date),
    }


def _windows(
    train_start_date: str,
    train_end_date: str,
    validation_start_date: str,
    validation_end_date: str,
) -> dict[str, dict[str, str]]:
    return {
        "train": {"start_date": train_start_date, "end_date": train_end_date},
        "validation": {"start_date": validation_start_date, "end_date": validation_end_date},
    }
