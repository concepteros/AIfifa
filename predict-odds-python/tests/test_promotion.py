import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from predict_odds.cli import main
from predict_odds.promotion import promote_strategy


class PromotionTest(unittest.TestCase):
    def test_approves_validation_report_and_outputs_decision_config(self):
        report = _validation_report()

        result = promote_strategy(
            report,
            min_bets=10,
            min_roi=0.05,
            min_profit=20,
            max_drawdown_pct=0.10,
        )

        self.assertTrue(result["approved"])
        self.assertEqual(result["reasons"], [])
        self.assertEqual(
            result["decision"],
            {
                "bankroll": 1000.0,
                "min_edge": 0.04,
                "fractional_kelly": 0.25,
                "max_stake_fraction": 0.05,
            },
        )
        self.assertEqual(result["metrics"]["roi"], 0.12)

    def test_rejects_when_risk_gates_fail(self):
        report = _validation_report()
        report["validation"]["total_bets"] = 4
        report["validation"]["max_drawdown_pct"] = 0.30

        result = promote_strategy(report, min_bets=10, max_drawdown_pct=0.10)

        self.assertFalse(result["approved"])
        self.assertIn("total_bets 4 < required 10", result["reasons"])
        self.assertIn("max_drawdown_pct 0.3 > allowed 0.1", result["reasons"])
        self.assertIsNone(result["decision"])

    def test_supports_walk_forward_summary(self):
        report = {
            "summary": {
                "total_bets": 20,
                "profit": 55.0,
                "roi": 0.11,
                "avg_max_drawdown": 15.0,
                "hit_rate": 0.55,
            },
            "folds": [
                {"selected_settings": {"min_edge": 0.05, "fractional_kelly": 0.1, "max_stake_fraction": 0.02}}
            ],
        }

        result = promote_strategy(report, bankroll=500, min_bets=10, min_roi=0.05)

        self.assertTrue(result["approved"])
        self.assertEqual(result["decision"]["bankroll"], 500.0)
        self.assertEqual(result["decision"]["min_edge"], 0.05)

    def test_promote_cli_prints_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "validation.json"
            path.write_text(json.dumps(_validation_report()), encoding="utf-8")

            with patch("sys.stdout") as stdout:
                code = main([
                    "promote",
                    "--report",
                    str(path),
                    "--min-bets",
                    "10",
                    "--min-roi",
                    "0.05",
                    "--min-profit",
                    "20",
                    "--max-drawdown-pct",
                    "0.10",
                    "--compact",
                ])

        self.assertEqual(code, 0)
        output = "".join(call.args[0] for call in stdout.write.call_args_list if call.args)
        payload = json.loads(output)
        self.assertTrue(payload["approved"])
        self.assertEqual(payload["decision"]["min_edge"], 0.04)

    def test_promote_cli_accepts_utf8_bom_json_from_powershell(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "validation.json"
            path.write_text(json.dumps(_validation_report()), encoding="utf-8-sig")

            with patch("sys.stdout") as stdout:
                code = main(["promote", "--report", str(path), "--compact"])

        self.assertEqual(code, 0)
        output = "".join(call.args[0] for call in stdout.write.call_args_list if call.args)
        payload = json.loads(output)
        self.assertTrue(payload["approved"])


def _validation_report() -> dict:
    return {
        "selected_settings": {
            "min_edge": 0.04,
            "fractional_kelly": 0.25,
            "max_stake_fraction": 0.05,
        },
        "validation": {
            "settings": {"bankroll": 1000.0},
            "total_bets": 25,
            "profit": 120.0,
            "roi": 0.12,
            "max_drawdown_pct": 0.08,
            "hit_rate": 0.56,
        },
    }


if __name__ == "__main__":
    unittest.main()
