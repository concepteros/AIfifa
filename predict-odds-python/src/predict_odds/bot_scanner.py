from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any, Callable

from .data_sources import Fixture, load_injuries, load_matches
from .decision import build_betting_decisions
from .feature_pipeline import build_match_features
from .market_sources import fetch_market_events
from .odds_normalizer import normalize_event_odds
from .prediction import predict_match
from .repository import BotRepository
from .telegram import TelegramNotifier, format_telegram_summary

TelegramSender = Callable[[str], Any]


def scan_upcoming_matches(
    config_path: str | Path,
    *,
    odds_events: list[dict[str, Any]] | None = None,
    telegram_sender: TelegramSender | None = None,
) -> dict[str, Any]:
    config = _load_json(config_path)
    repository = BotRepository(config["database"]["path"])
    run_id = repository.create_run(config)
    processed = []
    skipped = 0
    try:
        matches = load_matches(config["data"]["fbref"])
        injuries = load_injuries(config["data"]["transfermarkt"])
        events = odds_events if odds_events is not None else _fetch_events(config)
        for event in events:
            normalized = _normalize_event(event)
            if not _has_team_data(matches, normalized["home_team"], normalized["away_team"]):
                skipped += 1
                continue
            result = _process_event(config, normalized, matches, injuries)
            repository.save_match_result(run_id, result)
            processed.append(result)
            if config.get("telegram", {}).get("enabled", False):
                sender = telegram_sender or TelegramNotifier.from_env().send
                sender(format_telegram_summary(result))
        repository.finish_run(run_id, status="ok")
    except Exception as exc:
        repository.finish_run(run_id, status="error")
        _notify_error(config, telegram_sender, "Scan failed", exc)
        raise
    return {
        "run_id": run_id,
        "processed": len(processed),
        "skipped": skipped,
        "matches": processed,
    }


def _fetch_events(config: dict[str, Any]) -> list[dict[str, Any]]:
    return fetch_market_events(config)


def _normalize_event(event: dict[str, Any]) -> dict[str, Any]:
    if isinstance(event.get("markets"), dict):
        return event
    return normalize_event_odds(event)


def _process_event(
    config: dict[str, Any],
    normalized: dict[str, Any],
    matches,
    injuries,
) -> dict[str, Any]:
    scan = config["scan"]
    fixture = Fixture(
        league=scan["league"],
        date=scan["date"],
        home_team=normalized["home_team"],
        away_team=normalized["away_team"],
    )
    features = build_match_features(
        fixture=fixture,
        matches=matches,
        injuries=injuries,
        window=int(config.get("window", 5)),
    )
    prediction = predict_match(features)
    decisions = build_betting_decisions(
        prediction,
        normalized["markets"],
        bankroll=config["decision"]["bankroll"],
        min_edge=config["decision"].get("min_edge", 0.03),
        fractional_kelly=config["decision"].get("fractional_kelly", 0.25),
        max_stake_fraction=config["decision"].get("max_stake_fraction", 0.05),
    )
    result = {
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "event_id": normalized["event_id"],
        "fixture": {
            "league": fixture.league,
            "date": fixture.date,
            "home_team": fixture.home_team,
            "away_team": fixture.away_team,
        },
        "odds": normalized,
        "features": features,
        "prediction": prediction,
        "decisions": decisions,
    }
    result["result_path"] = str(_write_match_result(result, config))
    return result


def _write_match_result(result: dict[str, Any], config: dict[str, Any]) -> Path:
    output_dir = Path(config["output"]["directory"])
    output_dir.mkdir(parents=True, exist_ok=True)
    fixture = result["fixture"]
    path = output_dir / f"{fixture['date']}-{_slug(fixture['home_team'])}-vs-{_slug(fixture['away_team'])}.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _has_team_data(matches, home_team: str, away_team: str) -> bool:
    teams = {match.team.casefold() for match in matches}
    return home_team.casefold() in teams and away_team.casefold() in teams


def _load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"JSON file must contain an object: {path}")
    return payload


def _slug(value: str) -> str:
    return "-".join(value.lower().split())


def _notify_error(config: dict[str, Any], telegram_sender: TelegramSender | None, title: str, exc: Exception) -> None:
    if not config.get("telegram", {}).get("enabled", False):
        return
    sender = telegram_sender or TelegramNotifier.from_env().send
    sender(f"{title}: {type(exc).__name__}: {exc}")
