import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from predict_odds.cli import main
from predict_odds.decision import build_betting_decisions
from predict_odds.errors import PredictValidationError


class BettingDecisionTest(unittest.TestCase):
    def test_recommends_value_bets_with_fractional_kelly(self):
        prediction = {
            "model": "poisson_v2",
            "probabilities": {
                "home_win": 0.52,
                "draw": 0.24,
                "away_win": 0.24,
                "over_2_5": 0.55,
                "under_2_5": 0.45,
            },
        }
        odds = {
            "home_win": 2.1,
            "draw": 3.2,
            "away_win": 3.0,
            "over_2_5": 1.7,
        }

        result = build_betting_decisions(
            prediction,
            odds,
            bankroll=1000,
            min_edge=0.03,
            fractional_kelly=0.25,
            max_stake_fraction=0.05,
        )

        self.assertEqual(result["bankroll"], 1000)
        self.assertEqual(result["settings"]["min_edge"], 0.03)
        bets = [item for item in result["recommendations"] if item["action"] == "bet"]
        self.assertEqual([bet["market"] for bet in bets], ["home_win"])
        home = bets[0]
        self.assertAlmostEqual(home["implied_probability"], 0.47619, places=5)
        self.assertAlmostEqual(home["edge"], 0.04381, places=5)
        self.assertAlmostEqual(home["expected_value"], 0.092, places=6)
        self.assertAlmostEqual(home["kelly_fraction"], 0.083636, places=6)
        self.assertAlmostEqual(home["stake_fraction"], 0.020909, places=6)
        self.assertAlmostEqual(home["stake"], 20.91, places=2)

    def test_marks_non_value_markets_as_no_bet(self):
        prediction = {"probabilities": {"home_win": 0.45}}
        odds = {"home_win": 2.0}

        result = build_betting_decisions(prediction, odds, bankroll=500, min_edge=0.03)

        self.assertEqual(result["recommendations"][0]["action"], "no_bet")
        self.assertLess(result["recommendations"][0]["expected_value"], 0)
        self.assertEqual(result["recommendations"][0]["stake"], 0)

    def test_caps_stake_fraction(self):
        prediction = {"probabilities": {"home_win": 0.75}}
        odds = {"home_win": 3.0}

        result = build_betting_decisions(
            prediction,
            odds,
            bankroll=1000,
            min_edge=0.01,
            fractional_kelly=1.0,
            max_stake_fraction=0.05,
        )

        self.assertEqual(result["recommendations"][0]["action"], "bet")
        self.assertEqual(result["recommendations"][0]["stake_fraction"], 0.05)
        self.assertEqual(result["recommendations"][0]["stake"], 50)

    def test_rejects_invalid_odds(self):
        prediction = {"probabilities": {"home_win": 0.6}}
        odds = {"home_win": 1.0}

        with self.assertRaises(PredictValidationError):
            build_betting_decisions(prediction, odds, bankroll=1000)

    def test_decide_cli_prints_recommendations(self):
        prediction = {
            "model": "poisson_v2",
            "probabilities": {
                "home_win": 0.52,
                "draw": 0.24,
                "away_win": 0.24,
            },
        }
        odds = {
            "home_win": 2.1,
            "draw": 3.2,
            "away_win": 3.0,
        }
        with tempfile.TemporaryDirectory() as tmp:
            prediction_path = Path(tmp) / "prediction.json"
            odds_path = Path(tmp) / "odds.json"
            prediction_path.write_text(json.dumps(prediction), encoding="utf-8")
            odds_path.write_text(json.dumps(odds), encoding="utf-8")

            with patch("sys.stdout") as stdout:
                code = main([
                    "decide",
                    "--prediction",
                    str(prediction_path),
                    "--odds",
                    str(odds_path),
                    "--bankroll",
                    "1000",
                    "--compact",
                ])

        self.assertEqual(code, 0)
        output = "".join(call.args[0] for call in stdout.write.call_args_list if call.args)
        payload = json.loads(output)
        self.assertEqual(payload["recommendations"][0]["market"], "home_win")
        self.assertEqual(payload["recommendations"][0]["action"], "bet")


if __name__ == "__main__":
    unittest.main()
