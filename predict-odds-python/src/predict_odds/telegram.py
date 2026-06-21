from __future__ import annotations

import json
import os
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .errors import PredictConfigError, PredictHTTPError


class TelegramNotifier:
    def __init__(self, *, bot_token: str, chat_id: str, timeout: float = 10.0) -> None:
        if not bot_token:
            raise PredictConfigError("TELEGRAM_BOT_TOKEN is required.")
        if not chat_id:
            raise PredictConfigError("TELEGRAM_CHAT_ID is required.")
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.timeout = timeout

    @classmethod
    def from_env(cls) -> "TelegramNotifier":
        return cls(
            bot_token=os.environ.get("TELEGRAM_BOT_TOKEN", ""),
            chat_id=os.environ.get("TELEGRAM_CHAT_ID", ""),
        )

    def send(self, text: str) -> dict[str, Any]:
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        body = urlencode({"chat_id": self.chat_id, "text": text}).encode("utf-8")
        request = Request(url, data=body, method="POST")
        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except OSError as exc:
            raise PredictHTTPError(0, f"Could not send Telegram notification: {exc}") from exc
        if not payload.get("ok"):
            raise PredictHTTPError(0, "Telegram API rejected the notification.", json.dumps(payload))
        return payload


def format_telegram_summary(result: dict[str, Any]) -> str:
    fixture = result.get("fixture", {})
    prediction = result.get("prediction", {})
    decisions = result.get("decisions", {})
    top_bet = _top_bet(decisions.get("recommendations", []))
    score = _top_score(prediction.get("most_likely_scores", []))
    expected_goals = prediction.get("expected_goals", {})
    lines = [
        f"{fixture.get('league', 'Football')} {fixture.get('date', '')}".strip(),
        f"{fixture.get('home_team', 'Home')} vs {fixture.get('away_team', 'Away')}",
        f"Expected goals: {expected_goals.get('home', 0)} - {expected_goals.get('away', 0)}",
        f"Most likely score: {score}",
    ]
    if top_bet:
        lines.append(
            "Top value: "
            f"{top_bet['market']} EV {top_bet['expected_value']} stake {top_bet['stake']}"
        )
    else:
        lines.append("Top value: no qualifying bet")
    if result.get("result_path"):
        lines.append(f"Full JSON: {result['result_path']}")
    return "\n".join(lines)


def _top_bet(recommendations: list[dict[str, Any]]) -> dict[str, Any] | None:
    bets = [item for item in recommendations if item.get("action") == "bet"]
    if not bets:
        return None
    return max(bets, key=lambda item: item.get("expected_value", 0))


def _top_score(scores: list[dict[str, Any]]) -> str:
    if not scores:
        return "n/a"
    first = scores[0]
    return f"{first.get('score', 'n/a')} ({first.get('probability', 0)})"
