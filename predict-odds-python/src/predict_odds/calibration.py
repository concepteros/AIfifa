from __future__ import annotations


def calibrate_market_probabilities(probabilities: dict[str, float], *, shrinkage: float = 0.0) -> dict[str, float]:
    if not probabilities:
        return {}
    shrinkage = max(0.0, min(float(shrinkage), 1.0))
    market_count = len(probabilities)
    baseline = 1.0 / market_count
    adjusted = {
        market: max(0.0, (float(probability) * (1 - shrinkage)) + (baseline * shrinkage))
        for market, probability in probabilities.items()
    }
    total = sum(adjusted.values())
    if total <= 0:
        return {market: round(baseline, 6) for market in probabilities}
    normalized = {market: round(value / total, 6) for market, value in adjusted.items()}
    markets = list(normalized)
    if markets:
        remainder = round(1.0 - sum(normalized.values()), 6)
        normalized[markets[-1]] = round(normalized[markets[-1]] + remainder, 6)
    return normalized
