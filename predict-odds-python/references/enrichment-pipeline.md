# Enrichment Pipeline Architecture (v1.3)

Each daily scan now produces an `enrichment` field in the output JSON:

```json
{
  "prediction": { ... },
  "decisions": [ ... ],
  "enrichment": {
    "sentiment": {
      "home_team": "Tunisia",
      "away_team": "Japan",
      "home_sentiment": -0.68,
      "away_sentiment": 0.12,
      "sources": [...],
      "summary": "..."
    },
    "tactics": {
      "advantage": {"tactical_advantage": -0.13, ...},
      "analysis": "从战术匹配度来看，Japan..."
    },
    "supplementary": {
      "weather": {...},
      "referee": {...},
      "home_injuries": [...],
      "away_injuries": [...],
      "home_injury_impact": 0.0,
      "away_injury_impact": 0.0
    },
    "ml_ensemble": {
      "expected_goals": {"home": 0.8, "away": 1.5},
      ...
    }
  }
}
```

## Module Load Order

1. `data_enrichment.py` — replaced simulated FBref CSV with tier-based realistic stats
2. `feature_pipeline.py` — builds features from enriched data
3. `prediction.py` — Poisson prediction
4. `sentiment.py` — web search sentiment scoring (~20s, slowest module)
5. `tactics.py` — style matchup analysis
6. `supplementary.py` — weather/referee/injury lookup
7. `ml_model.py` — XGBoost ensemble (if xgboost installed)
8. `decision.py` — Kelly + EV betting decisions
9. `predict_fun_betting.py` — auto-execution (via CLI `bet` command)

## Graceful Degradation

All enrichment modules use `try/except ImportError` + `try/except Exception` guards.
If any module fails, it's set to `None` and the scan continues.

## Pitfalls

### Feature nesting: `build_match_features` wrapper vs `predict_match` consumer
`build_match_features()` returns `{league, date, match, features: {...}}` — the actual features are in the `features` sub-dict.
`predict_match()` reads flat keys like `home_xg_for_avg` from the dict it receives.
**Must pass `features["features"]` to `predict_match()`**, not the outer wrapper.
Passing the outer dict causes all features to read as 0 (fallback defaults), producing wrong predictions.

### CSV format mismatch — per-match vs per-team

`data_enrichment.py` outputs per-match CSV (home_team, away_team, home_xg, away_xg).
`data_sources.py` `load_matches()` expects per-team CSV (team, opponent, goals_for, xg).
These are DIFFERENT formats. Use the bridge function:

```python
from predict_odds.data_enrichment import to_match_records_for_data_sources, load_enriched_csv
rows = load_enriched_csv('data/fbref.csv')
records = to_match_records_for_data_sources(rows)  # converts to per-team format
# Now save in old format for backward compatibility
```

Symptom: `PredictValidationError: Missing required data column: league` when loading the new CSV.

### Dataclass JSON serialization

Enrichment functions return Python dataclass objects (`MatchSentiment`, `TacticalProfile`, `WeatherData`).
These crash `json.dumps()` with `TypeError: Object of type X is not JSON serializable`.

Fix: `bot_scanner.py` now has a `_to_json()` helper that recursively converts dataclasses via `dataclasses.asdict()`. All enrichment values pass through `_to_json()` before storage.

### Function signature mismatches

The enrichment functions have different signatures than initially expected:

| Function | Expected | Actual |
|----------|----------|--------|
| `get_match_supplementary_context()` | `venue=, ref=` | `venue_city=""` |
| `ensemble_predict()` | `poisson_prediction=, features=` | positional first arg |
| `analyze_match_sentiment()` | positional only | `alias_resolver=None` |

Always check the actual function signature before calling from bot_scanner.

## Data Sources

| Source | Status | Notes |
|--------|--------|-------|
| The Odds API | ✅ Live | Market odds |
| Sportmonks | ✅ Live | Fixtures + participant data |
| FBref | 🟡 Tier-based | 403 blocked, using FIFA rank tiers |
| Transfermarkt | 🟡 Tier-based | Same approach |
| Understat | ❌ 404 | World Cup 2026 not in dataset |
| Web search | ✅ Live | Used for sentiment |
