from __future__ import annotations

from math import exp, factorial
from typing import Any

MAX_GOALS = 6
MODEL_NAME = "poisson_v1"


def predict_match(feature_payload: dict[str, Any], *, max_goals: int = MAX_GOALS) -> dict[str, Any]:
    features = feature_payload.get("features", {})
    home_lambda = _estimate_home_goals(features)
    away_lambda = _estimate_away_goals(features)
    score_rows = _score_probabilities(home_lambda, away_lambda, max_goals=max_goals)
    probabilities = _aggregate_probabilities(score_rows)
    return {
        "model": MODEL_NAME,
        "league": feature_payload.get("league"),
        "date": feature_payload.get("date"),
        "match": feature_payload.get("match", {}),
        "expected_goals": {
            "home": round(home_lambda, 3),
            "away": round(away_lambda, 3),
        },
        "probabilities": probabilities,
        "most_likely_scores": _most_likely_scores(score_rows),
        "reasoning": _reasoning(features),
    }


def _estimate_home_goals(features: dict[str, Any]) -> float:
    base = _blend(_num(features, "home_xg_for_avg", 1.35), _num(features, "away_xga_avg", 1.35))
    modifier = (
        1
        + 0.04 * _num(features, "form_points_diff", 0)
        + 0.08 * _num(features, "xg_diff_delta", 0)
        - 0.18 * _num(features, "home_injury_impact", 0)
        + 0.12 * _num(features, "away_injury_impact", 0)
    )
    return _clamp(base * modifier, 0.2, 4.5)


def _estimate_away_goals(features: dict[str, Any]) -> float:
    base = _blend(_num(features, "away_xg_for_avg", 1.15), _num(features, "home_xga_avg", 1.15))
    modifier = (
        1
        - 0.04 * _num(features, "form_points_diff", 0)
        - 0.08 * _num(features, "xg_diff_delta", 0)
        - 0.18 * _num(features, "away_injury_impact", 0)
        + 0.12 * _num(features, "home_injury_impact", 0)
    )
    return _clamp(base * modifier, 0.2, 4.5)


def _score_probabilities(home_lambda: float, away_lambda: float, *, max_goals: int) -> list[dict[str, Any]]:
    rows = []
    total = 0.0
    for home_goals in range(max_goals + 1):
        for away_goals in range(max_goals + 1):
            probability = _poisson(home_goals, home_lambda) * _poisson(away_goals, away_lambda)
            total += probability
            rows.append({
                "home_goals": home_goals,
                "away_goals": away_goals,
                "probability": probability,
            })
    for row in rows:
        row["probability"] = row["probability"] / total
    return rows


def _aggregate_probabilities(score_rows: list[dict[str, Any]]) -> dict[str, float]:
    home_win = sum(row["probability"] for row in score_rows if row["home_goals"] > row["away_goals"])
    draw = sum(row["probability"] for row in score_rows if row["home_goals"] == row["away_goals"])
    away_win = sum(row["probability"] for row in score_rows if row["home_goals"] < row["away_goals"])
    over_2_5 = sum(row["probability"] for row in score_rows if row["home_goals"] + row["away_goals"] > 2.5)
    btts_yes = sum(row["probability"] for row in score_rows if row["home_goals"] > 0 and row["away_goals"] > 0)
    return {
        "home_win": _round(home_win),
        "draw": _round(draw),
        "away_win": _round(away_win),
        "over_2_5": _round(over_2_5),
        "under_2_5": _round(1 - over_2_5),
        "btts_yes": _round(btts_yes),
        "btts_no": _round(1 - btts_yes),
    }


def _most_likely_scores(score_rows: list[dict[str, Any]], *, limit: int = 5) -> list[dict[str, Any]]:
    ordered = sorted(score_rows, key=lambda row: row["probability"], reverse=True)
    return [
        {
            "score": f"{row['home_goals']}-{row['away_goals']}",
            "probability": _round(row["probability"]),
        }
        for row in ordered[:limit]
    ]


def _reasoning(features: dict[str, Any]) -> list[str]:
    reasons = []
    form_delta = _num(features, "form_points_diff", 0)
    xg_delta = _num(features, "xg_diff_delta", 0)
    injury_delta = _num(features, "injury_impact_delta", 0)
    if abs(form_delta) >= 0.25:
        side = "Home" if form_delta > 0 else "Away"
        reasons.append(f"{side} team has stronger recent form.")
    if abs(xg_delta) >= 0.2:
        side = "Home" if xg_delta > 0 else "Away"
        reasons.append(f"{side} team has the stronger recent xG differential.")
    if abs(injury_delta) >= 0.05:
        side = "Home" if injury_delta > 0 else "Away"
        reasons.append(f"{side} team has the higher injury impact.")
    if not reasons:
        reasons.append("Teams look closely matched across form, xG, and injury signals.")
    return reasons


def _poisson(k: int, rate: float) -> float:
    return exp(-rate) * rate**k / factorial(k)


def _blend(attack: float, defensive_concession: float) -> float:
    return 0.6 * attack + 0.4 * defensive_concession


def _num(features: dict[str, Any], key: str, default: float) -> float:
    value = features.get(key, default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(value, upper))


def _round(value: float) -> float:
    return round(value, 6)
