import json
import os
import unittest
from unittest.mock import patch

from predict_odds.errors import PredictAuthenticationError, PredictConfigError
from predict_odds.odds_normalizer import normalize_event_odds
from predict_odds.the_odds_api import TheOddsAPIClient


class TheOddsAPIClientTest(unittest.TestCase):
    def test_requires_api_key(self):
        with self.assertRaises(PredictConfigError):
            TheOddsAPIClient(api_key="")

    def test_from_env_reads_key(self):
        with patch.dict(os.environ, {"THE_ODDS_API_KEY": "abc"}):
            client = TheOddsAPIClient.from_env()
        self.assertEqual(client.api_key, "abc")

    def test_builds_odds_request_with_filters(self):
        seen = {}

        def transport(url, headers, timeout):
            seen["url"] = url
            seen["headers"] = headers
            return 200, json.dumps([])

        client = TheOddsAPIClient(api_key="secret", transport=transport)
        payload = client.get_odds(
            sport="soccer_epl",
            regions="eu",
            markets=["h2h", "spreads", "totals"],
            commence_time_from="2026-06-20T00:00:00Z",
            commence_time_to="2026-06-21T00:00:00Z",
        )

        self.assertEqual(payload, [])
        self.assertIn("/v4/sports/soccer_epl/odds/", seen["url"])
        self.assertIn("apiKey=secret", seen["url"])
        self.assertIn("regions=eu", seen["url"])
        self.assertIn("markets=h2h%2Cspreads%2Ctotals", seen["url"])
        self.assertIn("oddsFormat=decimal", seen["url"])
        self.assertIn("commenceTimeFrom=2026-06-20T00%3A00%3A00Z", seen["url"])
        self.assertEqual(seen["headers"]["Accept"], "application/json")

    def test_raises_authentication_error(self):
        client = TheOddsAPIClient(api_key="bad", transport=lambda url, headers, timeout: (401, "{}"))

        with self.assertRaises(PredictAuthenticationError):
            client.get_odds(sport="soccer_epl", regions="eu")


class OddsNormalizerTest(unittest.TestCase):
    def test_normalizes_h2h_totals_and_spreads(self):
        event = {
            "id": "event-1",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "commence_time": "2026-06-20T19:00:00Z",
            "bookmakers": [
                {
                    "key": "book_a",
                    "markets": [
                        {
                            "key": "h2h",
                            "outcomes": [
                                {"name": "Arsenal", "price": 2.1},
                                {"name": "Chelsea", "price": 3.0},
                                {"name": "Draw", "price": 3.4},
                            ],
                        },
                        {
                            "key": "totals",
                            "outcomes": [
                                {"name": "Over", "price": 1.9, "point": 2.5},
                                {"name": "Under", "price": 1.95, "point": 2.5},
                            ],
                        },
                        {
                            "key": "spreads",
                            "outcomes": [
                                {"name": "Arsenal", "price": 1.88, "point": -0.5},
                                {"name": "Chelsea", "price": 2.02, "point": 0.5},
                            ],
                        },
                    ],
                }
            ],
        }

        normalized = normalize_event_odds(event)

        self.assertEqual(normalized["event_id"], "event-1")
        self.assertEqual(normalized["home_team"], "Arsenal")
        self.assertEqual(normalized["markets"]["home_win"], 2.1)
        self.assertEqual(normalized["markets"]["draw"], 3.4)
        self.assertEqual(normalized["markets"]["away_win"], 3.0)
        self.assertEqual(normalized["markets"]["over_2_5"], 1.9)
        self.assertEqual(normalized["markets"]["under_2_5"], 1.95)
        self.assertEqual(normalized["markets"]["home_spread_-0_5"], 1.88)
        self.assertEqual(normalized["markets"]["away_spread_0_5"], 2.02)

    def test_uses_best_price_across_bookmakers(self):
        event = {
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "bookmakers": [
                {"markets": [{"key": "h2h", "outcomes": [{"name": "Arsenal", "price": 2.0}]}]},
                {"markets": [{"key": "h2h", "outcomes": [{"name": "Arsenal", "price": 2.2}]}]},
            ],
        }

        normalized = normalize_event_odds(event)

        self.assertEqual(normalized["markets"]["home_win"], 2.2)


if __name__ == "__main__":
    unittest.main()
