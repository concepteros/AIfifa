from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

from .bot_scanner import scan_upcoming_matches
from .bot_scanner import format_kelly_summary
from .backtest import run_backtest
from .config_writer import apply_promoted_decision_config
from .client import PredictOddsClient
from .client import DEFAULT_API_URL
from .data_sources import Fixture, load_injuries, load_matches
from .decision import build_betting_decisions
from .deep_analysis import gather_analysis_context, load_match_json
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
from .sentiment import analyze_match_sentiment
from .aliases import TeamAliasResolver
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
    scan_parser.add_argument("--summary", action="store_true", help="Print human-readable Kelly summary instead of JSON.")

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

    # ── Predict.fun betting ──
    bet_parser = subparsers.add_parser("bet", help="Place a bet on Predict.fun World Cup match markets.")
    bet_parser.add_argument("--market-id", type=int, help="Predict.fun market ID (e.g. 163340).")
    bet_parser.add_argument("--match-slug", help="Match slug (e.g. fifwc-tun-jpn-2026-06-21).")
    bet_parser.add_argument("--bet-type", default="home",
                            help="Bet type: home, away, draw, over_2_5, under_2_5, exact_score_X-Y.")
    bet_parser.add_argument("--side", help="Buy or sell (only with --market-id).")
    bet_parser.add_argument("--amount", type=float, default=10.0, help="Total USDC to bet (default: 10).")
    bet_parser.add_argument("--price", type=float, help="Price per share (auto-fetched if omitted).")
    bet_parser.add_argument("--size", type=float, help="Number of shares (calculated if omitted).")
    bet_parser.add_argument("--dry-run", action="store_true", default=True,
                            help="Simulate without placing order (default: True for safety).")
    bet_parser.add_argument("--live", dest="dry_run", action="store_false",
                            help="Actually place the bet (overrides --dry-run).")
    bet_parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompt.")
    bet_parser.add_argument("--max-bet", type=float, default=50.0, help="Max single bet in USDC (default: 50).")
    bet_parser.add_argument("--daily-limit", type=float, default=200.0,
                            help="Max daily total in USDC (default: 200).")

    panel_parser = subparsers.add_parser("telegram-panel", help="Run the interactive Telegram control panel.")
    panel_parser.add_argument("--config", required=True, help="Path to Telegram panel JSON config.")

    analyze_parser = subparsers.add_parser("analyze", help="Deep match analysis: odds, market, Poisson, tactical breakdown.")
    analyze_parser.add_argument("--match", required=True, help="Path to match result JSON (from out/ directory).")
    analyze_parser.add_argument("--no-prompt", action="store_true", help="Output structured context JSON instead of LLM prompt.")

    train_parser = subparsers.add_parser("train", help="Train a machine learning model on historical match data.")
    train_parser.add_argument("--model", required=True, choices=["xgboost"], help="Model type to train.")
    train_parser.add_argument("--data", required=True, help="Path to fbref.csv match data.")
    train_parser.add_argument("--output", default="data/xgboost_model.json", help="Path to save trained model.")
    train_parser.add_argument("--compact", action="store_true", help="Print compact JSON.")

    # ── Sell / take-profit ──
    sell_check_parser = subparsers.add_parser("sell-check", help="Check open Predict.fun positions for take-profit triggers.")
    sell_check_parser.add_argument("--position-file", required=True, help="Path to positions JSON file.")
    sell_check_parser.add_argument("--live", action="store_true", help="Execute sell orders (default: dry-run).")
    sell_check_parser.add_argument("--compact", action="store_true", help="Print compact output.")

    sell_track_parser = subparsers.add_parser("sell-track", help="Track a new position for take-profit monitoring.")
    sell_track_parser.add_argument("--position-file", required=True, help="Path to positions JSON file.")
    sell_track_parser.add_argument("--market-id", required=True, help="Predict.fun market ID.")
    sell_track_parser.add_argument("--token-id", required=True, help="On-chain token ID.")
    sell_track_parser.add_argument("--entry-price", type=float, required=True, help="Entry price per share in cents.")
    sell_track_parser.add_argument("--shares", type=float, required=True, help="Number of shares bought.")
    sell_track_parser.add_argument("--match-name", default="", help="Human-readable match name.")
    sell_track_parser.add_argument("--outcome", default="Yes", help="Outcome (Yes/No).")

    sell_now_parser = subparsers.add_parser("sell-now", help="Manually sell a percentage of a position (25%, 50%, 100%).")
    sell_now_parser.add_argument("--position-file", required=True, help="Path to positions JSON file.")
    sell_now_parser.add_argument("--market-id", required=True, help="Predict.fun market ID to sell.")
    sell_now_parser.add_argument("--pct", type=int, required=True, choices=[25, 50, 100], help="Percentage of position to sell (25, 50, or 100).")
    sell_now_parser.add_argument("--live", action="store_true", help="Execute sell order (default: dry-run).")
    sell_now_parser.add_argument("--limit-price", type=float, help="Limit price in cents (auto-fetched as market order if omitted).")

    sentiment_parser = subparsers.add_parser("sentiment", help="Analyze public sentiment for a football match.")
    sentiment_parser.add_argument("--match", help="Match slug or description (e.g. fifwc-tun-jpn-2026-06-21).")
    sentiment_parser.add_argument("--home-team", help="Home team name (overrides --match parsing).")
    sentiment_parser.add_argument("--away-team", help="Away team name (overrides --match parsing).")
    sentiment_parser.add_argument("--alias-file", help="Path to team alias JSON file.")
    sentiment_parser.add_argument("--no-fetch", action="store_true", help="Skip live web fetch (useful for testing).")
    sentiment_parser.add_argument("--compact", action="store_true", help="Print compact JSON.")

    return parser


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    elif isinstance(argv, tuple):
        argv = list(argv)
    if not argv:
        build_parser().print_help()
        return 2
    command_names = {"odds", "sportmonks-fixture", "features", "predict", "decide", "run", "schedule", "scan", "doctor", "settle", "report", "backtest", "optimize", "validate", "walk-forward", "promote", "apply-config", "evaluate-probs", "safety", "digest", "llm-prompt", "migrate-db", "demo", "telegram-panel", "analyze", "bet", "sentiment", "train", "sell-check", "sell-track", "sell-now", "-h", "--help"}
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
            if getattr(args, 'summary', False):
                print(format_kelly_summary(result))
            else:
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
        if command == "bet":
            from .predict_fun_betting import bet_cli
            return bet_cli(args)
        if command == "sentiment":
            home, away = _resolve_sentiment_teams(args)
            resolver = None
            if args.alias_file:
                resolver = TeamAliasResolver.from_file(args.alias_file)
            fetch_news = None if args.no_fetch else None  # use default fetcher when not suppressed
            result = analyze_match_sentiment(
                home, away,
                alias_resolver=resolver,
                articles=[] if args.no_fetch else None,
            )
            print(json.dumps({
                "home_team": result.home_team,
                "away_team": result.away_team,
                "home_sentiment": result.home_sentiment,
                "away_sentiment": result.away_sentiment,
                "sources": result.sources,
                "summary": result.summary,
            }, ensure_ascii=False, indent=None if args.compact else 2))
            return 0
        if command == "analyze":
            match = load_match_json(args.match)
            if args.no_prompt:
                context = gather_analysis_context(match)
                print(json.dumps(context, ensure_ascii=False, indent=2))
            else:
                from .deep_analysis import build_deep_analysis_prompt
                context = gather_analysis_context(match)
                print(build_deep_analysis_prompt(context))
            return 0
        if command == "train":
            from .ml_model import train_and_save
            result = train_and_save(args.data, save_path=args.output)
            print(json.dumps(result, ensure_ascii=False, indent=None if args.compact else 2))
            return 0
        if command == "sell-check":
            from .predict_fun_sell import sell_check_cli
            output = sell_check_cli(args.position_file, dry_run=not args.live)
            print(output)
            return 0
        if command == "sell-track":
            from .predict_fun_sell import Position, PositionTracker
            tracker = PositionTracker.load(args.position_file)
            tracker.add_position(Position(
                market_id=args.market_id,
                token_id=args.token_id,
                side="buy",
                entry_price=args.entry_price,
                shares=args.shares,
                entry_time=datetime.now(timezone.utc).isoformat(),
                match_name=args.match_name,
                outcome=args.outcome,
            ))
            print(f"✅ 已添加持仓: {args.match_name} {args.outcome} @ {args.entry_price}¢ × {args.shares}")
            print(f"   止盈: +25%/+50%/+100%")
            return 0
        if command == "sell-now":
            from .predict_fun_sell import sell_now_cli
            output = sell_now_cli(
                args.position_file,
                args.market_id,
                args.pct,
                dry_run=not args.live,
                limit_price=args.limit_price,
            )
            print(output)
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


def _resolve_sentiment_teams(args: argparse.Namespace) -> tuple[str, str]:
    """Extract home/away teams from CLI args or parse from --match slug."""
    if args.home_team and args.away_team:
        return args.home_team, args.away_team
    if args.match:
        return _parse_teams_from_slug(args.match)
    raise PredictAPIError("Either --match or both --home-team/--away-team must be provided.")


def _parse_teams_from_slug(slug: str) -> tuple[str, str]:
    """Parse team names from a match slug like 'fifwc-tun-jpn-2026-06-21'.

    Returns (home_team, away_team) with common abbreviations resolved.
    """
    # Map FIFA three-letter codes to team names
    _FIFA_CODE_MAP: dict[str, str] = {
        "arg": "Argentina",
        "aus": "Australia",
        "bel": "Belgium",
        "bra": "Brazil",
        "can": "Canada",
        "chi": "Chile",
        "cmr": "Cameroon",
        "col": "Colombia",
        "crc": "Costa Rica",
        "cro": "Croatia",
        "den": "Denmark",
        "ecu": "Ecuador",
        "egy": "Egypt",
        "eng": "England",
        "esp": "Spain",
        "fra": "France",
        "ger": "Germany",
        "gha": "Ghana",
        "irn": "Iran",
        "ita": "Italy",
        "jpn": "Japan",
        "kor": "South Korea",
        "ksa": "Saudi Arabia",
        "mar": "Morocco",
        "mex": "Mexico",
        "ned": "Netherlands",
        "nga": "Nigeria",
        "pol": "Poland",
        "por": "Portugal",
        "qat": "Qatar",
        "sen": "Senegal",
        "srb": "Serbia",
        "sui": "Switzerland",
        "tun": "Tunisia",
        "uru": "Uruguay",
        "usa": "United States",
        "wal": "Wales",
    }

    parts = slug.split("-")
    # Look for two adjacent 3-letter codes (home, away)
    for i in range(len(parts) - 1):
        a, b = parts[i].lower(), parts[i + 1].lower()
        if len(a) == 3 and len(b) == 3 and a in _FIFA_CODE_MAP and b in _FIFA_CODE_MAP:
            return _FIFA_CODE_MAP[a], _FIFA_CODE_MAP[b]

    # Fallback: treat first two parts as team names
    if len(parts) >= 2:
        return parts[0].capitalize(), parts[1].capitalize()
    raise PredictAPIError(f"Cannot parse teams from slug: {slug}")


def _load_events_file(path: str) -> list[dict[str, object]]:
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
        raise PredictAPIError(f"Events file must contain a list of objects: {path}")
    return payload
