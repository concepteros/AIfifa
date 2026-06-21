from __future__ import annotations

from typing import Any


def normalize_event_odds(event: dict[str, Any]) -> dict[str, Any]:
    home_team = str(event.get("home_team", ""))
    away_team = str(event.get("away_team", ""))
    markets: dict[str, float] = {}
    for bookmaker in event.get("bookmakers", []):
        for market in bookmaker.get("markets", []):
            market_key = market.get("key")
            for outcome in market.get("outcomes", []):
                key = _market_name(market_key, outcome, home_team, away_team)
                if key:
                    _set_best_price(markets, key, outcome.get("price"))
    return {
        "event_id": event.get("id"),
        "home_team": home_team,
        "away_team": away_team,
        "commence_time": event.get("commence_time"),
        "markets": markets,
    }


def _market_name(market_key: str, outcome: dict[str, Any], home_team: str, away_team: str) -> str | None:
    name = str(outcome.get("name", ""))
    if market_key == "h2h":
        if _same(name, home_team):
            return "home_win"
        if _same(name, away_team):
            return "away_win"
        if name.casefold() == "draw":
            return "draw"
    if market_key == "totals":
        side = name.casefold()
        point = _point_token(outcome.get("point"))
        if side == "over":
            return f"over_{point}"
        if side == "under":
            return f"under_{point}"
    if market_key == "spreads":
        side = None
        if _same(name, home_team):
            side = "home"
        if _same(name, away_team):
            side = "away"
        if side:
            return f"{side}_spread_{_point_token(outcome.get('point'))}"
    return None


def _set_best_price(markets: dict[str, float], key: str, price: Any) -> None:
    if price is None:
        return
    decimal_price = float(price)
    if key not in markets or decimal_price > markets[key]:
        markets[key] = decimal_price


def _point_token(point: Any) -> str:
    text = str(point).replace(".", "_").replace("-", "-")
    return text


def _same(left: str, right: str) -> bool:
    return left.strip().casefold() == right.strip().casefold()
