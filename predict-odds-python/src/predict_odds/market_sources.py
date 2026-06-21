from __future__ import annotations

import json
from typing import Any

from .client import PredictOddsClient
from .errors import PredictAPIError
from .models import FootballOddsResponse, OddsMarket, Outcome
from .odds_normalizer import normalize_event_odds
from .polymarket import PolymarketClient
from .the_odds_api import TheOddsAPIClient


DEFAULT_ODDS_SOURCES = ["the_odds_api", "predict_fun", "polymarket"]


def fetch_market_events(config: dict[str, Any], *, clients: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    clients = clients or {}
    scan = config["scan"]
    sources = config.get("odds_sources") or scan.get("odds_sources") or DEFAULT_ODDS_SOURCES
    events: list[dict[str, Any]] = []
    errors: list[str] = []
    for source in sources:
        try:
            events.extend(_fetch_source(str(source), config, clients))
        except Exception as exc:
            errors.append(f"{source}: {type(exc).__name__}: {exc}")
    if events:
        return merge_normalized_events(events)
    if errors:
        raise PredictAPIError("All odds sources failed: " + "; ".join(errors))
    return []


def _fetch_source(source: str, config: dict[str, Any], clients: dict[str, Any]) -> list[dict[str, Any]]:
    scan = config["scan"]
    if source == "the_odds_api":
        client = clients.get(source) or TheOddsAPIClient.from_env()
        return normalize_the_odds_api_events(
            client.get_odds(
                sport=scan["sport"],
                regions=scan["regions"],
                markets=scan.get("markets", ["h2h"]),
                bookmakers=scan.get("bookmakers"),
                commence_time_from=scan.get("commence_time_from"),
                commence_time_to=scan.get("commence_time_to"),
            )
        )
    if source == "predict_fun":
        client = clients.get(source) or PredictOddsClient.from_env()
        return predict_fun_response_to_events(client.get_football_odds(league=scan["league"], date=scan["date"]))
    if source == "polymarket":
        client = clients.get(source) or PolymarketClient.from_env()
        options = config.get("polymarket", {})
        query = options.get("query") or f"{scan['league']} {scan['date']}"
        return normalize_polymarket_markets(
            client.get_markets(
                query=query,
                limit=int(options.get("limit", 100)),
                active=bool(options.get("active", True)),
                closed=bool(options.get("closed", False)),
            )
        )
    raise PredictAPIError(f"Unsupported odds source: {source}")


def merge_normalized_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], dict[str, Any]] = {}
    for event in events:
        home_team = str(event.get("home_team", "")).strip()
        away_team = str(event.get("away_team", "")).strip()
        commence_time = str(event.get("commence_time") or "")
        key = (home_team.casefold(), away_team.casefold(), commence_time)
        merged = grouped.setdefault(
            key,
            {
                "event_ids": [],
                "home_team": home_team,
                "away_team": away_team,
                "commence_time": commence_time,
                "markets": {},
                "sources": [],
            },
        )
        if event.get("event_id"):
            merged["event_ids"].append(str(event["event_id"]))
        for source in event.get("sources", []):
            if source not in merged["sources"]:
                merged["sources"].append(source)
        for market, price in event.get("markets", {}).items():
            _set_best_price(merged["markets"], market, price)
    return [_finalize_event(event) for event in grouped.values()]


def predict_fun_response_to_events(response: FootballOddsResponse) -> list[dict[str, Any]]:
    events: dict[tuple[str, str, str], dict[str, Any]] = {}
    for market_group in response.markets.values():
        for market in market_group:
            home_team = market.home_team or ""
            away_team = market.away_team or ""
            kickoff = market.kickoff or ""
            key = (home_team.casefold(), away_team.casefold(), kickoff)
            event = events.setdefault(
                key,
                {
                    "event_id": f"predict_fun:{market.match_id or market.market_id or len(events) + 1}",
                    "home_team": home_team,
                    "away_team": away_team,
                    "commence_time": kickoff,
                    "markets": {},
                    "sources": ["predict_fun"],
                },
            )
            for outcome in market.outcomes:
                name = _predict_fun_market_name(market, outcome)
                if name:
                    _set_best_price(event["markets"], name, outcome.odds)
    return [event for event in events.values() if event["home_team"] and event["away_team"] and event["markets"]]


def normalize_polymarket_markets(markets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    events = []
    for market in markets:
        home_team = _string_or_none(market, "home_team", "home")
        away_team = _string_or_none(market, "away_team", "away")
        if not home_team or not away_team:
            teams = market.get("teams") if isinstance(market.get("teams"), dict) else {}
            home_team = home_team or _string_or_none(teams, "home")
            away_team = away_team or _string_or_none(teams, "away")
        if not home_team or not away_team:
            continue
        outcomes = _as_list(market.get("outcomes"))
        prices = _as_list(market.get("outcomePrices") or market.get("outcome_prices") or market.get("prices"))
        normalized = {
            "event_id": f"polymarket:{market.get('id') or market.get('conditionId') or market.get('slug')}",
            "home_team": home_team,
            "away_team": away_team,
            "commence_time": _string_or_none(market, "commence_time", "endDate", "end_date", "start_time"),
            "markets": {},
            "sources": ["polymarket"],
        }
        for index, outcome in enumerate(outcomes):
            probability = prices[index] if index < len(prices) else None
            name = _polymarket_market_name(str(outcome), home_team, away_team)
            odds = _probability_to_decimal(probability)
            if name and odds:
                _set_best_price(normalized["markets"], name, odds)
        if normalized["markets"]:
            events.append(normalized)
    return events


def normalize_the_odds_api_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for event in events:
        item = normalize_event_odds(event)
        item["sources"] = ["the_odds_api"]
        normalized.append(item)
    return normalized


def _finalize_event(event: dict[str, Any]) -> dict[str, Any]:
    event_ids = event.pop("event_ids", [])
    event["event_id"] = "+".join(event_ids) if event_ids else None
    return event


def _predict_fun_market_name(market: OddsMarket, outcome: Outcome) -> str | None:
    outcome_name = outcome.name.strip()
    if market.market_type == "win_draw_win":
        if _same(outcome_name, market.home_team or "") or outcome_name.casefold() == "home":
            return "home_win"
        if _same(outcome_name, market.away_team or "") or outcome_name.casefold() == "away":
            return "away_win"
        if outcome_name.casefold() == "draw":
            return "draw"
    if market.market_type == "totals":
        side = outcome.side or outcome_name
        line = _point_token(outcome.line)
        if side.casefold() == "over":
            return f"over_{line}"
        if side.casefold() == "under":
            return f"under_{line}"
    if market.market_type == "handicap":
        side = outcome.side or outcome_name
        if _same(side, market.home_team or "") or side.casefold() == "home":
            return f"home_spread_{_point_token(outcome.line)}"
        if _same(side, market.away_team or "") or side.casefold() == "away":
            return f"away_spread_{_point_token(outcome.line)}"
    return None


def _polymarket_market_name(outcome_name: str, home_team: str, away_team: str) -> str | None:
    if _same(outcome_name, home_team) or outcome_name.casefold() in {"home", "yes"}:
        return "home_win"
    if _same(outcome_name, away_team) or outcome_name.casefold() == "away":
        return "away_win"
    if outcome_name.casefold() == "draw":
        return "draw"
    return None


def _probability_to_decimal(value: Any) -> float | None:
    try:
        probability = float(value)
    except (TypeError, ValueError):
        return None
    if probability <= 0:
        return None
    return round(1 / probability, 6)


def _set_best_price(markets: dict[str, float], key: str, price: Any) -> None:
    try:
        decimal_price = float(price)
    except (TypeError, ValueError):
        return
    if decimal_price <= 1:
        return
    if key not in markets or decimal_price > markets[key]:
        markets[key] = round(decimal_price, 6)


def _point_token(point: Any) -> str:
    return str(point).replace(".", "_")


def _same(left: str, right: str) -> bool:
    return left.strip().casefold() == right.strip().casefold()


def _string_or_none(source: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = source.get(key)
        if value is not None and str(value).strip():
            return str(value)
    return None


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        return parsed if isinstance(parsed, list) else []
    return value if isinstance(value, list) else []
