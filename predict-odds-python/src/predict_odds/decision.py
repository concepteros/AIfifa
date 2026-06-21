from __future__ import annotations

from typing import Any

from .errors import PredictValidationError

DEFAULT_MIN_EDGE = 0.03
DEFAULT_FRACTIONAL_KELLY = 0.25
DEFAULT_MAX_STAKE_FRACTION = 0.05


def build_betting_decisions(
    prediction: dict[str, Any],
    odds: dict[str, Any],
    *,
    bankroll: float,
    min_edge: float = DEFAULT_MIN_EDGE,
    fractional_kelly: float = DEFAULT_FRACTIONAL_KELLY,
    max_stake_fraction: float = DEFAULT_MAX_STAKE_FRACTION,
) -> dict[str, Any]:
    bankroll = _validate_non_negative(bankroll, "bankroll")
    min_edge = _validate_non_negative(min_edge, "min_edge")
    fractional_kelly = _validate_non_negative(fractional_kelly, "fractional_kelly")
    max_stake_fraction = _validate_non_negative(max_stake_fraction, "max_stake_fraction")
    probabilities = prediction.get("probabilities", {})
    if not isinstance(probabilities, dict):
        raise PredictValidationError("prediction.probabilities must be an object.")
    recommendations = [
        _recommend_market(
            market=market,
            model_probability=_to_probability(probabilities.get(market), market),
            odds_value=_to_decimal_odds(odds_value, market),
            bankroll=bankroll,
            min_edge=min_edge,
            fractional_kelly=fractional_kelly,
            max_stake_fraction=max_stake_fraction,
        )
        for market, odds_value in odds.items()
        if market in probabilities
    ]
    recommendations.sort(key=lambda item: (item["action"] != "bet", -item["expected_value"], item["market"]))
    return {
        "bankroll": _round_money(bankroll),
        "settings": {
            "min_edge": min_edge,
            "fractional_kelly": fractional_kelly,
            "max_stake_fraction": max_stake_fraction,
        },
        "recommendations": recommendations,
    }


def _recommend_market(
    *,
    market: str,
    model_probability: float,
    odds_value: float,
    bankroll: float,
    min_edge: float,
    fractional_kelly: float,
    max_stake_fraction: float,
) -> dict[str, Any]:
    implied_probability = 1 / odds_value
    edge = model_probability - implied_probability
    expected_value = model_probability * odds_value - 1
    kelly_fraction = max(_kelly_fraction(model_probability, odds_value), 0.0)
    stake_fraction = 0.0
    action = "no_bet"
    if edge >= min_edge and expected_value > 0 and kelly_fraction > 0:
        action = "bet"
        stake_fraction = min(kelly_fraction * fractional_kelly, max_stake_fraction)
    return {
        "market": market,
        "model_probability": _round_probability(model_probability),
        "odds": _round_probability(odds_value),
        "implied_probability": _round_probability(implied_probability),
        "edge": _round_probability(edge),
        "expected_value": _round_probability(expected_value),
        "kelly_fraction": _round_probability(kelly_fraction),
        "stake_fraction": _round_probability(stake_fraction),
        "stake": _round_money(bankroll * stake_fraction),
        "action": action,
    }


def _kelly_fraction(probability: float, odds_value: float) -> float:
    b = odds_value - 1
    q = 1 - probability
    return (b * probability - q) / b


def _to_probability(value: Any, market: str) -> float:
    try:
        probability = float(value)
    except (TypeError, ValueError) as exc:
        raise PredictValidationError(f"Missing or invalid model probability for market: {market}") from exc
    if probability < 0 or probability > 1:
        raise PredictValidationError(f"Model probability must be between 0 and 1 for market: {market}")
    return probability


def _to_decimal_odds(value: Any, market: str) -> float:
    try:
        odds_value = float(value)
    except (TypeError, ValueError) as exc:
        raise PredictValidationError(f"Invalid decimal odds for market: {market}") from exc
    if odds_value <= 1:
        raise PredictValidationError(f"Decimal odds must be greater than 1 for market: {market}")
    return odds_value


def _validate_non_negative(value: float, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise PredictValidationError(f"{name} must be numeric.") from exc
    if number < 0:
        raise PredictValidationError(f"{name} must be non-negative.")
    return number


def _round_probability(value: float) -> float:
    return round(value, 6)


def _round_money(value: float) -> float:
    return round(value, 2)
