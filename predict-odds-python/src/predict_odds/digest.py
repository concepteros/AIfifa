from __future__ import annotations

from typing import Any


def build_daily_digest(*, scan: dict[str, Any] | None = None, report: dict[str, Any] | None = None) -> dict[str, Any]:
    scan = scan or {}
    report = report or {}
    matches = scan.get("matches", [])
    signals = 0
    if isinstance(matches, list):
        for match in matches:
            recommendations = match.get("decisions", {}).get("recommendations", []) if isinstance(match, dict) else []
            signals += sum(1 for item in recommendations if isinstance(item, dict) and item.get("action") == "bet")
    return {
        "processed": int(scan.get("processed", 0) or 0),
        "skipped": int(scan.get("skipped", 0) or 0),
        "signals": signals,
        "total_bets": int(report.get("total_bets", 0) or 0),
        "profit": round(float(report.get("profit", 0) or 0), 2),
        "roi": float(report.get("roi", 0) or 0),
        "max_drawdown": float(report.get("max_drawdown", report.get("avg_max_drawdown", 0)) or 0),
    }
