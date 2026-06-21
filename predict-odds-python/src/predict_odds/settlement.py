from __future__ import annotations

from pathlib import Path
from typing import Any

from .closing_odds import find_closing_odds, load_closing_odds
from .repository import BotRepository
from .results import MatchResult, load_results

SUPPORTED_MARKETS = {"home_win", "draw", "away_win"}


def settle_recommendation(
    recommendation: dict[str, Any],
    result: MatchResult,
    *,
    closing_odds: float | None = None,
) -> dict[str, Any]:
    market = str(recommendation.get("market", ""))
    action = recommendation.get("action")
    stake = float(recommendation.get("stake") or 0)
    odds = float(recommendation.get("odds") or 0)
    if action != "bet":
        return {
            "market": market,
            "status": "skipped",
            "stake": 0.0,
            "profit": 0.0,
        }
    status = _settle_status(market, result)
    if status == "skipped":
        return {
            "market": market,
            "status": "skipped",
            "stake": 0.0,
            "profit": 0.0,
        }
    profit = _profit(status, stake, odds)
    settlement = {
        "market": market,
        "status": status,
        "stake": round(stake, 2),
        "profit": round(profit, 2),
        "odds": odds,
    }
    if closing_odds is not None:
        settlement["closing_odds"] = round(float(closing_odds), 6)
        settlement["clv"] = round(float(closing_odds) - odds, 6)
        settlement["clv_pct"] = round((float(closing_odds) / odds) - 1, 6) if odds else 0.0
    return settlement


def settle_database(
    database: str | Path,
    results_path: str | Path,
    *,
    closing_odds_path: str | Path | None = None,
) -> dict[str, Any]:
    repository = BotRepository(database)
    results = load_results(results_path)
    closing_rows = load_closing_odds(closing_odds_path) if closing_odds_path else []
    settled = 0
    for match in repository.list_match_decisions():
        result = _find_result(match, results)
        if result is None:
            continue
        decisions = match.get("decision", {}).get("recommendations", [])
        for recommendation in decisions:
            closing = find_closing_odds(closing_rows, result, str(recommendation.get("market", ""))) if closing_rows else None
            settlement = settle_recommendation(recommendation, result, closing_odds=closing)
            if settlement["status"] == "skipped":
                continue
            repository.save_settlement(match["id"], settlement)
            settled += 1
    return {"settled": settled}


def build_performance_report(database: str | Path) -> dict[str, Any]:
    return BotRepository(database).performance_report()


def _find_result(match: dict[str, Any], results: list[MatchResult]) -> MatchResult | None:
    for result in results:
        if (
            _same(match["league"], result.league)
            and _same(match["home_team"], result.home_team)
            and _same(match["away_team"], result.away_team)
            and match["match_date"] == result.date
        ):
            return result
    return None


def _same(left: str, right: str) -> bool:
    return str(left).strip().casefold() == str(right).strip().casefold()


def _settle_status(market: str, result: MatchResult) -> str:
    if market in SUPPORTED_MARKETS:
        return "won" if market == result.outcome else "lost"
    if market.startswith("over_") or market.startswith("under_"):
        return _settle_total(market, result)
    if market.startswith("home_spread_") or market.startswith("away_spread_"):
        return _settle_spread(market, result)
    return "skipped"


def _settle_total(market: str, result: MatchResult) -> str:
    side, raw_line = market.split("_", 1)
    line = _parse_line(raw_line)
    total_goals = result.home_goals + result.away_goals
    if total_goals == line:
        return "push"
    if side == "over":
        return "won" if total_goals > line else "lost"
    return "won" if total_goals < line else "lost"


def _settle_spread(market: str, result: MatchResult) -> str:
    if market.startswith("home_spread_"):
        raw_line = market.removeprefix("home_spread_")
        adjusted = result.home_goals + _parse_line(raw_line) - result.away_goals
    else:
        raw_line = market.removeprefix("away_spread_")
        adjusted = result.away_goals + _parse_line(raw_line) - result.home_goals
    if adjusted == 0:
        return "push"
    return "won" if adjusted > 0 else "lost"


def _parse_line(raw: str) -> float:
    return float(raw.replace("_", "."))


def _profit(status: str, stake: float, odds: float) -> float:
    if status == "won":
        return stake * (odds - 1)
    if status == "lost":
        return -stake
    return 0.0
