import json
import os
import unittest
from unittest.mock import patch

from predict_odds.errors import PredictHTTPError, PredictResponseError
from predict_odds.polymarket import PolymarketClient


class PolymarketClientTest(unittest.TestCase):
    def test_from_env_reads_url(self):
        with patch.dict(os.environ, {"POLYMARKET_API_URL": "https://example.test"}):
            client = PolymarketClient.from_env()
        self.assertEqual(client.base_url, "https://example.test")

    def test_fetches_markets_with_filters(self):
        seen = {}

        def transport(url, headers, timeout):
            seen["url"] = url
            seen["headers"] = headers
            return 200, json.dumps([{"id": "m1"}])

        client = PolymarketClient(base_url="https://example.test", transport=transport)
        payload = client.get_markets(query="Arsenal Chelsea", limit=25, active=True, closed=False)

        self.assertEqual(payload, [{"id": "m1"}])
        self.assertIn("/markets?", seen["url"])
        self.assertIn("search=Arsenal+Chelsea", seen["url"])
        self.assertIn("limit=25", seen["url"])
        self.assertIn("active=true", seen["url"])
        self.assertIn("closed=false", seen["url"])
        self.assertEqual(seen["headers"]["Accept"], "application/json")
        self.assertIn("Mozilla/5.0", seen["headers"]["User-Agent"])

    def test_accepts_data_wrapped_response(self):
        client = PolymarketClient(transport=lambda url, headers, timeout: (200, json.dumps({"data": [{"id": "m1"}]})))

        self.assertEqual(client.get_markets(), [{"id": "m1"}])

    def test_raises_http_error(self):
        client = PolymarketClient(transport=lambda url, headers, timeout: (500, "down"))

        with self.assertRaises(PredictHTTPError):
            client.get_markets()

    def test_rejects_unexpected_response_shape(self):
        client = PolymarketClient(transport=lambda url, headers, timeout: (200, json.dumps({"items": []})))

        with self.assertRaises(PredictResponseError):
            client.get_markets()


if __name__ == "__main__":
    unittest.main()
