import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from predict_odds.cli import main
from predict_odds.prediction import predict_match


class PoissonPredictionTest(unittest.TestCase):
    def test_predicts_score_and_outcome_probabilities(self):
        feature_payload = {
            "league": "Premier League",
            "date": "2026-06-20",
            "match": {"home_team": "Arsenal", "away_team": "Chelsea"},
            "features": {
                "home_form_points_avg": 2.0,
                "away_form_points_avg": 1.0,
                "home_xg_for_avg": 1.8,
                "away_xg_for_avg": 1.1,
                "home_xga_avg": 0.9,
                "away_xga_avg": 1.4,
                "home_xg_diff_avg": 0.9,
                "away_xg_diff_avg": -0.3,
                "home_injury_impact": 0.1,
                "away_injury_impact": 0.35,
                "form_points_diff": 1.0,
                "xg_diff_delta": 1.2,
                "injury_impact_delta": -0.25,
            },
        }

        prediction = predict_match(feature_payload)

        self.assertEqual(prediction["model"], "poisson_v1")
        self.assertEqual(prediction["match"]["home_team"], "Arsenal")
        self.assertGreater(prediction["expected_goals"]["home"], prediction["expected_goals"]["away"])
        outcome_total = (
            prediction["probabilities"]["home_win"]
            + prediction["probabilities"]["draw"]
            + prediction["probabilities"]["away_win"]
        )
        self.assertAlmostEqual(outcome_total, 1.0, places=6)
        self.assertGreater(prediction["probabilities"]["home_win"], prediction["probabilities"]["away_win"])
        self.assertAlmostEqual(
            prediction["probabilities"]["over_2_5"] + prediction["probabilities"]["under_2_5"],
            1.0,
            places=6,
        )
        self.assertAlmostEqual(
            prediction["probabilities"]["btts_yes"] + prediction["probabilities"]["btts_no"],
            1.0,
            places=6,
        )
        self.assertGreaterEqual(len(prediction["most_likely_scores"]), 3)
        self.assertGreaterEqual(
            prediction["most_likely_scores"][0]["probability"],
            prediction["most_likely_scores"][1]["probability"],
        )
        self.assertTrue(any("form" in reason.casefold() for reason in prediction["reasoning"]))

    def test_predict_cli_prints_poisson_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            fbref = Path(tmp) / "fbref.csv"
            transfermarkt = Path(tmp) / "transfermarkt.csv"
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

            with patch("sys.stdout") as stdout:
                code = main([
                    "predict",
                    "--league",
                    "Premier League",
                    "--date",
                    "2026-06-20",
                    "--home-team",
                    "Arsenal",
                    "--away-team",
                    "Chelsea",
                    "--fbref",
                    str(fbref),
                    "--transfermarkt",
                    str(transfermarkt),
                    "--compact",
                ])

        self.assertEqual(code, 0)
        output = "".join(call.args[0] for call in stdout.write.call_args_list if call.args)
        payload = json.loads(output)
        self.assertEqual(payload["model"], "poisson_v1")
        self.assertEqual(payload["match"]["away_team"], "Chelsea")


if __name__ == "__main__":
    unittest.main()
