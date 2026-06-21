from __future__ import annotations

from dataclasses import dataclass
import csv
import json
from pathlib import Path
from typing import Any

from .errors import PredictResponseError, PredictValidationError


@dataclass(frozen=True)
class MatchResult:
    date: str
    league: str
    home_team: str
    away_team: str
    home_goals: int
    away_goals: int

    @property
    def outcome(self) -> str:
        if self.home_goals > self.away_goals:
            return "home_win"
        if self.home_goals < self.away_goals:
            return "away_win"
        return "draw"


def load_results(path: str | Path) -> list[MatchResult]:
    rows = _load_rows(path)
    return [_result_from_row(row) for row in rows]


def _load_rows(path: str | Path) -> list[dict[str, Any]]:
    file_path = Path(path)
    if not file_path.exists():
        raise PredictValidationError(f"Results file does not exist: {file_path}")
    if file_path.suffix.casefold() == ".json":
        payload = json.loads(file_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            payload = payload.get("results", payload.get("data"))
        if not isinstance(payload, list) or not all(isinstance(row, dict) for row in payload):
            raise PredictResponseError("Results JSON must contain a list of objects.")
        return payload
    with file_path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _result_from_row(row: dict[str, Any]) -> MatchResult:
    return MatchResult(
        date=_required(row, "date", "Date"),
        league=_required(row, "league", "League"),
        home_team=_required(row, "home_team", "Home", "home"),
        away_team=_required(row, "away_team", "Away", "away"),
        home_goals=_to_int(_required(row, "home_goals", "HG", "home_score")),
        away_goals=_to_int(_required(row, "away_goals", "AG", "away_score")),
    )


def _required(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    raise PredictValidationError(f"Missing required result column: {keys[0]}")


def _to_int(value: str) -> int:
    return int(float(str(value).strip()))
