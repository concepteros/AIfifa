import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from predict_odds.bot_scanner import scan_upcoming_matches
from predict_odds.cli import main
from predict_odds.doctor import check_bot_health
from predict_odds.env_loader import load_env_file
from predict_odds.retry import retry_call
from predict_odds.workflow import run_workflow


class EnvLoaderTest(unittest.TestCase):
    def test_loads_env_file_without_overriding_existing_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text("A=from_file\nB=\"quoted value\"\n# ignored\n", encoding="utf-8")
            with patch.dict(os.environ, {"A": "existing"}, clear=False):
                loaded = load_env_file(env_path)

                self.assertEqual(os.environ["A"], "existing")
                self.assertEqual(os.environ["B"], "quoted value")
                self.assertEqual(loaded, {"B": "quoted value"})

    def test_loads_env_file_with_utf8_bom(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text("\ufeffPREDICT_API_KEY=secret\n", encoding="utf-8")
            with patch.dict(os.environ, {}, clear=True):
                loaded = load_env_file(env_path)

                self.assertEqual(os.environ["PREDICT_API_KEY"], "secret")
                self.assertEqual(loaded, {"PREDICT_API_KEY": "secret"})


class RetryTest(unittest.TestCase):
    def test_retries_until_success(self):
        attempts = {"count": 0}

        def flaky():
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise RuntimeError("temporary")
            return "ok"

        self.assertEqual(retry_call(flaky, attempts=3, delay_seconds=0), "ok")
        self.assertEqual(attempts["count"], 3)

    def test_raises_after_retry_exhaustion(self):
        with self.assertRaises(RuntimeError):
            retry_call(lambda: (_ for _ in ()).throw(RuntimeError("nope")), attempts=2, delay_seconds=0)


class DoctorTest(unittest.TestCase):
    def test_reports_healthy_scan_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = _write_scan_config(tmp)
            env_path = Path(tmp) / ".env"
            env_path.write_text("THE_ODDS_API_KEY=abc\nTELEGRAM_BOT_TOKEN=bot\nTELEGRAM_CHAT_ID=chat\n", encoding="utf-8")

            report = check_bot_health(config_path=config_path, env_file=env_path, mode="scan", skip_network=True)

        self.assertTrue(report["ok"])
        self.assertTrue(all(check["ok"] for check in report["checks"]))

    def test_reports_missing_required_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = _write_scan_config(tmp)
            with patch.dict(os.environ, {"THE_ODDS_API_KEY": ""}, clear=False):
                report = check_bot_health(config_path=config_path, mode="scan", skip_network=True)

        self.assertFalse(report["ok"])
        self.assertTrue(any(check["name"] == "env:THE_ODDS_API_KEY" and not check["ok"] for check in report["checks"]))

    def test_doctor_cli_prints_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = _write_scan_config(tmp)
            env_path = Path(tmp) / ".env"
            env_path.write_text("THE_ODDS_API_KEY=abc\nTELEGRAM_BOT_TOKEN=bot\nTELEGRAM_CHAT_ID=chat\n", encoding="utf-8")
            with patch("sys.stdout") as stdout:
                code = main(["--env-file", str(env_path), "doctor", "--config", str(config_path), "--mode", "scan", "--skip-network", "--compact"])

        self.assertEqual(code, 0)
        output = "".join(call.args[0] for call in stdout.write.call_args_list if call.args)
        self.assertTrue(json.loads(output)["ok"])


class ErrorNotificationTest(unittest.TestCase):
    def test_workflow_sends_telegram_error_summary_when_enabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = _write_workflow_config(tmp, missing_odds=True)
            sent = []

            with self.assertRaises(Exception):
                run_workflow(config_path, telegram_sender=sent.append)

        self.assertEqual(len(sent), 1)
        self.assertIn("Workflow failed", sent[0])

    def test_scan_sends_telegram_error_summary_when_enabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = _write_scan_config(tmp, missing_fbref=True)
            sent = []

            with self.assertRaises(Exception):
                scan_upcoming_matches(config_path, odds_events=[], telegram_sender=sent.append)

        self.assertEqual(len(sent), 1)
        self.assertIn("Scan failed", sent[0])


def _write_scan_config(tmp: str, *, missing_fbref: bool = False) -> Path:
    root = Path(tmp)
    fbref = root / "fbref.csv"
    transfermarkt = root / "transfermarkt.csv"
    if not missing_fbref:
        fbref.write_text(
            "date,league,team,opponent,venue,goals_for,goals_against,xg,xga,result\n"
            "2026-06-01,Premier League,Arsenal,Chelsea,home,2,1,1.8,1.1,W\n",
            encoding="utf-8",
        )
    transfermarkt.write_text(
        "team,player,position,market_value_eur,status,days_out\n"
        "Arsenal,Forward,Forward,50000000,injured,21\n",
        encoding="utf-8",
    )
    config = {
        "scan": {"sport": "soccer_epl", "regions": "eu", "markets": ["h2h"], "league": "Premier League", "date": "2026-06-20"},
        "data": {"fbref": str(fbref), "transfermarkt": str(transfermarkt)},
        "decision": {"bankroll": 1000},
        "output": {"directory": str(root / "out")},
        "database": {"path": str(root / "bot.sqlite")},
        "telegram": {"enabled": True},
    }
    path = root / "scan.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    return path


def _write_workflow_config(tmp: str, *, missing_odds: bool = False) -> Path:
    root = Path(tmp)
    fbref = root / "fbref.csv"
    transfermarkt = root / "transfermarkt.csv"
    odds = root / "odds.json"
    fbref.write_text(
        "date,league,team,opponent,venue,goals_for,goals_against,xg,xga,result\n"
        "2026-06-01,Premier League,Arsenal,Chelsea,home,2,1,1.8,1.1,W\n"
        "2026-06-01,Premier League,Chelsea,Arsenal,away,1,2,1.1,1.8,L\n",
        encoding="utf-8",
    )
    transfermarkt.write_text("team,player,position,market_value_eur,status,days_out\n", encoding="utf-8")
    if not missing_odds:
        odds.write_text(json.dumps({"home_win": 2.1}), encoding="utf-8")
    config = {
        "fixture": {"league": "Premier League", "date": "2026-06-20", "home_team": "Arsenal", "away_team": "Chelsea"},
        "data": {"fbref": str(fbref), "transfermarkt": str(transfermarkt), "odds": str(odds)},
        "decision": {"bankroll": 1000},
        "output": {"directory": str(root / "out")},
        "telegram": {"enabled": True},
    }
    path = root / "workflow.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    return path


if __name__ == "__main__":
    unittest.main()
