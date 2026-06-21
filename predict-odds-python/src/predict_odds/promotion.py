from __future__ import annotations

from typing import Any


def promote_strategy(
    report: dict[str, Any],
    *,
    min_bets: int = 1,
    min_roi: float = 0.0,
    min_profit: float = 0.0,
    max_drawdown_pct: float | None = None,
    bankroll: float | None = None,
) -> dict[str, Any]:
    metrics = _extract_metrics(report)
    settings = _extract_settings(report)
    reasons = _gate_reasons(
        metrics,
        min_bets=min_bets,
        min_roi=min_roi,
        min_profit=min_profit,
        max_drawdown_pct=max_drawdown_pct,
    )
    approved = not reasons and settings is not None
    if settings is None:
        approved = False
        reasons.append("no selected settings found")
    return {
        "approved": approved,
        "reasons": reasons,
        "metrics": metrics,
        "decision": _decision_config(settings, metrics, bankroll=bankroll) if approved else None,
    }


def _extract_metrics(report: dict[str, Any]) -> dict[str, Any]:
    if isinstance(report.get("validation"), dict):
        validation = report["validation"]
        return {
            "total_bets": int(validation.get("total_bets", 0)),
            "profit": float(validation.get("profit", 0)),
            "roi": float(validation.get("roi", 0)),
            "max_drawdown_pct": float(validation.get("max_drawdown_pct", 0)),
            "hit_rate": float(validation.get("hit_rate", 0)),
            "bankroll": float(validation.get("settings", {}).get("bankroll", 0)),
        }
    summary = report.get("summary", {})
    return {
        "total_bets": int(summary.get("total_bets", 0)),
        "profit": float(summary.get("profit", 0)),
        "roi": float(summary.get("roi", 0)),
        "max_drawdown_pct": float(summary.get("avg_max_drawdown_pct", summary.get("max_drawdown_pct", 0))),
        "hit_rate": float(summary.get("hit_rate", 0)),
        "bankroll": 0.0,
    }


def _extract_settings(report: dict[str, Any]) -> dict[str, Any] | None:
    settings = report.get("selected_settings")
    if isinstance(settings, dict):
        return settings
    folds = report.get("folds")
    if isinstance(folds, list):
        for fold in folds:
            if isinstance(fold, dict) and isinstance(fold.get("selected_settings"), dict):
                return fold["selected_settings"]
    return None


def _gate_reasons(
    metrics: dict[str, Any],
    *,
    min_bets: int,
    min_roi: float,
    min_profit: float,
    max_drawdown_pct: float | None,
) -> list[str]:
    reasons = []
    if metrics["total_bets"] < min_bets:
        reasons.append(f"total_bets {metrics['total_bets']} < required {min_bets}")
    if metrics["roi"] < min_roi:
        reasons.append(f"roi {metrics['roi']} < required {min_roi}")
    if metrics["profit"] < min_profit:
        reasons.append(f"profit {metrics['profit']} < required {min_profit}")
    if max_drawdown_pct is not None and metrics["max_drawdown_pct"] > max_drawdown_pct:
        reasons.append(f"max_drawdown_pct {metrics['max_drawdown_pct']} > allowed {max_drawdown_pct}")
    return reasons


def _decision_config(
    settings: dict[str, Any] | None,
    metrics: dict[str, Any],
    *,
    bankroll: float | None,
) -> dict[str, float]:
    assert settings is not None
    return {
        "bankroll": round(float(bankroll if bankroll is not None else metrics.get("bankroll") or 0), 2),
        "min_edge": float(settings["min_edge"]),
        "fractional_kelly": float(settings["fractional_kelly"]),
        "max_stake_fraction": float(settings["max_stake_fraction"]),
    }
