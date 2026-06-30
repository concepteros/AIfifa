import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from predict_odds.cli import main
from predict_odds.repository import BotRepository
from predict_odds.results import MatchResult, load_results
from predict_odds.settlement import build_performance_report, settle_database, settle_recommendation


class SettlementTest(unittest.TestCase):
    def test_loads_match_results_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "results.csv"
            path.write_text(
                "date,league,home_team,away_team,home_goals,away_goals\n"
                "2026-06-20,Premier League,Arsenal,Chelsea,2,1\n",
                encoding="utf-8",
            )

            results = load_results(path)

        self.assertEqual(results, [
            MatchResult(
                date="2026-06-20",
                league="Premier League",
                home_team="Arsenal",
                away_team="Chelsea",
                home_goals=2,
                away_goals=1,
            )
        ])

    def test_settles_1x2_recommendations(self):
        recommendation = {
            "market": "home_win",
            "action": "bet",
            "stake": 20.0,
            "odds": 2.1,
        }
        result = MatchResult("2026-06-20", "Premier League", "Arsenal", "Chelsea", 2, 1)

        settlement = settle_recommendation(recommendation, result)

        self.assertEqual(settlement["status"], "won")
        self.assertEqual(settlement["profit"], 22.0)
        self.assertEqual(settlement["stake"], 20.0)

    def test_losing_and_no_bet_settlements(self):
        result = MatchResult("2026-06-20", "Premier League", "Arsenal", "Chelsea", 0, 0)

        lost = settle_recommendation({"market": "home_win", "action": "bet", "stake": 20.0, "odds": 2.1}, result)
        skipped = settle_recommendation({"market": "away_win", "action": "no_bet", "stake": 0, "odds": 3.0}, result)

        self.assertEqual(lost["status"], "lost")
        self.assertEqual(lost["profit"], -20.0)
        self.assertEqual(skipped["status"], "skipped")

    def test_settles_totals_markets(self):
        result = MatchResult("2026-06-20", "Premier League", "Arsenal", "Chelsea", 2, 1)

        over = settle_recommendation({"market": "over_2_5", "action": "bet", "stake": 10.0, "odds": 1.9}, result)
        under = settle_recommendation({"market": "under_2_5", "action": "bet", "stake": 10.0, "odds": 1.9}, result)
        push = settle_recommendation({"market": "over_3", "action": "bet", "stake": 10.0, "odds": 2.0}, result)

        self.assertEqual(over["status"], "won")
        self.assertEqual(over["profit"], 9.0)
        self.assertEqual(under["status"], "lost")
        self.assertEqual(push["status"], "push")
        self.assertEqual(push["profit"], 0.0)

    def test_settles_spread_markets(self):
        result = MatchResult("2026-06-20", "Premier League", "Arsenal", "Chelsea", 2, 1)

        home = settle_recommendation({"market": "home_spread_-0_5", "action": "bet", "stake": 10.0, "odds": 1.88}, result)
        away = settle_recommendation({"market": "away_spread_0_5", "action": "bet", "stake": 10.0, "odds": 2.02}, result)
        push = settle_recommendation({"market": "home_spread_-1", "action": "bet", "stake": 10.0, "odds": 1.95}, result)

        self.assertEqual(home["status"], "won")
        self.assertEqual(away["status"], "lost")
        self.assertEqual(push["status"], "push")
        self.assertEqual(push["stake"], 10.0)
        self.assertEqual(push["profit"], 0.0)

    def test_settles_database_and_reports_roi(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "bot.sqlite"
            results_path = Path(tmp) / "results.csv"
            repository = BotRepository(db_path)
            run_id = repository.create_run({"test": True})
            repository.save_match_result(run_id, _match_result_payload())
            repository.finish_run(run_id, status="ok")
            results_path.write_text(
                "date,league,home_team,away_team,home_goals,away_goals\n"
                "2026-06-20,Premier League,Arsenal,Chelsea,2,1\n",
                encoding="utf-8",
            )

            summary = settle_database(db_path, results_path)
            report = build_performance_report(db_path)

        self.assertEqual(summary["settled"], 1)
        self.assertEqual(report["total_bets"], 1)
        self.assertEqual(report["wins"], 1)
        self.assertEqual(report["stake"], 20.0)
        self.assertEqual(report["profit"], 22.0)
        self.assertEqual(report["roi"], 1.1)
        self.assertEqual(report["by_market"]["home_win"]["wins"], 1)
        self.assertEqual(report["pushes"], 0)
        self.assertEqual(report["by_family"]["1x2"]["wins"], 1)

    def test_reports_market_families_and_pushes(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "bot.sqlite"
            results_path = Path(tmp) / "results.csv"
            repository = BotRepository(db_path)
            run_id = repository.create_run({"test": True})
            repository.save_match_result(run_id, _multi_market_payload())
            repository.finish_run(run_id, status="ok")
            results_path.write_text(
                "date,league,home_team,away_team,home_goals,away_goals\n"
                "2026-06-20,Premier League,Arsenal,Chelsea,2,1\n",
                encoding="utf-8",
            )

            settle_database(db_path, results_path)
            report = build_performance_report(db_path)

        self.assertEqual(report["total_bets"], 3)
        self.assertEqual(report["pushes"], 1)
        self.assertEqual(report["by_family"]["totals"]["bets"], 1)
        self.assertEqual(report["by_family"]["spreads"]["pushes"], 1)

    def test_settle_and_report_cli_print_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "bot.sqlite"
            results_path = Path(tmp) / "results.csv"
            repository = BotRepository(db_path)
            run_id = repository.create_run({"test": True})
            repository.save_match_result(run_id, _match_result_payload())
            repository.finish_run(run_id, status="ok")
            results_path.write_text(
                "date,league,home_team,away_team,home_goals,away_goals\n"
                "2026-06-20,Premier League,Arsenal,Chelsea,2,1\n",
                encoding="utf-8",
            )

            with patch("sys.stdout") as stdout:
                settle_code = main(["settle", "--database", str(db_path), "--results", str(results_path), "--compact"])
                report_code = main(["report", "--database", str(db_path), "--compact"])

        self.assertEqual(settle_code, 0)
        self.assertEqual(report_code, 0)
        output = "".join(call.args[0] for call in stdout.write.call_args_list if call.args)
        lines = [json.loads(line) for line in output.splitlines() if line.strip()]
        self.assertEqual(lines[0]["settled"], 1)
        self.assertEqual(lines[1]["total_bets"], 1)


def _match_result_payload():
    return {
        "fixture": {
            "league": "Premier League",
            "date": "2026-06-20",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
        },
        "prediction": {"model": "poisson_v2"},
        "decisions": {
            "recommendations": [
                {"market": "home_win", "action": "bet", "stake": 20.0, "odds": 2.1},
                {"market": "draw", "action": "no_bet", "stake": 0, "odds": 3.2},
            ]
        },
        "result_path": "out/result.json",
    }


def _multi_market_payload():
    payload = _match_result_payload()
    payload["decisions"]["recommendations"] = [
        {"market": "home_win", "action": "bet", "stake": 20.0, "odds": 2.1},
        {"market": "over_2_5", "action": "bet", "stake": 10.0, "odds": 1.9},
        {"market": "home_spread_-1", "action": "bet", "stake": 10.0, "odds": 1.95},
    ]
    return payload


if __name__ == "__main__":
    unittest.main()
