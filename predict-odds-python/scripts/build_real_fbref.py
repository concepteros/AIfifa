#!/usr/bin/env python3
"""Build fbref.csv from REAL ESPN World Cup 2026 match data."""

import csv

# All match results from ESPN API (June 11-21, 2026)
# Format: (date, home, away, home_goals, away_goals)
RESULTS = [
    # June 11
    ("2026-06-11", "Mexico", "South Africa", 2, 0),
    ("2026-06-11", "South Korea", "Czechia", 2, 1),
    # June 12
    ("2026-06-12", "Canada", "Bosnia-Herzegovina", 1, 1),
    ("2026-06-12", "United States", "Paraguay", 4, 1),
    # June 13
    ("2026-06-13", "Qatar", "Switzerland", 1, 1),
    ("2026-06-13", "Brazil", "Morocco", 1, 1),
    ("2026-06-13", "Haiti", "Scotland", 0, 1),
    # June 14
    ("2026-06-14", "Australia", "Türkiye", 2, 0),
    ("2026-06-14", "Germany", "Curaçao", 7, 1),
    ("2026-06-14", "Netherlands", "Japan", 2, 2),
    ("2026-06-14", "Ivory Coast", "Ecuador", 1, 0),
    ("2026-06-14", "Sweden", "Tunisia", 5, 1),
    # June 15 — KEY: our 8 target teams' first matches
    ("2026-06-15", "Spain", "Cape Verde", 0, 0),
    ("2026-06-15", "Belgium", "Egypt", 1, 1),
    ("2026-06-15", "Saudi Arabia", "Uruguay", 1, 1),
    ("2026-06-15", "Iran", "New Zealand", 2, 2),
    # June 16
    ("2026-06-16", "France", "Senegal", 3, 1),
    ("2026-06-16", "Iraq", "Norway", 1, 4),
    ("2026-06-16", "Argentina", "Algeria", 3, 0),
    # June 17
    ("2026-06-17", "Austria", "Jordan", 3, 1),
    ("2026-06-17", "Portugal", "Congo DR", 1, 1),
    ("2026-06-17", "England", "Croatia", 4, 2),
    ("2026-06-17", "Ghana", "Panama", 1, 0),
    ("2026-06-17", "Uzbekistan", "Colombia", 1, 3),
    # June 18
    ("2026-06-18", "Czechia", "South Africa", 1, 1),
    ("2026-06-18", "Switzerland", "Bosnia-Herzegovina", 4, 1),
    ("2026-06-18", "Canada", "Qatar", 6, 0),
    ("2026-06-18", "Mexico", "South Korea", 1, 0),
    # June 19
    ("2026-06-19", "United States", "Australia", 2, 0),
    ("2026-06-19", "Scotland", "Morocco", 0, 1),
    ("2026-06-19", "Brazil", "Haiti", 3, 0),
    ("2026-06-19", "Türkiye", "Paraguay", 0, 1),
    # June 20
    ("2026-06-20", "Netherlands", "Sweden", 5, 1),
    ("2026-06-20", "Germany", "Ivory Coast", 2, 1),
    ("2026-06-20", "Ecuador", "Curaçao", 0, 0),
    # June 21 morning (BJT)
    ("2026-06-21", "Tunisia", "Japan", 0, 4),
]

FIFA = {
    "Argentina": 1877, "Spain": 1875, "France": 1871, "England": 1828,
    "Portugal": 1768, "Brazil": 1766, "Morocco": 1755, "Netherlands": 1754,
    "Belgium": 1742, "Germany": 1736, "Croatia": 1715, "Italy": 1705,
    "Colombia": 1698, "Mexico": 1687, "Senegal": 1684, "Uruguay": 1673,
    "United States": 1671, "Japan": 1662, "Switzerland": 1650, "Iran": 1620,
    "Austria": 1610, "Ecuador": 1600, "South Korea": 1590, "Australia": 1585,
    "Egypt": 1560, "South Africa": 1430, "Türkiye": 1575, "Scotland": 1570,
    "Sweden": 1535, "Paraguay": 1445, "Ivory Coast": 1435, "Ghana": 1425,
    "Saudi Arabia": 1450, "Cape Verde": 1400, "Qatar": 1390,
    "Tunisia": 1380, "Curaçao": 1360, "Haiti": 1300, "New Zealand": 1280,
    "Uzbekistan": 1270, "Iraq": 1260, "Jordan": 1240, "Panama": 1430,
    "Norway": 1500, "Canada": 1495, "Czechia": 1510, "Congo DR": 1320,
    "Bosnia-Herzegovina": 1380, "Algeria": 1540,
    "Bosnia & Herzegovina": 1380,
}

def est_xg(goals, self_fifa, opp_fifa):
    base = {0: 0.45, 1: 1.05, 2: 1.75, 3: 2.45, 4: 3.1, 5: 3.6, 6: 4.0, 7: 4.3}
    base = base.get(goals, goals * 0.8)
    diff = (self_fifa - opp_fifa) / 100
    adj = 1.0 + max(min(diff * 0.04, 0.25), -0.15)
    return round(base * adj, 2)


rows = []

for date, home, away, hg, ag in RESULTS:
    f_h = FIFA.get(home, 1400)
    f_a = FIFA.get(away, 1400)
    
    # Home team row
    res_h = "W" if hg > ag else ("D" if hg == ag else "L")
    rows.append([date, "FIFA World Cup", home, away, "home",
                hg, ag, est_xg(hg, f_h, f_a), est_xg(ag, f_a, f_h), res_h])
    
    # Away team row
    res_a = "W" if ag > hg else ("D" if ag == hg else "L")
    rows.append([date, "FIFA World Cup", away, home, "away",
                ag, hg, est_xg(ag, f_a, f_h), est_xg(hg, f_h, f_a), res_a])

# Sort by date
rows.sort(key=lambda r: r[0])

header = ["date", "league", "team", "opponent", "venue",
          "goals_for", "goals_against", "xg", "xga", "result"]

with open("/Users/macbook/AIfifa/predict-odds-python/data/fbref.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(header)
    w.writerows(rows)

print(f"Written {len(rows)} rows with {len(RESULTS)} REAL match results")
print()

# Show our 8 target teams' data
targets = ["Spain", "Saudi Arabia", "Belgium", "Iran", "Uruguay", "Cape Verde", "New Zealand", "Egypt"]
print("=== TARGET TEAM REAL DATA ===")
for t in targets:
    for r in rows:
        if r[2] == t:
            print(f"  {r[0]} {t} {r[5]}-{r[6]} vs {r[3]} (xG={r[7]}/{r[8]}) {r[9]}")
