"""
Predict.fun World Cup moneyline odds — direct search-based fetcher.

Replaces the broken PredictOddsClient path which uses the generic /v1/markets
endpoint that doesn't return properly structured football data.

Uses /v1/search (confirmed working) to find match markets by team names,
converts bestAsk prices (0.xx cents) to decimal odds (1/price).
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from .errors import PredictAPIError, PredictConfigError


BASE_URL = "https://api.predict.fun"
USER_AGENT = "predict-odds-bot/2.0"


def _get_api_key() -> str:
    key = os.getenv("PREDICTFUN_API_KEY", "") or os.getenv("PREDICT_API_KEY", "")
    if not key:
        raise PredictConfigError("PREDICTFUN_API_KEY not set")
    return key


def _request_get(path: str) -> dict[str, Any]:
    url = f"{BASE_URL}{path}"
    h = {
        "x-api-key": _get_api_key(),
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }
    req = Request(url, headers=h)
    try:
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        body = e.read().decode()
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {"error": str(e), "body": body[:500]}


def fetch_predict_fun_moneyline(
    match_slug: str,
    home_team: str,
    away_team: str,
    commence_time: str = "",
) -> dict[str, Any] | None:
    """Fetch moneyline odds for a match from Predict.fun.

    Args:
        match_slug: e.g. 'fifwc-tun-jpn-2026-06-21'
        home_team: e.g. 'Tunisia'
        away_team: e.g. 'Japan'
        commence_time: ISO timestamp

    Returns:
        Normalized event dict with markets {home_win, away_win, draw} as decimal odds,
        or None if no markets found.
    """
    # Always search by team names (country codes often match esports, not football)
    query = f"{home_team} {away_team}"

    data = _request_get(f"/v1/search?query={query.replace(' ', '%20')}")
    categories = data.get("data", {}).get("categories", [])

    markets_dict: dict[str, float] = {}

    for cat in categories:
        cat_slug = cat.get("slug", "")
        # Only match the base slug (no -exact-score, -more-markets suffixes)
        if cat_slug != match_slug:
            continue

        for market in cat.get("markets", []):
            question = str(market.get("question", "")).lower()
            outcomes = market.get("outcomes", [])

            for outcome in outcomes:
                name = str(outcome.get("name", "")).strip().lower()
                if name != "yes":
                    continue

                # bestAsk = price to BUY Yes
                best_ask = outcome.get("bestAsk", {})
                if isinstance(best_ask, dict):
                    price = best_ask.get("price")
                else:
                    price = best_ask

                if price is None:
                    continue

                try:
                    price_f = float(price)
                except (TypeError, ValueError):
                    continue

                if price_f <= 0 or price_f >= 1:
                    continue

                # Convert probability price → decimal odds
                decimal_odds = round(1.0 / price_f, 6)

                # Map question to market name
                home_lower = home_team.lower()
                away_lower = away_team.lower()

                if "draw" in question:
                    markets_dict["draw"] = decimal_odds
                elif home_lower in question:
                    markets_dict["home_win"] = decimal_odds
                elif away_lower in question:
                    markets_dict["away_win"] = decimal_odds

    if not markets_dict:
        return None

    return {
        "event_id": f"predict_fun:{match_slug}",
        "home_team": home_team,
        "away_team": away_team,
        "commence_time": commence_time,
        "markets": markets_dict,
        "sources": ["predict_fun"],
    }


def fetch_predict_fun_odds_by_date(
    league: str,
    date: str,
    *,
    match_list: list[dict[str, str]] | None = None,
) -> list[dict[str, Any]]:
    """Fetch Predict.fun odds for all matches on a given date.

    Args:
        league: League name (for context)
        date: YYYY-MM-DD
        match_list: Optional list of {home_team, away_team, match_slug} dicts.
                    If None, searches broadly.

    Returns:
        List of normalized event dicts with moneyline odds.
    """
    if match_list is None:
        # Try config-provided match list first
        match_list = _get_match_list_from_config(league, date)
        if not match_list:
            # Fallback: use known World Cup 2026 schedule
            match_list = _get_known_world_cup_matches(date)

    events: list[dict[str, Any]] = []
    for m in match_list:
        try:
            event = fetch_predict_fun_moneyline(
                match_slug=m["match_slug"],
                home_team=m["home_team"],
                away_team=m["away_team"],
                commence_time=m.get("commence_time", ""),
            )
            if event:
                events.append(event)
        except Exception:
            continue

    return events


def _get_match_list_from_config(league: str, date: str) -> list[dict[str, str]]:
    """Try to get match list from bot-scan.json config."""
    try:
        import json
        from pathlib import Path
        config_path = Path("data/bot-scan.json")
        if config_path.exists():
            config = json.loads(config_path.read_text())
            matches = config.get("predict_fun_matches", [])
            if matches:
                return [
                    {"match_slug": m["slug"], "home_team": m["home"], "away_team": m["away"]}
                    for m in matches
                    if m.get("date") == date
                ]
    except Exception:
        pass
    return []


def _get_known_world_cup_matches(date: str) -> list[dict[str, str]]:
    """Return known World Cup 2026 group stage matches for a given date."""
    return [
        {"match_slug": slug, "home_team": home, "away_team": away}
        for match_date, slug, home, away in _WORLD_CUP_SCHEDULE
        if match_date == date
    ]


# World Cup 2026 Group Stage schedule (partial — key matches on Predict.fun)
# Format: (date, slug, home_team, away_team)
_WORLD_CUP_SCHEDULE: list[tuple[str, str, str, str]] = [
    # June 21, 2026
    ("2026-06-21", "fifwc-tun-jpn-2026-06-21", "Tunisia", "Japan"),
    ("2026-06-21", "fifwc-esp-ksa-2026-06-21", "Spain", "Saudi Arabia"),
    ("2026-06-21", "fifwc-bel-irn-2026-06-21", "Belgium", "Iran"),
    ("2026-06-21", "fifwc-ecu-cuw-2026-06-21", "Ecuador", "Curaçao"),
    ("2026-06-21", "fifwc-nzl-egy-2026-06-21", "New Zealand", "Egypt"),
    ("2026-06-21", "fifwc-por-uzb-2026-06-21", "Portugal", "Uzbekistan"),
    ("2026-06-21", "fifwc-cro-pan-2026-06-21", "Croatia", "Panama"),
    ("2026-06-21", "fifwc-swe-sui-2026-06-21", "Sweden", "Switzerland"),
    # June 22, 2026
    ("2026-06-22", "fifwc-arg-ira-2026-06-22", "Argentina", "Iran"),
    ("2026-06-22", "fifwc-bra-gha-2026-06-22", "Brazil", "Ghana"),
    ("2026-06-22", "fifwc-fra-mex-2026-06-22", "France", "Mexico"),
    ("2026-06-22", "fifwc-eng-col-2026-06-22", "England", "Colombia"),
    ("2026-06-22", "fifwc-ger-civ-2026-06-22", "Germany", "Ivory Coast"),
    ("2026-06-22", "fifwc-ned-sen-2026-06-22", "Netherlands", "Senegal"),
    # June 23, 2026
    ("2026-06-23", "fifwc-ita-uru-2026-06-23", "Italy", "Uruguay"),
    ("2026-06-23", "fifwc-usa-wal-2026-06-23", "USA", "Wales"),
    ("2026-06-23", "fifwc-mar-crc-2026-06-23", "Morocco", "Costa Rica"),
    ("2026-06-23", "fifwc-kor-rsa-2026-06-23", "South Korea", "South Africa"),
    # June 24, 2026
    ("2026-06-24", "fifwc-can-qat-2026-06-24", "Canada", "Qatar"),
    ("2026-06-24", "fifwc-den-rou-2026-06-24", "Denmark", "Romania"),
    ("2026-06-24", "fifwc-sen-nor-2026-06-24", "Senegal", "Norway"),
    # June 25, 2026
    ("2026-06-25", "fifwc-tun-nld-2026-06-25", "Tunisia", "Netherlands"),
    ("2026-06-25", "fifwc-jpn-swe-2026-06-25", "Japan", "Sweden"),
    ("2026-06-25", "fifwc-ecu-ger-2026-06-25", "Ecuador", "Germany"),
    # June 26, 2026
    ("2026-06-26", "fifwc-esp-ury-2026-06-26", "Spain", "Uruguay"),
    ("2026-06-26", "fifwc-ksa-cvi-2026-06-26", "Saudi Arabia", "Cape Verde"),
    ("2026-06-26", "fifwc-bel-nzl-2026-06-26", "Belgium", "New Zealand"),
    ("2026-06-26", "fifwc-irn-egy-2026-06-26", "Iran", "Egypt"),
]


def _extract_teams_from_slug(slug: str) -> tuple[str, str] | None:
    """Extract team display names from slug like 'fifwc-tun-jpn-2026-06-21'.

    Returns (home_team, away_team) or None.
    """
    parts = slug.split("-")
    codes = [p.upper() for p in parts if len(p) == 3 and p.isalpha()]
    if len(codes) < 2:
        return None

    home = _FIFA_CODE_TO_NAME.get(codes[0], codes[0].title())
    away = _FIFA_CODE_TO_NAME.get(codes[1], codes[1].title())
    return (home, away)


# FIFA 3-letter country codes → display names (World Cup 2026 qualifiers)
_FIFA_CODE_TO_NAME: dict[str, str] = {
    "ARG": "Argentina", "AUS": "Australia", "BEL": "Belgium",
    "BRA": "Brazil", "CAN": "Canada", "CPV": "Cape Verde",
    "CHI": "Chile", "COL": "Colombia", "CRC": "Costa Rica",
    "CRO": "Croatia", "CUW": "Curaçao", "DEN": "Denmark",
    "ECU": "Ecuador", "EGY": "Egypt", "ENG": "England",
    "FRA": "France", "GER": "Germany", "GHA": "Ghana",
    "GRE": "Greece", "IRN": "Iran", "IRQ": "Iraq",
    "ITA": "Italy", "CIV": "Ivory Coast", "JAM": "Jamaica",
    "JPN": "Japan", "JOR": "Jordan", "KSA": "Saudi Arabia",
    "KOR": "South Korea", "MEX": "Mexico", "MAR": "Morocco",
    "NED": "Netherlands", "NZL": "New Zealand", "NGA": "Nigeria",
    "NOR": "Norway", "PAN": "Panama", "PAR": "Paraguay",
    "POR": "Portugal", "QAT": "Qatar", "ROU": "Romania",
    "RUS": "Russia", "SEN": "Senegal", "SRB": "Serbia",
    "RSA": "South Africa", "ESP": "Spain", "SWE": "Sweden",
    "SUI": "Switzerland", "TUN": "Tunisia", "TUR": "Turkey",
    "UKR": "Ukraine", "UAE": "United Arab Emirates", "USA": "USA",
    "URU": "Uruguay", "UZB": "Uzbekistan", "VEN": "Venezuela",
    "WAL": "Wales", "ZAM": "Zambia",
}
