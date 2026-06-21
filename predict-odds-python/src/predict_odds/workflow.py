from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any, Callable

from .data_sources import Fixture, load_injuries, load_matches
from .decision import build_betting_decisions
from .errors import PredictValidationError
from .feature_pipeline import build_match_features
from .prediction import predict_match
from .telegram import TelegramNotifier, format_telegram_summary

TelegramSender = Callable[[str], Any]


def run_workflow(config_path: str | Path, *, telegram_sender: TelegramSender | None = None) -> dict[str, Any]:
    config = load_workflow_config(config_path)
    try:
        fixture = _fixture_from_config(config)
        features = build_match_features(
            fixture=fixture,
            matches=load_matches(config["data"]["fbref"]),
            injuries=load_injuries(config["data"]["transfermarkt"]),
            window=int(config.get("window", 5)),
        )
        prediction = predict_match(features)
        decisions = build_betting_decisions(
            prediction,
            _load_json(config["data"]["odds"]),
            bankroll=config["decision"]["bankroll"],
            min_edge=config["decision"].get("min_edge", 0.03),
            fractional_kelly=config["decision"].get("fractional_kelly", 0.25),
            max_stake_fraction=config["decision"].get("max_stake_fraction", 0.05),
        )
        result = {
            "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "fixture": {
                "league": fixture.league,
                "date": fixture.date,
                "home_team": fixture.home_team,
                "away_team": fixture.away_team,
            },
            "features": features,
            "prediction": prediction,
            "decisions": decisions,
        }
        result["result_path"] = str(_write_result(result, config))
        if config.get("telegram", {}).get("enabled", False):
            sender = telegram_sender or TelegramNotifier.from_env().send
            sender(format_telegram_summary(result))
        return result
    except Exception as exc:
        _notify_error(config, telegram_sender, "Workflow failed", exc)
        raise


def load_workflow_config(path: str | Path) -> dict[str, Any]:
    payload = _load_json(path)
    for key in ("fixture", "data", "decision", "output"):
        if key not in payload or not isinstance(payload[key], dict):
            raise PredictValidationError(f"Workflow config requires object field: {key}")
    for key in ("fbref", "transfermarkt", "odds"):
        if key not in payload["data"]:
            raise PredictValidationError(f"Workflow config data requires: {key}")
    if "bankroll" not in payload["decision"]:
        raise PredictValidationError("Workflow config decision requires: bankroll")
    return payload


def _fixture_from_config(config: dict[str, Any]) -> Fixture:
    fixture = config["fixture"]
    return Fixture(
        league=str(fixture["league"]),
        date=str(fixture["date"]),
        home_team=str(fixture["home_team"]),
        away_team=str(fixture["away_team"]),
    )


def _write_result(result: dict[str, Any], config: dict[str, Any]) -> Path:
    output_dir = Path(config["output"]["directory"])
    output_dir.mkdir(parents=True, exist_ok=True)
    fixture = result["fixture"]
    filename = (
        f"{fixture['date']}-"
        f"{_slug(fixture['home_team'])}-vs-{_slug(fixture['away_team'])}.json"
    )
    path = output_dir / filename
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise PredictValidationError(f"JSON file must contain an object: {path}")
    return payload


def _slug(value: str) -> str:
    return "-".join(value.lower().split())


def _notify_error(config: dict[str, Any], telegram_sender: TelegramSender | None, title: str, exc: Exception) -> None:
    if not config.get("telegram", {}).get("enabled", False):
        return
    sender = telegram_sender or TelegramNotifier.from_env().send
    sender(f"{title}: {type(exc).__name__}: {exc}")
