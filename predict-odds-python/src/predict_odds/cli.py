from __future__ import annotations

import argparse
import json
import os
import sys

from .bot_scanner import scan_upcoming_matches
from .backtest import run_backtest
from .config_writer import apply_promoted_decision_config
from .client import PredictOddsClient
from .client import DEFAULT_API_URL
from .data_sources import Fixture, load_injuries, load_matches
from .decision import build_betting_decisions
from .demo import run_demo
from .doctor import check_bot_health
from .digest import build_daily_digest
from .env_loader import load_env_file
from .errors import PredictAPIError
from .feature_pipeline import build_match_features
from .llm_prompt import build_match_analysis_prompt
from .migrations import migrate_database
from .optimize import optimize_parameters, parse_float_grid
from .prediction import predict_match
from .promotion import promote_strategy
from .probability_metrics import evaluate_probability_predictions
from .safety import evaluate_safety_gates
from .scheduler import configure_daily_job
from .scheduler import create_blocking_scheduler
from .settlement import build_performance_report
from .settlement import settle_database
from .sportmonks import DEFAULT_SPORTMONKS_INCLUDES, SportmonksClient
from .telegram_panel import run_telegram_panel
from .validation import validate_strategy
from .walk_forward import parse_walk_forward_window, run_walk_forward
from .workflow import run_workflow


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch odds or engineer football match features.")
    parser.add_argument("--env-file", default=".env", help="Path to a dotenv-style environment file.")
    subparsers = parser.add_subparsers(dest="command")

    odds_parser = subparsers.add_parser("odds", help="Fetch structured football odds from Predict API.")
    _add_match_filter_args(odds_parser)
    odds_parser.add_argument("--api-url", help="Override Predict API URL.")
    odds_parser.add_argument("--api-key", help="Override PREDICT_API_KEY for this invocation.")
    odds_parser.add_argument("--compact", action="store_true", help="Print compact JSON.")

    sportmonks_parser = subparsers.add_parser("sportmonks-fixture", help="Fetch Sportmonks football fixture details.")
    sportmonks_parser.add_argument("--fixture-id", required=True, type=int, help="Sportmonks fixture ID.")
    sportmonks_parser.add_argument("--includes", default=DEFAULT_SPORTMONKS_INCLUDES, help="Semicolon-separated Sportmonks includes.")
    sportmonks_parser.add_argument("--compact", action="store_true", help="Print compact JSON.")

    features_parser = subparsers.add_parser("features", help="Build match features from FBref and Transfermarkt exports.")
    _add_match_filter_args(features_parser)
    features_parser.add_argument("--home-team", required=True, help="Home team name.")
    features_parser.add_argument("--away-team", required=True, help="Away team name.")
    features_parser.add_argument("--fbref", required=True, help="Path to FBref-style CSV or JSON match data.")
    features_parser.add_argument("--transfermarkt", required=True, help="Path to Transfermarkt-style CSV or JSON injury data.")
    features_parser.add_argument("--window", type=int, default=5, help="Number of recent matches to use.")
    features_parser.add_argument("--compact", action="store_true", help="Print compact JSON.")

    predict_parser = subparsers.add_parser("predict", help="Predict score and outcome probabilities from engineered features.")
    _add_match_filter_args(predict_parser)
    predict_parser.add_argument("--home-team", required=True, help="Home team name.")
    predict_parser.add_argument("--away-team", required=True, help="Away team name.")
    predict_parser.add_argument("--fbref", required=True, help="Path to FBref-style CSV or JSON match data.")
    predict_parser.add_argument("--transfermarkt", required=True, help="Path to Transfermarkt-style CSV or JSON injury data.")
    predict_parser.add_argument("--window", type=int, default=5, help="Number of recent matches to use.")
    predict_parser.add_argument("--compact", action="store_true", help="Print compact JSON.")

    decide_parser = subparsers.add_parser("decide", help="Find value bets and Kelly stake sizes from prediction and odds JSON.")
    decide_parser.add_argument("--prediction", required=True, help="Path to prediction JSON from the predict command.")
    decide_parser.add_argument("--odds", required=True, help="Path to decimal odds JSON keyed by market name.")
    decide_parser.add_argument("--bankroll", type=float, required=True, help="Available bankroll.")
    decide_parser.add_argument("--min-edge", type=float, default=0.03, help="Minimum model edge required to bet.")
    decide_parser.add_argument("--fractional-kelly", type=float, default=0.25, help="Kelly fraction multiplier.")
    decide_parser.add_argument("--max-stake-fraction", type=float, default=0.05, help="Maximum stake as a bankroll fraction.")
    decide_parser.add_argument("--compact", action="store_true", help="Print compact JSON.")

    run_parser = subparsers.add_parser("run", help="Run the full feature, prediction, and decision workflow once.")
    run_parser.add_argument("--config", required=True, help="Path to workflow JSON config.")
    run_parser.add_argument("--compact", action="store_true", help="Print compact JSON.")

    schedule_parser = subparsers.add_parser("schedule", help="Schedule the full workflow to run daily.")
    schedule_parser.add_argument("--config", required=True, help="Path to workflow JSON config.")
    schedule_parser.add_argument("--time", required=True, help="Daily run time in HH:MM format.")
    schedule_parser.add_argument("--timezone", default="Asia/Shanghai", help="Scheduler timezone.")
    schedule_parser.add_argument("--once", action="store_true", help="Start scheduler then return; useful for tests.")

    scan_parser = subparsers.add_parser("scan", help="Scan upcoming matches from The Odds API and process value signals.")
    scan_parser.add_argument("--config", required=True, help="Path to scanner JSON config.")
    scan_parser.add_argument("--events-file", help="Optional local The Odds API events JSON for dry runs and tests.")
    scan_parser.add_argument("--compact", action="store_true", help="Print compact JSON.")

    doctor_parser = subparsers.add_parser("doctor", help="Check bot configuration, files, environment, and optional connectivity.")
    doctor_parser.add_argument("--config", required=True, help="Path to workflow or scanner JSON config.")
    doctor_parser.add_argument("--mode", choices=["scan", "workflow"], default="scan", help="Config type to validate.")
    doctor_parser.add_argument("--skip-network", action="store_true", help="Skip network probes.")
    doctor_parser.add_argument("--compact", action="store_true", help="Print compact JSON.")

    settle_parser = subparsers.add_parser("settle", help="Settle stored betting decisions from match results.")
    settle_parser.add_argument("--database", required=True, help="Path to bot SQLite database.")
    settle_parser.add_argument("--results", required=True, help="Path to results CSV or JSON.")
    settle_parser.add_argument("--closing-odds", help="Optional closing odds CSV or JSON for CLV tracking.")
    settle_parser.add_argument("--compact", action="store_true", help="Print compact JSON.")

    report_parser = subparsers.add_parser("report", help="Report settled betting performance.")
    report_parser.add_argument("--database", required=True, help="Path to bot SQLite database.")
    report_parser.add_argument("--compact", action="store_true", help="Print compact JSON.")

    backtest_parser = subparsers.add_parser("backtest", help="Replay stored recommendations with different risk settings.")
    backtest_parser.add_argument("--database", required=True, help="Path to bot SQLite database.")
    backtest_parser.add_argument("--results", required=True, help="Path to results CSV or JSON.")
    backtest_parser.add_argument("--bankroll", type=float, required=True, help="Bankroll to use for replayed stake sizing.")
    backtest_parser.add_argument("--min-edge", type=float, default=0.03, help="Minimum model edge required to bet.")
    backtest_parser.add_argument("--fractional-kelly", type=float, default=0.25, help="Kelly fraction multiplier.")
    backtest_parser.add_argument("--max-stake-fraction", type=float, default=0.05, help="Maximum stake as a bankroll fraction.")
    backtest_parser.add_argument("--league", help="Optional league filter.")
    backtest_parser.add_argument("--start-date", help="Optional start date filter in YYYY-MM-DD format.")
    backtest_parser.add_argument("--end-date", help="Optional end date filter in YYYY-MM-DD format.")
    backtest_parser.add_argument("--compact", action="store_true", help="Print compact JSON.")

    optimize_parser = subparsers.add_parser("optimize", help="Grid-search backtest risk parameters.")
    optimize_parser.add_argument("--database", required=True, help="Path to bot SQLite database.")
    optimize_parser.add_argument("--results", required=True, help="Path to results CSV or JSON.")
    optimize_parser.add_argument("--bankroll", type=float, required=True, help="Bankroll to use for replayed stake sizing.")
    optimize_parser.add_argument("--min-edges", required=True, help="Comma-separated min_edge values, for example 0.02,0.03,0.05.")
    optimize_parser.add_argument("--fractional-kellies", default="0.25", help="Comma-separated fractional Kelly values.")
    optimize_parser.add_argument("--max-stake-fractions", default="0.05", help="Comma-separated max stake fractions.")
    optimize_parser.add_argument("--min-bets", type=int, default=1, help="Minimum replayed bets required for a run to be returned.")
    optimize_parser.add_argument("--league", help="Optional league filter.")
    optimize_parser.add_argument("--start-date", help="Optional start date filter in YYYY-MM-DD format.")
    optimize_parser.add_argument("--end-date", help="Optional end date filter in YYYY-MM-DD format.")
    optimize_parser.add_argument("--compact", action="store_true", help="Print compact JSON.")

    validate_parser = subparsers.add_parser("validate", help="Optimize on a train window and backtest a validation window.")
    validate_parser.add_argument("--database", required=True, help="Path to bot SQLite database.")
    validate_parser.add_argument("--results", required=True, help="Path to results CSV or JSON.")
    validate_parser.add_argument("--bankroll", type=float, required=True, help="Bankroll to use for replayed stake sizing.")
    validate_parser.add_argument("--min-edges", required=True, help="Comma-separated min_edge values.")
    validate_parser.add_argument("--fractional-kellies", default="0.25", help="Comma-separated fractional Kelly values.")
    validate_parser.add_argument("--max-stake-fractions", default="0.05", help="Comma-separated max stake fractions.")
    validate_parser.add_argument("--min-bets", type=int, default=1, help="Minimum train bets required for a run to be considered.")
    validate_parser.add_argument("--league", help="Optional league filter.")
    validate_parser.add_argument("--train-start-date", required=True, help="Training start date in YYYY-MM-DD format.")
    validate_parser.add_argument("--train-end-date", required=True, help="Training end date in YYYY-MM-DD format.")
    validate_parser.add_argument("--validation-start-date", required=True, help="Validation start date in YYYY-MM-DD format.")
    validate_parser.add_argument("--validation-end-date", required=True, help="Validation end date in YYYY-MM-DD format.")
    validate_parser.add_argument("--compact", action="store_true", help="Print compact JSON.")

    walk_forward_parser = subparsers.add_parser("walk-forward", help="Run validation over multiple rolling train/validation windows.")
    walk_forward_parser.add_argument("--database", required=True, help="Path to bot SQLite database.")
    walk_forward_parser.add_argument("--results", required=True, help="Path to results CSV or JSON.")
    walk_forward_parser.add_argument("--bankroll", type=float, required=True, help="Bankroll to use for replayed stake sizing.")
    walk_forward_parser.add_argument("--min-edges", required=True, help="Comma-separated min_edge values.")
    walk_forward_parser.add_argument("--fractional-kellies", default="0.25", help="Comma-separated fractional Kelly values.")
    walk_forward_parser.add_argument("--max-stake-fractions", default="0.05", help="Comma-separated max stake fractions.")
    walk_forward_parser.add_argument("--min-bets", type=int, default=1, help="Minimum train bets required for a run to be considered.")
    walk_forward_parser.add_argument("--league", help="Optional league filter.")
    walk_forward_parser.add_argument(
        "--window",
        action="append",
        required=True,
        help="Window as train_start:train_end:validation_start:validation_end. Repeat for multiple folds.",
    )
    walk_forward_parser.add_argument("--compact", action="store_true", help="Print compact JSON.")

    promote_parser = subparsers.add_parser("promote", help="Approve or reject validation output for live bot settings.")
    promote_parser.add_argument("--report", required=True, help="Path to validate or walk-forward JSON output.")
    promote_parser.add_argument("--min-bets", type=int, default=1, help="Minimum validation bets required.")
    promote_parser.add_argument("--min-roi", type=float, default=0.0, help="Minimum validation ROI required.")
    promote_parser.add_argument("--min-profit", type=float, default=0.0, help="Minimum validation profit required.")
    promote_parser.add_argument("--max-drawdown-pct", type=float, help="Maximum validation drawdown percentage allowed.")
    promote_parser.add_argument("--bankroll", type=float, help="Override bankroll in the emitted decision config.")
    promote_parser.add_argument("--compact", action="store_true", help="Print compact JSON.")

    apply_config_parser = subparsers.add_parser("apply-config", help="Write approved promoted decision settings into a bot config.")
    apply_config_parser.add_argument("--config", required=True, help="Path to bot config JSON.")
    apply_config_parser.add_argument("--promotion", required=True, help="Path to promote JSON output.")
    apply_config_parser.add_argument("--no-backup", action="store_true", help="Do not create a .bak backup.")
    apply_config_parser.add_argument("--compact", action="store_true", help="Print compact JSON.")

    evaluate_parser = subparsers.add_parser("evaluate-probs", help="Evaluate probability predictions from JSON.")
    evaluate_parser.add_argument("--input", required=True, help="Path to JSON list or object with rows.")
    evaluate_parser.add_argument("--compact", action="store_true", help="Print compact JSON.")

    safety_parser = subparsers.add_parser("safety", help="Evaluate live safety gates from a report JSON.")
    safety_parser.add_argument("--report", required=True, help="Path to report JSON.")
    safety_parser.add_argument("--max-daily-stake", type=float)
    safety_parser.add_argument("--max-drawdown-pct", type=float)
    safety_parser.add_argument("--max-consecutive-losses", type=int)
    safety_parser.add_argument("--min-bankroll", type=float)
    safety_parser.add_argument("--compact", action="store_true", help="Print compact JSON.")

    digest_parser = subparsers.add_parser("digest", help="Build a compact daily digest from scan and report JSON.")
    digest_parser.add_argument("--scan", help="Path to scan JSON.")
    digest_parser.add_argument("--report", help="Path to report JSON.")
    digest_parser.add_argument("--compact", action="store_true", help="Print compact JSON.")

    llm_prompt_parser = subparsers.add_parser("llm-prompt", help="Build an LLM match-analysis prompt from match JSON.")
    llm_prompt_parser.add_argument("--input", required=True, help="Path to match JSON.")

    migrate_parser = subparsers.add_parser("migrate-db", help="Apply lightweight SQLite schema migrations.")
    migrate_parser.add_argument("--database", required=True, help="Path to bot SQLite database.")
    migrate_parser.add_argument("--compact", action="store_true", help="Print compact JSON.")

    demo_parser = subparsers.add_parser("demo", help="Generate sample data and run an offline dry-run.")
    demo_parser.add_argument("--output", required=True, help="Output directory for demo files.")
    demo_parser.add_argument("--compact", action="store_true", help="Print compact JSON.")

    panel_parser = subparsers.add_parser("telegram-panel", help="Run the interactive Telegram control panel.")
    panel_parser.add_argument("--config", required=True, help="Path to Telegram panel JSON config.")

    return parser


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    elif isinstance(argv, tuple):
        argv = list(argv)
    if not argv:
        build_parser().print_help()
        return 2
    command_names = {"odds", "sportmonks-fixture", "features", "predict", "decide", "run", "schedule", "scan", "doctor", "settle", "report", "backtest", "optimize", "validate", "walk-forward", "promote", "apply-config", "evaluate-probs", "safety", "digest", "llm-prompt", "migrate-db", "demo", "telegram-panel", "-h", "--help"}
    if argv and argv[0] not in command_names and not argv[0].startswith("-"):
        argv = ["odds", *argv]
    parser = build_parser()
    args = parser.parse_args(argv)
    load_env_file(args.env_file)
    command = args.command
    try:
        if command in {"features", "predict"}:
            fixture = Fixture(
                league=args.league,
                date=args.date,
                home_team=args.home_team,
                away_team=args.away_team,
            )
            result = build_match_features(
                fixture=fixture,
                matches=load_matches(args.fbref),
                injuries=load_injuries(args.transfermarkt),
                window=args.window,
            )
            if command == "predict":
                result = predict_match(result)
            print(json.dumps(result, ensure_ascii=False, indent=None if args.compact else 2))
            return 0
        if command == "sportmonks-fixture":
            result = SportmonksClient.from_env().get_fixture(args.fixture_id, includes=args.includes)
            print(json.dumps(result, ensure_ascii=False, indent=None if args.compact else 2))
            return 0
        if command == "decide":
            result = build_betting_decisions(
                _load_json_file(args.prediction),
                _load_json_file(args.odds),
                bankroll=args.bankroll,
                min_edge=args.min_edge,
                fractional_kelly=args.fractional_kelly,
                max_stake_fraction=args.max_stake_fraction,
            )
            print(json.dumps(result, ensure_ascii=False, indent=None if args.compact else 2))
            return 0
        if command == "run":
            result = run_workflow(args.config)
            print(json.dumps(result, ensure_ascii=False, indent=None if args.compact else 2))
            return 0
        if command == "schedule":
            scheduler = configure_daily_job(
                config_path=args.config,
                run_time=args.time,
                timezone=args.timezone,
                scheduler=create_blocking_scheduler(args.timezone),
            )
            scheduler.start()
            return 0
        if command == "scan":
            result = scan_upcoming_matches(
                args.config,
                odds_events=_load_events_file(args.events_file) if args.events_file else None,
            )
            print(json.dumps(result, ensure_ascii=False, indent=None if args.compact else 2))
            return 0
        if command == "doctor":
            result = check_bot_health(
                config_path=args.config,
                env_file=args.env_file,
                mode=args.mode,
                skip_network=args.skip_network,
            )
            print(json.dumps(result, ensure_ascii=False, indent=None if args.compact else 2))
            return 0 if result["ok"] else 1
        if command == "settle":
            result = settle_database(args.database, args.results, closing_odds_path=args.closing_odds)
            print(json.dumps(result, ensure_ascii=False, indent=None if args.compact else 2))
            return 0
        if command == "report":
            result = build_performance_report(args.database)
            print(json.dumps(result, ensure_ascii=False, indent=None if args.compact else 2))
            return 0
        if command == "backtest":
            result = run_backtest(
                args.database,
                args.results,
                bankroll=args.bankroll,
                min_edge=args.min_edge,
                fractional_kelly=args.fractional_kelly,
                max_stake_fraction=args.max_stake_fraction,
                league=args.league,
                start_date=args.start_date,
                end_date=args.end_date,
            )
            print(json.dumps(result, ensure_ascii=False, indent=None if args.compact else 2))
            return 0
        if command == "optimize":
            result = optimize_parameters(
                args.database,
                args.results,
                bankroll=args.bankroll,
                min_edges=parse_float_grid(args.min_edges),
                fractional_kellies=parse_float_grid(args.fractional_kellies),
                max_stake_fractions=parse_float_grid(args.max_stake_fractions),
                min_bets=args.min_bets,
                league=args.league,
                start_date=args.start_date,
                end_date=args.end_date,
            )
            print(json.dumps(result, ensure_ascii=False, indent=None if args.compact else 2))
            return 0
        if command == "validate":
            result = validate_strategy(
                args.database,
                args.results,
                bankroll=args.bankroll,
                min_edges=parse_float_grid(args.min_edges),
                fractional_kellies=parse_float_grid(args.fractional_kellies),
                max_stake_fractions=parse_float_grid(args.max_stake_fractions),
                min_bets=args.min_bets,
                league=args.league,
                train_start_date=args.train_start_date,
                train_end_date=args.train_end_date,
                validation_start_date=args.validation_start_date,
                validation_end_date=args.validation_end_date,
            )
            print(json.dumps(result, ensure_ascii=False, indent=None if args.compact else 2))
            return 0
        if command == "walk-forward":
            result = run_walk_forward(
                args.database,
                args.results,
                bankroll=args.bankroll,
                min_edges=parse_float_grid(args.min_edges),
                fractional_kellies=parse_float_grid(args.fractional_kellies),
                max_stake_fractions=parse_float_grid(args.max_stake_fractions),
                min_bets=args.min_bets,
                league=args.league,
                windows=[parse_walk_forward_window(item) for item in args.window],
            )
            print(json.dumps(result, ensure_ascii=False, indent=None if args.compact else 2))
            return 0
        if command == "promote":
            result = promote_strategy(
                _load_json_file(args.report),
                min_bets=args.min_bets,
                min_roi=args.min_roi,
                min_profit=args.min_profit,
                max_drawdown_pct=args.max_drawdown_pct,
                bankroll=args.bankroll,
            )
            print(json.dumps(result, ensure_ascii=False, indent=None if args.compact else 2))
            return 0
        if command == "apply-config":
            result = apply_promoted_decision_config(args.config, args.promotion, backup=not args.no_backup)
            print(json.dumps(result, ensure_ascii=False, indent=None if args.compact else 2))
            return 0
        if command == "evaluate-probs":
            payload = _load_json_or_list_file(args.input)
            rows = payload.get("rows", payload.get("predictions", [])) if isinstance(payload, dict) else payload
            result = evaluate_probability_predictions(rows)
            print(json.dumps(result, ensure_ascii=False, indent=None if args.compact else 2))
            return 0
        if command == "safety":
            result = evaluate_safety_gates(
                _load_json_file(args.report),
                max_daily_stake=args.max_daily_stake,
                max_drawdown_pct=args.max_drawdown_pct,
                max_consecutive_losses=args.max_consecutive_losses,
                min_bankroll=args.min_bankroll,
            )
            print(json.dumps(result, ensure_ascii=False, indent=None if args.compact else 2))
            return 0
        if command == "digest":
            result = build_daily_digest(
                scan=_load_json_file(args.scan) if args.scan else None,
                report=_load_json_file(args.report) if args.report else None,
            )
            print(json.dumps(result, ensure_ascii=False, indent=None if args.compact else 2))
            return 0
        if command == "llm-prompt":
            print(build_match_analysis_prompt(_load_json_file(args.input)))
            return 0
        if command == "migrate-db":
            result = migrate_database(args.database)
            print(json.dumps(result, ensure_ascii=False, indent=None if args.compact else 2))
            return 0
        if command == "demo":
            result = run_demo(args.output)
            print(json.dumps(result, ensure_ascii=False, indent=None if args.compact else 2))
            return 0
        if command == "telegram-panel":
            run_telegram_panel(args.config)
            return 0
        client = PredictOddsClient(
            api_key=args.api_key or os.environ.get("PREDICT_API_KEY", ""),
            api_url=args.api_url or os.environ.get("PREDICT_API_URL", DEFAULT_API_URL),
        )
        result = client.get_football_odds(league=args.league, date=args.date)
    except PredictAPIError as exc:
        print(f"predict-odds: {exc}", file=sys.stderr)
        return 1
    print(result.to_json(indent=None if args.compact else 2))
    return 0


def _add_match_filter_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--league", required=True, help="League name, for example 'Premier League'.")
    parser.add_argument("--date", required=True, help="Match date in YYYY-MM-DD format.")


def _load_json_file(path: str) -> dict[str, object]:
    with open(path, "r", encoding="utf-8-sig") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise PredictAPIError(f"JSON file must contain an object: {path}")
    return payload


def _load_json_or_list_file(path: str) -> object:
    with open(path, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def _load_events_file(path: str) -> list[dict[str, object]]:
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
        raise PredictAPIError(f"Events file must contain a list of objects: {path}")
    return payload
