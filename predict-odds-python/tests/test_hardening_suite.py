import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from predict_odds.aliases import TeamAliasResolver
from predict_odds.calibration import calibrate_market_probabilities
from predict_odds.cli import main
from predict_odds.config_writer import apply_promoted_decision_config
from predict_odds.digest import build_daily_digest
from predict_odds.llm_prompt import build_match_analysis_prompt
from predict_odds.migrations import migrate_database
from predict_odds.probability_metrics import evaluate_probability_predictions
from predict_odds.safety import evaluate_safety_gates


class HardeningSuiteTest(unittest.TestCase):
    def test_apply_promoted_decision_config_updates_config_and_creates_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "bot-scan.json"
            promotion_path = Path(tmp) / "promotion.json"
            config_path.write_text(json.dumps({"decision": {"bankroll": 100}}), encoding="utf-8")
            promotion_path.write_text(
                json.dumps({
                    "approved": True,
                    "decision": {
                        "bankroll": 1000,
                        "min_edge": 0.04,
                        "fractional_kelly": 0.25,
                        "max_stake_fraction": 0.05,
                    },
                }),
                encoding="utf-8",
            )

            result = apply_promoted_decision_config(config_path, promotion_path)
            updated = json.loads(config_path.read_text(encoding="utf-8"))

            self.assertEqual(updated["decision"]["min_edge"], 0.04)
            self.assertTrue(result["backup_path"].endswith(".bak"))
            self.assertTrue(Path(result["backup_path"]).exists())

    def test_alias_resolver_normalizes_provider_names(self):
        resolver = TeamAliasResolver({"Arsenal": ["Arsenal FC", "ARS"], "Chelsea": ["Chelsea FC"]})

        self.assertEqual(resolver.resolve("arsenal fc"), "Arsenal")
        self.assertEqual(resolver.resolve("ARS"), "Arsenal")
        self.assertEqual(resolver.resolve("Unknown United"), "Unknown United")

    def test_probability_metrics_and_calibration(self):
        rows = [
            {"probabilities": {"home_win": 0.70, "draw": 0.20, "away_win": 0.10}, "outcome": "home_win"},
            {"probabilities": {"home_win": 0.20, "draw": 0.30, "away_win": 0.50}, "outcome": "draw"},
        ]

        metrics = evaluate_probability_predictions(rows)
        calibrated = calibrate_market_probabilities({"home_win": 0.8, "draw": 0.1, "away_win": 0.1}, shrinkage=0.2)

        self.assertAlmostEqual(metrics["brier_score"], 0.46, places=6)
        self.assertGreater(metrics["log_loss"], 0)
        self.assertAlmostEqual(sum(calibrated.values()), 1.0, places=6)
        self.assertLess(calibrated["home_win"], 0.8)

    def test_migration_records_schema_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "bot.sqlite"

            result = migrate_database(db_path)
            conn = sqlite3.connect(db_path)
            version = conn.execute("SELECT version FROM schema_version").fetchone()[0]
            conn.close()

        self.assertEqual(result["version"], 1)
        self.assertEqual(version, 1)

    def test_safety_gates_pause_risky_state(self):
        result = evaluate_safety_gates(
            {"stake": 120, "max_drawdown_pct": 0.22, "losses": 4, "wins": 1},
            max_daily_stake=100,
            max_drawdown_pct=0.15,
            max_consecutive_losses=3,
        )

        self.assertFalse(result["allowed"])
        self.assertIn("daily stake 120.0 > limit 100.0", result["reasons"])
        self.assertIn("drawdown 0.22 > limit 0.15", result["reasons"])

    def test_digest_and_llm_prompt_are_structured(self):
        digest = build_daily_digest(
            scan={"processed": 2, "skipped": 1, "matches": [{"decisions": {"recommendations": [{"action": "bet"}]}}]},
            report={"total_bets": 5, "profit": 42.5, "roi": 0.12, "max_drawdown": 8.0},
        )
        prompt = build_match_analysis_prompt({
            "fixture": {"home_team": "Arsenal", "away_team": "Chelsea"},
            "features": {"features": {"form_points_diff": 0.5}},
            "prediction": {"probabilities": {"home_win": 0.5}},
        })

        self.assertEqual(digest["signals"], 1)
        self.assertIn("Arsenal", prompt)
        self.assertIn("Return JSON", prompt)

    def test_apply_config_cli_prints_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "bot-scan.json"
            promotion_path = Path(tmp) / "promotion.json"
            config_path.write_text("{}", encoding="utf-8")
            promotion_path.write_text(
                json.dumps({"approved": True, "decision": {"bankroll": 500, "min_edge": 0.03}}),
                encoding="utf-8",
            )

            with patch("sys.stdout") as stdout:
                code = main(["apply-config", "--config", str(config_path), "--promotion", str(promotion_path), "--compact"])

        self.assertEqual(code, 0)
        output = "".join(call.args[0] for call in stdout.write.call_args_list if call.args)
        payload = json.loads(output)
        self.assertTrue(payload["updated"])


if __name__ == "__main__":
    unittest.main()
