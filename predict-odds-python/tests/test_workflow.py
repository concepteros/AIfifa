import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from predict_odds.cli import main
from predict_odds.scheduler import configure_daily_job
from predict_odds.telegram import format_telegram_summary
from predict_odds.workflow import run_workflow


class WorkflowTest(unittest.TestCase):
    def test_runs_full_workflow_and_writes_result_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = _write_config(tmp)
            sent = []

            result = run_workflow(config_path, telegram_sender=sent.append)

            self.assertEqual(result["fixture"]["home_team"], "Arsenal")
            self.assertEqual(result["prediction"]["model"], "poisson_v1")
            self.assertEqual(result["decisions"]["recommendations"][0]["action"], "bet")
            result_path = Path(result["result_path"])
            self.assertTrue(result_path.exists())
            persisted = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(persisted["prediction"]["model"], "poisson_v1")
            self.assertEqual(len(sent), 1)
            self.assertIn("Arsenal vs Chelsea", sent[0])

    def test_formats_telegram_summary_with_top_recommendation(self):
        result = {
            "fixture": {"league": "Premier League", "date": "2026-06-20", "home_team": "Arsenal", "away_team": "Chelsea"},
            "prediction": {
                "expected_goals": {"home": 1.6, "away": 1.1},
                "most_likely_scores": [{"score": "1-1", "probability": 0.12}],
            },
            "decisions": {
                "recommendations": [
                    {"market": "home_win", "action": "bet", "expected_value": 0.09, "stake": 20.5},
                    {"market": "draw", "action": "no_bet", "expected_value": -0.1, "stake": 0},
                ]
            },
            "result_path": "out/result.json",
        }

        summary = format_telegram_summary(result)

        self.assertIn("Premier League", summary)
        self.assertIn("Arsenal vs Chelsea", summary)
        self.assertIn("home_win", summary)
        self.assertIn("20.5", summary)
        self.assertIn("out/result.json", summary)

    def test_run_cli_prints_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = _write_config(tmp, notify=False)
            with patch("sys.stdout") as stdout:
                code = main(["run", "--config", str(config_path), "--compact"])

        self.assertEqual(code, 0)
        output = "".join(call.args[0] for call in stdout.write.call_args_list if call.args)
        payload = json.loads(output)
        self.assertEqual(payload["fixture"]["away_team"], "Chelsea")
        self.assertEqual(payload["prediction"]["model"], "poisson_v1")

    def test_configures_daily_scheduler_job(self):
        scheduler = FakeScheduler()

        configured = configure_daily_job(
            config_path="workflow.json",
            run_time="09:30",
            timezone="Asia/Shanghai",
            scheduler=scheduler,
        )

        self.assertIs(configured, scheduler)
        self.assertEqual(len(scheduler.jobs), 1)
        job = scheduler.jobs[0]
        self.assertEqual(job["trigger"], "cron")
        self.assertEqual(job["hour"], 9)
        self.assertEqual(job["minute"], 30)
        self.assertEqual(job["timezone"], "Asia/Shanghai")

    def test_schedule_cli_can_use_injected_scheduler_factory(self):
        scheduler = FakeScheduler()
        with patch("predict_odds.cli.create_blocking_scheduler", return_value=scheduler):
            code = main([
                "schedule",
                "--config",
                "workflow.json",
                "--time",
                "09:30",
                "--timezone",
                "Asia/Shanghai",
                "--once",
            ])

        self.assertEqual(code, 0)
        self.assertEqual(len(scheduler.jobs), 1)
        self.assertTrue(scheduler.started)


class FakeScheduler:
    def __init__(self):
        self.jobs = []
        self.started = False

    def add_job(self, func, trigger, **kwargs):
        self.jobs.append({"func": func, "trigger": trigger, **kwargs})

    def start(self):
        self.started = True


def _write_config(tmp: str, *, notify: bool = True) -> Path:
    root = Path(tmp)
    fbref = root / "fbref.csv"
    transfermarkt = root / "transfermarkt.csv"
    odds = root / "odds.json"
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
    odds.write_text(json.dumps({"home_win": 2.1, "draw": 3.2, "away_win": 3.0}), encoding="utf-8")
    config = {
        "fixture": {
            "league": "Premier League",
            "date": "2026-06-20",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
        },
        "data": {
            "fbref": str(fbref),
            "transfermarkt": str(transfermarkt),
            "odds": str(odds),
        },
        "decision": {
            "bankroll": 1000,
            "min_edge": 0.03,
            "fractional_kelly": 0.25,
            "max_stake_fraction": 0.05,
        },
        "output": {"directory": str(output_dir)},
        "telegram": {"enabled": notify},
    }
    config_path = root / "workflow.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    return config_path


if __name__ == "__main__":
    unittest.main()
