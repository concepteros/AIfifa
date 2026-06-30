#!/usr/bin/env python3
"""Scrape FBref for World Cup 2026 teams' recent match data.

Uses seleniumbase UC driver to bypass Cloudflare blocking.
Extracts: date, team, opponent, venue, goals_for, goals_against, xg, xga,
           possession, shots, shots_on_target, result.
Outputs CSV matching predict_odds.data_sources.MatchRecord schema.
"""

from __future__ import annotations

import csv
import json
import re
import sys
import time
from pathlib import Path

from bs4 import BeautifulSoup
from seleniumbase import Driver


# ============================================================
# CONFIGURATION
# ============================================================

# All 48 teams expected to participate in 2026 FIFA World Cup
# (matches the teams in the existing simulated fbref.csv)
WC2026_TEAMS = [
    "Algeria", "Argentina", "Australia", "Austria", "Belgium",
    "Bosnia & Herzegovina", "Brazil", "Canada", "Cape Verde",
    "Colombia", "Croatia", "Curaçao", "Czech Republic", "DR Congo",
    "Ecuador", "Egypt", "England", "France", "Germany", "Ghana",
    "Haiti", "Iran", "Iraq", "Ivory Coast", "Japan", "Jordan",
    "Mexico", "Morocco", "Netherlands", "New Zealand", "Norway",
    "Panama", "Paraguay", "Portugal", "Qatar", "Saudi Arabia",
    "Scotland", "Senegal", "South Africa", "South Korea", "Spain",
    "Sweden", "Switzerland", "Tunisia", "Turkey", "USA",
    "Uruguay", "Uzbekistan",
]

# fbref team slugs — mapping from team name to fbref URL slug
# Generated from known fbref national team IDs
TEAM_SLUGS = {
    "Algeria": "Algeria",
    "Argentina": "Argentina",
    "Australia": "Australia",
    "Austria": "Austria",
    "Belgium": "Belgium",
    "Bosnia & Herzegovina": "Bosnia-and-Herzegovina",
    "Brazil": "Brazil",
    "Canada": "Canada",
    "Cape Verde": "Cape-Verde",
    "Colombia": "Colombia",
    "Croatia": "Croatia",
    "Curaçao": "Curacao",
    "Czech Republic": "Czech-Republic",
    "DR Congo": "Congo-DR",
    "Ecuador": "Ecuador",
    "Egypt": "Egypt",
    "England": "England",
    "France": "France",
    "Germany": "Germany",
    "Ghana": "Ghana",
    "Haiti": "Haiti",
    "Iran": "Iran",
    "Iraq": "Iraq",
    "Ivory Coast": "Ivory-Coast",
    "Japan": "Japan",
    "Jordan": "Jordan",
    "Mexico": "Mexico",
    "Morocco": "Morocco",
    "Netherlands": "Netherlands",
    "New Zealand": "New-Zealand",
    "Norway": "Norway",
    "Panama": "Panama",
    "Paraguay": "Paraguay",
    "Portugal": "Portugal",
    "Qatar": "Qatar",
    "Saudi Arabia": "Saudi-Arabia",
    "Scotland": "Scotland",
    "Senegal": "Senegal",
    "South Africa": "South-Africa",
    "South Korea": "South-Korea",
    "Spain": "Spain",
    "Sweden": "Sweden",
    "Switzerland": "Switzerland",
    "Tunisia": "Tunisia",
    "Turkey": "Turkey",
    "USA": "United-States",
    "Uruguay": "Uruguay",
    "Uzbekistan": "Uzbekistan",
}

# Number of recent matches per team
MATCHES_PER_TEAM = 5

# Output path
OUTPUT_PATH = Path("/Users/macbook/AIfifa/predict-odds-python/data/fbref.csv")

# Cache directory for HTML pages (avoid re-downloading)
CACHE_DIR = Path("/Users/macbook/AIfifa/predict-odds-python/data/fbref_cache")

# ============================================================
# HELPERS
# ============================================================

def strip_country_code(name: str) -> str:
    """Strip 2-3 char country code prefix from team names (e.g., 'ecEcuador' -> 'Ecuador')."""
    name = name.strip()
    # Remove leading lowercase country code prefix
    match = re.match(r'^[a-z]{2,3}\s*(.+)', name)
    if match:
        return match.group(1).strip()
    return name


def normalize_team(name: str) -> str:
    """Normalize team name to match our canonical names."""
    name = strip_country_code(name)
    name = name.strip()
    # Fix common alternate names
    name_map = {
        "United States": "USA",
        "IR Iran": "Iran",
        "Korea Republic": "South Korea",
        "Korea DPR": "North Korea",
        "Congo DR": "DR Congo",
        "Czechia": "Czech Republic",
        "Côte d'Ivoire": "Ivory Coast",
        "Ivory Coast": "Ivory Coast",
        "Bosnia and Herzegovina": "Bosnia & Herzegovina",
        "Saudi Arabia": "Saudi Arabia",
        "New Zealand": "New Zealand",
        "South Africa": "South Africa",
        "Cape Verde": "Cape Verde",
        "Cabo Verde": "Cape Verde",
        "Curacao": "Curaçao",
    }
    return name_map.get(name, name)


def normalize_comp(comp: str) -> str:
    """Normalize competition name."""
    comp_map = {
        "WCQ": "World Cup Qualifying",
        "World Cup": "FIFA World Cup",
        "Copa América": "Copa America",
        "African Cup of Nations": "Africa Cup of Nations",
        "Africa Cup of Nations qualification": "Africa Cup of Nations Qualifying",
        "AFC Asian Cup": "Asian Cup",
        "UEFA Euro": "European Championship",
        "UEFA Euro Qualifying": "European Championship Qualifying",
        "UEFA Nations League": "UEFA Nations League",
        "Friendlies (M)": "International Friendly",
        "Friendly": "International Friendly",
    }
    return comp_map.get(comp, comp)


def get_result(gf: int, ga: int) -> str:
    """Determine result: W, D, or L."""
    if gf > ga:
        return "W"
    elif gf < ga:
        return "L"
    return "D"


def safe_int(val: str) -> int:
    """Parse integer safely."""
    val = str(val).strip()
    if val in ("", "-", "—", "N/A"):
        return 0
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return 0


def safe_float(val: str) -> float:
    """Parse float safely."""
    val = str(val).strip()
    if val in ("", "-", "—", "N/A"):
        return 0.0
    try:
        return float(val.replace("%", ""))
    except (ValueError, TypeError):
        return 0.0


# ============================================================
# FBREF SCRAPER
# ============================================================

class FBrefScraper:
    """Scrape national team match logs from fbref.com."""

    FBREF_SQUAD_URL = "https://fbref.com/en/squads/{team_id}/matchlogs/c9/{stat_type}/{team_slug}-Match-Logs-All-Competitions"

    def __init__(self):
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self.driver = None
        self.all_matches = []

    def _get_driver(self):
        """Get or create a UC selenium driver."""
        if self.driver is None:
            self.driver = Driver(uc=True, headless=True)
        return self.driver

    def close(self):
        if self.driver:
            self.driver.quit()
            self.driver = None

    def _get_team_id(self, team_name: str) -> str | None:
        """Look up fbref team ID from the main national teams page."""
        cache_file = CACHE_DIR / "team_ids.json"
        if cache_file.exists():
            ids = json.loads(cache_file.read_text())
            slug = TEAM_SLUGS.get(team_name, team_name.replace(" ", "-"))
            if slug in ids:
                return ids[slug]

        # Fetch the national teams index page
        url = "https://fbref.com/en/squads/nations/"
        html = self._fetch_url(url, "nations_index.html")
        soup = BeautifulSoup(html, "lxml")

        # Parse team IDs from the page
        ids = {}
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if "/en/squads/" in href and "/matchlogs/" not in href:
                team_id = href.split("/")[3]
                slug = href.split("/")[4] if len(href.split("/")) > 4 else ""
                name = link.get_text(strip=True)
                key = TEAM_SLUGS.get(name, slug or name)
                ids[key] = team_id

        # Also try to find by checking links in common national team tables
        for row in soup.find_all("tr"):
            link = row.find("a", href=True)
            if link and "/en/squads/" in link["href"]:
                parts = link["href"].split("/")
                if len(parts) >= 5:
                    team_id = parts[3]
                    slug = parts[4]
                    name = link.get_text(strip=True)
                    ids[slug] = team_id

        cache_file.write_text(json.dumps(ids, indent=2))
        slug = TEAM_SLUGS.get(team_name, team_name.replace(" ", "-"))
        return ids.get(slug)

    def _fetch_url(self, url: str, cache_name: str) -> str:
        """Fetch a URL, using cache if available."""
        cache_file = CACHE_DIR / cache_name
        if cache_file.exists():
            return cache_file.read_text(encoding="utf-8")

        driver = self._get_driver()
        print(f"    Fetching: {url}")
        driver.get(url)
        time.sleep(3)  # Let page render

        html = driver.page_source
        cache_file.write_text(html, encoding="utf-8")
        return html

    def _parse_match_log_schedule(self, html: str) -> list[dict]:
        """Parse the schedule tab of a team's match log page.

        Returns list of dicts with: date, comp, round, venue, result, gf, ga, opponent, possession
        """
        soup = BeautifulSoup(html, "lxml")
        table = soup.find("table", id="matchlogs_for")
        if not table:
            return []

        matches = []
        rows = table.find_all("tr")
        if not rows:
            return matches

        # Find header row
        header_row = None
        for row in rows:
            ths = row.find_all("th")
            if len(ths) > 3:
                header_row = row
                break

        if not header_row:
            return matches

        headers = [th.get_text(strip=True) for th in header_row.find_all("th")]
        # Add td headers too (sometimes there are column group headers)
        td_headers = [td.get_text(strip=True) for td in header_row.find_all("td")]

        # Find data rows (skip header)
        for row in rows:
            th_cells = row.find_all("th")
            td_cells = row.find_all("td")

            if len(th_cells) < 2 or len(td_cells) < 5:
                continue

            # Extract date from the first th
            date = th_cells[0].get_text(strip=True)
            if not re.match(r'\d{4}-\d{2}-\d{2}', date):
                continue

            try:
                comp = td_cells[0].get_text(strip=True)  # Competition
                round_info = td_cells[1].get_text(strip=True) if len(td_cells) > 1 else ""
                day = td_cells[2].get_text(strip=True) if len(td_cells) > 2 else ""
                venue = td_cells[3].get_text(strip=True) if len(td_cells) > 3 else "Home"
                result = td_cells[4].get_text(strip=True) if len(td_cells) > 4 else ""
                gf_str = td_cells[5].get_text(strip=True) if len(td_cells) > 5 else "0"
                ga_str = td_cells[6].get_text(strip=True) if len(td_cells) > 6 else "0"
                opponent = td_cells[7].get_text(strip=True) if len(td_cells) > 7 else ""
                possession = td_cells[8].get_text(strip=True) if len(td_cells) > 8 else ""

                matches.append({
                    "date": date,
                    "comp": comp,
                    "round": round_info,
                    "venue": "Home" if "home" in venue.lower() else "Away" if "away" in venue.lower() else "neutral",
                    "result": result,
                    "gf": safe_int(gf_str),
                    "ga": safe_int(ga_str),
                    "opponent": normalize_team(opponent),
                    "possession": safe_float(possession),
                })
            except (IndexError, ValueError):
                continue

        return matches

    def _parse_match_log_shooting(self, html: str) -> dict[str, dict]:
        """Parse the shooting tab of a team's match log page.

        Returns dict mapping date -> {shots, sot}
        """
        soup = BeautifulSoup(html, "lxml")
        table = soup.find("table", id="matchlogs_for")
        if not table:
            return {}

        stats = {}
        rows = table.find_all("tr")

        for row in rows:
            th_cells = row.find_all("th")
            td_cells = row.find_all("td")

            if len(th_cells) < 1 or len(td_cells) < 8:
                continue

            date = th_cells[0].get_text(strip=True)
            if not re.match(r'\d{4}-\d{2}-\d{2}', date):
                continue

            try:
                # Columns: Date, Time, Comp, Round, Day, Venue, Result, GF, GA, Opponent,
                #           Gls, Sh, SoT, SoT%, G/Sh, G/SoT, PK, PKatt, Match Report
                shots = td_cells[8].get_text(strip=True) if len(td_cells) > 8 else "0"
                sot = td_cells[9].get_text(strip=True) if len(td_cells) > 9 else "0"

                stats[date] = {
                    "shots": safe_int(shots),
                    "sot": safe_int(sot),
                }
            except (IndexError, ValueError):
                continue

        return stats

    def scrape_team_match_logs(self, team_name: str) -> list[dict]:
        """Scrape recent match data for a team.

        Gets match log data from two tabs: schedule (results, possession)
        and shooting (shots, shots on target).
        xG is estimated from shots and SoT since it's not available in team match logs for
        international teams (it's only in match report pages and league summary pages).
        """
        slug = TEAM_SLUGS.get(team_name, team_name.replace(" ", "-"))
        team_id = self._get_team_id(team_name)

        if not team_id:
            print(f"  [SKIP] {team_name}: Could not find team ID on fbref")
            return []

        # Fetch schedule page
        schedule_url = self.FBREF_SQUAD_URL.format(
            team_id=team_id, stat_type="all", team_slug=slug
        )
        schedule_html = self._fetch_url(
            schedule_url, f"matchlog_{slug}_schedule.html"
        )
        schedule_data = self._parse_match_log_schedule(schedule_html)

        # Fetch shooting page  
        shooting_url = self.FBREF_SQUAD_URL.format(
            team_id=team_id, stat_type="shooting", team_slug=slug
        )
        shooting_html = self._fetch_url(
            shooting_url, f"matchlog_{slug}_shooting.html"
        )
        shooting_data = self._parse_match_log_shooting(shooting_html)

        # Merge data and take most recent N matches
        matches = []
        for s_match in schedule_data[:MATCHES_PER_TEAM * 2]:  # Get more to account for filtering
            date = s_match["date"]
            opponent = s_match["opponent"]
            comp = normalize_comp(s_match["comp"])

            if not opponent:
                continue

            shoot = shooting_data.get(date, {"shots": 0, "sot": 0})

            # Estimate xG from shots/SoT (simple heuristic based on typical ratios)
            shots = shoot["shots"]
            sot = shoot["sot"]
            # Simple xG estimation: ~0.1 per shot, ~0.3 per SoT
            if sot > 0 and shots > 0:
                xg = round(sot * 0.30 + (shots - sot) * 0.05, 1)
            elif shots > 0:
                xg = round(shots * 0.10, 1)
            else:
                xg = round(s_match["gf"] * 0.5, 1)  # Fallback based on goals

            matches.append({
                "date": date,
                "league": comp,
                "team": team_name,
                "opponent": opponent,
                "venue": s_match["venue"],
                "goals_for": s_match["gf"],
                "goals_against": s_match["ga"],
                "xg": xg,
                "xga": 0.0,  # Will be filled when processing opponent's perspective
                "result": get_result(s_match["gf"], s_match["ga"]),
                "possession": s_match["possession"],
                "shots": shots,
                "sot": sot,
            })

        return matches[:MATCHES_PER_TEAM]


# ============================================================
# MAIN
# ============================================================

def main():
    scraper = FBrefScraper()
    all_rows = []

    try:
        for i, team in enumerate(WC2026_TEAMS):
            print(f"[{i+1}/{len(WC2026_TEAMS)}] Scraping {team}...")
            matches = scraper.scrape_team_match_logs(team)
            print(f"    Got {len(matches)} matches")
            all_rows.extend(matches)

            # Rate limiting: delay between teams
            if i < len(WC2026_TEAMS) - 1:
                time.sleep(2)
    finally:
        scraper.close()

    # Compute opponent xGA by matching games
    print(f"\nTotal raw matches: {len(all_rows)}")

    # Deduplicate and compute xGA (opponent's xG)
    # Build a lookup
    match_lookup = {}
    for row in all_rows:
        key = (row["date"], row["team"], row["opponent"])
        match_lookup[key] = row

    for row in all_rows:
        # Find the opponent's perspective
        opp_key = (row["date"], row["opponent"], row["team"])
        if opp_key in match_lookup:
            row["xga"] = match_lookup[opp_key]["xg"]

    # Write CSV matching MatchRecord schema
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "date", "league", "team", "opponent", "venue",
        "goals_for", "goals_against", "xg", "xga", "result",
        "possession", "shots", "sot",
    ]

    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in all_rows:
            # Filter to only MatchRecord fields
            csv_row = {k: row.get(k, "") for k in fieldnames}
            writer.writerow(csv_row)

    print(f"\nSaved {len(all_rows)} rows to {OUTPUT_PATH}")
    print(f"Unique teams: {len(set(r['team'] for r in all_rows))}")

    # Print first 10 lines for verification
    print("\n--- First 10 lines of CSV ---")
    with open(OUTPUT_PATH) as f:
        for i, line in enumerate(f):
            if i < 11:
                print(line.rstrip())


if __name__ == "__main__":
    main()
