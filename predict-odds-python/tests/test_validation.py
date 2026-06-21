import json
import tempfile
import unittest
from unittest.mock import patch

from predict_odds.cli import main
from predict_odds.validation import validate_strategy
from tests.test_backtest import _build_history


class ValidationTest(unittest.TestCase):
    def test_optimizes_on_train_window_and_backtests_validation_window(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path, results_path = _build_history(tmp)

            report = validate_strategy(
                db_path,
                results_path,
                bankroll=1000,
                min_edges=[0.03, 0.08],
                fractional_kellies=[0.25],
                max_stake_fractions=[0.05],
                train_start_date="2026-06-20",
                train_end_date="2026-06-20",
                validation_start_date="2026-06-21",
                validation_end_date="2026-06-21",
            )

        self.assertEqual(report["selected_settings"]["min_edge"], 0.03)
        self.assertEqual(report["train"]["best"]["total_bets"], 1)
        self.assertEqual(report["train"]["best"]["profit"], 50.0)
        self.assertEqual(report["validation"]["total_matches"], 1)
        self.assertEqual(report["validation"]["total_bets"], 1)
        self.assertEqual(report["validation"]["profit"], -25.0)
        self.assertEqual(report["validation"]["ending_bankroll"], 975.0)

    def test_returns_empty_validation_when_no_train_candidate_passes_min_bets(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path, results_path = _build_history(tmp)

            report = validate_strategy(
                db_path,
                results_path,
                bankroll=1000,
                min_edges=[0.20],
                fractional_kellies=[0.25],
                max_stake_fractions=[0.05],
                min_bets=1,
                train_start_date="2026-06-20",
                train_end_date="2026-06-20",
                validation_start_date="2026-06-21",
                validation_end_date="2026-06-21",
            )

        self.assertIsNone(report["selected_settings"])
        self.assertIsNone(report["validation"])
        self.assertEqual(report["train"]["returned"], 0)

    def test_validate_cli_prints_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path, results_path = _build_history(tmp)

            with patch("sys.stdout") as stdout:
                code = main([
                    "validate",
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
                    "--train-start-date",
                    "2026-06-20",
                    "--train-end-date",
                    "2026-06-20",
                    "--validation-start-date",
                    "2026-06-21",
                    "--validation-end-date",
                    "2026-06-21",
                    "--compact",
                ])

        self.assertEqual(code, 0)
        output = "".join(call.args[0] for call in stdout.write.call_args_list if call.args)
        payload = json.loads(output)
        self.assertEqual(payload["validation"]["profit"], -25.0)
        self.assertEqual(payload["selected_settings"]["min_edge"], 0.03)


if __name__ == "__main__":
    unittest.main()
