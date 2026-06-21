from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import json
import logging
import os
from pathlib import Path
from typing import Any

from .bot_scanner import scan_upcoming_matches
from .errors import PredictConfigError, PredictValidationError
from .market_sources import fetch_market_events
from .repository import BotRepository

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class TelegramPanelConfig:
    config_path: Path
    scan_config: Path
    database: Path
    bot_token_env: str = "TELEGRAM_BOT_TOKEN"
    allowed_chat_ids: set[str] = field(default_factory=set)
    approvals_path: Path = Path("out/telegram-approvals.json")
    limits: dict[str, float] = field(default_factory=dict)
    poll_interval: float = 1.0

    def is_authorized(self, chat_id: int | str | None) -> bool:
        if not self.allowed_chat_ids:
            return True
        return str(chat_id) in self.allowed_chat_ids

    @property
    def bot_token(self) -> str:
        value = os.environ.get(self.bot_token_env, "")
        if not value:
            raise PredictConfigError(f"{self.bot_token_env} is required.")
        return value


def load_panel_config(path: str | Path) -> TelegramPanelConfig:
    config_path = Path(path)
    payload = _load_json(config_path)
    panel = payload.get("telegram_panel")
    if not isinstance(panel, dict):
        raise PredictValidationError("Telegram panel config requires object field: telegram_panel")
    scan_config = _required_path(panel, "scan_config")
    database = _required_path(panel, "database")
    approvals = Path(panel.get("approvals") or panel.get("approvals_path") or "out/telegram-approvals.json")
    if not approvals.is_absolute():
        approvals = config_path.parent / approvals
    limits = {
        str(key): float(value)
        for key, value in (panel.get("limits") or {}).items()
    }
    return TelegramPanelConfig(
        config_path=config_path,
        scan_config=_resolve_relative(config_path, scan_config),
        database=_resolve_relative(config_path, database),
        bot_token_env=str(panel.get("bot_token_env", "TELEGRAM_BOT_TOKEN")),
        allowed_chat_ids={str(item) for item in panel.get("allowed_chat_ids", [])},
        approvals_path=approvals,
        limits=limits,
        poll_interval=float(panel.get("poll_interval", 1.0)),
    )


class TelegramPanelService:
    def __init__(self, config: TelegramPanelConfig) -> None:
        self.config = config

    def dashboard(self) -> str:
        runs = BotRepository(self.config.database).list_runs()
        report = BotRepository(self.config.database).performance_report()
        last_run = runs[0] if runs else None
        lines = [
            "AI Football Betting Bot",
            f"Last run: {_run_line(last_run)}",
            f"Total bets: {report['total_bets']} ROI {report['roi']}",
            f"Daily stake limit: {self.config.limits.get('daily_stake', 0.0)}",
            f"Max single stake: {self.config.limits.get('max_single_stake', 0.0)}",
        ]
        return "\n".join(lines)

    def upcoming(self, *, limit: int = 8) -> str:
        scan_config = _load_json(self.config.scan_config)
        events = fetch_market_events(scan_config)
        if not events:
            return "Upcoming Matches\nNo upcoming market events found."
        lines = ["Upcoming Matches"]
        for event in events[:limit]:
            markets = event.get("markets", {})
            preview = ", ".join(f"{name} {price}" for name, price in list(markets.items())[:3])
            lines.append(
                f"{event.get('home_team')} vs {event.get('away_team')} | "
                f"{event.get('commence_time', 'time n/a')} | {preview}"
            )
        return "\n".join(lines)

    def scan(self) -> str:
        result = scan_upcoming_matches(self.config.scan_config)
        top = _top_value_signal(result.get("matches", []))
        lines = [
            "Scan complete",
            f"Processed: {result.get('processed', 0)}",
            f"Skipped: {result.get('skipped', 0)}",
        ]
        if top:
            lines.append(f"Top value: {top['market']} EV {top['expected_value']} stake {top['stake']}")
        else:
            lines.append("Top value: none")
        return "\n".join(lines)

    def history(self, *, limit: int = 8) -> str:
        runs = BotRepository(self.config.database).list_runs()
        if not runs:
            return "Recent Runs\nNo runs recorded yet."
        lines = ["Recent Runs"]
        for run in runs[:limit]:
            lines.append(f"#{run['id']} {run['status']} matches {run['matches']}")
        return "\n".join(lines)

    def approvals(self, *, limit: int = 8) -> str:
        matches = BotRepository(self.config.database).list_match_decisions()
        signals = _pending_signals(matches)
        if not signals:
            return "Pending Approvals\nNo bet signals awaiting approval."
        lines = ["Pending Approvals"]
        for signal in signals[:limit]:
            lines.append(
                f"{signal['signal_id']} {signal['home_team']} vs {signal['away_team']} "
                f"{signal['market']} stake {signal['stake']}"
            )
        return "\n".join(lines)

    def set_limit(self, name: str, value: str | float) -> str:
        normalized = str(name).strip()
        if normalized not in {"daily_stake", "max_single_stake", "max_daily_stake"}:
            raise PredictValidationError(f"Unsupported limit: {name}")
        try:
            amount = float(value)
        except (TypeError, ValueError) as exc:
            raise PredictValidationError(f"Invalid limit value: {value}") from exc
        if amount < 0:
            raise PredictValidationError("Limit value must be non-negative.")
        _update_panel_limit(self.config.config_path, normalized, amount)
        self.config.limits[normalized] = amount
        return f"{normalized} set to {amount}"

    def approve_signal(self, signal_id: str, *, approved: bool) -> str:
        decision = {
            "signal_id": str(signal_id),
            "approved": bool(approved),
            "decided_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        }
        self.config.approvals_path.parent.mkdir(parents=True, exist_ok=True)
        payload = _load_json(self.config.approvals_path) if self.config.approvals_path.exists() else {"decisions": []}
        decisions = payload.setdefault("decisions", [])
        decisions.append(decision)
        self.config.approvals_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        status = "approved" if approved else "rejected"
        return f"Signal {signal_id} {status}."


def build_dashboard_keyboard() -> list[list[dict[str, str]]]:
    return [
        [
            {"text": "Scan Now", "callback_data": "dashboard:scan"},
            {"text": "Upcoming", "callback_data": "dashboard:upcoming"},
        ],
        [
            {"text": "History", "callback_data": "dashboard:history"},
            {"text": "Limits", "callback_data": "dashboard:limits"},
        ],
    ]


def run_telegram_panel(config_path: str | Path) -> None:
    config = load_panel_config(config_path)
    service = TelegramPanelService(config)
    try:
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
        from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes
    except ImportError as exc:
        raise PredictConfigError("Install python-telegram-bot to run telegram-panel.") from exc

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    def keyboard_markup() -> Any:
        return InlineKeyboardMarkup(
            [
                [InlineKeyboardButton(button["text"], callback_data=button["callback_data"]) for button in row]
                for row in build_dashboard_keyboard()
            ]
        )

    async def guard(update: Any) -> bool:
        chat_id = update.effective_chat.id if update.effective_chat else None
        if config.is_authorized(chat_id):
            return True
        LOGGER.warning("Unauthorized Telegram chat id: %s", chat_id)
        if update.effective_message:
            await update.effective_message.reply_text("Unauthorized chat.")
        return False

    async def dashboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await guard(update):
            return
        await update.effective_message.reply_text(service.dashboard(), reply_markup=keyboard_markup())

    async def upcoming_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await _reply_text(update, service.upcoming, guard)

    async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await _reply_text(update, service.scan, guard)

    async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await _reply_text(update, service.history, guard)

    async def approve_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await guard(update):
            return
        text = service.approvals()
        matches = BotRepository(config.database).list_match_decisions()
        rows = []
        for signal in _pending_signals(matches)[:5]:
            rows.append(
                [
                    InlineKeyboardButton(f"Approve {signal['signal_id']}", callback_data=f"signal:approve:{signal['signal_id']}"),
                    InlineKeyboardButton(f"Reject {signal['signal_id']}", callback_data=f"signal:reject:{signal['signal_id']}"),
                ]
            )
        await update.effective_message.reply_text(text, reply_markup=InlineKeyboardMarkup(rows) if rows else None)

    async def set_limit_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await guard(update):
            return
        if len(context.args) != 2:
            await update.effective_message.reply_text("Usage: /set_limit daily_stake 100")
            return
        await _send_or_error(update, lambda: service.set_limit(context.args[0], context.args[1]))

    async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await guard(update):
            return
        query = update.callback_query
        await query.answer()
        data = query.data or ""
        if data == "dashboard:scan":
            await _edit_or_error(query, service.scan)
        elif data == "dashboard:upcoming":
            await _edit_or_error(query, service.upcoming)
        elif data == "dashboard:history":
            await _edit_or_error(query, service.history)
        elif data == "dashboard:limits":
            await _edit_or_error(query, service.dashboard)
        elif data.startswith("signal:approve:"):
            await _edit_or_error(query, lambda: service.approve_signal(data.rsplit(":", 1)[-1], approved=True))
        elif data.startswith("signal:reject:"):
            await _edit_or_error(query, lambda: service.approve_signal(data.rsplit(":", 1)[-1], approved=False))
        else:
            await query.edit_message_text("Unknown action.")

    app = Application.builder().token(config.bot_token).build()
    app.add_handler(CommandHandler("dashboard", dashboard_command))
    app.add_handler(CommandHandler("upcoming", upcoming_command))
    app.add_handler(CommandHandler("scan", scan_command))
    app.add_handler(CommandHandler("approve", approve_command))
    app.add_handler(CommandHandler("history", history_command))
    app.add_handler(CommandHandler("set_limit", set_limit_command))
    app.add_handler(CallbackQueryHandler(callback_handler))
    LOGGER.info("Starting Telegram control panel")
    app.run_polling(poll_interval=config.poll_interval)


async def _reply_text(update: Any, renderer: Any, guard: Any) -> None:
    if not await guard(update):
        return
    await _send_or_error(update, renderer)


async def _send_or_error(update: Any, renderer: Any) -> None:
    try:
        text = renderer()
    except Exception as exc:
        LOGGER.exception("Telegram panel command failed")
        text = f"Command failed: {type(exc).__name__}: {exc}"
    await update.effective_message.reply_text(text)


async def _edit_or_error(query: Any, renderer: Any) -> None:
    try:
        text = renderer()
    except Exception as exc:
        LOGGER.exception("Telegram panel callback failed")
        text = f"Action failed: {type(exc).__name__}: {exc}"
    await query.edit_message_text(text)


def _pending_signals(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    signals = []
    for match in matches:
        for recommendation in match.get("decision", {}).get("recommendations", []):
            if recommendation.get("action") != "bet":
                continue
            signals.append(
                {
                    "signal_id": f"{match['id']}:{recommendation['market']}",
                    "home_team": match["home_team"],
                    "away_team": match["away_team"],
                    "market": recommendation["market"],
                    "stake": recommendation.get("stake", 0),
                    "expected_value": recommendation.get("expected_value", 0),
                }
            )
    return signals


def _top_value_signal(matches: list[dict[str, Any]]) -> dict[str, Any] | None:
    recommendations = []
    for match in matches:
        recommendations.extend(match.get("decisions", {}).get("recommendations", []))
    bets = [item for item in recommendations if item.get("action") == "bet"]
    if not bets:
        return None
    return max(bets, key=lambda item: item.get("expected_value", 0))


def _run_line(run: dict[str, Any] | None) -> str:
    if not run:
        return "none"
    return f"{run['status']}, matches {run['matches']}"


def _update_panel_limit(config_path: Path, name: str, amount: float) -> None:
    payload = _load_json(config_path)
    panel = payload.setdefault("telegram_panel", {})
    limits = panel.setdefault("limits", {})
    limits[name] = amount
    config_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _required_path(panel: dict[str, Any], key: str) -> Path:
    value = panel.get(key)
    if not value:
        raise PredictValidationError(f"Telegram panel config requires: {key}")
    return Path(str(value))


def _resolve_relative(config_path: Path, value: Path) -> Path:
    return value if value.is_absolute() else config_path.parent / value


def _load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8-sig") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise PredictValidationError(f"JSON file must contain an object: {path}")
    return payload
