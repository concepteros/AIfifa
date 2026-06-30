from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
UTC = timezone.utc
import json
import logging
import os
from pathlib import Path
from typing import Any

from .bot_scanner import scan_upcoming_matches
from .errors import PredictConfigError, PredictValidationError
from .market_sources import fetch_market_events
from .predict_fun_wallet import get_wallet_dashboard, get_positions as fetch_pf_positions
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
            "⚽ AI 足球投注机器人",
            f"最近扫描: {_run_line(last_run)}",
            f"累计下注: {report['total_bets']} 单  收益率: {_pct(report['roi'])}",
            f"日限额: {self.config.limits.get('daily_stake', 0.0)}",
            f"单注上限: {self.config.limits.get('max_single_stake', 0.0)}",
        ]
        return "\n".join(lines)

    def upcoming(self, *, limit: int = 20) -> str:
        scan_config = _load_json(self.config.scan_config)
        events = fetch_market_events(scan_config)
        if not events:
            return "📅 即将开赛\n暂无赛事数据。"
        lines = [f"📅 {scan_config.get('scan', {}).get('date', '')} 赛程（{len(events)}场）"]
        for event in events[:limit]:
            lines.append(f"{event.get('home_team')} vs {event.get('away_team')}")
        return "\n".join(lines)

    def scan(self) -> str:
        result = scan_upcoming_matches(self.config.scan_config)
        config = _load_json(self.config.scan_config)
        processed = result.get("matches", [])
        if not processed:
            return "✅ 扫描完成\n今日无赛程。"
        lines = [
            f"📅 {config.get('scan', {}).get('date', '')} 赛程（{len(processed)}场）",
            f"🏆 {config.get('scan', {}).get('league', '')}",
            "",
        ]
        for r in processed:
            f = r["fixture"]
            p = r["prediction"]["probabilities"]
            h = p["home_win"]
            d = p["draw"]
            a = p["away_win"]
            if h > a and h > d:
                lines.append(f"**{f['home_team']}** vs {f['away_team']}")
            elif a > h and a > d:
                lines.append(f"{f['home_team']} vs **{f['away_team']}**")
            else:
                lines.append(f"{f['home_team']} vs {f['away_team']}")
            lines.append(f"  {h:.0%} / {d:.0%} / {a:.0%}")
        return "\n".join(lines)

    def history(self, *, limit: int = 8) -> str:
        runs = BotRepository(self.config.database).list_runs()
        if not runs:
            return "📊 历史记录\n暂无记录。"
        lines = ["📊 历史记录"]
        for run in runs[:limit]:
            lines.append(f"#{run['id']}  {_status_cn(run['status'])}  场次 {run['matches']}")
        return "\n".join(lines)

    def approvals(self, *, limit: int = 8) -> str:
        matches = BotRepository(self.config.database).list_match_decisions()
        signals = _pending_signals(matches)
        if not signals:
            return "📋 待审核\n暂无待审核信号。"
        lines = ["📋 待审核"]
        for signal in signals[:limit]:
            lines.append(
                f"{signal['signal_id']}  {signal['home_team']} vs {signal['away_team']}  "
                f"{_market_cn(signal['market'])}  建议 {signal['stake']:.1f}"
            )
        return "\n".join(lines)

    def set_limit(self, name: str, value: str | float) -> str:
        normalized = str(name).strip()
        cn_name = _limit_cn(normalized)
        if normalized not in {"daily_stake", "max_single_stake", "max_daily_stake"}:
            raise PredictValidationError(f"不支持的限额类型: {name}")
        try:
            amount = float(value)
        except (TypeError, ValueError) as exc:
            raise PredictValidationError(f"无效的限额值: {value}") from exc
        if amount < 0:
            raise PredictValidationError("限额不能为负数。")
        _update_panel_limit(self.config.config_path, normalized, amount)
        self.config.limits[normalized] = amount
        return f"{cn_name} 已设为 {amount}"

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
        status = "已批准" if approved else "已拒绝"
        return f"信号 {signal_id} {status}。"

    def wallet(self) -> str:
        """Predict.fun wallet + positions summary."""
        try:
            return get_wallet_dashboard()
        except Exception as exc:
            return f"❌ 钱包查询失败: {type(exc).__name__}: {exc}"

    def positions(self) -> str:
        """Predict.fun positions detail."""
        try:
            pf_positions = fetch_pf_positions()
        except Exception as exc:
            return f"❌ 仓位查询失败: {type(exc).__name__}: {exc}"
        if not pf_positions:
            return "📊 当前仓位\n无持仓。"
        lines = ["📊 Predict.fun 仓位"]
        for p in pf_positions:
            mkt = p.get("marketId", "?")
            side = "看涨" if p.get("side", "").upper() == "BUY" else "看跌"
            size = p.get("size", 0)
            price = p.get("price", "?")
            pnl = p.get("pnl", "?")
            q = p.get("question", p.get("title", ""))[:30]
            lines.append(f"  #{mkt} {q}")
            lines.append(f"    {side} x{size} @ {price}  PnL: {pnl}")
        return "\n".join(lines)

    def deposit(self) -> str:
        """Show deposit address for Predict.fun wallet."""
        addr = os.getenv("PREDICTFUN_WALLET_ADDRESS", "未配置")
        return (
            "💰 充值 Predict.fun\n"
            f"网络: Polygon\n"
            f"地址: `{addr}`\n"
            "币种: USDC / POL\n"
            "到账后刷新 /w 查看余额。"
        )

    def analysis(self, *, limit: int = 5) -> str:
        """Detailed match analysis for the most recent scan only."""
        matches = BotRepository(self.config.database).list_match_decisions()
        if not matches:
            return "📋 赛事分析\n暂无扫描数据，先点「扫描下注」。"
        # Only show matches from the most recent run
        runs = BotRepository(self.config.database).list_runs()
        if runs:
            latest_run_id = runs[0]["id"]
            matches = [m for m in matches if m.get("run_id") == latest_run_id]
        lines = ["📋 赛事分析（最新扫描）"]
        shown = 0
        for match in matches:
            if shown >= limit:
                break
            h = match.get("home_team", "?")
            a = match.get("away_team", "?")
            pred = match.get("prediction", {})
            exp = pred.get("expected_goals", {})
            prob = pred.get("probabilities", {})
            scores = pred.get("most_likely_scores", [])[:2]
            score_str = ", ".join(f"{s['score']} ({s['probability']:.0%})" for s in scores)
            lines.append(
                f"\n⚽ {h} vs {a}\n"
                f"  比分预测: {score_str}\n"
                f"  胜平负: 主{_pct(prob.get('home_win',0))} / 平{_pct(prob.get('draw',0))} / 客{_pct(prob.get('away_win',0))}\n"
                f"  大小球: 大2.5 {_pct(prob.get('over_2_5',0))} / 小2.5 {_pct(prob.get('under_2_5',0))}"
            )
            shown += 1
        if shown == 0:
            return "📋 赛事分析\n暂无扫描数据，先点「扫描下注」。"
        return "\n".join(lines)


def build_dashboard_keyboard() -> list[list[dict[str, str]]]:
    return [
        [
            {"text": "🔍 扫描下注", "callback_data": "dashboard:scan"},
            {"text": "📅 赛事预测", "callback_data": "dashboard:upcoming"},
        ],
        [
            {"text": "📋 赛事分析", "callback_data": "dashboard:analysis"},
            {"text": "💳 钱包", "callback_data": "dashboard:wallet"},
        ],
        [
            {"text": "📊 仓位", "callback_data": "dashboard:positions"},
            {"text": "📜 历史", "callback_data": "dashboard:history"},
        ],
        [
            {"text": "⚙️ 限额", "callback_data": "dashboard:limits"},
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
            await update.effective_message.reply_text("⛔ 未授权的会话。")
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
                    InlineKeyboardButton(f"✅ {signal['signal_id']}", callback_data=f"signal:approve:{signal['signal_id']}"),
                    InlineKeyboardButton(f"❌ {signal['signal_id']}", callback_data=f"signal:reject:{signal['signal_id']}"),
                ]
            )
        await update.effective_message.reply_text(text, reply_markup=InlineKeyboardMarkup(rows) if rows else None)

    async def set_limit_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await guard(update):
            return
        if len(context.args) != 2:
            await update.effective_message.reply_text("用法: /set_limit daily_stake 100")
            return
        await _send_or_error(update, lambda: service.set_limit(context.args[0], context.args[1]))

    async def wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await _reply_text(update, service.wallet, guard)

    async def positions_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await _reply_text(update, service.positions, guard)

    async def deposit_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await _reply_text(update, service.deposit, guard)

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
        elif data == "dashboard:wallet":
            await _edit_or_error(query, service.wallet)
        elif data == "dashboard:positions":
            await _edit_or_error(query, service.positions)
        elif data == "dashboard:analysis":
            await _edit_or_error(query, service.analysis)
        elif data.startswith("signal:approve:"):
            await _edit_or_error(query, lambda: service.approve_signal(data.rsplit(":", 1)[-1], approved=True))
        elif data.startswith("signal:reject:"):
            await _edit_or_error(query, lambda: service.approve_signal(data.rsplit(":", 1)[-1], approved=False))
        else:
            await query.edit_message_text("未知操作。")

    app = Application.builder().token(config.bot_token).build()
    app.add_handler(CommandHandler("dashboard", dashboard_command))
    app.add_handler(CommandHandler("upcoming", upcoming_command))
    app.add_handler(CommandHandler("scan", scan_command))
    app.add_handler(CommandHandler("approve", approve_command))
    app.add_handler(CommandHandler("history", history_command))
    app.add_handler(CommandHandler("set_limit", set_limit_command))
    app.add_handler(CommandHandler("wallet", wallet_command))
    app.add_handler(CommandHandler("positions", positions_command))
    app.add_handler(CommandHandler("deposit", deposit_command))
    # 快捷命令
    app.add_handler(CommandHandler("d", dashboard_command))
    app.add_handler(CommandHandler("u", upcoming_command))
    app.add_handler(CommandHandler("s", scan_command))
    app.add_handler(CommandHandler("a", approve_command))
    app.add_handler(CommandHandler("h", history_command))
    app.add_handler(CommandHandler("l", set_limit_command))
    app.add_handler(CommandHandler("w", wallet_command))
    app.add_handler(CommandHandler("p", positions_command))
    app.add_handler(CommandHandler("de", deposit_command))
    app.add_handler(CallbackQueryHandler(callback_handler))
    LOGGER.info("Starting Telegram control panel (中文模式)")
    app.run_polling(poll_interval=config.poll_interval)


# ── helpers ──────────────────────────────────────────────

async def _reply_text(update: Any, renderer: Any, guard: Any) -> None:
    if not await guard(update):
        return
    await _send_or_error(update, renderer)


async def _send_or_error(update: Any, renderer: Any) -> None:
    try:
        text = renderer()
    except Exception as exc:
        LOGGER.exception("Telegram panel command failed")
        text = f"命令失败: {type(exc).__name__}: {exc}"
    await update.effective_message.reply_text(text)


async def _edit_or_error(query: Any, renderer: Any) -> None:
    try:
        text = renderer()
    except Exception as exc:
        LOGGER.exception("Telegram panel callback failed")
        text = f"操作失败: {type(exc).__name__}: {exc}"
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
        return "无"
    return f"#{run['id']} {_status_cn(run['status'])} {run['matches']}场"


def _status_cn(status: str) -> str:
    return {"ok": "成功", "error": "失败", "running": "运行中"}.get(status, status)


def _market_cn(market: str) -> str:
    """Translate market key to Chinese display name."""
    return {
        "home_win": "主胜",
        "away_win": "客胜",
        "draw": "平局",
        "over_2_5": "大2.5",
        "under_2_5": "小2.5",
        "over_3_0": "大3.0",
        "under_3_0": "小3.0",
        "over_3_5": "大3.5",
        "under_3_5": "小3.5",
        "btts_yes": "双方进球",
        "btts_no": "零封",
    }.get(market, market)


def _limit_cn(name: str) -> str:
    return {
        "daily_stake": "日限额",
        "max_single_stake": "单注上限",
        "max_daily_stake": "日最大投注",
    }.get(name, name)


def _pct(value: float) -> str:
    return f"{value * 100:+.1f}%"


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
