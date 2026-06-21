from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class DeploymentAssetsTests(unittest.TestCase):
    def read_asset(self, relative_path: str) -> str:
        path = PROJECT_ROOT / relative_path
        self.assertTrue(path.exists(), f"{relative_path} should exist")
        return path.read_text(encoding="utf-8")

    def test_powershell_scripts_call_expected_cli_commands(self):
        expected_commands = {
            "scripts/run-demo.ps1": "demo",
            "scripts/run-doctor.ps1": "doctor",
            "scripts/run-scan.ps1": "scan",
            "scripts/run-schedule.ps1": "schedule",
            "scripts/run-telegram-panel.ps1": "telegram-panel",
        }

        for relative_path, command in expected_commands.items():
            with self.subTest(script=relative_path):
                content = self.read_asset(relative_path)
                self.assertIn("$env:PYTHONPATH", content)
                self.assertIn("-m predict_odds", content)
                self.assertIn(command, content)
                self.assertNotIn("$env:PREDICT_API_KEY =", content)
                self.assertNotIn("$env:THE_ODDS_API_KEY =", content)

    def test_docker_assets_use_env_file_and_data_mounts(self):
        dockerfile = self.read_asset("Dockerfile")
        compose = self.read_asset("docker-compose.example.yml")

        self.assertIn("FROM python:3.12-slim", dockerfile)
        self.assertIn("pip install --no-cache-dir .", dockerfile)
        self.assertIn('CMD ["predict-odds", "--help"]', dockerfile)
        self.assertIn("env_file:", compose)
        self.assertIn("./data:/app/data", compose)
        self.assertIn("./out:/app/out", compose)
        self.assertIn("--skip-network", compose)

    def test_operations_guide_covers_local_and_container_runs(self):
        content = self.read_asset("OPERATIONS.md")

        for phrase in [
            "run-demo.ps1",
            "run-doctor.ps1",
            "run-scan.ps1",
            "run-schedule.ps1",
            "docker build",
            "docker compose",
            "TELEGRAM_BOT_TOKEN",
        ]:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, content)

        self.assertIn("replace-with-your-predict-key", content)
        self.assertIn("replace-with-your-odds-key", content)

    def test_readme_links_to_operations_guide(self):
        content = self.read_asset("README.md")
        self.assertIn("OPERATIONS.md", content)

    def test_telegram_panel_example_config_exists(self):
        content = self.read_asset("data/telegram-panel.example.json")
        self.assertIn("telegram_panel", content)
        self.assertIn("allowed_chat_ids", content)
        self.assertIn("daily_stake", content)


if __name__ == "__main__":
    unittest.main()
