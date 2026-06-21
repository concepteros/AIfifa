import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from predict_odds.cli import main
from predict_odds.repository import BotRepository
from predict_odds.telegram_panel import (
    TelegramPanelConfig,
    TelegramPanelService,
    build_dashboard_keyboard,
    load_panel_config,
)


class TelegramPanelConfigTest(unittest.TestCase):
    def test_loads_panel_config_with_limits_and_allowed_chats(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "panel.json"
            scan_config = Path(tmp) / "scan.json"
            db_path = Path(tmp) / "bot.sqlite"
            path.write_text(
                json.dumps(
                    {
                        "telegram_panel": {
                            "bot_token_env": "BOT_TOKEN",
                            "allowed_chat_ids": ["123"],
                            "scan_config": str(scan_config),
                            "database": str(db_path),
                            "limits": {"daily_stake": 100, "max_single_stake": 25},
                        }
                    }
                ),
                encoding="utf-8",
            )

            config = load_panel_config(path)

        self.assertEqual(config.bot_token_env, "BOT_TOKEN")
        self.assertEqual(config.allowed_chat_ids, {"123"})
        self.assertEqual(config.scan_config, scan_config)
        self.assertEqual(config.database, db_path)
        self.assertEqual(config.limits["daily_stake"], 100)

    def test_loads_panel_config_with_utf8_bom(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "panel.json"
            path.write_text(
                '\ufeff{"telegram_panel":{"scan_config":"scan.json","database":"bot.sqlite"}}',
                encoding="utf-8",
            )

            config = load_panel_config(path)

        self.assertEqual(config.scan_config.name, "scan.json")

    def test_authorizes_configured_chat_ids(self):
        config = TelegramPanelConfig(
            config_path=Path("panel.json"),
            scan_config=Path("scan.json"),
            database=Path("bot.sqlite"),
            allowed_chat_ids={"123"},
        )

        self.assertTrue(config.is_authorized(123))
        self.assertFalse(config.is_authorized(456))


class TelegramPanelServiceTest(unittest.TestCase):
    def test_dashboard_summarizes_runs_report_and_limits(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = _panel_config(tmp)
            repository = BotRepository(config.database)
            run_id = repository.create_run({"scan": "demo"})
            repository.save_match_result(run_id, _match_result())
            repository.finish_run(run_id, status="ok")

            service = TelegramPanelService(config)
            message = service.dashboard()

        self.assertIn("AI Football Betting Bot", message)
        self.assertIn("Last run: ok, matches 1", message)
        self.assertIn("Daily stake limit: 100.0", message)

    def test_upcoming_uses_market_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = _panel_config(tmp)
            with patch("predict_odds.telegram_panel.fetch_market_events", return_value=[_normalized_event()]):
                message = TelegramPanelService(config).upcoming()

        self.assertIn("Upcoming Matches", message)
        self.assertIn("Arsenal vs Chelsea", message)
        self.assertIn("home_win 2.2", message)

    def test_scan_runs_pipeline_and_returns_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = _panel_config(tmp)
            with patch(
                "predict_odds.telegram_panel.scan_upcoming_matches",
                return_value={"processed": 1, "skipped": 0, "matches": [_match_result()]},
            ):
                message = TelegramPanelService(config).scan()

        self.assertIn("Scan complete", message)
        self.assertIn("Processed: 1", message)
        self.assertIn("Top value: home_win", message)

    def test_history_reads_recent_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = _panel_config(tmp)
            repository = BotRepository(config.database)
            run_id = repository.create_run({"scan": "demo"})
            repository.finish_run(run_id, status="ok")

            message = TelegramPanelService(config).history()

        self.assertIn("Recent Runs", message)
        self.assertIn("#1 ok matches 0", message)

    def test_set_limit_updates_config_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = _panel_config(tmp)
            service = TelegramPanelService(config)

            message = service.set_limit("daily_stake", "250")
            updated = load_panel_config(config.config_path)

        self.assertIn("daily_stake set to 250.0", message)
        self.assertEqual(updated.limits["daily_stake"], 250.0)

    def test_approve_signal_writes_decision_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = _panel_config(tmp)
            service = TelegramPanelService(config)

            message = service.approve_signal("match-1", approved=True)
            payload = json.loads(config.approvals_path.read_text(encoding="utf-8"))

        self.assertIn("approved", message)
        self.assertEqual(payload["decisions"][0]["signal_id"], "match-1")
        self.assertTrue(payload["decisions"][0]["approved"])

    def test_dashboard_keyboard_uses_inline_buttons(self):
        keyboard = build_dashboard_keyboard()

        self.assertEqual(keyboard[0][0]["text"], "Scan Now")
        self.assertEqual(keyboard[0][0]["callback_data"], "dashboard:scan")

    def test_cli_starts_telegram_panel(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = _panel_config(tmp)

            with patch("predict_odds.cli.run_telegram_panel") as runner:
                code = main(["telegram-panel", "--config", str(config.config_path)])

        self.assertEqual(code, 0)
        runner.assert_called_once_with(str(config.config_path))


def _panel_config(tmp: str) -> TelegramPanelConfig:
    root = Path(tmp)
    scan_config = root / "scan.json"
    scan_config.write_text(json.dumps({"scan": {"league": "Premier League", "date": "2026-06-20"}}), encoding="utf-8")
    config_path = root / "panel.json"
    config_path.write_text(
        json.dumps(
            {
                "telegram_panel": {
                    "scan_config": str(scan_config),
                    "database": str(root / "bot.sqlite"),
                    "approvals": str(root / "approvals.json"),
                    "allowed_chat_ids": ["123"],
                    "limits": {"daily_stake": 100.0, "max_single_stake": 25.0},
                }
            }
        ),
        encoding="utf-8",
    )
    return load_panel_config(config_path)


def _normalized_event():
    return {
        "event_id": "event-1",
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "commence_time": "2026-06-20T19:00:00Z",
        "markets": {"home_win": 2.2, "draw": 3.4, "away_win": 3.0},
        "sources": ["the_odds_api", "predict_fun"],
    }


def _match_result():
    return {
        "fixture": {"league": "Premier League", "date": "2026-06-20", "home_team": "Arsenal", "away_team": "Chelsea"},
        "prediction": {"model": "poisson_v1"},
        "decisions": {
            "recommendations": [
                {"market": "home_win", "action": "bet", "expected_value": 0.12, "stake": 20.0},
                {"market": "draw", "action": "no_bet", "expected_value": -0.1, "stake": 0.0},
            ]
        },
        "result_path": "out/result.json",
    }


if __name__ == "__main__":
    unittest.main()
