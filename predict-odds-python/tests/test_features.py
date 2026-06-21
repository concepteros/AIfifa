import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from predict_odds.cli import main
from predict_odds.data_sources import (
    Fixture,
    InjuryRecord,
    MatchRecord,
    load_injuries,
    load_matches,
)
from predict_odds.feature_pipeline import build_match_features
from predict_odds.features import (
    calculate_injury_impact,
    calculate_team_features,
)


class DataSourceTest(unittest.TestCase):
    def test_loads_fbref_style_match_csv(self):
        csv_text = (
            "date,league,team,opponent,venue,goals_for,goals_against,xg,xga,result\n"
            "2026-06-01,Premier League,Arsenal,Chelsea,home,2,1,1.8,1.1,W\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fbref.csv"
            path.write_text(csv_text, encoding="utf-8")

            records = load_matches(path)

        self.assertEqual(records, [
            MatchRecord(
                date="2026-06-01",
                league="Premier League",
                team="Arsenal",
                opponent="Chelsea",
                venue="home",
                goals_for=2,
                goals_against=1,
                xg=1.8,
                xga=1.1,
                result="W",
            )
        ])

    def test_loads_transfermarkt_style_injury_json(self):
        payload = [
            {
                "team": "Arsenal",
                "player": "Starter",
                "position": "Forward",
                "market_value_eur": "€50m",
                "status": "injured",
                "days_out": "21",
            }
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "injuries.json"
            path.write_text(json.dumps(payload), encoding="utf-8")

            records = load_injuries(path)

        self.assertEqual(records, [
            InjuryRecord(
                team="Arsenal",
                player="Starter",
                position="Forward",
                market_value_eur=50000000.0,
                status="injured",
                days_out=21,
            )
        ])


class FeatureCalculationTest(unittest.TestCase):
    def test_calculates_recent_form_and_xg_features(self):
        matches = [
            MatchRecord("2026-06-01", "Premier League", "Arsenal", "Chelsea", "home", 2, 1, 1.8, 1.1, "W"),
            MatchRecord("2026-06-08", "Premier League", "Arsenal", "Spurs", "away", 1, 1, 1.2, 1.0, "D"),
            MatchRecord("2026-06-10", "Premier League", "Chelsea", "Arsenal", "home", 0, 2, 0.7, 1.4, "L"),
            MatchRecord("2026-05-01", "Premier League", "Arsenal", "Everton", "home", 0, 1, 0.5, 1.2, "L"),
        ]

        features = calculate_team_features(matches, team="Arsenal", league="Premier League", before_date="2026-06-20", window=2)

        self.assertEqual(features["form_points_total"], 4)
        self.assertEqual(features["form_points_avg"], 2.0)
        self.assertEqual(features["form_sequence"], "DW")
        self.assertEqual(features["goal_diff_avg"], 0.5)
        self.assertAlmostEqual(features["xg_for_avg"], 1.5)
        self.assertAlmostEqual(features["xga_avg"], 1.05)
        self.assertAlmostEqual(features["xg_diff_avg"], 0.45)

    def test_calculates_weighted_injury_impact(self):
        injuries = [
            InjuryRecord("Arsenal", "Forward", "Forward", 50_000_000, "injured", 21),
            InjuryRecord("Arsenal", "Keeper", "Goalkeeper", 30_000_000, "suspended", 7),
            InjuryRecord("Arsenal", "Fit Player", "Midfielder", 80_000_000, "available", 0),
            InjuryRecord("Chelsea", "Other", "Defender", 40_000_000, "injured", 14),
        ]

        impact = calculate_injury_impact(injuries, team="Arsenal")

        self.assertEqual(impact["injured_players"], 2)
        self.assertAlmostEqual(impact["injury_value_eur"], 80_000_000.0)
        self.assertAlmostEqual(impact["injury_impact"], 0.497, places=3)

    def test_builds_match_feature_payload_with_deltas(self):
        fixture = Fixture(
            league="Premier League",
            date="2026-06-20",
            home_team="Arsenal",
            away_team="Chelsea",
        )
        matches = [
            MatchRecord("2026-06-01", "Premier League", "Arsenal", "Chelsea", "home", 2, 1, 1.8, 1.1, "W"),
            MatchRecord("2026-06-08", "Premier League", "Arsenal", "Spurs", "away", 1, 1, 1.2, 1.0, "D"),
            MatchRecord("2026-06-01", "Premier League", "Chelsea", "Arsenal", "away", 1, 2, 1.1, 1.8, "L"),
            MatchRecord("2026-06-08", "Premier League", "Chelsea", "Spurs", "home", 3, 0, 2.2, 0.7, "W"),
        ]
        injuries = [
            InjuryRecord("Arsenal", "Forward", "Forward", 50_000_000, "injured", 21),
            InjuryRecord("Chelsea", "Defender", "Defender", 40_000_000, "injured", 14),
        ]

        payload = build_match_features(fixture=fixture, matches=matches, injuries=injuries, window=2)

        self.assertEqual(payload["match"]["home_team"], "Arsenal")
        self.assertEqual(payload["match"]["away_team"], "Chelsea")
        self.assertAlmostEqual(payload["features"]["home_form_points_avg"], 2.0)
        self.assertAlmostEqual(payload["features"]["away_form_points_avg"], 1.5)
        self.assertAlmostEqual(payload["features"]["form_points_diff"], 0.5)
        self.assertIn("injury_impact_delta", payload["features"])

    def test_features_cli_prints_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            fbref = Path(tmp) / "fbref.csv"
            transfermarkt = Path(tmp) / "transfermarkt.csv"
            fbref.write_text(
                "date,league,team,opponent,venue,goals_for,goals_against,xg,xga,result\n"
                "2026-06-01,Premier League,Arsenal,Chelsea,home,2,1,1.8,1.1,W\n"
                "2026-06-01,Premier League,Chelsea,Arsenal,away,1,2,1.1,1.8,L\n",
                encoding="utf-8",
            )
            transfermarkt.write_text(
                "team,player,position,market_value_eur,status,days_out\n"
                "Arsenal,Forward,Forward,50000000,injured,21\n",
                encoding="utf-8",
            )

            with patch("sys.stdout") as stdout:
                code = main([
                    "features",
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
        self.assertEqual(json.loads(output)["match"]["home_team"], "Arsenal")


if __name__ == "__main__":
    unittest.main()
