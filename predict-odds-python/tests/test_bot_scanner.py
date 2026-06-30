import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from predict_odds.bot_scanner import scan_upcoming_matches
from predict_odds.cli import main
from predict_odds.repository import BotRepository


class BotScannerTest(unittest.TestCase):
    def test_repository_persists_scan_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "bot.sqlite"
            repository = BotRepository(db_path)
            run_id = repository.create_run({"sport": "soccer_epl"})
            repository.save_match_result(
                run_id,
                {
                    "fixture": {"home_team": "Arsenal", "away_team": "Chelsea", "date": "2026-06-20", "league": "Premier League"},
                    "prediction": {"model": "poisson_v2"},
                    "decisions": {"recommendations": [{"market": "home_win", "action": "bet"}]},
                    "result_path": "out/result.json",
                },
            )
            repository.finish_run(run_id, status="ok")

            rows = repository.list_runs()

        self.assertEqual(rows[0]["status"], "ok")
        self.assertEqual(rows[0]["matches"], 1)

    def test_scans_events_and_processes_matching_local_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = _write_scan_config(tmp)
            events = [_event("event-1", "Arsenal", "Chelsea"), _event("event-2", "Liverpool", "Everton")]
            sent = []

            result = scan_upcoming_matches(
                config_path,
                odds_events=events,
                telegram_sender=sent.append,
            )

            self.assertEqual(result["processed"], 1)
            self.assertEqual(result["skipped"], 1)
            self.assertEqual(result["matches"][0]["fixture"]["home_team"], "Arsenal")
            self.assertTrue(Path(result["matches"][0]["result_path"]).exists())
            self.assertEqual(len(sent), 0)
            repository = BotRepository(Path(tmp) / "bot.sqlite")
            self.assertEqual(repository.list_runs()[0]["matches"], 1)

    def test_scan_cli_prints_summary_with_injected_events_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = _write_scan_config(tmp, notify=False)
            events_path = Path(tmp) / "events.json"
            events_path.write_text(json.dumps([_event("event-1", "Arsenal", "Chelsea")]), encoding="utf-8")

            with patch("sys.stdout"):
                code = main(["scan", "--config", str(config_path), "--events-file", str(events_path), "--compact"])

        self.assertEqual(code, 0)

    def test_scanner_fetches_from_configured_market_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = _write_scan_config(tmp, notify=False)

            with patch("predict_odds.bot_scanner.fetch_market_events", return_value=[_event("event-1", "Arsenal", "Chelsea")]) as fetch:
                result = scan_upcoming_matches(config_path)

        self.assertEqual(result["processed"], 1)
        fetch.assert_called_once()
        self.assertIn("scan", fetch.call_args.args[0])

    def test_scanner_accepts_pre_normalized_market_source_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = _write_scan_config(tmp, notify=False)
            events = [
                {
                    "event_id": "merged-1",
                    "home_team": "Arsenal",
                    "away_team": "Chelsea",
                    "commence_time": "2026-06-20T19:00:00Z",
                    "markets": {"home_win": 2.2, "draw": 3.4, "away_win": 3.0},
                    "sources": ["the_odds_api", "predict_fun", "polymarket"],
                }
            ]

            with patch("predict_odds.bot_scanner.fetch_market_events", return_value=events):
                result = scan_upcoming_matches(config_path)

        self.assertEqual(result["processed"], 1)
        self.assertEqual(result["matches"][0]["odds"]["markets"]["home_win"], 2.2)
        self.assertEqual(result["matches"][0]["odds"]["sources"], ["the_odds_api", "predict_fun", "polymarket"])


def _write_scan_config(tmp: str, *, notify: bool = True) -> Path:
    root = Path(tmp)
    fbref = root / "fbref.csv"
    transfermarkt = root / "transfermarkt.csv"
    output_dir = root / "out"
    fbref.write_text(
        "date,league,team,opponent,venue,goals_for,goals_against,xg,xga,result\n"
        "2026-06-01,Premier League,Arsenal,Chelsea,home,2,1,1.8,1.1,W\n"
        "2026-06-08,Premier League,Arsenal,Spurs,away,1,1,1.2,1.0,D\n"
        "2026-06-01,Premier League,Chelsea,Arsenal,away,1,2,1.1,1.8,L\n"
        "2026-06-08,Premier League,Chelsea,Spurs,home,3,0,2.2,0.7,W\n",
        encoding="utf-8",
    )
    transfermarkt.write_text(
        "team,player,position,market_value_eur,status,days_out\n"
        "Arsenal,Forward,Forward,50000000,injured,21\n"
        "Chelsea,Defender,Defender,40000000,injured,14\n",
        encoding="utf-8",
    )
    config = {
        "scan": {
            "sport": "soccer_epl",
            "regions": "eu",
            "markets": ["h2h", "totals", "spreads"],
            "league": "Premier League",
            "date": "2026-06-20",
        },
        "data": {"fbref": str(fbref), "transfermarkt": str(transfermarkt)},
        "decision": {"bankroll": 1000, "min_edge": 0.03, "fractional_kelly": 0.25, "max_stake_fraction": 0.05},
        "output": {"directory": str(output_dir)},
        "database": {"path": str(root / "bot.sqlite")},
        "telegram": {"enabled": notify},
    }
    config_path = root / "scan.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    return config_path


def _event(event_id: str, home: str, away: str) -> dict:
    return {
        "id": event_id,
        "home_team": home,
        "away_team": away,
        "commence_time": "2026-06-20T19:00:00Z",
        "bookmakers": [
            {
                "markets": [
                    {
                        "key": "h2h",
                        "outcomes": [
                            {"name": home, "price": 2.1},
                            {"name": away, "price": 3.0},
                            {"name": "Draw", "price": 3.4},
                        ],
                    }
                ]
            }
        ],
    }


if __name__ == "__main__":
    unittest.main()
