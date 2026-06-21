from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from typing import Any


@dataclass(frozen=True)
class Outcome:
    name: str
    odds: float | int | str | None = None
    line: float | int | str | None = None
    side: str | None = None


@dataclass(frozen=True)
class OddsMarket:
    market_id: str | None
    market_type: str
    match_id: str | None = None
    home_team: str | None = None
    away_team: str | None = None
    kickoff: str | None = None
    bookmaker: str | None = None
    outcomes: list[Outcome] = field(default_factory=list)


@dataclass(frozen=True)
class FootballOddsResponse:
    league: str
    date: str
    source: str
    fetched_at: str
    raw_count: int
    markets: dict[str, list[OddsMarket]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)
