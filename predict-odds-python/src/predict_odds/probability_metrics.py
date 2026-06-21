from __future__ import annotations

import math
from typing import Any


def evaluate_probability_predictions(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"count": 0, "brier_score": 0.0, "log_loss": 0.0}
    brier_total = 0.0
    log_total = 0.0
    for row in rows:
        probabilities = row.get("probabilities", {})
        outcome = row.get("outcome")
        markets = list(probabilities.keys())
        for market in markets:
            actual = 1.0 if market == outcome else 0.0
            probability = min(max(float(probabilities[market]), 1e-12), 1 - 1e-12)
            brier_total += (probability - actual) ** 2
        outcome_probability = min(max(float(probabilities.get(outcome, 0.0)), 1e-12), 1 - 1e-12)
        log_total += -math.log(outcome_probability)
    return {
        "count": len(rows),
        "brier_score": round(brier_total / len(rows), 6),
        "log_loss": round(log_total / len(rows), 6),
    }
