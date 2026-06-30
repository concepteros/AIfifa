# ESPN API — World Cup 2026 Match Results

## Overview

ESPN's hidden REST API provides **complete World Cup match results** with no API key required, no rate limits observed, and no date restrictions.

**Base URL**: `https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard`

## Query by Date

```
GET /apis/site/v2/sports/soccer/fifa.world/scoreboard?dates=YYYYMMDD
```

Example:
```bash
curl -s "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard?dates=20260615" \
  -H "User-Agent: Mozilla/5.0"
```

## Response Structure

```json
{
  "events": [
    {
      "name": "Spain vs Cape Verde",
      "status": {
        "type": {
          "name": "STATUS_FULL_TIME"
        }
      },
      "competitions": [{
        "competitors": [
          {
            "team": {"displayName": "Spain", "abbreviation": "ESP"},
            "score": "0"
          },
          {
            "team": {"displayName": "Cape Verde", "abbreviation": "CPV"},
            "score": "0"
          }
        ]
      }]
    }
  ]
}
```

## Status Values

| Status | Meaning |
|--------|---------|
| `STATUS_FULL_TIME` | Match completed |
| `STATUS_SCHEDULED` | Not yet started (score = "0"-"0", ignore) |

## Key Discoveries (2026-06-22)

All 36 completed matches from June 11-21 retrieved via 12 date queries. Critical finding:

**June 15 (Matchday 1 for 8 target teams) — ALL DRAWS:**
- Spain 0-0 Cape Verde
- Belgium 1-1 Egypt
- Saudi Arabia 1-1 Uruguay
- Iran 2-2 New Zealand

This completely changed the prediction model — Spain dropped from 58% to 35% win probability.

## Advantages Over api-football

| Feature | ESPN API | api-football Free |
|---------|----------|-------------------|
| API Key | None required | Required |
| Date Range | June 11+ (full tournament) | June 20-22 only (3 days) |
| Rate Limits | None observed | 100/day |
| Match Results | ✅ | ✅ |
| xG/Stats | ❌ | ⚠️ Free plan limited |

## Integration Script

See `scripts/build_real_fbref.py` — builds `fbref.csv` from ESPN data with FIFA ranking-based xG estimation.
