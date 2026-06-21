from __future__ import annotations

from collections.abc import Callable, Mapping
import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .errors import PredictAuthenticationError, PredictConfigError, PredictHTTPError, PredictResponseError

DEFAULT_SPORTMONKS_API_URL = "https://api.sportmonks.com"
DEFAULT_SPORTMONKS_INCLUDES = "participants;scores;venue;state;events;statistics;lineups;league"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
)
Transport = Callable[[str, Mapping[str, str], float], tuple[int, str]]


class SportmonksClient:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = DEFAULT_SPORTMONKS_API_URL,
        timeout: float = 10.0,
        transport: Transport | None = None,
    ) -> None:
        if not api_key or not api_key.strip():
            raise PredictConfigError("SPORTMONKS_API_KEY is required.")
        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._transport = transport or _urlopen_transport

    @classmethod
    def from_env(cls, *, transport: Transport | None = None) -> "SportmonksClient":
        return cls(
            api_key=os.environ.get("SPORTMONKS_API_KEY", ""),
            base_url=os.environ.get("SPORTMONKS_API_URL", DEFAULT_SPORTMONKS_API_URL),
            transport=transport,
        )

    def get_fixture(self, fixture_id: int | str, *, includes: str = DEFAULT_SPORTMONKS_INCLUDES) -> dict[str, Any]:
        fixture_id = int(fixture_id)
        status_code, body = self._request_fixture(fixture_id, includes=includes, auth_mode="query")
        if _is_cloudflare_denial(status_code, body):
            raise PredictHTTPError(status_code, "Sportmonks request was blocked by Cloudflare.", body)
        if status_code in {401, 403}:
            status_code, body = self._request_fixture(fixture_id, includes=includes, auth_mode="bearer")
        if _is_cloudflare_denial(status_code, body):
            raise PredictHTTPError(status_code, "Sportmonks request was blocked by Cloudflare.", body)
        if status_code in {401, 403}:
            raise PredictAuthenticationError("Sportmonks authentication failed.")
        if status_code < 200 or status_code >= 300:
            raise PredictHTTPError(status_code, f"Sportmonks returned HTTP {status_code}.", body)
        payload = _parse_json(body)
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, dict):
            message = payload.get("message") if isinstance(payload, dict) else None
            if isinstance(message, str) and message.strip():
                raise PredictResponseError(f"Sportmonks fixture response did not include data: {message.strip()}")
            raise PredictResponseError("Sportmonks fixture response must contain a data object.")
        return _normalize_fixture(data, includes=includes)

    def _request_fixture(self, fixture_id: int, *, includes: str, auth_mode: str) -> tuple[int, str]:
        query: dict[str, str] = {}
        headers = {"Accept": "application/json", "User-Agent": DEFAULT_USER_AGENT}
        if auth_mode == "query":
            query["api_token"] = self.api_key
        elif auth_mode == "bearer":
            headers["Authorization"] = f"Bearer {self.api_key}"
        else:
            raise ValueError(f"Unsupported Sportmonks auth mode: {auth_mode}")
        if includes:
            query["includes"] = includes
        url = f"{self.base_url}/v3/football/fixtures/{fixture_id}"
        if query:
            url = f"{url}?{urlencode(query)}"
        return self._transport(url, headers, self.timeout)


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
        raise PredictHTTPError(0, f"Could not reach Sportmonks: {exc.reason}") from exc
    except TimeoutError as exc:
        raise PredictHTTPError(0, "Sportmonks request timed out.") from exc


def _parse_json(body: str) -> Any:
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise PredictResponseError("Sportmonks returned invalid JSON.") from exc


def _is_cloudflare_denial(status_code: int, body: str) -> bool:
    if status_code != 403:
        return False
    lowered = body.casefold()
    return "cloudflare_error" in lowered or "error 1010" in lowered or "browser_signature_banned" in lowered


def _normalize_fixture(data: dict[str, Any], *, includes: str) -> dict[str, Any]:
    participants = _participants_by_location(data.get("participants"))
    return {
        "fixture_id": data.get("id"),
        "name": data.get("name"),
        "starting_at": data.get("starting_at"),
        "includes": includes,
        "league": _object_or_empty(data.get("league")),
        "venue": _object_or_empty(data.get("venue")),
        "state": _object_or_empty(data.get("state")),
        "participants": participants,
        "scores": _scores(data.get("scores"), participants),
        "events": _list_or_empty(data.get("events")),
        "statistics": _list_or_empty(data.get("statistics")),
        "lineups": _list_or_empty(data.get("lineups")),
        "raw": data,
    }


def _participants_by_location(value: Any) -> dict[str, Any]:
    result: dict[str, Any] = {}
    if not isinstance(value, list):
        return result
    for participant in value:
        if not isinstance(participant, dict):
            continue
        location = str(participant.get("meta", {}).get("location", "")).casefold()
        if location in {"home", "away"}:
            result[location] = participant
    return result


def _scores(value: Any, participants: dict[str, Any]) -> dict[str, Any]:
    result = {"home": None, "away": None, "raw": _list_or_empty(value)}
    if not isinstance(value, list):
        return result
    location_by_id = {
        participant.get("id"): location
        for location, participant in participants.items()
        if isinstance(participant, dict)
    }
    for score in value:
        if not isinstance(score, dict):
            continue
        location = location_by_id.get(score.get("participant_id"))
        goals = score.get("score", {}).get("goals") if isinstance(score.get("score"), dict) else None
        if location in {"home", "away"} and goals is not None:
            result[location] = goals
    return result


def _object_or_empty(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list_or_empty(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []
