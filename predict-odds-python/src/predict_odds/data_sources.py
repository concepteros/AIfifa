from __future__ import annotations

from dataclasses import dataclass
import csv
import json
from pathlib import Path
import re
from typing import Any

from .errors import PredictResponseError, PredictValidationError


@dataclass(frozen=True)
class MatchRecord:
    date: str
    league: str
    team: str
    opponent: str
    venue: str
    goals_for: int
    goals_against: int
    xg: float
    xga: float
    result: str


@dataclass(frozen=True)
class InjuryRecord:
    team: str
    player: str
    position: str
    market_value_eur: float
    status: str
    days_out: int


@dataclass(frozen=True)
class Fixture:
    league: str
    date: str
    home_team: str
    away_team: str


def load_matches(path: str | Path) -> list[MatchRecord]:
    rows = _load_rows(path)
    return [_match_from_row(row) for row in rows]


def load_injuries(path: str | Path) -> list[InjuryRecord]:
    rows = _load_rows(path)
    return [_injury_from_row(row) for row in rows]


def recent_matches(
    matches: list[MatchRecord],
    *,
    team: str,
    league: str,
    before_date: str,
    window: int,
) -> list[MatchRecord]:
    selected = [
        match
        for match in matches
        if _same(match.team, team) and _same(match.league, league) and match.date < before_date
    ]
    selected.sort(key=lambda match: match.date, reverse=True)
    return selected[:window]


def injuries_for_team(injuries: list[InjuryRecord], *, team: str) -> list[InjuryRecord]:
    return [injury for injury in injuries if _same(injury.team, team) and injury.status.casefold() not in {"available", "fit", "healthy"}]


def _load_rows(path: str | Path) -> list[dict[str, Any]]:
    file_path = Path(path)
    if not file_path.exists():
        raise PredictValidationError(f"Data file does not exist: {file_path}")
    if file_path.suffix.casefold() == ".json":
        payload = json.loads(file_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            for key in ("data", "rows", "matches", "injuries"):
                if isinstance(payload.get(key), list):
                    payload = payload[key]
                    break
        if not isinstance(payload, list) or not all(isinstance(row, dict) for row in payload):
            raise PredictResponseError("JSON data file must contain a list of objects.")
        return payload
    with file_path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _match_from_row(row: dict[str, Any]) -> MatchRecord:
    return MatchRecord(
        date=_required(row, "date", "Date"),
        league=_required(row, "league", "League", "comp"),
        team=_required(row, "team", "Team", "squad"),
        opponent=_required(row, "opponent", "Opponent"),
        venue=_optional(row, "venue", "Venue") or "neutral",
        goals_for=_to_int(_required(row, "goals_for", "GF", "gf")),
        goals_against=_to_int(_required(row, "goals_against", "GA", "ga")),
        xg=_to_float(_required(row, "xg", "xG")),
        xga=_to_float(_required(row, "xga", "xGA")),
        result=_required(row, "result", "Result"),
    )


def _injury_from_row(row: dict[str, Any]) -> InjuryRecord:
    return InjuryRecord(
        team=_required(row, "team", "Team", "club"),
        player=_required(row, "player", "Player", "name"),
        position=_required(row, "position", "Position"),
        market_value_eur=_to_float(_required(row, "market_value_eur", "market_value", "Market Value")),
        status=_required(row, "status", "Status"),
        days_out=_to_int(_optional(row, "days_out", "Days Out") or 0),
    )


def _required(row: dict[str, Any], *keys: str) -> str:
    value = _optional(row, *keys)
    if value is None:
        raise PredictValidationError(f"Missing required data column: {keys[0]}")
    return value


def _optional(row: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _to_int(value: str | int | float) -> int:
    return int(float(str(value).replace(",", "").strip()))


def _to_float(value: str | int | float) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    normalized = str(value).replace(",", "").strip().casefold()
    normalized = normalized.replace("€", "").replace("$", "").replace("£", "")
    match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)(bn|b|m|k)?", normalized)
    if not match:
        return float(normalized)
    number = float(match.group(1))
    suffix = match.group(2)
    if suffix in {"bn", "b"}:
        return number * 1_000_000_000
    if suffix == "m":
        return number * 1_000_000
    if suffix == "k":
        return number * 1_000
    return number


def _same(left: str, right: str) -> bool:
    return left.strip().casefold() == right.strip().casefold()
