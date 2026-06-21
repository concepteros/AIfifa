import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from predict_odds.closing_odds import ClosingOdds, find_closing_odds, load_closing_odds
from predict_odds.cli import main
from predict_odds.repository import BotRepository
from predict_odds.results import MatchResult
from predict_odds.settlement import build_performance_report, settle_database, settle_recommendation


class CLVTrackingTest(unittest.TestCase):
    def test_loads_closing_odds_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "closing.csv"
            path.write_text(
                "date,league,home_team,away_team,market,closing_odds\n"
                "2026-06-20,Premier League,Arsenal,Chelsea,home_win,1.95\n",
                encoding="utf-8",
            )

            rows = load_closing_odds(path)

        self.assertEqual(rows, [
            ClosingOdds("2026-06-20", "Premier League", "Arsenal", "Chelsea", "home_win", 1.95)
        ])

    def test_finds_closing_odds_for_match_and_market(self):
        rows = [ClosingOdds("2026-06-20", "Premier League", "Arsenal", "Chelsea", "home_win", 1.95)]
        result = MatchResult("2026-06-20", "Premier League", "Arsenal", "Chelsea", 2, 1)

        closing = find_closing_odds(rows, result, "home_win")

        self.assertEqual(closing, 1.95)

    def test_settlement_includes_clv_fields(self):
        result = MatchResult("2026-06-20", "Premier League", "Arsenal", "Chelsea", 2, 1)

        settlement = settle_recommendation(
            {"market": "home_win", "action": "bet", "stake": 20.0, "odds": 2.1},
            result,
            closing_odds=1.95,
        )

        self.assertEqual(settlement["closing_odds"], 1.95)
        self.assertEqual(settlement["clv"], -0.15)
        self.assertAlmostEqual(settlement["clv_pct"], -0.071429, places=6)

    def test_settle_database_uses_closing_odds_and_report_metrics(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "bot.sqlite"
            results_path = Path(tmp) / "results.csv"
            closing_path = Path(tmp) / "closing.csv"
            repository = BotRepository(db_path)
            run_id = repository.create_run({"test": True})
            repository.save_match_result(run_id, _payload())
            repository.finish_run(run_id, status="ok")
            results_path.write_text(
                "date,league,home_team,away_team,home_goals,away_goals\n"
                "2026-06-20,Premier League,Arsenal,Chelsea,2,1\n",
                encoding="utf-8",
            )
            closing_path.write_text(
                "date,league,home_team,away_team,market,closing_odds\n"
                "2026-06-20,Premier League,Arsenal,Chelsea,home_win,1.95\n",
                encoding="utf-8",
            )

            settle_database(db_path, results_path, closing_odds_path=closing_path)
            report = build_performance_report(db_path)

        self.assertEqual(report["avg_clv"], -0.15)
        self.assertEqual(report["positive_clv_rate"], 0.0)
        self.assertEqual(report["by_market"]["home_win"]["avg_clv"], -0.15)
        self.assertEqual(report["by_family"]["1x2"]["avg_clv"], -0.15)

    def test_settle_cli_accepts_closing_odds(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "bot.sqlite"
            results_path = Path(tmp) / "results.csv"
            closing_path = Path(tmp) / "closing.csv"
            repository = BotRepository(db_path)
            run_id = repository.create_run({"test": True})
            repository.save_match_result(run_id, _payload())
            repository.finish_run(run_id, status="ok")
            results_path.write_text(
                "date,league,home_team,away_team,home_goals,away_goals\n"
                "2026-06-20,Premier League,Arsenal,Chelsea,2,1\n",
                encoding="utf-8",
            )
            closing_path.write_text(
                "date,league,home_team,away_team,market,closing_odds\n"
                "2026-06-20,Premier League,Arsenal,Chelsea,home_win,1.95\n",
                encoding="utf-8",
            )

            with patch("sys.stdout") as stdout:
                settle_code = main([
                    "settle",
                    "--database",
                    str(db_path),
                    "--results",
                    str(results_path),
                    "--closing-odds",
                    str(closing_path),
                    "--compact",
                ])
                report_code = main(["report", "--database", str(db_path), "--compact"])

        self.assertEqual(settle_code, 0)
        self.assertEqual(report_code, 0)
        output = "".join(call.args[0] for call in stdout.write.call_args_list if call.args)
        report = json.loads(output.splitlines()[1])
        self.assertEqual(report["avg_clv"], -0.15)


def _payload():
    return {
        "fixture": {
            "league": "Premier League",
            "date": "2026-06-20",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
        },
        "prediction": {"model": "poisson_v1"},
        "decisions": {
            "recommendations": [
                {"market": "home_win", "action": "bet", "stake": 20.0, "odds": 2.1},
            ]
        },
        "result_path": "out/result.json",
    }


if __name__ == "__main__":
    unittest.main()
