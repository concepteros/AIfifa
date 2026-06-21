import json
import os
import unittest
from unittest.mock import patch

from predict_odds import (
    PredictAuthenticationError,
    PredictConfigError,
    PredictHTTPError,
    PredictOddsClient,
    PredictResponseError,
    PredictValidationError,
)


class PredictOddsClientTest(unittest.TestCase):
    def test_requires_api_key(self):
        with self.assertRaises(PredictConfigError):
            PredictOddsClient(api_key="")

    def test_from_env_reads_key_and_url(self):
        with patch.dict(os.environ, {"PREDICT_API_KEY": "abc", "PREDICT_API_URL": "https://example.test/markets"}):
            client = PredictOddsClient.from_env()
        self.assertEqual(client.api_key, "abc")
        self.assertEqual(client.api_url, "https://example.test/markets")

    def test_validates_league_and_date(self):
        client = PredictOddsClient(api_key="key", transport=_transport_with({"markets": []}))
        with self.assertRaises(PredictValidationError):
            client.get_football_odds(league="", date="2026-06-20")
        with self.assertRaises(PredictValidationError):
            client.get_football_odds(league="Premier League", date="2026-99-20")

    def test_sends_league_date_and_auth_headers(self):
        seen = {}

        def transport(url, headers, timeout):
            seen["url"] = url
            seen["headers"] = headers
            seen["timeout"] = timeout
            return 200, json.dumps({"markets": []})

        client = PredictOddsClient(api_key="secret", api_url="https://example.test/markets", transport=transport)
        client.get_football_odds(league="Premier League", date="2026-06-20")

        self.assertIn("sport=football", seen["url"])
        self.assertIn("league=Premier+League", seen["url"])
        self.assertIn("date=2026-06-20", seen["url"])
        self.assertEqual(seen["headers"]["Authorization"], "Bearer secret")
        self.assertEqual(seen["headers"]["X-API-Key"], "secret")
        self.assertIn("Mozilla/5.0", seen["headers"]["User-Agent"])

    def test_groups_supported_market_types(self):
        payload = {
            "data": [
                {
                    "id": "m1",
                    "type": "1x2",
                    "match": {"id": "game-1", "home_team": "A", "away_team": "B", "kickoff": "2026-06-20T19:00:00Z"},
                    "outcomes": [{"name": "Home", "odds": 2.1}, {"name": "Draw", "odds": 3.2}, {"name": "Away", "odds": 3.5}],
                },
                {"id": "m2", "type": "Asian Handicap", "home": "A", "away": "B", "outcomes": [{"name": "A -0.5", "odds": 1.9, "line": -0.5}]},
                {"id": "m3", "name": "Total Over/Under", "odds": {"Over 2.5": 1.8, "Under 2.5": 2.0}},
            ]
        }
        client = PredictOddsClient(api_key="key", api_url="https://example.test/markets", transport=_transport_with(payload))

        result = client.get_football_odds(league="Premier League", date="2026-06-20")
        data = result.to_dict()

        self.assertEqual(data["raw_count"], 3)
        self.assertEqual(data["markets"]["win_draw_win"][0]["match_id"], "game-1")
        self.assertEqual(data["markets"]["handicap"][0]["outcomes"][0]["line"], -0.5)
        self.assertEqual(data["markets"]["totals"][0]["outcomes"][0]["name"], "Over 2.5")

    def test_raises_authentication_error_for_401_or_403(self):
        client = PredictOddsClient(api_key="key", transport=lambda url, headers, timeout: (401, "{}"))
        with self.assertRaises(PredictAuthenticationError):
            client.get_football_odds(league="Premier League", date="2026-06-20")

    def test_cloudflare_denial_is_reported_as_http_error(self):
        body = json.dumps({"cloudflare_error": True, "error_code": 1010})
        client = PredictOddsClient(api_key="key", transport=lambda url, headers, timeout: (403, body))

        with self.assertRaises(PredictHTTPError) as context:
            client.get_football_odds(league="Premier League", date="2026-06-20")

        self.assertEqual(context.exception.status_code, 403)

    def test_rejects_unexpected_response_shape(self):
        client = PredictOddsClient(api_key="key", transport=_transport_with({"items": []}))
        with self.assertRaises(PredictResponseError):
            client.get_football_odds(league="Premier League", date="2026-06-20")


def _transport_with(payload):
    return lambda url, headers, timeout: (200, json.dumps(payload))


if __name__ == "__main__":
    unittest.main()
