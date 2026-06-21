from __future__ import annotations

from collections.abc import Callable, Mapping
import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .errors import (
    PredictAuthenticationError,
    PredictConfigError,
    PredictHTTPError,
    PredictResponseError,
)

DEFAULT_THE_ODDS_API_URL = "https://api.the-odds-api.com"
Transport = Callable[[str, Mapping[str, str], float], tuple[int, str]]


class TheOddsAPIClient:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = DEFAULT_THE_ODDS_API_URL,
        timeout: float = 10.0,
        transport: Transport | None = None,
    ) -> None:
        if not api_key or not api_key.strip():
            raise PredictConfigError("THE_ODDS_API_KEY is required.")
        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._transport = transport or _urlopen_transport

    @classmethod
    def from_env(cls, *, transport: Transport | None = None) -> "TheOddsAPIClient":
        return cls(api_key=os.environ.get("THE_ODDS_API_KEY", ""), transport=transport)

    def get_odds(
        self,
        *,
        sport: str,
        regions: str,
        markets: list[str] | None = None,
        bookmakers: str | None = None,
        commence_time_from: str | None = None,
        commence_time_to: str | None = None,
    ) -> list[dict[str, Any]]:
        query: dict[str, str] = {
            "apiKey": self.api_key,
            "regions": regions,
            "markets": ",".join(markets or ["h2h"]),
            "oddsFormat": "decimal",
            "dateFormat": "iso",
        }
        if bookmakers:
            query["bookmakers"] = bookmakers
        if commence_time_from:
            query["commenceTimeFrom"] = commence_time_from
        if commence_time_to:
            query["commenceTimeTo"] = commence_time_to
        url = f"{self.base_url}/v4/sports/{sport}/odds/?{urlencode(query)}"
        status_code, body = self._transport(url, {"Accept": "application/json"}, self.timeout)
        if status_code in {401, 403}:
            raise PredictAuthenticationError("The Odds API authentication failed.")
        if status_code < 200 or status_code >= 300:
            raise PredictHTTPError(status_code, f"The Odds API returned HTTP {status_code}.", body)
        payload = _parse_json(body)
        if not isinstance(payload, list):
            raise PredictResponseError("The Odds API response must be a list.")
        return [_ensure_event(item) for item in payload]


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
        raise PredictHTTPError(0, f"Could not reach The Odds API: {exc.reason}") from exc
    except TimeoutError as exc:
        raise PredictHTTPError(0, "The Odds API request timed out.") from exc


def _parse_json(body: str) -> Any:
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise PredictResponseError("The Odds API returned invalid JSON.") from exc


def _ensure_event(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise PredictResponseError("The Odds API returned a non-object event.")
    return item
