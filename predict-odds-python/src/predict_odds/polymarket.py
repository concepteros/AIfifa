from __future__ import annotations

from collections.abc import Callable, Mapping
import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .errors import PredictHTTPError, PredictResponseError

DEFAULT_POLYMARKET_API_URL = "https://gamma-api.polymarket.com"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
)
Transport = Callable[[str, Mapping[str, str], float], tuple[int, str]]


class PolymarketClient:
    def __init__(
        self,
        *,
        base_url: str = DEFAULT_POLYMARKET_API_URL,
        timeout: float = 10.0,
        transport: Transport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._transport = transport or _urlopen_transport

    @classmethod
    def from_env(cls, *, transport: Transport | None = None) -> "PolymarketClient":
        return cls(
            base_url=os.environ.get("POLYMARKET_API_URL", DEFAULT_POLYMARKET_API_URL),
            transport=transport,
        )

    def get_markets(
        self,
        *,
        query: str | None = None,
        limit: int = 100,
        active: bool = True,
        closed: bool = False,
    ) -> list[dict[str, Any]]:
        query_params = {
            "limit": str(int(limit)),
            "active": _bool_token(active),
            "closed": _bool_token(closed),
        }
        if query:
            query_params["search"] = query
        url = f"{self.base_url}/markets?{urlencode(query_params)}"
        headers = {"Accept": "application/json", "User-Agent": DEFAULT_USER_AGENT}
        status_code, body = self._transport(url, headers, self.timeout)
        if status_code < 200 or status_code >= 300:
            raise PredictHTTPError(status_code, f"Polymarket returned HTTP {status_code}.", body)
        payload = _parse_json(body)
        if isinstance(payload, list):
            return [_ensure_market(item) for item in payload]
        if isinstance(payload, dict) and isinstance(payload.get("data"), list):
            return [_ensure_market(item) for item in payload["data"]]
        raise PredictResponseError("Polymarket response must be a list or a data list.")


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
        raise PredictHTTPError(0, f"Could not reach Polymarket: {exc.reason}") from exc
    except TimeoutError as exc:
        raise PredictHTTPError(0, "Polymarket request timed out.") from exc


def _parse_json(body: str) -> Any:
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise PredictResponseError("Polymarket returned invalid JSON.") from exc


def _ensure_market(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise PredictResponseError("Polymarket returned a non-object market.")
    return item


def _bool_token(value: bool) -> str:
    return "true" if value else "false"
