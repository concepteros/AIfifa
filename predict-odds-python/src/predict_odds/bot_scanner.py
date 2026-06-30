from __future__ import annotations

from datetime import datetime, timezone
UTC = timezone.utc
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

# New enrichment modules
try:
    from .sentiment import analyze_match_sentiment as _sentiment_analyze
    _HAS_SENTIMENT = True
except ImportError:
    _HAS_SENTIMENT = False

try:
    from .tactics import analyze_tactical_matchup as _tactical_analyze
    from .tactics import generate_tactical_analysis as _tactical_summary
    _HAS_TACTICS = True
except ImportError:
    _HAS_TACTICS = False

try:
    from .supplementary import get_match_supplementary_context as _supplementary_context
    _HAS_SUPPLEMENTARY = True
except ImportError:
    _HAS_SUPPLEMENTARY = False

try:
    from .ml_model import ensemble_predict as _ensemble_predict
    _HAS_ML = True
except ImportError:
    _HAS_ML = False

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
    prediction = predict_match(features["features"], odds=normalized.get("markets"))
    
    # --- Enrichment: sentiment, tactics, supplementary, ML ensemble ---
    enrichment = {}
    
    # Helper to convert dataclass to dict
    import dataclasses as _dc
    def _to_json(v):
        if hasattr(v, '__dataclass_fields__'):
            return _dc.asdict(v)
        if isinstance(v, dict):
            return {k: _to_json(vv) for k, vv in v.items()}
        if isinstance(v, list):
            return [_to_json(x) for x in v]
        return v
    
    # Sentiment analysis
    if _HAS_SENTIMENT:
        try:
            enrichment["sentiment"] = _to_json(_sentiment_analyze(fixture.home_team, fixture.away_team, alias_resolver=None))
        except Exception:
            enrichment["sentiment"] = None
    
    # Tactical analysis
    if _HAS_TACTICS:
        try:
            enrichment["tactics"] = _to_json({
                "advantage": _tactical_analyze(fixture.home_team, fixture.away_team),
                "analysis": _tactical_summary(fixture.home_team, fixture.away_team),
            })
        except Exception:
            enrichment["tactics"] = None
    
    # Supplementary (weather, referee, injuries)
    if _HAS_SUPPLEMENTARY:
        try:
            enrichment["supplementary"] = _to_json(_supplementary_context(
                fixture.home_team, fixture.away_team, venue_city=""
            ))
        except Exception:
            enrichment["supplementary"] = None
    
    # ML ensemble prediction
    if _HAS_ML:
        try:
            enrichment["ml_ensemble"] = _to_json(_ensemble_predict(
                prediction,
                xgb_prediction=None,
            ))
        except Exception:
            enrichment["ml_ensemble"] = None
    
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
        "enrichment": enrichment if enrichment else None,
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


def _format_daily_schedule(config: dict[str, Any], results: list[dict[str, Any]]) -> str:
    if not results:
        return "📅 今日无赛程"
    league = config.get("scan", {}).get("league", "")
    date = config.get("scan", {}).get("date", "")
    lines = [f"📅 {date} 赛程（{len(results)}场）", f"🏆 {league}", ""]
    for r in results:
        f = r["fixture"]
        p = r["prediction"]["probabilities"]
        home = p["home_win"]
        draw = p["draw"]
        away = p["away_win"]
        # Highlight favorite
        if home > away and home > draw:
            hl = f"**{f['home_team']}**"
            al = f["away_team"]
        elif away > home and away > draw:
            hl = f["home_team"]
            al = f"**{f['away_team']}**"
        else:
            hl = f["home_team"]
            al = f["away_team"]
        lines.append(f"{hl} vs {al}")
        lines.append(f"  {home:.0%} / {draw:.0%} / {away:.0%}")
    lines.append("")
    lines.append("💡 /d 仪表盘 | /a 赛事分析")
    return "\n".join(lines)


def _notify_error(config: dict[str, Any], telegram_sender: TelegramSender | None, title: str, exc: Exception) -> None:
    if not config.get("telegram", {}).get("enabled", False):
        return
    sender = telegram_sender or TelegramNotifier.from_env().send
    sender(f"{title}: {type(exc).__name__}: {exc}")


def format_kelly_summary(scan_result: dict[str, Any]) -> str:
    """Format scan results with Kelly Criterion position sizing as human-readable text.

    Returns a markdown-formatted string suitable for Telegram delivery.
    """
    matches = scan_result.get("matches", [])
    if not matches:
        return "📅 今日无赛程"

    lines = ["⚽ **Kelly 仓位分析**", ""]

    for r in matches:
        f = r.get("fixture", {})
        home = f.get("home_team", "?")
        away = f.get("away_team", "?")
        decisions = r.get("decisions", {})
        probs = r.get("prediction", {}).get("probabilities", {})

        lines.append(f"### {home} vs {away}")
        lines.append(f"模型: 主{probs.get('home_win',0):.0%} / 平{probs.get('draw',0):.0%} / 客{probs.get('away_win',0):.0%}")

        # Show odds
        odds = r.get("odds", {}).get("markets", {})
        if odds:
            parts = []
            for k in ("home_win", "draw", "away_win"):
                if k in odds:
                    parts.append(f"{k.replace('_',' ')}:{odds[k]:.2f}")
            if parts:
                lines.append(f"赔率: {' | '.join(parts)}")

        recs = decisions.get("recommendations", [])
        bets = [rec for rec in recs if rec.get("action") == "bet"]
        no_bets = [rec for rec in recs if rec.get("action") != "bet"]

        if bets:
            lines.append("")
            lines.append("📊 **下注建议:**")
            for b in bets:
                market_cn = {
                    "home_win": "主胜", "away_win": "客胜", "draw": "平局",
                    "over_2_5": "大2.5", "under_2_5": "小2.5",
                }.get(b["market"], b["market"])
                edge = b["edge"] * 100
                ev = b["expected_value"] * 100
                kelly = b["kelly_fraction"] * 100
                stake = b["stake"]
                model_p = b["model_probability"] * 100
                market_p = b["implied_probability"] * 100

                lines.append(f"✅ **{market_cn}** — 下注 **${stake:.2f}**")
                lines.append(f"   Kelly: {kelly:.1f}% (1/4: {kelly/4:.1f}%) · Edge: {edge:.1f}% · EV: +{ev:.1f}%")
                lines.append(f"   模型 {model_p:.0f}% vs 市场 {market_p:.0f}%")
        else:
            if recs:
                lines.append("⛔ 无价值投注（edge不足或赔率不利）")

        lines.append("")

    # Get config from first match that has decisions
    bankroll = 0
    cfg = {}
    for r in matches:
        d = r.get("decisions", {})
        if d:
            bankroll = d.get("bankroll", bankroll)
            cfg = d.get("settings", cfg)
            break
    lines.append("---")
    lines.append(f"💰 资金池: ${bankroll:.0f} · 最低Edge: {cfg.get('min_edge', 0.03)*100:.0f}% · Kelly系数: {cfg.get('fractional_kelly', 0.25)} · 单注上限: {cfg.get('max_stake_fraction', 0.05)*100:.0f}%")

    return "\n".join(lines)
