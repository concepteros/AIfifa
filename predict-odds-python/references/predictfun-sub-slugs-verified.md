# Predict.fun Sub-Slugs — Verified Discovery (2026-06-22)

## Background

On 2026-06-22, the agent initially claimed Predict.fun had no Over/Under or Exact Score markets. The user insisted they existed, and after thorough searching, they were found under sub-category slugs that are NOT returned by the main API endpoints.

## Root Cause

The main category API (`GET /v1/categories/fifwc-esp-ksa-2026-06-21`) only returns 3 moneyline markets (Win/Draw/Win). The sub-categories (exact-score, more-markets, halftime-result) are separate slugs with NO parent-child relationship in the API response — no `children` or `subCategories` field.

## Discovery Pattern

Construct sub-slugs manually from the main match slug:

```
Main slug:    fifwc-{t1}-{t2}-{date}
Exact score:  fifwc-{t1}-{t2}-{date}-exact-score
More markets: fifwc-{t1}-{t2}-{date}-more-markets
Halftime:     fifwc-{t1}-{t2}-{date}-halftime-result
```

Team codes use 3-letter abbreviations: esp=Spain, ksa=Saudi Arabia, bel=Belgium, irn=Iran, etc.

**These sub-slugs do NOT appear in:**
- `/v1/categories` (flat list)
- `/v1/search?query=...` (only returns main slug)
- The main category's `categories` or `children` field

## Verified Sub-Market Contents

### more-markets (11 markets)
- Spread: {team} (-1.5), (-2.5) — 4 markets total (2 per team)
- O/U: 0.5, 1.5, 2.5, 3.5, 4.5, 5.5 — 6 markets
- BTTS: Both Teams to Score — 1 market

**Outcome naming:**
- Spread outcomes are team abbreviations (e.g., "ESP", "KSA"), NOT "Yes"/"No"
- O/U outcomes are "Over" and "Under", NOT "Yes"/"No"
- BTTS outcomes are "Yes"/"No"

### exact-score (17 markets)
All 16 standard scorelines (0-0 through 3-3) + 1 "Any Other Score"
Outcome names are "Yes"/"No"

### halftime-result (3 markets)
Same as moneyline: {team} Win / Draw / {team} Win

## Spain vs Saudi Arabia — Full Market Data

```
Main slug:      Spain Win YES @ 0.89 ($178k depth)
more-markets:   O/U 2.5 Over YES @ 0.74 ($151k depth)
                Spain -1.5 ESP @ 0.76 ($152k depth)
                BTTS YES @ 0.38 ($103k depth)
exact-score:    2-0 @ 0.15 ($16k) | 3-0 @ 0.17 ($38k) | Any Other @ 0.42 ($15k)
```

## Lesson

**When the user says a market exists on Predict.fun, ALWAYS check sub-slugs before concluding it doesn't.**
The main slug returns only moneyline. Sub-slugs are manually constructed, never discovered via search.
