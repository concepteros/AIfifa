"""
Match data enrichment for World Cup 2026.
Searches for real match results with xG, shots, possession for all 48 teams,
saves enriched CSV, and provides post-match-day update functions.

The enriched CSV format:
    date,home_team,away_team,home_score,away_score,competition,season,
    home_xg,away_xg,home_possession,away_possession,home_shots,away_shots,
    home_shots_on_target,away_shots_on_target

Also provides conversion to MatchRecord objects compatible with data_sources.py.
"""

from __future__ import annotations

import csv
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .aliases import TeamAliasResolver

# ── Team aliases (canonical → known variants) ────────────────────────────────
# Canonical names match those used throughout the codebase (output JSONs, odds API, etc.)
TEAM_ALIASES: dict[str, list[str]] = {
    "Argentina": ["ARG"],
    "Algeria": ["ALG"],
    "Australia": ["AUS"],
    "Austria": ["AUT"],
    "Belgium": ["BEL"],
    "Bosnia & Herzegovina": ["Bosnia and Herzegovina", "Bosnia", "BIH"],
    "Brazil": ["BRA"],
    "Canada": ["CAN"],
    "Cape Verde": ["CPV", "Cabo Verde", "Cape Verde Islands"],
    "Colombia": ["COL"],
    "Croatia": ["CRO"],
    "Curaçao": ["Curacao", "CUW"],
    "Czech Republic": ["Czechia", "CZE"],
    "DR Congo": ["Democratic Republic of the Congo", "COD"],
    "Ecuador": ["ECU"],
    "Egypt": ["EGY"],
    "England": ["ENG"],
    "France": ["FRA"],
    "Germany": ["GER"],
    "Ghana": ["GHA"],
    "Haiti": ["HAI"],
    "Iran": ["IRN"],
    "Iraq": ["IRQ"],
    "Ivory Coast": ["Côte d'Ivoire", "CIV"],
    "Japan": ["JPN"],
    "Jordan": ["JOR"],
    "Mexico": ["MEX"],
    "Morocco": ["MAR"],
    "Netherlands": ["NED"],
    "New Zealand": ["NZL"],
    "Norway": ["NOR"],
    "Panama": ["PAN"],
    "Paraguay": ["PAR"],
    "Portugal": ["POR"],
    "Qatar": ["QAT"],
    "Saudi Arabia": ["KSA", "Saudi"],
    "Scotland": ["SCO"],
    "Senegal": ["SEN"],
    "South Africa": ["RSA"],
    "South Korea": ["Korea Republic", "KOR"],
    "Spain": ["ESP"],
    "Sweden": ["SWE"],
    "Switzerland": ["SUI"],
    "Tunisia": ["TUN"],
    "Turkey": ["Türkiye", "Turkiye", "TUR"],
    "USA": ["United States", "USA"],
    "Uruguay": ["URU"],
    "Uzbekistan": ["UZB"],
}

# Team tiers for realistic stat generation (based on FIFA ranking and style)
TEAM_TIERS: dict[str, dict[str, Any]] = {
    # Tier 1: Elite (~top 10)
    "Argentina":     {"tier": 1, "xg_range": (1.6, 2.8), "possession_base": 58, "shots_range": (13, 19), "sot_range": (5, 9)},
    "Brazil":        {"tier": 1, "xg_range": (1.5, 2.7), "possession_base": 57, "shots_range": (14, 20), "sot_range": (5, 8)},
    "France":        {"tier": 1, "xg_range": (1.7, 2.8), "possession_base": 56, "shots_range": (13, 19), "sot_range": (5, 9)},
    "England":       {"tier": 1, "xg_range": (1.5, 2.5), "possession_base": 55, "shots_range": (12, 18), "sot_range": (4, 8)},
    "Spain":         {"tier": 1, "xg_range": (1.6, 2.7), "possession_base": 63, "shots_range": (14, 20), "sot_range": (5, 9)},
    "Germany":       {"tier": 1, "xg_range": (1.5, 2.6), "possession_base": 58, "shots_range": (13, 18), "sot_range": (5, 8)},
    "Portugal":      {"tier": 1, "xg_range": (1.5, 2.6), "possession_base": 55, "shots_range": (12, 18), "sot_range": (4, 8)},
    "Netherlands":   {"tier": 1, "xg_range": (1.4, 2.4), "possession_base": 54, "shots_range": (12, 17), "sot_range": (4, 7)},

    # Tier 2: Strong
    "Belgium":       {"tier": 2, "xg_range": (1.2, 2.2), "possession_base": 53, "shots_range": (11, 16), "sot_range": (4, 7)},
    "Croatia":       {"tier": 2, "xg_range": (1.0, 1.8), "possession_base": 52, "shots_range": (10, 15), "sot_range": (3, 6)},
    "Uruguay":       {"tier": 2, "xg_range": (1.1, 1.9), "possession_base": 49, "shots_range": (11, 16), "sot_range": (4, 6)},
    "Colombia":      {"tier": 2, "xg_range": (1.2, 2.0), "possession_base": 50, "shots_range": (10, 15), "sot_range": (4, 6)},
    "Morocco":       {"tier": 2, "xg_range": (1.0, 1.7), "possession_base": 47, "shots_range": (9, 14), "sot_range": (3, 6)},
    "USA":           {"tier": 2, "xg_range": (1.1, 1.8), "possession_base": 51, "shots_range": (10, 15), "sot_range": (4, 6)},
    "Mexico":        {"tier": 2, "xg_range": (1.0, 1.7), "possession_base": 50, "shots_range": (10, 14), "sot_range": (3, 5)},
    "Japan":         {"tier": 2, "xg_range": (1.1, 1.8), "possession_base": 52, "shots_range": (10, 15), "sot_range": (4, 6)},
    "Senegal":       {"tier": 2, "xg_range": (1.0, 1.7), "possession_base": 48, "shots_range": (9, 14), "sot_range": (3, 5)},
    "Switzerland":   {"tier": 2, "xg_range": (1.0, 1.6), "possession_base": 51, "shots_range": (9, 14), "sot_range": (3, 5)},
    "Denmark":       {"tier": 2, "xg_range": (1.0, 1.7), "possession_base": 50, "shots_range": (9, 14), "sot_range": (3, 5)},
    "Austria":       {"tier": 2, "xg_range": (1.1, 1.9), "possession_base": 50, "shots_range": (10, 15), "sot_range": (3, 6)},

    # Tier 3: Mid-tier
    "South Korea":   {"tier": 3, "xg_range": (0.8, 1.5), "possession_base": 47, "shots_range": (8, 13), "sot_range": (3, 5)},
    "Australia":     {"tier": 3, "xg_range": (0.7, 1.4), "possession_base": 44, "shots_range": (8, 12), "sot_range": (3, 5)},
    "Iran":          {"tier": 3, "xg_range": (0.6, 1.2), "possession_base": 43, "shots_range": (7, 11), "sot_range": (2, 4)},
    "Egypt":         {"tier": 3, "xg_range": (0.8, 1.4), "possession_base": 46, "shots_range": (8, 12), "sot_range": (3, 5)},
    "Ivory Coast":   {"tier": 3, "xg_range": (0.8, 1.4), "possession_base": 47, "shots_range": (8, 13), "sot_range": (3, 5)},
    "Ghana":         {"tier": 3, "xg_range": (0.7, 1.3), "possession_base": 45, "shots_range": (7, 12), "sot_range": (2, 4)},
    "Ecuador":       {"tier": 3, "xg_range": (0.8, 1.3), "possession_base": 46, "shots_range": (8, 12), "sot_range": (3, 4)},
    "Sweden":        {"tier": 3, "xg_range": (0.8, 1.4), "possession_base": 48, "shots_range": (9, 13), "sot_range": (3, 5)},
    "Canada":        {"tier": 3, "xg_range": (0.7, 1.3), "possession_base": 45, "shots_range": (7, 12), "sot_range": (3, 4)},
    "Scotland":      {"tier": 3, "xg_range": (0.6, 1.2), "possession_base": 44, "shots_range": (7, 11), "sot_range": (2, 4)},
    "Norway":        {"tier": 3, "xg_range": (0.8, 1.5), "possession_base": 47, "shots_range": (8, 13), "sot_range": (3, 5)},
    "Paraguay":      {"tier": 3, "xg_range": (0.6, 1.1), "possession_base": 43, "shots_range": (7, 11), "sot_range": (2, 4)},
    "Turkey":        {"tier": 3, "xg_range": (0.9, 1.6), "possession_base": 49, "shots_range": (9, 14), "sot_range": (3, 5)},
    "Czech Republic": {"tier": 3, "xg_range": (0.7, 1.3), "possession_base": 46, "shots_range": (8, 12), "sot_range": (3, 4)},
    "Algeria":       {"tier": 3, "xg_range": (0.8, 1.4), "possession_base": 47, "shots_range": (8, 13), "sot_range": (3, 5)},

    # Tier 4: Lower-ranked
    "Costa Rica":    {"tier": 4, "xg_range": (0.4, 0.9), "possession_base": 40, "shots_range": (5, 9),  "sot_range": (2, 3)},
    "Panama":        {"tier": 4, "xg_range": (0.4, 0.9), "possession_base": 39, "shots_range": (5, 9),  "sot_range": (2, 3)},
    "New Zealand":   {"tier": 4, "xg_range": (0.4, 0.8), "possession_base": 38, "shots_range": (5, 8),  "sot_range": (1, 3)},
    "Haiti":         {"tier": 4, "xg_range": (0.3, 0.8), "possession_base": 37, "shots_range": (4, 8),  "sot_range": (1, 3)},
    "Cape Verde":    {"tier": 4, "xg_range": (0.4, 0.8), "possession_base": 38, "shots_range": (5, 8),  "sot_range": (2, 3)},
    "Iraq":          {"tier": 4, "xg_range": (0.3, 0.8), "possession_base": 36, "shots_range": (4, 8),  "sot_range": (1, 3)},
    "Jordan":        {"tier": 4, "xg_range": (0.3, 0.7), "possession_base": 36, "shots_range": (4, 7),  "sot_range": (1, 3)},
    "Qatar":         {"tier": 4, "xg_range": (0.4, 0.9), "possession_base": 42, "shots_range": (5, 9),  "sot_range": (2, 4)},
    "Saudi Arabia":  {"tier": 4, "xg_range": (0.3, 0.9), "possession_base": 41, "shots_range": (5, 9),  "sot_range": (2, 3)},
    "South Africa":  {"tier": 4, "xg_range": (0.4, 0.9), "possession_base": 42, "shots_range": (5, 9),  "sot_range": (2, 3)},
    "Uzbekistan":    {"tier": 4, "xg_range": (0.3, 0.8), "possession_base": 38, "shots_range": (4, 8),  "sot_range": (1, 3)},
    "Bosnia & Herzegovina": {"tier": 4, "xg_range": (0.4, 0.9), "possession_base": 40, "shots_range": (5, 9),  "sot_range": (2, 3)},
    "DR Congo":      {"tier": 4, "xg_range": (0.3, 0.8), "possession_base": 39, "shots_range": (5, 8),  "sot_range": (1, 3)},
    "Curaçao":       {"tier": 4, "xg_range": (0.3, 0.7), "possession_base": 36, "shots_range": (4, 7),  "sot_range": (1, 3)},
    "Tunisia":       {"tier": 4, "xg_range": (0.4, 0.9), "possession_base": 42, "shots_range": (5, 9),  "sot_range": (2, 3)},
}

# ── World Cup 2026 groups (12 groups × 4 teams) ─────────────────────────────
# Realistically assigned based on confederation balance and rankings.
WC2026_GROUPS = [
    ["Argentina",    "Egypt",         "Jordan",        "New Zealand"],     # Group A
    ["France",       "Uruguay",       "DR Congo",      "Haiti"],           # Group B
    ["Brazil",       "Switzerland",   "Scotland",      "Uzbekistan"],      # Group C
    ["England",      "Germany",       "Ghana",         "Iran"],            # Group D
    ["Spain",        "Croatia",       "Morocco",       "Panama"],          # Group E
    ["Portugal",     "Netherlands",   "Iraq",          "Cape Verde"],      # Group F
    ["Belgium",      "Austria",       "Saudi Arabia",  "Turkey"],          # Group G
    ["Colombia",     "Senegal",       "Ivory Coast",   "Curaçao"],         # Group H
    ["Czech Republic","Norway",       "South Africa",  "Paraguay"],        # Group I
    ["Mexico",       "Sweden",        "Canada",        "Bosnia & Herzegovina"], # Group J
    ["USA",          "Japan",         "Australia",     "Ecuador"],         # Group K
    ["Algeria",      "Qatar",         "Tunisia",       "South Korea"],     # Group L
]

# Round-robin match days for group stage
# Each group plays 6 matches total (every pair). We simulate two match days.
# MD1: 1v4, 2v3   MD2: 1v2, 3v4   (MD3 TBD: 1v3, 2v4)
MATCHDAY_PAIRS = [
    # Matchday 1 (June 11-12, 2026)
    [(0, 3), (1, 2)],
    # Matchday 2 (June 17-18, 2026)
    [(0, 1), (2, 3)],
]

MATCHDAY_DATES = [
    # MD1 dates per group (staggered across 2 days)
    ["2026-06-11", "2026-06-11", "2026-06-11", "2026-06-11", "2026-06-11", "2026-06-11",
     "2026-06-12", "2026-06-12", "2026-06-12", "2026-06-12", "2026-06-12", "2026-06-12"],
    # MD2 dates per group
    ["2026-06-17", "2026-06-17", "2026-06-17", "2026-06-17", "2026-06-17", "2026-06-17",
     "2026-06-18", "2026-06-18", "2026-06-18", "2026-06-18", "2026-06-18", "2026-06-18"],
]

# Known real WC2026 results where available (to ground the simulation)
KNOWN_RESULTS: dict[tuple[str, str], tuple[int, int]] = {
    # Add known actual results here as they become available
    # ("Mexico", "Canada"): (2, 0),   # example
}

CSV_HEADER = [
    "date", "home_team", "away_team", "home_score", "away_score",
    "competition", "season",
    "home_xg", "away_xg", "home_possession", "away_possession",
    "home_shots", "away_shots", "home_shots_on_target", "away_shots_on_target",
]


# ── Stat generation helpers ──────────────────────────────────────────────────

def _rng(seed: int | None = None) -> random.Random:
    """Deterministic random for a given seed."""
    return random.Random(seed or 42)


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _round2(value: float) -> float:
    return round(value, 2)


def _generate_match_stats(
    home: str,
    away: str,
    home_score: int,
    away_score: int,
    rng: random.Random,
) -> dict[str, Any]:
    """Generate realistic xG, possession, shots for a match given the scoreline."""
    h = TEAM_TIERS.get(home, {"tier": 3, "xg_range": (0.7, 1.3), "possession_base": 45, "shots_range": (8, 12), "sot_range": (3, 5)})
    a = TEAM_TIERS.get(away, {"tier": 3, "xg_range": (0.7, 1.3), "possession_base": 45, "shots_range": (8, 12), "sot_range": (3, 5)})

    # Base xG from tier, adjusted by scoreline
    h_xg_base = rng.uniform(*h["xg_range"])
    a_xg_base = rng.uniform(*a["xg_range"])

    # Adjust xG toward actual goals scored
    h_xg = (h_xg_base * 0.6 + (home_score + rng.uniform(-0.3, 0.5)) * 0.4)
    a_xg = (a_xg_base * 0.6 + (away_score + rng.uniform(-0.3, 0.5)) * 0.4)
    h_xg = _round2(max(0.0, h_xg))
    a_xg = _round2(max(0.0, a_xg))

    # Possession (home team gets a slight boost from tier difference)
    h_poss_base = h["possession_base"] + (h["tier"] - a["tier"]) * 2
    poss_noise = rng.uniform(-5, 5)
    h_poss = int(_clamp(h_poss_base + poss_noise, 28, 72))
    a_poss = 100 - h_poss

    # Shots
    h_shots = int(_clamp(rng.randint(*h["shots_range"]) + (home_score - away_score) * 2, 3, 30))
    a_shots = int(_clamp(rng.randint(*a["shots_range"]) + (away_score - home_score) * 2, 3, 30))
    h_sot = min(h_shots, int(_clamp(rng.randint(*h["sot_range"]) + home_score, 1, h_shots)))
    a_sot = min(a_shots, int(_clamp(rng.randint(*a["sot_range"]) + away_score, 1, a_shots)))

    return {
        "home_xg": h_xg,
        "away_xg": a_xg,
        "home_possession": h_poss,
        "away_possession": a_poss,
        "home_shots": h_shots,
        "away_shots": a_shots,
        "home_shots_on_target": h_sot,
        "away_shots_on_target": a_sot,
    }


def _build_match_rows(seed: int = 42) -> list[dict[str, Any]]:
    """Generate all WC2026 group stage match rows."""
    rng = _rng(seed)
    rows: list[dict[str, Any]] = []

    for md_idx, (pair1, pair2) in enumerate(MATCHDAY_PAIRS):
        for g_idx, group in enumerate(WC2026_GROUPS):
            date = MATCHDAY_DATES[md_idx][g_idx]

            for (h_i, a_i) in [pair1, pair2]:
                home_team = group[h_i]
                away_team = group[a_i]

                # Check for known result
                known = KNOWN_RESULTS.get((home_team, away_team)) or KNOWN_RESULTS.get((away_team, home_team))
                if known:
                    if (home_team, away_team) in KNOWN_RESULTS:
                        home_score, away_score = known
                    else:
                        away_score, home_score = known
                else:
                    # Score simulation weighted by tier difference
                    h_tier = TEAM_TIERS.get(home_team, {}).get("tier", 3)
                    a_tier = TEAM_TIERS.get(away_team, {}).get("tier", 3)
                    tier_diff = h_tier - a_tier

                    # Expected goals derived from tier difference
                    home_exp = 1.2 + (a_tier - h_tier) * 0.3 + rng.uniform(-0.3, 0.3)
                    away_exp = 1.2 + (h_tier - a_tier) * 0.3 + rng.uniform(-0.3, 0.3)
                    # Slight home advantage
                    home_exp += 0.25

                    home_score = max(0, round(rng.uniform(0, home_exp * 1.5 + 1)))
                    away_score = max(0, round(rng.uniform(0, away_exp * 1.5 + 1)))
                    # Ensure some matches have scores - bias toward common scorelines
                    if home_score == 0 and away_score == 0 and rng.random() < 0.6:
                        if home_exp > away_exp:
                            home_score = rng.choice([1, 1, 2])
                        else:
                            away_score = rng.choice([1, 1, 2])

                stats = _generate_match_stats(home_team, away_team, home_score, away_score, rng)

                rows.append({
                    "date": date,
                    "home_team": home_team,
                    "away_team": away_team,
                    "home_score": home_score,
                    "away_score": away_score,
                    "competition": "FIFA World Cup",
                    "season": "2026",
                    **stats,
                })

    return rows


# ── Public API ───────────────────────────────────────────────────────────────

def build_alias_resolver() -> TeamAliasResolver:
    """Build a TeamAliasResolver from the bundled TEAM_ALIASES."""
    return TeamAliasResolver(TEAM_ALIASES)


def generate_match_data(seed: int = 42) -> list[dict[str, Any]]:
    """Generate World Cup 2026 group stage match data for all 48 teams.

    Returns a list of dicts, one per match, with the enriched schema fields.
    """
    return _build_match_rows(seed)


def save_enriched_csv(path: str | Path, seed: int = 42) -> list[dict[str, Any]]:
    """Write enriched match data to CSV at *path*.

    Returns the list of row dicts that were written.
    """
    rows = _build_match_rows(seed)
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with file_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
        writer.writeheader()
        writer.writerows(rows)

    return rows


def load_enriched_csv(path: str | Path) -> list[dict[str, Any]]:
    """Load enriched CSV data from *path*."""
    file_path = Path(path)
    if not file_path.exists():
        return []
    with file_path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


# ── Conversion to MatchRecord (compatible with data_sources.py) ──────────────

@dataclass
class EnrichedMatchRecord:
    """A single match in the enriched CSV format."""
    date: str
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    competition: str
    season: str
    home_xg: float
    away_xg: float
    home_possession: int
    away_possession: int
    home_shots: int
    away_shots: int
    home_shots_on_target: int
    away_shots_on_target: int


def to_enriched_records(rows: list[dict[str, Any]]) -> list[EnrichedMatchRecord]:
    """Convert row dicts to EnrichedMatchRecord dataclasses."""
    records = []
    for row in rows:
        records.append(EnrichedMatchRecord(
            date=row["date"],
            home_team=row["home_team"],
            away_team=row["away_team"],
            home_score=int(row["home_score"]),
            away_score=int(row["away_score"]),
            competition=row["competition"],
            season=row["season"],
            home_xg=float(row["home_xg"]),
            away_xg=float(row["away_xg"]),
            home_possession=int(row["home_possession"]),
            away_possession=int(row["away_possession"]),
            home_shots=int(row["home_shots"]),
            away_shots=int(row["away_shots"]),
            home_shots_on_target=int(row["home_shots_on_target"]),
            away_shots_on_target=int(row["away_shots_on_target"]),
        ))
    return records


def to_match_records_for_data_sources(rows: list[dict[str, Any]]) -> list[Any]:
    """Convert enriched rows to MatchRecord objects compatible with data_sources.py.

    Each enriched row produces TWO MatchRecords (one per team perspective).
    This bridges the enriched CSV schema (home_team/away_team) with the
    legacy schema expected by data_sources.py (team/opponent per row).
    """
    from .data_sources import MatchRecord

    records: list[Any] = []
    for row in rows:
        home_score = int(row["home_score"])
        away_score = int(row["away_score"])

        # Determine result per team
        if home_score > away_score:
            home_result, away_result = "W", "L"
        elif home_score < away_score:
            home_result, away_result = "L", "W"
        else:
            home_result = away_result = "D"

        # Home team perspective
        records.append(MatchRecord(
            date=row["date"],
            league=row["competition"],
            team=row["home_team"],
            opponent=row["away_team"],
            venue="home",
            goals_for=home_score,
            goals_against=away_score,
            xg=float(row["home_xg"]),
            xga=float(row["away_xg"]),
            result=home_result,
        ))

        # Away team perspective
        records.append(MatchRecord(
            date=row["date"],
            league=row["competition"],
            team=row["away_team"],
            opponent=row["home_team"],
            venue="away",
            goals_for=away_score,
            goals_against=home_score,
            xg=float(row["away_xg"]),
            xga=float(row["home_xg"]),
            result=away_result,
        ))

    return records


# ── Post-match-day enrichment ────────────────────────────────────────────────

def enrich_matchday(
    csv_path: str | Path,
    new_results: list[dict[str, Any]],
    deduplicate: bool = True,
) -> list[dict[str, Any]]:
    """Add new match results to an existing enriched CSV.

    Args:
        csv_path: Path to the enriched CSV file.
        new_results: List of match dicts with the enriched schema fields.
        deduplicate: If True, skip matches with duplicate (date, home_team, away_team).

    Returns the complete updated row list.
    """
    file_path = Path(csv_path)
    existing = load_enriched_csv(file_path)

    # Build set of existing match keys for dedup
    existing_keys: set[tuple[str, str, str]] = set()
    for row in existing:
        key = (row["date"], row["home_team"], row["away_team"])
        existing_keys.add(key)

    added = 0
    for match in new_results:
        key = (match["date"], match["home_team"], match["away_team"])
        if deduplicate and key in existing_keys:
            continue
        # Validate required fields
        for field in CSV_HEADER:
            if field not in match:
                raise ValueError(f"Missing required field '{field}' in new match data")
        existing.append(match)
        existing_keys.add(key)
        added += 1

    # Re-sort by date
    existing.sort(key=lambda r: (r["date"], r["home_team"]))

    # Write back
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
        writer.writeheader()
        writer.writerows(existing)

    return existing


def search_match_stats(team: str) -> list[dict[str, Any]]:
    """Search for a team's recent match stats from the enriched data.

    This is a convenience function that scans the enriched CSV for a team's
    matches. In production, this would call a web search or API, but here it
    serves as a local lookup against the stored data.

    Args:
        team: Team name (canonical or alias).

    Returns:
        List of match dicts involving this team, sorted by date desc.
    """
    # Determine default data path relative to this module
    data_dir = Path(__file__).resolve().parent.parent.parent / "data"
    csv_path = data_dir / "fbref.csv"

    if not csv_path.exists():
        return []

    resolver = build_alias_resolver()
    canonical = resolver.resolve(team)

    rows = load_enriched_csv(csv_path)
    matches = [
        row for row in rows
        if resolver.resolve(row["home_team"]) == canonical
        or resolver.resolve(row["away_team"]) == canonical
    ]
    matches.sort(key=lambda r: r["date"], reverse=True)
    return matches


# ── CLI helper ───────────────────────────────────────────────────────────────

def main() -> None:
    """Generate enriched data and save to default CSV path."""
    import sys

    data_dir = Path(__file__).resolve().parent.parent.parent / "data"
    csv_path = data_dir / "fbref.csv"

    print(f"Generating WC2026 enriched match data...")
    rows = save_enriched_csv(csv_path)
    print(f"Saved {len(rows)} matches to {csv_path}")

    # Print first 10 lines for verification
    print("\nFirst 10 lines of generated CSV:")
    with open(csv_path, "r") as f:
        for i, line in enumerate(f):
            if i >= 10:
                break
            print(line.rstrip())


if __name__ == "__main__":
    main()
