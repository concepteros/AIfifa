from __future__ import annotations

from math import exp, factorial, sqrt
from typing import Any

MAX_GOALS = 6
MODEL_NAME = "poisson_v2"
DEFAULT_MARKET_WEIGHT = 0.90
# Grid-search resolution & range for market-implied λ calibration
_LAMBDA_STEP = 0.05
_LAMBDA_MIN = 0.02
_LAMBDA_MAX = 5.00


def predict_match(
    feature_payload: dict[str, Any],
    *,
    max_goals: int = MAX_GOALS,
    odds: dict[str, float] | None = None,
    market_weight: float = DEFAULT_MARKET_WEIGHT,
) -> dict[str, Any]:
    features = feature_payload.get("features", feature_payload)
    data_home = _estimate_home_goals(features)
    data_away = _estimate_away_goals(features)
    source_labels = ["data"]
    if odds:
        market_home, market_away = _market_implied_lambdas(odds, max_goals=max_goals)
        home_lambda = market_weight * market_home + (1 - market_weight) * data_home
        away_lambda = market_weight * market_away + (1 - market_weight) * data_away
        # Cap data influence: final λ must stay within ±20% of market λ
        home_lambda = max(market_home * 0.8, min(home_lambda, market_home * 1.2))
        away_lambda = max(market_away * 0.8, min(away_lambda, market_away * 1.2))
        source_labels = ["market", "data"]
    else:
        home_lambda = data_home
        away_lambda = data_away
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
        "expected_goals_sources": source_labels,
        "probabilities": probabilities,
        "most_likely_scores": _most_likely_scores(score_rows),
        "reasoning": _reasoning(features),
    }


def _estimate_home_goals(features: dict[str, Any]) -> float:
    base = _blend(_num(features, "home_xg_for_avg", 1.35), _num(features, "away_xga_avg", 1.35))
    ref_mod = _referee_modifier(features, is_home=True)
    modifier = (
        1
        + 0.04 * _num(features, "form_points_diff", 0)
        + 0.08 * _num(features, "xg_diff_delta", 0)
        - 0.18 * _num(features, "home_injury_impact", 0)
        + 0.12 * _num(features, "away_injury_impact", 0)
    )
    return _clamp(base * modifier * ref_mod, 0.2, 4.5)


def _estimate_away_goals(features: dict[str, Any]) -> float:
    base = _blend(_num(features, "away_xg_for_avg", 1.15), _num(features, "home_xga_avg", 1.15))
    ref_mod = _referee_modifier(features, is_home=False)
    modifier = (
        1
        - 0.04 * _num(features, "form_points_diff", 0)
        - 0.08 * _num(features, "xg_diff_delta", 0)
        - 0.18 * _num(features, "away_injury_impact", 0)
        + 0.12 * _num(features, "home_injury_impact", 0)
    )
    return _clamp(base * modifier * ref_mod, 0.2, 4.5)


def _referee_modifier(features: dict[str, Any], *, is_home: bool) -> float:
    """Compute a referee-driven multiplier on goal expectancy.

    Factors:
      - strictness > 0.60 → more whistle, less flow → fewer goals
      - card_tendency > 0.50 → more cards = disrupted rhythm
      - var_usage > 0.30 → more penalties caught → more goals
      - home_bias → shifts advantage to home/away side
    """
    strictness = _num(features, "referee_strictness", 0.60)
    card_tendency = _num(features, "referee_card_tendency", 0.50)
    var_usage = _num(features, "referee_var_usage", 0.30)
    home_bias = _num(features, "referee_home_bias", 0.0)

    # Game-flow modifier (same for both teams)
    flow = (
        1.0
        - 0.04 * (strictness - 0.60)     # strict → fewer goals
        - 0.03 * (card_tendency - 0.50)   # card-happy → disrupted flow
        + 0.025 * (var_usage - 0.30)      # VAR → more penalties
    )

    # Home advantage shift from referee bias
    if is_home:
        bias = 1.0 + 0.04 * home_bias
    else:
        bias = 1.0 - 0.04 * home_bias

    return _clamp(flow * bias, 0.80, 1.20)


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
    strictness = _num(features, "referee_strictness", 0.60)
    card_tendency = _num(features, "referee_card_tendency", 0.50)
    home_bias = _num(features, "referee_home_bias", 0.0)
    ref_name = features.get("referee_name", "")

    if abs(form_delta) >= 0.25:
        side = "Home" if form_delta > 0 else "Away"
        reasons.append(f"{side} team has stronger recent form.")
    if abs(xg_delta) >= 0.2:
        side = "Home" if xg_delta > 0 else "Away"
        reasons.append(f"{side} team has the stronger recent xG differential.")
    if abs(injury_delta) >= 0.05:
        side = "Home" if injury_delta > 0 else "Away"
        reasons.append(f"{side} team has the higher injury impact.")
    # Referee reasoning
    ref_reasons: list[str] = []
    if strictness > 0.68:
        ref_reasons.append("strict officiating may suppress scoring")
    elif strictness < 0.48:
        ref_reasons.append("lenient officiating allows more physical play")
    if card_tendency >= 0.55:
        ref_reasons.append("high card tendency could disrupt flow")
    if abs(home_bias) >= 0.07:
        direction = "home" if home_bias > 0 else "away"
        ref_reasons.append(f"slight {direction} bias detected")
    if ref_reasons and ref_name:
        reasons.append(f"Referee {ref_name}: {'; '.join(ref_reasons)}.")

    if not reasons:
        reasons.append("Teams look closely matched across form, xG, injury, and referee signals.")
    return reasons


def _poisson(k: int, rate: float) -> float:
    return exp(-rate) * rate**k / factorial(k)


def _market_implied_lambdas(
    odds: dict[str, float],
    *,
    max_goals: int = MAX_GOALS,
) -> tuple[float, float]:
    """Solve for λ_home, λ_away that best match market-implied win/draw/away probabilities.

    Uses exhaustive grid search over [_LAMBDA_MIN, _LAMBDA_MAX] at _LAMBDA_STEP
    resolution, minimising mean-squared-error between Poisson-derived probabilities
    and the market's de-vigged (overround-removed) implied probabilities.

    Returns (home_lambda, away_lambda).
    """
    # Extract raw implied probabilities (before overround removal)
    raw_home = 1.0 / float(odds.get("home_win", 2.0))
    raw_draw = 1.0 / float(odds.get("draw", 3.0))
    raw_away = 1.0 / float(odds.get("away_win", 2.0))
    # Remove overround
    total_implied = raw_home + raw_draw + raw_away
    target_home = raw_home / total_implied
    target_draw = raw_draw / total_implied
    target_away = raw_away / total_implied

    best_loss = float("inf")
    best_home = 1.35
    best_away = 1.15
    steps = int((_LAMBDA_MAX - _LAMBDA_MIN) / _LAMBDA_STEP) + 1
    for i in range(steps):
        home_l = _LAMBDA_MIN + i * _LAMBDA_STEP
        for j in range(steps):
            away_l = _LAMBDA_MIN + j * _LAMBDA_STEP
            rows = _score_probabilities(home_l, away_l, max_goals=max_goals)
            probs = _aggregate_probabilities(rows)
            loss = (
                (probs["home_win"] - target_home) ** 2
                + (probs["draw"] - target_draw) ** 2
                + (probs["away_win"] - target_away) ** 2
            )
            if loss < best_loss:
                best_loss = loss
                best_home = home_l
                best_away = away_l
    return best_home, best_away


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
