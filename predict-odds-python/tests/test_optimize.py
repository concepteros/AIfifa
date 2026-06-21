import json
import tempfile
import unittest
from unittest.mock import patch

from predict_odds.cli import main
from predict_odds.optimize import optimize_parameters
from tests.test_backtest import _build_history


class OptimizeParametersTest(unittest.TestCase):
    def test_ranks_grid_search_results_by_roi_profit_and_bets(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path, results_path = _build_history(tmp)

            report = optimize_parameters(
                db_path,
                results_path,
                bankroll=1000,
                min_edges=[0.03, 0.08],
                fractional_kellies=[0.25],
                max_stake_fractions=[0.05],
            )

        self.assertEqual(report["evaluated"], 2)
        self.assertEqual(len(report["runs"]), 2)
        self.assertEqual(report["best"]["settings"]["min_edge"], 0.08)
        self.assertEqual(report["best"]["total_bets"], 1)
        self.assertEqual(report["best"]["profit"], 50.0)
        self.assertEqual(report["best"]["ending_bankroll"], 1050.0)
        self.assertEqual(report["best"]["max_drawdown"], 0.0)
        self.assertGreater(report["runs"][0]["roi"], report["runs"][1]["roi"])

    def test_filters_runs_below_minimum_bet_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path, results_path = _build_history(tmp)

            report = optimize_parameters(
                db_path,
                results_path,
                bankroll=1000,
                min_edges=[0.03, 0.08],
                fractional_kellies=[0.25],
                max_stake_fractions=[0.05],
                min_bets=2,
            )

        self.assertEqual(report["evaluated"], 2)
        self.assertEqual(len(report["runs"]), 1)
        self.assertEqual(report["best"]["settings"]["min_edge"], 0.03)
        self.assertEqual(report["best"]["total_bets"], 2)

    def test_optimize_cli_prints_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path, results_path = _build_history(tmp)

            with patch("sys.stdout") as stdout:
                code = main([
                    "optimize",
                    "--database",
                    str(db_path),
                    "--results",
                    str(results_path),
                    "--bankroll",
                    "1000",
                    "--min-edges",
                    "0.03,0.08",
                    "--fractional-kellies",
                    "0.25",
                    "--max-stake-fractions",
                    "0.05",
                    "--compact",
                ])

        self.assertEqual(code, 0)
        output = "".join(call.args[0] for call in stdout.write.call_args_list if call.args)
        payload = json.loads(output)
        self.assertEqual(payload["evaluated"], 2)
        self.assertEqual(payload["best"]["settings"]["min_edge"], 0.08)


if __name__ == "__main__":
    unittest.main()
