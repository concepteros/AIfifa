from __future__ import annotations

from pathlib import Path
from typing import Any

from .decision import build_betting_decisions
from .repository import BotRepository
from .results import MatchResult, load_results
from .settlement import settle_recommendation


def run_backtest(
    database: str | Path,
    results_path: str | Path,
    *,
    bankroll: float,
    min_edge: float = 0.03,
    fractional_kelly: float = 0.25,
    max_stake_fraction: float = 0.05,
    league: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    matches = [
        match
        for match in BotRepository(database).list_match_decisions()
        if _included(match, league=league, start_date=start_date, end_date=end_date)
    ]
    results = load_results(results_path)
    settlements: list[dict[str, Any]] = []
    candidate_markets = 0
    matched_results = 0
    for match in matches:
        result = _find_result(match, results)
        if result is None:
            continue
        matched_results += 1
        recommendations = match.get("decision", {}).get("recommendations", [])
        for recommendation in recommendations:
            replayed = _replay_recommendation(
                recommendation,
                bankroll=bankroll,
                min_edge=min_edge,
                fractional_kelly=fractional_kelly,
                max_stake_fraction=max_stake_fraction,
            )
            if replayed is None:
                continue
            candidate_markets += 1
            settlement = settle_recommendation(replayed, result)
            if settlement["status"] != "skipped":
                settlements.append(settlement)
    report = _performance_report(settlements, starting_bankroll=float(bankroll))
    report.update(
        {
            "total_matches": len(matches),
            "matched_results": matched_results,
            "candidate_markets": candidate_markets,
            "settings": {
                "bankroll": round(float(bankroll), 2),
                "min_edge": float(min_edge),
                "fractional_kelly": float(fractional_kelly),
                "max_stake_fraction": float(max_stake_fraction),
                "league": league,
                "start_date": start_date,
                "end_date": end_date,
            },
        }
    )
    return report


def _replay_recommendation(
    recommendation: dict[str, Any],
    *,
    bankroll: float,
    min_edge: float,
    fractional_kelly: float,
    max_stake_fraction: float,
) -> dict[str, Any] | None:
    market = str(recommendation.get("market", ""))
    probability = recommendation.get("model_probability")
    odds = recommendation.get("odds")
    if not market or probability is None or odds is None:
        return None
    decision = build_betting_decisions(
        {"probabilities": {market: probability}},
        {market: odds},
        bankroll=bankroll,
        min_edge=min_edge,
        fractional_kelly=fractional_kelly,
        max_stake_fraction=max_stake_fraction,
    )
    return decision["recommendations"][0]


def _performance_report(settlements: list[dict[str, Any]], *, starting_bankroll: float) -> dict[str, Any]:
    total_bets = len(settlements)
    wins = sum(1 for item in settlements if item["status"] == "won")
    pushes = sum(1 for item in settlements if item["status"] == "push")
    stake = round(sum(float(item["stake"]) for item in settlements), 2)
    profit = round(sum(float(item["profit"]) for item in settlements), 2)
    curve = _equity_curve(settlements, starting_bankroll=starting_bankroll)
    by_market: dict[str, dict[str, Any]] = {}
    by_family: dict[str, dict[str, Any]] = {}
    for item in settlements:
        _add_to_bucket(by_market.setdefault(item["market"], _empty_bucket()), item)
        _add_to_bucket(by_family.setdefault(_market_family(item["market"]), _empty_bucket()), item)
    return {
        "total_bets": total_bets,
        "wins": wins,
        "pushes": pushes,
        "losses": total_bets - wins - pushes,
        "stake": stake,
        "profit": profit,
        "roi": round(profit / stake, 6) if stake else 0.0,
        "starting_bankroll": round(starting_bankroll, 2),
        "ending_bankroll": curve[-1]["bankroll"],
        "max_drawdown": max(point["drawdown"] for point in curve),
        "max_drawdown_pct": max(point["drawdown_pct"] for point in curve),
        "hit_rate": round(wins / total_bets, 6) if total_bets else 0.0,
        "equity_curve": [{key: value for key, value in point.items() if key != "drawdown_pct"} for point in curve],
        "by_market": by_market,
        "by_family": by_family,
    }


def _equity_curve(settlements: list[dict[str, Any]], *, starting_bankroll: float) -> list[dict[str, float | int]]:
    bankroll = round(starting_bankroll, 2)
    peak = bankroll
    curve: list[dict[str, float | int]] = [
        {"bet": 0, "bankroll": bankroll, "drawdown": 0.0, "drawdown_pct": 0.0}
    ]
    for index, settlement in enumerate(settlements, start=1):
        bankroll = round(bankroll + float(settlement["profit"]), 2)
        peak = max(peak, bankroll)
        drawdown = round(peak - bankroll, 2)
        drawdown_pct = round(drawdown / peak, 6) if peak else 0.0
        curve.append(
            {
                "bet": index,
                "bankroll": bankroll,
                "drawdown": drawdown,
                "drawdown_pct": drawdown_pct,
            }
        )
    return curve


def _empty_bucket() -> dict[str, Any]:
    return {
        "bets": 0,
        "wins": 0,
        "pushes": 0,
        "losses": 0,
        "stake": 0.0,
        "profit": 0.0,
        "roi": 0.0,
    }


def _add_to_bucket(bucket: dict[str, Any], settlement: dict[str, Any]) -> None:
    status = settlement["status"]
    bucket["bets"] += 1
    bucket["wins"] += 1 if status == "won" else 0
    bucket["pushes"] += 1 if status == "push" else 0
    bucket["losses"] += 1 if status == "lost" else 0
    bucket["stake"] = round(bucket["stake"] + float(settlement["stake"]), 2)
    bucket["profit"] = round(bucket["profit"] + float(settlement["profit"]), 2)
    bucket["roi"] = round(bucket["profit"] / bucket["stake"], 6) if bucket["stake"] else 0.0


def _market_family(market: str) -> str:
    if market in {"home_win", "draw", "away_win"}:
        return "1x2"
    if market.startswith("over_") or market.startswith("under_"):
        return "totals"
    if "_spread_" in market:
        return "spreads"
    return "other"


def _included(
    match: dict[str, Any],
    *,
    league: str | None,
    start_date: str | None,
    end_date: str | None,
) -> bool:
    if league and not _same(str(match["league"]), league):
        return False
    match_date = str(match["match_date"])
    if start_date and match_date < start_date:
        return False
    if end_date and match_date > end_date:
        return False
    return True


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
