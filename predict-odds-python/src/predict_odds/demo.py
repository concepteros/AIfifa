from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .bot_scanner import scan_upcoming_matches
from .settlement import build_performance_report, settle_database


def run_demo(output_dir: str | Path) -> dict[str, Any]:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    paths = _write_demo_files(root)
    events = json.loads(paths["events"].read_text(encoding="utf-8"))
    scan = scan_upcoming_matches(paths["config"], odds_events=events)
    settlement = settle_database(paths["database"], paths["results"], closing_odds_path=paths["closing_odds"])
    report = build_performance_report(paths["database"])
    return {
        "output_dir": str(root),
        "config": str(paths["config"]),
        "database": str(paths["database"]),
        "scan": scan,
        "settlement": settlement,
        "report": report,
    }


def _write_demo_files(root: Path) -> dict[str, Path]:
    paths = {
        "config": root / "bot-scan.json",
        "fbref": root / "fbref.csv",
        "transfermarkt": root / "transfermarkt.csv",
        "events": root / "events.json",
        "results": root / "results.csv",
        "closing_odds": root / "closing_odds.csv",
        "database": root / "bot.sqlite",
        "out": root / "out",
    }
    paths["fbref"].write_text(_fbref_csv(), encoding="utf-8")
    paths["transfermarkt"].write_text(_transfermarkt_csv(), encoding="utf-8")
    paths["events"].write_text(json.dumps(_events(), ensure_ascii=False, indent=2), encoding="utf-8")
    paths["results"].write_text(_results_csv(), encoding="utf-8")
    paths["closing_odds"].write_text(_closing_odds_csv(), encoding="utf-8")
    config = {
        "odds_sources": ["the_odds_api", "predict_fun", "polymarket"],
        "scan": {
            "sport": "soccer_epl",
            "regions": "eu",
            "markets": ["h2h", "totals", "spreads"],
            "league": "Premier League",
            "date": "2026-06-20",
        },
        "polymarket": {
            "query": "Premier League Arsenal Chelsea",
            "limit": 100,
            "active": True,
            "closed": False,
        },
        "data": {
            "fbref": str(paths["fbref"]),
            "transfermarkt": str(paths["transfermarkt"]),
        },
        "decision": {
            "bankroll": 1000,
            "min_edge": 0.01,
            "fractional_kelly": 0.25,
            "max_stake_fraction": 0.05,
        },
        "output": {"directory": str(paths["out"])},
        "database": {"path": str(paths["database"])},
        "telegram": {"enabled": False},
    }
    paths["config"].write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    return paths


def _fbref_csv() -> str:
    return (
        "date,league,team,opponent,venue,goals_for,goals_against,xg,xga,result\n"
        "2026-06-01,Premier League,Arsenal,Chelsea,home,2,1,1.8,1.1,W\n"
        "2026-06-08,Premier League,Arsenal,Spurs,away,1,1,1.2,1.0,D\n"
        "2026-06-01,Premier League,Chelsea,Arsenal,away,1,2,1.1,1.8,L\n"
        "2026-06-08,Premier League,Chelsea,Spurs,home,3,0,2.2,0.7,W\n"
    )


def _transfermarkt_csv() -> str:
    return (
        "team,player,position,market_value_eur,status,days_out\n"
        "Arsenal,Forward,Forward,50000000,injured,21\n"
        "Chelsea,Defender,Defender,40000000,injured,14\n"
    )


def _events() -> list[dict[str, Any]]:
    return [
        {
            "id": "demo-event-1",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "commence_time": "2026-06-20T19:00:00Z",
            "bookmakers": [
                {
                    "key": "demo_book",
                    "markets": [
                        {
                            "key": "h2h",
                            "outcomes": [
                                {"name": "Arsenal", "price": 2.1},
                                {"name": "Chelsea", "price": 3.0},
                                {"name": "Draw", "price": 3.4},
                            ],
                        },
                        {
                            "key": "totals",
                            "outcomes": [
                                {"name": "Over", "price": 1.9, "point": 2.5},
                                {"name": "Under", "price": 1.95, "point": 2.5},
                            ],
                        },
                    ],
                }
            ],
        }
    ]


def _results_csv() -> str:
    return (
        "date,league,home_team,away_team,home_goals,away_goals\n"
        "2026-06-20,Premier League,Arsenal,Chelsea,2,1\n"
    )


def _closing_odds_csv() -> str:
    return (
        "date,league,home_team,away_team,market,closing_odds\n"
        "2026-06-20,Premier League,Arsenal,Chelsea,away_win,2.8\n"
        "2026-06-20,Premier League,Arsenal,Chelsea,over_2_5,1.82\n"
    )
