from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, date as date_type, datetime
import json
import os
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .errors import (
    PredictAuthenticationError,
    PredictConfigError,
    PredictHTTPError,
    PredictResponseError,
    PredictValidationError,
)
from .models import FootballOddsResponse, OddsMarket, Outcome

DEFAULT_API_URL = "https://api.predict.fun/v1/markets"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
Transport = Callable[[str, Mapping[str, str], float], tuple[int, str]]


class PredictOddsClient:
    def __init__(
        self,
        *,
        api_key: str,
        api_url: str = DEFAULT_API_URL,
        timeout: float = 10.0,
        transport: Transport | None = None,
    ) -> None:
        if not api_key or not api_key.strip():
            raise PredictConfigError("PREDICT_API_KEY is required.")
        if not api_url or not api_url.startswith(("http://", "https://")):
            raise PredictConfigError("A valid Predict API URL is required.")
        self.api_key = api_key.strip()
        self.api_url = api_url.rstrip("?")
        self.timeout = timeout
        self._transport = transport or _urlopen_transport

    @classmethod
    def from_env(cls, *, transport: Transport | None = None) -> "PredictOddsClient":
        return cls(
            api_key=os.environ.get("PREDICT_API_KEY", ""),
            api_url=os.environ.get("PREDICT_API_URL", DEFAULT_API_URL),
            transport=transport,
        )

    def get_football_odds(self, *, league: str, date: str) -> FootballOddsResponse:
        league = _validate_league(league)
        date = _validate_date(date)
        url = self._build_url(league=league, date=date)
        status_code, body = self._request(url)
        payload = _parse_json(body)
        raw_markets = _extract_markets(payload)
        return FootballOddsResponse(
            league=league,
            date=date,
            source=self.api_url,
            fetched_at=datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            raw_count=len(raw_markets),
            markets=_group_markets(raw_markets),
        )

    def _build_url(self, *, league: str, date: str) -> str:
        separator = "&" if "?" in self.api_url else "?"
        query = urlencode({"sport": "football", "league": league, "date": date})
        return f"{self.api_url}{separator}{query}"

    def _request(self, url: str) -> tuple[int, str]:
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": DEFAULT_USER_AGENT,
            "X-API-Key": self.api_key,
        }
        status_code, body = self._transport(url, headers, self.timeout)
        if _is_cloudflare_denial(status_code, body):
            raise PredictHTTPError(status_code, "Predict API request was blocked by Cloudflare.", body)
        if status_code in {401, 403}:
            raise PredictAuthenticationError("Predict API authentication failed.")
        if status_code < 200 or status_code >= 300:
            raise PredictHTTPError(status_code, f"Predict API returned HTTP {status_code}.", body)
        return status_code, body


def _urlopen_transport(url: str, headers: Mapping[str, str], timeout: float) -> tuple[int, str]:
    request = Request(url, headers=dict(headers), method="GET")
    try:
        with urlopen(request, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.status, response.read().decode(charset)
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return exc.code, body
    except URLError as exc:
        raise PredictHTTPError(0, f"Could not reach Predict API: {exc.reason}") from exc
    except TimeoutError as exc:
        raise PredictHTTPError(0, "Predict API request timed out.") from exc


def _validate_league(league: str) -> str:
    normalized = (league or "").strip()
    if not normalized:
        raise PredictValidationError("league is required.")
    return normalized


def _validate_date(value: str) -> str:
    normalized = (value or "").strip()
    if not DATE_RE.match(normalized):
        raise PredictValidationError("date must use YYYY-MM-DD format.")
    try:
        date_type.fromisoformat(normalized)
    except ValueError as exc:
        raise PredictValidationError("date must be a valid calendar date.") from exc
    return normalized


def _parse_json(body: str) -> Any:
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise PredictResponseError("Predict API returned invalid JSON.") from exc


def _is_cloudflare_denial(status_code: int, body: str) -> bool:
    if status_code != 403:
        return False
    lowered = body.casefold()
    return "cloudflare_error" in lowered or "error 1010" in lowered or "browser_signature_banned" in lowered


def _extract_markets(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [_ensure_market(item) for item in payload]
    if isinstance(payload, dict):
        for key in ("markets", "data", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return [_ensure_market(item) for item in value]
    raise PredictResponseError("Predict API response did not include a markets list.")


def _ensure_market(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise PredictResponseError("Predict API returned a non-object market item.")
    return item


def _group_markets(raw_markets: list[dict[str, Any]]) -> dict[str, list[OddsMarket]]:
    grouped: dict[str, list[OddsMarket]] = {
        "win_draw_win": [],
        "handicap": [],
        "totals": [],
        "other": [],
    }
    for raw_market in raw_markets:
        category = _market_category(raw_market)
        grouped[category].append(_normalize_market(raw_market, category))
    return grouped


def _market_category(raw_market: dict[str, Any]) -> str:
    text = " ".join(
        str(raw_market.get(key, ""))
        for key in ("market_type", "type", "name", "label", "category")
    ).casefold()
    if any(token in text for token in ("1x2", "moneyline", "match winner", "win draw win", "胜平负")):
        return "win_draw_win"
    if any(token in text for token in ("handicap", "spread", "asian handicap", "让球")):
        return "handicap"
    if any(token in text for token in ("total", "over/under", "over under", "大小球")):
        return "totals"
    return "other"


def _normalize_market(raw_market: dict[str, Any], category: str) -> OddsMarket:
    match = raw_market.get("match") if isinstance(raw_market.get("match"), dict) else {}
    teams = raw_market.get("teams") if isinstance(raw_market.get("teams"), dict) else {}
    return OddsMarket(
        market_id=_string_or_none(raw_market, "id", "market_id"),
        market_type=category,
        match_id=_string_or_none(raw_market, "match_id") or _string_or_none(match, "id"),
        home_team=_string_or_none(raw_market, "home_team", "home") or _string_or_none(match, "home_team", "home") or _string_or_none(teams, "home"),
        away_team=_string_or_none(raw_market, "away_team", "away") or _string_or_none(match, "away_team", "away") or _string_or_none(teams, "away"),
        kickoff=_string_or_none(raw_market, "kickoff", "start_time", "commence_time") or _string_or_none(match, "kickoff", "start_time"),
        bookmaker=_string_or_none(raw_market, "bookmaker", "exchange", "provider"),
        outcomes=_normalize_outcomes(raw_market),
    )


def _normalize_outcomes(raw_market: dict[str, Any]) -> list[Outcome]:
    raw_outcomes = raw_market.get("outcomes") or raw_market.get("prices") or raw_market.get("odds")
    if isinstance(raw_outcomes, dict):
        raw_outcomes = [
            {"name": name, "odds": odds}
            for name, odds in raw_outcomes.items()
        ]
    if not isinstance(raw_outcomes, list):
        return []
    outcomes = []
    for raw_outcome in raw_outcomes:
        if isinstance(raw_outcome, dict):
            outcomes.append(
                Outcome(
                    name=str(_first_present(raw_outcome, "name", "label", "side") or ""),
                    odds=_first_present(raw_outcome, "odds", "price", "decimal"),
                    line=_first_present(raw_outcome, "line", "point", "handicap"),
                    side=_optional_string(raw_outcome.get("side")),
                )
            )
        else:
            outcomes.append(Outcome(name=str(raw_outcome)))
    return outcomes


def _string_or_none(source: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = source.get(key)
        if value is not None and str(value).strip():
            return str(value)
    return None


def _first_present(source: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in source and source[key] is not None:
            return source[key]
    return None


def _optional_string(value: Any) -> str | None:
    if value is None or not str(value).strip():
        return None
    return str(value)
