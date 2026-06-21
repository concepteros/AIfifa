import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from predict_odds.cli import main
from predict_odds.demo import run_demo


class DemoTest(unittest.TestCase):
    def test_run_demo_generates_files_and_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_demo(tmp)
            output = Path(tmp)

            self.assertTrue((output / "bot-scan.json").exists())
            self.assertTrue((output / "fbref.csv").exists())
            self.assertTrue((output / "transfermarkt.csv").exists())
            self.assertTrue((output / "events.json").exists())
            self.assertTrue((output / "results.csv").exists())
            self.assertTrue((output / "closing_odds.csv").exists())
            self.assertTrue((output / "bot.sqlite").exists())
            self.assertGreaterEqual(result["scan"]["processed"], 1)
            self.assertGreaterEqual(result["report"]["total_bets"], 1)
            self.assertIn("avg_clv", result["report"])

    def test_demo_cli_prints_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("sys.stdout") as stdout:
                code = main(["demo", "--output", tmp, "--compact"])

        self.assertEqual(code, 0)
        output = "".join(call.args[0] for call in stdout.write.call_args_list if call.args)
        payload = json.loads(output)
        self.assertGreaterEqual(payload["report"]["total_bets"], 1)
        self.assertGreaterEqual(payload["scan"]["processed"], 1)


if __name__ == "__main__":
    unittest.main()
