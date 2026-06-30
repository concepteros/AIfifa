import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from predict_odds.backtest import run_backtest
from predict_odds.cli import main
from predict_odds.repository import BotRepository


class BacktestTest(unittest.TestCase):
    def test_replays_recommendations_with_requested_thresholds(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path, results_path = _build_history(tmp)

            report = run_backtest(
                db_path,
                results_path,
                bankroll=1000,
                min_edge=0.03,
                fractional_kelly=0.25,
                max_stake_fraction=0.05,
            )

        self.assertEqual(report["total_matches"], 2)
        self.assertEqual(report["matched_results"], 2)
        self.assertEqual(report["candidate_markets"], 4)
        self.assertEqual(report["total_bets"], 2)
        self.assertEqual(report["wins"], 1)
        self.assertEqual(report["losses"], 1)
        self.assertEqual(report["stake"], 75.0)
        self.assertEqual(report["profit"], 25.0)
        self.assertAlmostEqual(report["roi"], 0.333333, places=6)
        self.assertEqual(report["starting_bankroll"], 1000.0)
        self.assertEqual(report["ending_bankroll"], 1025.0)
        self.assertEqual(report["max_drawdown"], 25.0)
        self.assertAlmostEqual(report["max_drawdown_pct"], 0.02381, places=5)
        self.assertEqual(report["hit_rate"], 0.5)
        self.assertEqual(
            report["equity_curve"],
            [
                {"bet": 0, "bankroll": 1000.0, "drawdown": 0.0},
                {"bet": 1, "bankroll": 1050.0, "drawdown": 0.0},
                {"bet": 2, "bankroll": 1025.0, "drawdown": 25.0},
            ],
        )
        self.assertEqual(report["by_market"]["home_win"]["wins"], 1)
        self.assertEqual(report["by_market"]["home_win"]["losses"], 1)
        self.assertEqual(report["by_family"]["1x2"]["bets"], 2)

    def test_filters_by_league_and_date_range(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path, results_path = _build_history(tmp)

            report = run_backtest(
                db_path,
                results_path,
                bankroll=1000,
                min_edge=0.03,
                league="Premier League",
                start_date="2026-06-20",
                end_date="2026-06-20",
            )

        self.assertEqual(report["total_matches"], 1)
        self.assertEqual(report["matched_results"], 1)
        self.assertEqual(report["candidate_markets"], 2)
        self.assertEqual(report["total_bets"], 1)
        self.assertEqual(report["wins"], 1)
        self.assertEqual(report["profit"], 50.0)

    def test_stricter_edge_threshold_reduces_replayed_bets(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path, results_path = _build_history(tmp)

            report = run_backtest(db_path, results_path, bankroll=1000, min_edge=0.08)

        self.assertEqual(report["candidate_markets"], 4)
        self.assertEqual(report["total_bets"], 1)
        self.assertEqual(report["wins"], 1)
        self.assertEqual(report["profit"], 50.0)

    def test_backtest_cli_prints_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path, results_path = _build_history(tmp)

            with patch("sys.stdout") as stdout:
                code = main([
                    "backtest",
                    "--database",
                    str(db_path),
                    "--results",
                    str(results_path),
                    "--bankroll",
                    "1000",
                    "--min-edge",
                    "0.03",
                    "--compact",
                ])

        self.assertEqual(code, 0)
        output = "".join(call.args[0] for call in stdout.write.call_args_list if call.args)
        payload = json.loads(output)
        self.assertEqual(payload["total_bets"], 2)
        self.assertEqual(payload["by_family"]["1x2"]["bets"], 2)


def _build_history(tmp: str) -> tuple[Path, Path]:
    tmp_path = Path(tmp)
    db_path = tmp_path / "bot.sqlite"
    results_path = tmp_path / "results.csv"
    repository = BotRepository(db_path)
    run_id = repository.create_run({"test": True})
    repository.save_match_result(run_id, _match_payload("Premier League", "2026-06-20", "Arsenal", "Chelsea", 0.60))
    repository.save_match_result(run_id, _match_payload("La Liga", "2026-06-21", "Madrid", "Sevilla", 0.55))
    repository.finish_run(run_id, status="ok")
    results_path.write_text(
        "date,league,home_team,away_team,home_goals,away_goals\n"
        "2026-06-20,Premier League,Arsenal,Chelsea,2,1\n"
        "2026-06-21,La Liga,Madrid,Sevilla,0,1\n",
        encoding="utf-8",
    )
    return db_path, results_path


def _match_payload(league: str, date: str, home: str, away: str, home_probability: float) -> dict:
    return {
        "fixture": {
            "league": league,
            "date": date,
            "home_team": home,
            "away_team": away,
        },
        "prediction": {"model": "poisson_v2"},
        "decisions": {
            "recommendations": [
                {
                    "market": "home_win",
                    "model_probability": home_probability,
                    "odds": 2.0,
                    "action": "no_bet",
                    "stake": 0.0,
                },
                {
                    "market": "away_win",
                    "model_probability": 0.35,
                    "odds": 3.0,
                    "action": "no_bet",
                    "stake": 0.0,
                },
            ]
        },
        "result_path": "out/result.json",
    }


if __name__ == "__main__":
    unittest.main()
