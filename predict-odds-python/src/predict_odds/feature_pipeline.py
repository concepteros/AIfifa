from __future__ import annotations

from typing import Any

from .data_sources import Fixture, InjuryRecord, MatchRecord
from .features import calculate_injury_impact, calculate_team_features
from .supplementary import DEFAULT_REFEREE, RefereeProfile, get_match_referee_profile


def build_match_features(
    *,
    fixture: Fixture,
    matches: list[MatchRecord],
    injuries: list[InjuryRecord],
    window: int = 5,
    referee_profile: RefereeProfile | None = None,
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

    # Auto-assign referee if not provided
    if referee_profile is None:
        referee_profile = get_match_referee_profile(fixture.home_team, fixture.away_team)

    # Fallback to tier-based estimates when a team has 0 real matches
    # This prevents all-features-zero when teams haven't played yet
    from .data_enrichment import TEAM_TIERS
    h_tier = TEAM_TIERS.get(fixture.home_team, {}).get('tier', 3)
    a_tier = TEAM_TIERS.get(fixture.away_team, {}).get('tier', 3)
    
    _TIER_XG_MAP = {1: 2.0, 2: 1.4, 3: 0.9, 4: 0.5}
    _TIER_XGA_MAP = {1: 0.7, 2: 1.0, 3: 1.3, 4: 1.8}
    _TIER_FORM_MAP = {1: 2.2, 2: 1.6, 3: 1.0, 4: 0.4}
    
    if home_form["matches_used"] == 0:
        home_form["matches_used"] = 1
        home_form["xg_for_avg"] = _TIER_XG_MAP.get(h_tier, 0.9)
        home_form["xga_avg"] = _TIER_XGA_MAP.get(h_tier, 1.3)
        home_form["xg_diff_avg"] = home_form["xg_for_avg"] - home_form["xga_avg"]
        home_form["goal_diff_avg"] = (h_tier - a_tier) * 0.3
        home_form["form_points_avg"] = _TIER_FORM_MAP.get(h_tier, 1.0)
        home_form["form_sequence"] = "?" * min(5, h_tier)
    if away_form["matches_used"] == 0:
        away_form["matches_used"] = 1
        away_form["xg_for_avg"] = _TIER_XG_MAP.get(a_tier, 0.9)
        away_form["xga_avg"] = _TIER_XGA_MAP.get(a_tier, 1.3)
        away_form["xg_diff_avg"] = away_form["xg_for_avg"] - away_form["xga_avg"]
        away_form["goal_diff_avg"] = (a_tier - h_tier) * 0.3
        away_form["form_points_avg"] = _TIER_FORM_MAP.get(a_tier, 1.0)
        away_form["form_sequence"] = "?" * min(5, a_tier)
    
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
        # Referee features
        "referee_name": referee_profile.name,
        "referee_strictness": referee_profile.strictness,
        "referee_card_tendency": referee_profile.card_tendency,
        "referee_home_bias": referee_profile.home_bias,
        "referee_var_usage": referee_profile.var_usage,
        "referee_avg_yellows": referee_profile.avg_yellows,
        "referee_avg_reds": referee_profile.avg_reds,
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
