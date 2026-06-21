import json
import tempfile
import unittest
from unittest.mock import patch

from predict_odds.cli import main
from predict_odds.walk_forward import parse_walk_forward_window, run_walk_forward
from tests.test_backtest import _build_history


class WalkForwardTest(unittest.TestCase):
    def test_parses_walk_forward_window(self):
        window = parse_walk_forward_window("2026-06-01:2026-06-15:2026-06-16:2026-06-30")

        self.assertEqual(window["train_start_date"], "2026-06-01")
        self.assertEqual(window["train_end_date"], "2026-06-15")
        self.assertEqual(window["validation_start_date"], "2026-06-16")
        self.assertEqual(window["validation_end_date"], "2026-06-30")

    def test_runs_multiple_folds_and_aggregates_validation_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path, results_path = _build_history(tmp)

            report = run_walk_forward(
                db_path,
                results_path,
                bankroll=1000,
                min_edges=[0.03, 0.08],
                fractional_kellies=[0.25],
                max_stake_fractions=[0.05],
                windows=[
                    parse_walk_forward_window("2026-06-20:2026-06-20:2026-06-21:2026-06-21"),
                    parse_walk_forward_window("2026-06-21:2026-06-21:2026-06-20:2026-06-20"),
                ],
            )

        self.assertEqual(report["fold_count"], 2)
        self.assertEqual(len(report["folds"]), 2)
        self.assertEqual(report["summary"]["total_bets"], 2)
        self.assertEqual(report["summary"]["wins"], 1)
        self.assertEqual(report["summary"]["losses"], 1)
        self.assertEqual(report["summary"]["stake"], 75.0)
        self.assertEqual(report["summary"]["profit"], 25.0)
        self.assertAlmostEqual(report["summary"]["roi"], 0.333333, places=6)
        self.assertEqual(report["folds"][0]["selected_settings"]["min_edge"], 0.03)

    def test_walk_forward_cli_prints_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path, results_path = _build_history(tmp)

            with patch("sys.stdout") as stdout:
                code = main([
                    "walk-forward",
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
                    "--window",
                    "2026-06-20:2026-06-20:2026-06-21:2026-06-21",
                    "--window",
                    "2026-06-21:2026-06-21:2026-06-20:2026-06-20",
                    "--compact",
                ])

        self.assertEqual(code, 0)
        output = "".join(call.args[0] for call in stdout.write.call_args_list if call.args)
        payload = json.loads(output)
        self.assertEqual(payload["fold_count"], 2)
        self.assertEqual(payload["summary"]["profit"], 25.0)


if __name__ == "__main__":
    unittest.main()
