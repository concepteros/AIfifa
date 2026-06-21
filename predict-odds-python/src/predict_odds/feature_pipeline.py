from __future__ import annotations

from typing import Any

from .data_sources import Fixture, InjuryRecord, MatchRecord
from .features import calculate_injury_impact, calculate_team_features


def build_match_features(
    *,
    fixture: Fixture,
    matches: list[MatchRecord],
    injuries: list[InjuryRecord],
    window: int = 5,
) -> dict[str, Any]:
    home_form = calculate_team_features(
        matches,
        team=fixture.home_team,
        league=fixture.league,
        before_date=fixture.date,
        window=window,
    )
    away_form = calculate_team_features(
        matches,
        team=fixture.away_team,
        league=fixture.league,
        before_date=fixture.date,
        window=window,
    )
    home_injuries = calculate_injury_impact(injuries, team=fixture.home_team)
    away_injuries = calculate_injury_impact(injuries, team=fixture.away_team)
    features = {
        "home_matches_used": home_form["matches_used"],
        "away_matches_used": away_form["matches_used"],
        "home_form_sequence": home_form["form_sequence"],
        "away_form_sequence": away_form["form_sequence"],
        "home_form_points_avg": home_form["form_points_avg"],
        "away_form_points_avg": away_form["form_points_avg"],
        "form_points_diff": round(home_form["form_points_avg"] - away_form["form_points_avg"], 6),
        "home_goal_diff_avg": home_form["goal_diff_avg"],
        "away_goal_diff_avg": away_form["goal_diff_avg"],
        "goal_diff_delta": round(home_form["goal_diff_avg"] - away_form["goal_diff_avg"], 6),
        "home_xg_for_avg": home_form["xg_for_avg"],
        "away_xg_for_avg": away_form["xg_for_avg"],
        "home_xga_avg": home_form["xga_avg"],
        "away_xga_avg": away_form["xga_avg"],
        "home_xg_diff_avg": home_form["xg_diff_avg"],
        "away_xg_diff_avg": away_form["xg_diff_avg"],
        "xg_diff_delta": round(home_form["xg_diff_avg"] - away_form["xg_diff_avg"], 6),
        "home_injured_players": home_injuries["injured_players"],
        "away_injured_players": away_injuries["injured_players"],
        "home_injury_value_eur": home_injuries["injury_value_eur"],
        "away_injury_value_eur": away_injuries["injury_value_eur"],
        "home_injury_impact": home_injuries["injury_impact"],
        "away_injury_impact": away_injuries["injury_impact"],
        "injury_impact_delta": round(home_injuries["injury_impact"] - away_injuries["injury_impact"], 6),
    }
    return {
        "league": fixture.league,
        "date": fixture.date,
        "match": {
            "home_team": fixture.home_team,
            "away_team": fixture.away_team,
        },
        "features": features,
    }
