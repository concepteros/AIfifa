from __future__ import annotations

from statistics import mean
from typing import Any

from .data_sources import InjuryRecord, MatchRecord, injuries_for_team, recent_matches

POINTS_BY_RESULT = {"W": 3, "D": 1, "L": 0}
POSITION_WEIGHTS = {
    "goalkeeper": 1.1,
    "defender": 1.0,
    "midfielder": 1.05,
    "forward": 1.2,
}


def calculate_team_features(
    matches: list[MatchRecord],
    *,
    team: str,
    league: str,
    before_date: str,
    window: int = 5,
) -> dict[str, Any]:
    recent = recent_matches(matches, team=team, league=league, before_date=before_date, window=window)
    points = [_points(match.result) for match in recent]
    goal_diffs = [match.goals_for - match.goals_against for match in recent]
    xg_for = [match.xg for match in recent]
    xga = [match.xga for match in recent]
    xg_diffs = [match.xg - match.xga for match in recent]
    return {
        "matches_used": len(recent),
        "form_sequence": "".join(match.result.upper()[:1] for match in recent),
        "form_points_total": sum(points),
        "form_points_avg": _avg(points),
        "goal_diff_avg": _avg(goal_diffs),
        "xg_for_avg": _avg(xg_for),
        "xga_avg": _avg(xga),
        "xg_diff_avg": _avg(xg_diffs),
    }


def calculate_injury_impact(injuries: list[InjuryRecord], *, team: str) -> dict[str, Any]:
    unavailable = injuries_for_team(injuries, team=team)
    injury_value = sum(injury.market_value_eur for injury in unavailable)
    weighted_value = sum(_weighted_injury_value(injury) for injury in unavailable)
    return {
        "injured_players": len(unavailable),
        "injury_value_eur": injury_value,
        "injury_impact": round(min(weighted_value / 100_000_000, 1.0), 6),
    }


def _weighted_injury_value(injury: InjuryRecord) -> float:
    return injury.market_value_eur * _position_weight(injury.position) * _severity(injury.days_out)


def _position_weight(position: str) -> float:
    return POSITION_WEIGHTS.get(position.strip().casefold(), 1.0)


def _severity(days_out: int) -> float:
    if days_out <= 0:
        return 0.5
    return min(days_out / 30, 1.0)


def _points(result: str) -> int:
    return POINTS_BY_RESULT.get(result.strip().upper()[:1], 0)


def _avg(values: list[float | int]) -> float:
    if not values:
        return 0.0
    return round(float(mean(values)), 6)
