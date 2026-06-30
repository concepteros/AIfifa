"""Supplementary data module for World Cup 2026: weather, referees, and injuries.

Provides mock data for all WC 2026 venues and teams to augment
the prediction pipeline and deep analysis system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ── Dataclasses ─────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class WeatherData:
    """Weather conditions at a venue."""

    city: str
    temperature_c: float  # Celsius
    humidity_pct: float  # 0-100
    wind_kmh: float
    conditions: str  # e.g. "Clear", "Partly Cloudy", "Rain", "Thunderstorms"
    altitude_m: int = 0  # metres above sea level


@dataclass(frozen=True)
class RefereeProfile:
    """Profile of a match official."""

    name: str
    nationality: str
    strictness: float  # 0.0 (lenient) to 1.0 (very strict)
    card_tendency: float  # 0.0 (rarely cards) to 1.0 (card-happy)
    home_bias: float  # -0.5 (away bias) to +0.5 (home bias), 0 = neutral
    avg_yellows: float  # average yellow cards per match
    avg_reds: float  # average red cards per match
    var_usage: float  # 0.0 (rarely uses VAR) to 1.0 (VAR-heavy)


@dataclass(frozen=True)
class InjuredPlayer:
    """An injured or unavailable player."""

    name: str
    position: str  # goalkeeper, defender, midfielder, forward
    market_value_eur: float
    impact_score: float  # 0.0 (trivial) to 1.0 (catastrophic loss)
    status: str  # "out", "doubtful", "suspended"
    expected_return: str = ""  # e.g. "Group Stage MD3" or ""


# ── Venue Weather Data ──────────────────────────────────────────────────────

# June/July 2026 typical conditions for World Cup venues.
_VENUE_WEATHER: dict[str, WeatherData] = {
    # Mexico venues (altitude plays a huge role)
    "Mexico City": WeatherData(
        city="Mexico City",
        temperature_c=22.0,
        humidity_pct=55,
        wind_kmh=10,
        conditions="Partly Cloudy",
        altitude_m=2250,
    ),
    "Guadalajara": WeatherData(
        city="Guadalajara",
        temperature_c=28.0,
        humidity_pct=45,
        wind_kmh=8,
        conditions="Clear",
        altitude_m=1566,
    ),
    "Monterrey": WeatherData(
        city="Monterrey",
        temperature_c=33.0,
        humidity_pct=60,
        wind_kmh=14,
        conditions="Hot & Humid",
        altitude_m=540,
    ),
    # USA venues
    "Los Angeles": WeatherData(
        city="Los Angeles",
        temperature_c=27.0,
        humidity_pct=50,
        wind_kmh=12,
        conditions="Clear",
        altitude_m=93,
    ),
    "New York / New Jersey": WeatherData(
        city="New York / New Jersey",
        temperature_c=29.0,
        humidity_pct=65,
        wind_kmh=15,
        conditions="Partly Cloudy",
        altitude_m=5,
    ),
    "Dallas": WeatherData(
        city="Dallas",
        temperature_c=35.0,
        humidity_pct=55,
        wind_kmh=18,
        conditions="Hot",
        altitude_m=131,
    ),
    "Atlanta": WeatherData(
        city="Atlanta",
        temperature_c=31.0,
        humidity_pct=70,
        wind_kmh=10,
        conditions="Humid, Thunderstorms Possible",
        altitude_m=320,
    ),
    "Miami": WeatherData(
        city="Miami",
        temperature_c=32.0,
        humidity_pct=80,
        wind_kmh=16,
        conditions="Hot & Humid, Thunderstorms Likely",
        altitude_m=2,
    ),
    "Kansas City": WeatherData(
        city="Kansas City",
        temperature_c=30.0,
        humidity_pct=65,
        wind_kmh=18,
        conditions="Partly Cloudy",
        altitude_m=277,
    ),
    "Seattle": WeatherData(
        city="Seattle",
        temperature_c=22.0,
        humidity_pct=60,
        wind_kmh=12,
        conditions="Partly Cloudy, Light Rain Possible",
        altitude_m=50,
    ),
    "San Francisco / Bay Area": WeatherData(
        city="San Francisco / Bay Area",
        temperature_c=20.0,
        humidity_pct=70,
        wind_kmh=22,
        conditions="Overcast, Windy",
        altitude_m=5,
    ),
    "Boston": WeatherData(
        city="Boston",
        temperature_c=26.0,
        humidity_pct=60,
        wind_kmh=18,
        conditions="Partly Cloudy",
        altitude_m=14,
    ),
    "Houston": WeatherData(
        city="Houston",
        temperature_c=34.0,
        humidity_pct=75,
        wind_kmh=14,
        conditions="Hot & Humid",
        altitude_m=13,
    ),
    "Philadelphia": WeatherData(
        city="Philadelphia",
        temperature_c=29.0,
        humidity_pct=62,
        wind_kmh=14,
        conditions="Partly Cloudy",
        altitude_m=12,
    ),
    # Canada venues
    "Vancouver": WeatherData(
        city="Vancouver",
        temperature_c=20.0,
        humidity_pct=65,
        wind_kmh=12,
        conditions="Partly Cloudy",
        altitude_m=10,
    ),
    "Toronto": WeatherData(
        city="Toronto",
        temperature_c=26.0,
        humidity_pct=60,
        wind_kmh=16,
        conditions="Clear to Partly Cloudy",
        altitude_m=76,
    ),
}


# ── Referee Profiles ────────────────────────────────────────────────────────

_REFEREES: dict[str, RefereeProfile] = {}

_REFS_RAW = [
    ("Daniele Orsato", "Italy", 0.75, 0.60, 0.05, 3.8, 0.15, 0.3),
    ("Felix Zwayer", "Germany", 0.65, 0.55, 0.08, 3.5, 0.18, 0.4),
    ("Jesus Valenzuela", "Venezuela", 0.60, 0.65, -0.05, 4.2, 0.20, 0.2),
    ("Wilton Sampaio", "Brazil", 0.55, 0.50, 0.02, 3.2, 0.12, 0.3),
    ("Cesar Ramos", "Mexico", 0.58, 0.52, 0.10, 3.6, 0.14, 0.25),
    ("Tess Olofsson", "Sweden", 0.70, 0.45, -0.10, 3.0, 0.08, 0.35),
    ("Stephanie Frappart", "France", 0.72, 0.48, -0.05, 3.1, 0.10, 0.3),
    ("Abdulrahman Al-Jassim", "Qatar", 0.50, 0.55, 0.05, 3.4, 0.16, 0.2),
    ("Victor Gomes", "South Africa", 0.62, 0.58, 0.0, 3.7, 0.18, 0.25),
    ("Yamashita Yoshimi", "Japan", 0.68, 0.40, -0.08, 2.8, 0.06, 0.35),
    ("Drew Fischer", "Canada", 0.55, 0.50, 0.05, 3.0, 0.10, 0.3),
    ("Ismail Elfath", "USA", 0.60, 0.48, 0.08, 3.2, 0.12, 0.35),
    ("Salima Mukansanga", "Rwanda", 0.65, 0.52, 0.0, 3.5, 0.14, 0.25),
    ("Szymon Marciniak", "Poland", 0.70, 0.58, 0.03, 3.6, 0.16, 0.3),
    ("Michael Oliver", "England", 0.60, 0.50, -0.02, 3.0, 0.12, 0.35),
]

for name, nat, strict, card, bias, yel, red, var in _REFS_RAW:
    _REFEREES[name.casefold()] = RefereeProfile(
        name=name,
        nationality=nat,
        strictness=strict,
        card_tendency=card,
        home_bias=bias,
        avg_yellows=yel,
        avg_reds=red,
        var_usage=var,
    )

DEFAULT_REFEREE = RefereeProfile(
    name="Neutral Official",
    nationality="FIFA",
    strictness=0.60,
    card_tendency=0.50,
    home_bias=0.0,
    avg_yellows=3.4,
    avg_reds=0.14,
    var_usage=0.30,
)


# ── Injury Reports ──────────────────────────────────────────────────────────

# Key injuries / suspensions for WC 2026. These are semi-realistic based on
# late-2025/early-2026 form, age profiles, and known fitness concerns.
_INJURY_REPORTS: dict[str, list[InjuredPlayer]] = {
    "France": [],
    "England": [
        InjuredPlayer("John Stones", "defender", 38_000_000, 0.55, "doubtful", "Group Stage MD1"),
    ],
    "Spain": [
        InjuredPlayer("Rodri", "midfielder", 130_000_000, 0.85, "out", "Knockout Stage possible"),
    ],
    "Germany": [
        InjuredPlayer("Marc-Andre ter Stegen", "goalkeeper", 28_000_000, 0.45, "out", "Tournament"),
    ],
    "Portugal": [
        InjuredPlayer("Pepe", "defender", 5_000_000, 0.25, "doubtful", "Group Stage"),
    ],
    "Netherlands": [],
    "Italy": [
        InjuredPlayer("Federico Chiesa", "forward", 45_000_000, 0.60, "doubtful", "Group Stage MD2"),
    ],
    "Belgium": [
        InjuredPlayer("Thibaut Courtois", "goalkeeper", 40_000_000, 0.70, "out", "Tournament"),
    ],
    "Croatia": [],
    "Switzerland": [],
    "Denmark": [],
    "Austria": [],
    "Ukraine": [],
    "Serbia": [],
    "Poland": [],
    "Turkey": [],
    "Argentina": [
        InjuredPlayer("Angel Di Maria", "forward", 8_000_000, 0.30, "doubtful", "Group Stage"),
    ],
    "Brazil": [
        InjuredPlayer("Neymar", "forward", 30_000_000, 0.65, "out", "Tournament"),
        InjuredPlayer("Ederson", "goalkeeper", 35_000_000, 0.40, "doubtful", "Group Stage"),
    ],
    "Uruguay": [],
    "Colombia": [],
    "Ecuador": [],
    "Paraguay": [],
    "Chile": [],
    "USA": [],
    "Mexico": [
        InjuredPlayer("Santiago Gimenez", "forward", 50_000_000, 0.50, "doubtful", "Group Stage MD1"),
    ],
    "Canada": [],
    "Costa Rica": [],
    "Panama": [],
    "Jamaica": [],
    "Japan": [],
    "Iran": [],
    "South Korea": [],
    "Saudi Arabia": [],
    "Australia": [],
    "Uzbekistan": [],
    "UAE": [],
    "Qatar": [],
    "Morocco": [],
    "Senegal": [
        InjuredPlayer("Kalidou Koulibaly", "defender", 15_000_000, 0.50, "doubtful", "Group Stage"),
    ],
    "Nigeria": [
        InjuredPlayer("Samuel Chukwueze", "forward", 20_000_000, 0.35, "doubtful", "Group Stage MD3"),
    ],
    "Egypt": [],
    "Ivory Coast": [],
    "Algeria": [],
    "Tunisia": [],
    "Cameroon": [],
    "Ghana": [],
    "New Zealand": [],
    "Peru": [],
    "Honduras": [],
    "Sweden": [],
    "Norway": [
        InjuredPlayer("Martin Odegaard", "midfielder", 100_000_000, 0.75, "out", "Group Stage"),
    ],
    "Hungary": [],
    "Greece": [],
    "Scotland": [],
    "Wales": [],
    "Czech Republic": [],
    "Venezuela": [],
    "Bolivia": [],
    "South Africa": [],
}


# ── Public API ──────────────────────────────────────────────────────────────


def get_weather(venue_city: str) -> WeatherData | None:
    """Return weather data for a World Cup venue city.

    Args:
        venue_city: City name (e.g. "Mexico City", "Los Angeles").

    Returns:
        WeatherData if the city is a known venue, else None.
    """
    return _VENUE_WEATHER.get(venue_city.strip())


def get_referee_profile(match: dict[str, Any] | str) -> RefereeProfile:
    """Get referee profile for a match.

    Args:
        match: Either a dict with 'referee' key, or a referee name string.

    Returns:
        RefereeProfile for the match official, or DEFAULT_REFEREE.
    """
    if isinstance(match, dict):
        ref_name = (
            match.get("referee")
            or match.get("official")
            or match.get("fixture", {}).get("referee", "")
        )
    else:
        ref_name = match

    if not ref_name or not str(ref_name).strip():
        return DEFAULT_REFEREE

    return _REFEREES.get(str(ref_name).strip().casefold(), DEFAULT_REFEREE)


def get_injury_report(team: str) -> list[InjuredPlayer]:
    """Return the injury report for a given team.

    Args:
        team: Team name (case-insensitive).

    Returns:
        List of InjuredPlayer records; empty list if no injuries.
    """
    # Try exact match first, then case-insensitive partial match.
    key = team.strip().casefold()

    # Direct lookup
    if key in _INJURY_REPORTS:
        return _INJURY_REPORTS[key]

    # Fuzzy: check if any registered team contains the query
    for registered in _INJURY_REPORTS:
        if registered.casefold() in key or key in registered.casefold():
            return _INJURY_REPORTS[registered]

    return []


def get_total_injury_impact(team: str) -> float:
    """Compute aggregate injury impact score for a team.

    Returns a float 0.0 (no issues) to theoretically ~5.0 (devastated).
    """
    injuries = get_injury_report(team)
    return round(sum(p.impact_score for p in injuries), 4)


def list_venues() -> list[str]:
    """Return all World Cup venue cities."""
    return sorted(_VENUE_WEATHER.keys())


def list_referees() -> list[str]:
    """Return all registered referee names."""
    return sorted(r.name for r in _REFEREES.values())


def weather_impact_summary(venue_city: str) -> str:
    """Generate a human-readable weather impact assessment for a venue.

    Returns a one-line summary suitable for deep analysis display.
    """
    weather = get_weather(venue_city)
    if weather is None:
        return f"场馆 {venue_city} 暂无天气数据"

    parts = [f"{weather.city}：{weather.conditions}，{weather.temperature_c:.0f}°C"]

    if weather.humidity_pct > 75:
        parts.append("高湿度影响球员体能消耗")
    if weather.temperature_c > 32:
        parts.append("高温可能需要补水暂停")
    if weather.temperature_c < 10:
        parts.append("低温可能影响肌肉表现")
    if weather.wind_kmh > 25:
        parts.append("大风影响长传和高球精度")
    if weather.altitude_m > 1500:
        parts.append(f"高海拔 ({weather.altitude_m}m) 对不适应球队是显著劣势")
    if weather.altitude_m > 2000:
        parts.append("极高海拔，球速和球员耐力均受影响")

    if len(parts) == 1:
        return f"{weather.city}：{weather.conditions}，{weather.temperature_c:.0f}°C，条件良好"

    return "，".join(parts)


def referee_impact_summary(match: dict[str, Any] | str) -> str:
    """Generate a human-readable referee impact summary.

    Args:
        match: Match dict with referee info, or referee name string.

    Returns:
        A one-line Chinese summary of how the referee might affect the match.
    """
    ref = get_referee_profile(match)
    impacts: list[str] = []

    if ref.strictness > 0.70:
        impacts.append("执法严格，身体对抗较多的球队需谨慎")
    elif ref.strictness < 0.45:
        impacts.append("执法宽松，身体对抗将被允许更多")

    if ref.card_tendency > 0.60:
        impacts.append("出牌倾向高，防守型球队需注意纪律")
    elif ref.card_tendency < 0.35:
        impacts.append("出牌率低，比赛流畅度较高")

    if ref.home_bias > 0.10:
        impacts.append("主场倾向微偏主队")
    elif ref.home_bias < -0.10:
        impacts.append("稀有：略偏客队")

    if ref.var_usage > 0.40:
        impacts.append("VAR介入频率高，关键判罚可能被复审")

    base = f"主裁 {ref.name} ({ref.nationality})：场均黄牌{ref.avg_yellows}张/红牌{ref.avg_reds}张"
    if impacts:
        return f"{base}——{'; '.join(impacts)}"
    return base


def injury_report_summary(team: str) -> str:
    """Generate a concise injury summary for display."""
    injuries = get_injury_report(team)
    if not injuries:
        return f"{team}：全员健康，无重大伤病"

    out_list = [p for p in injuries if p.status == "out"]
    doubt_list = [p for p in injuries if p.status == "doubtful"]
    susp_list = [p for p in injuries if p.status == "suspended"]

    parts: list[str] = []
    if out_list:
        parts.append(
            f"缺阵 {len(out_list)} 人：{'、'.join(p.name for p in out_list)}"
        )
    if doubt_list:
        parts.append(
            f"出战成疑 {len(doubt_list)} 人：{'、'.join(p.name for p in doubt_list)}"
        )
    if susp_list:
        parts.append(
            f"停赛 {len(susp_list)} 人：{'、'.join(p.name for p in susp_list)}"
        )

    impact = get_total_injury_impact(team)
    severity = "轻度" if impact < 0.3 else ("中度" if impact < 0.7 else "严重")
    return f"{team} 伤病情况 [{severity}，影响指数 {impact:.2f}]：{'；'.join(parts)}"


# ── Match → Referee Assignment ──────────────────────────────────────────────
# Deterministic assignment based on matchup hash, ensuring the same pairing
# always gets the same referee. Uses neutral-confederation logic where possible.

# Referee list for assignment (name, confederation)
_REFEREE_POOL: list[tuple[str, str]] = [
    ("Daniele Orsato", "UEFA"),
    ("Felix Zwayer", "UEFA"),
    ("Jesus Valenzuela", "CONMEBOL"),
    ("Wilton Sampaio", "CONMEBOL"),
    ("Cesar Ramos", "CONCACAF"),
    ("Tess Olofsson", "UEFA"),
    ("Stephanie Frappart", "UEFA"),
    ("Abdulrahman Al-Jassim", "AFC"),
    ("Victor Gomes", "CAF"),
    ("Yamashita Yoshimi", "AFC"),
    ("Drew Fischer", "CONCACAF"),
    ("Ismail Elfath", "CONCACAF"),
    ("Salima Mukansanga", "CAF"),
    ("Szymon Marciniak", "UEFA"),
    ("Michael Oliver", "UEFA"),
]

# Team confederation mapping (48 teams)
_TEAM_CONFED: dict[str, str] = {
    # UEFA
    "France": "UEFA", "England": "UEFA", "Spain": "UEFA", "Germany": "UEFA",
    "Portugal": "UEFA", "Netherlands": "UEFA", "Italy": "UEFA", "Belgium": "UEFA",
    "Croatia": "UEFA", "Switzerland": "UEFA", "Denmark": "UEFA", "Austria": "UEFA",
    "Ukraine": "UEFA", "Serbia": "UEFA", "Poland": "UEFA", "Turkey": "UEFA",
    "Sweden": "UEFA", "Norway": "UEFA", "Hungary": "UEFA", "Greece": "UEFA",
    "Scotland": "UEFA", "Wales": "UEFA", "Czech Republic": "UEFA",
    # CONMEBOL
    "Argentina": "CONMEBOL", "Brazil": "CONMEBOL", "Uruguay": "CONMEBOL",
    "Colombia": "CONMEBOL", "Ecuador": "CONMEBOL", "Paraguay": "CONMEBOL",
    "Chile": "CONMEBOL", "Peru": "CONMEBOL", "Venezuela": "CONMEBOL", "Bolivia": "CONMEBOL",
    # CONCACAF
    "USA": "CONCACAF", "Mexico": "CONCACAF", "Canada": "CONCACAF",
    "Costa Rica": "CONCACAF", "Panama": "CONCACAF", "Jamaica": "CONCACAF",
    "Honduras": "CONCACAF", "Curaçao": "CONCACAF", "Haiti": "CONCACAF",
    # AFC
    "Japan": "AFC", "Iran": "AFC", "South Korea": "AFC", "Saudi Arabia": "AFC",
    "Australia": "AFC", "Uzbekistan": "AFC", "UAE": "AFC", "Qatar": "AFC",
    "Iraq": "AFC", "Jordan": "AFC",
    # CAF
    "Morocco": "CAF", "Senegal": "CAF", "Nigeria": "CAF", "Egypt": "CAF",
    "Ivory Coast": "CAF", "Algeria": "CAF", "Tunisia": "CAF", "Cameroon": "CAF",
    "Ghana": "CAF", "South Africa": "CAF", "DR Congo": "CAF", "Cape Verde": "CAF",
    # OFC
    "New Zealand": "OFC",
    # Bosnia
    "Bosnia & Herzegovina": "UEFA",
}


def get_match_referee(home_team: str, away_team: str) -> str:
    """Assign a referee to a match based on neutral-confederation logic.

    Uses a deterministic hash to ensure same matchup always gets same ref.
    Prefers referees from confederations different from both teams.
    """
    import hashlib

    h_conf = _TEAM_CONFED.get(home_team, "")
    a_conf = _TEAM_CONFED.get(away_team, "")

    key = "|".join(sorted([home_team.casefold(), away_team.casefold()]))
    hash_val = int(hashlib.md5(key.encode()).hexdigest()[:8], 16)

    # Prefer neutral refs (different confederation from both teams)
    neutral = [
        (name, conf)
        for name, conf in _REFEREE_POOL
        if conf != h_conf and conf != a_conf
    ]
    pool = neutral if neutral else _REFEREE_POOL
    idx = hash_val % len(pool)
    return pool[idx][0]


def get_match_referee_profile(home_team: str, away_team: str) -> "RefereeProfile":
    """Get the RefereeProfile for an automatically assigned match referee.

    Args:
        home_team: Home team name.
        away_team: Away team name.

    Returns:
        RefereeProfile for the assigned referee.
    """
    ref_name = get_match_referee(home_team, away_team)
    return get_referee_profile(ref_name)


def get_match_supplementary_context(
    home_team: str,
    away_team: str,
    *,
    venue_city: str = "",
    referee: str = "",
) -> dict[str, Any]:
    """Build a comprehensive supplementary context dict for a fixture.

    This can be piped directly into the prediction pipeline or
    deep analysis context.

    Args:
        home_team: Home team name.
        away_team: Away team name.
        venue_city: Optional venue city for weather data.
        referee: Optional referee name.

    Returns:
        Dict with weather, referee, and injury data for both teams.
    """
    weather = get_weather(venue_city) if venue_city else None
    ref_profile = get_referee_profile(referee) if referee else DEFAULT_REFEREE
    home_injuries = get_injury_report(home_team)
    away_injuries = get_injury_report(away_team)

    return {
        "weather": weather,
        "referee": ref_profile,
        "home_injuries": home_injuries,
        "away_injuries": away_injuries,
        "home_injury_impact": get_total_injury_impact(home_team),
        "away_injury_impact": get_total_injury_impact(away_team),
    }
