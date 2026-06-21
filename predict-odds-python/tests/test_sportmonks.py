import json
import os
import unittest
from unittest.mock import patch

from predict_odds.cli import main
from predict_odds.errors import PredictAuthenticationError, PredictConfigError, PredictHTTPError, PredictResponseError
from predict_odds.sportmonks import DEFAULT_SPORTMONKS_INCLUDES, SportmonksClient


class SportmonksClientTest(unittest.TestCase):
    def test_requires_api_key(self):
        with self.assertRaises(PredictConfigError):
            SportmonksClient(api_key="")

    def test_from_env_reads_key(self):
        with patch.dict(os.environ, {"SPORTMONKS_API_KEY": "sm-key"}):
            client = SportmonksClient.from_env()
        self.assertEqual(client.api_key, "sm-key")

    def test_fetches_fixture_with_default_includes_and_normalizes_payload(self):
        seen = {}

        def transport(url, headers, timeout):
            seen["url"] = url
            seen["headers"] = headers
            return 200, json.dumps(_fixture_payload())

        client = SportmonksClient(api_key="secret", transport=transport)
        result = client.get_fixture(19102725)

        self.assertIn("/v3/football/fixtures/19102725", seen["url"])
        self.assertIn("api_token=secret", seen["url"])
        self.assertIn("includes=participants%3Bscores%3Bvenue%3Bstate%3Bevents%3Bstatistics%3Blineups%3Bleague", seen["url"])
        self.assertEqual(seen["headers"]["Accept"], "application/json")
        self.assertIn("Mozilla/5.0", seen["headers"]["User-Agent"])
        self.assertEqual(result["fixture_id"], 19102725)
        self.assertEqual(result["league"]["name"], "Premier League")
        self.assertEqual(result["participants"]["home"]["name"], "Arsenal")
        self.assertEqual(result["participants"]["away"]["name"], "Chelsea")
        self.assertEqual(result["scores"]["home"], 2)
        self.assertEqual(result["scores"]["away"], 1)
        self.assertEqual(result["venue"]["name"], "Emirates Stadium")
        self.assertEqual(result["state"]["name"], "Finished")
        self.assertEqual(result["raw"]["id"], 19102725)

    def test_raises_authentication_error(self):
        client = SportmonksClient(api_key="bad", transport=lambda url, headers, timeout: (401, "{}"))

        with self.assertRaises(PredictAuthenticationError):
            client.get_fixture(19102725)

    def test_cloudflare_denial_is_reported_as_http_error(self):
        body = json.dumps({"cloudflare_error": True, "error_code": 1010, "detail": "Access denied"})
        client = SportmonksClient(api_key="secret", transport=lambda url, headers, timeout: (403, body))

        with self.assertRaises(PredictHTTPError) as context:
            client.get_fixture(19102725)

        self.assertEqual(context.exception.status_code, 403)

    def test_response_error_includes_sportmonks_message_when_data_is_missing(self):
        body = json.dumps({"message": "No result(s) found matching your request."})
        client = SportmonksClient(api_key="secret", transport=lambda url, headers, timeout: (200, body))

        with self.assertRaises(PredictResponseError) as context:
            client.get_fixture(19102725)

        self.assertIn("No result(s) found", str(context.exception))

    def test_retries_with_bearer_token_when_query_token_is_rejected(self):
        seen = []

        def transport(url, headers, timeout):
            seen.append({"url": url, "headers": headers})
            if len(seen) == 1:
                return 401, "{}"
            return 200, json.dumps(_fixture_payload())

        client = SportmonksClient(api_key="secret", transport=transport)
        result = client.get_fixture(19102725)

        self.assertEqual(result["fixture_id"], 19102725)
        self.assertIn("api_token=secret", seen[0]["url"])
        self.assertNotIn("api_token=secret", seen[1]["url"])
        self.assertEqual(seen[1]["headers"]["Authorization"], "Bearer secret")

    def test_sportmonks_fixture_cli_prints_json(self):
        with patch.dict(os.environ, {"SPORTMONKS_API_KEY": "secret"}):
            with patch("predict_odds.cli.SportmonksClient.from_env") as from_env, patch("sys.stdout") as stdout:
                client = from_env.return_value
                client.get_fixture.return_value = {"fixture_id": 19102725, "includes": DEFAULT_SPORTMONKS_INCLUDES}

                code = main(["sportmonks-fixture", "--fixture-id", "19102725", "--compact"])

        self.assertEqual(code, 0)
        client.get_fixture.assert_called_once_with(19102725, includes=DEFAULT_SPORTMONKS_INCLUDES)
        output = "".join(call.args[0] for call in stdout.write.call_args_list if call.args)
        payload = json.loads(output)
        self.assertEqual(payload["fixture_id"], 19102725)


def _fixture_payload():
    return {
        "data": {
            "id": 19102725,
            "name": "Arsenal vs Chelsea",
            "starting_at": "2026-06-20 19:00:00",
            "league": {"id": 8, "name": "Premier League"},
            "venue": {"id": 1, "name": "Emirates Stadium"},
            "state": {"id": 5, "name": "Finished"},
            "participants": [
                {"id": 1, "name": "Arsenal", "meta": {"location": "home"}},
                {"id": 2, "name": "Chelsea", "meta": {"location": "away"}},
            ],
            "scores": [
                {"score": {"goals": 2}, "description": "CURRENT", "participant_id": 1},
                {"score": {"goals": 1}, "description": "CURRENT", "participant_id": 2},
            ],
            "events": [{"type_id": 14, "minute": 12}],
            "statistics": [{"type_id": 42, "data": {"value": 10}}],
            "lineups": [{"player_name": "Example Player"}],
        }
    }


if __name__ == "__main__":
    unittest.main()
