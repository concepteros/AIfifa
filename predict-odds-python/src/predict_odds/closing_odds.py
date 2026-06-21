from __future__ import annotations

from dataclasses import dataclass
import csv
import json
from pathlib import Path
from typing import Any

from .errors import PredictResponseError, PredictValidationError
from .results import MatchResult


@dataclass(frozen=True)
class ClosingOdds:
    date: str
    league: str
    home_team: str
    away_team: str
    market: str
    closing_odds: float


def load_closing_odds(path: str | Path) -> list[ClosingOdds]:
    rows = _load_rows(path)
    return [_closing_from_row(row) for row in rows]


def find_closing_odds(rows: list[ClosingOdds], result: MatchResult, market: str) -> float | None:
    for row in rows:
        if (
            _same(row.date, result.date)
            and _same(row.league, result.league)
            and _same(row.home_team, result.home_team)
            and _same(row.away_team, result.away_team)
            and _same(row.market, market)
        ):
            return row.closing_odds
    return None


def _load_rows(path: str | Path) -> list[dict[str, Any]]:
    file_path = Path(path)
    if not file_path.exists():
        raise PredictValidationError(f"Closing odds file does not exist: {file_path}")
    if file_path.suffix.casefold() == ".json":
        payload = json.loads(file_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            payload = payload.get("closing_odds", payload.get("data"))
        if not isinstance(payload, list) or not all(isinstance(row, dict) for row in payload):
            raise PredictResponseError("Closing odds JSON must contain a list of objects.")
        return payload
    with file_path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _closing_from_row(row: dict[str, Any]) -> ClosingOdds:
    return ClosingOdds(
        date=_required(row, "date", "Date"),
        league=_required(row, "league", "League"),
        home_team=_required(row, "home_team", "Home", "home"),
        away_team=_required(row, "away_team", "Away", "away"),
        market=_required(row, "market", "Market"),
        closing_odds=float(_required(row, "closing_odds", "closing", "Close")),
    )


def _required(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    raise PredictValidationError(f"Missing required closing odds column: {keys[0]}")


def _same(left: str, right: str) -> bool:
    return str(left).strip().casefold() == str(right).strip().casefold()
