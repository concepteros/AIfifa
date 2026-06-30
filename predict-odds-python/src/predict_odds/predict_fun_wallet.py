"""Predict.fun wallet auth, account, and position operations for the football bot."""

from __future__ import annotations

import json
import os
from urllib.request import Request, urlopen
from urllib.error import HTTPError

BASE_URL = "https://api.predict.fun"

HEADERS = {
    "x-api-key": os.getenv("PREDICTFUN_API_KEY") or os.getenv("PREDICT_API_KEY", ""),
    "User-Agent": "predict-odds-bot/1.0",
    "Accept": "application/json",
}

_jwt_token: str | None = None


def _request(method: str, path: str, body: dict = None, *, use_jwt: bool = False) -> dict:
    url = f"{BASE_URL}{path}"
    h = dict(HEADERS)
    if use_jwt and _jwt_token:
        h["Authorization"] = f"Bearer {_jwt_token}"
    data_bytes = json.dumps(body).encode() if body else None
    if data_bytes:
        h["Content-Type"] = "application/json"

    req = Request(url, data=data_bytes, headers=h)
    if method != "GET":
        req.method = method

    try:
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        body_text = e.read().decode()
        try:
            return json.loads(body_text)
        except json.JSONDecodeError:
            return {"error": str(e), "body": body_text[:500]}


def _authenticate() -> str:
    """Authenticate wallet and return JWT token. Caches globally."""
    global _jwt_token
    if _jwt_token:
        return _jwt_token

    pk = os.getenv("PREDICTFUN_WALLET_PRIVATE_KEY", "")
    if not pk:
        raise RuntimeError("PREDICTFUN_WALLET_PRIVATE_KEY not set")

    # 1. Get message
    resp = _request("GET", "/v1/auth/message")
    if not resp.get("success"):
        raise RuntimeError(f"Auth message failed: {resp}")
    msg = resp["data"]["message"]

    # 2. Sign
    from eth_account import Account
    from eth_account.messages import encode_defunct

    acct = Account.from_key(pk)
    signed = acct.sign_message(encode_defunct(text=msg))
    sig = f"0x{signed.signature.hex()}"

    # 3. Get JWT (retry once on 500)
    for attempt in range(2):
        resp = _request("POST", "/v1/auth", {
            "signer": acct.address,
            "signature": sig,
            "message": msg,
        })
        if resp.get("success"):
            _jwt_token = resp["data"]["token"]
            return _jwt_token
        if attempt == 0:
            import time
            time.sleep(1)

    raise RuntimeError(f"Auth failed after retry: {resp}")


def get_account() -> dict:
    """Return connected account info."""
    return _request("GET", "/v1/account", use_jwt=True)


def get_positions() -> list[dict]:
    """Return list of open positions."""
    resp = _request("GET", "/v1/positions", use_jwt=True)
    return resp.get("data", [])


def get_wallet_dashboard() -> str:
    """Compact wallet + positions summary for Telegram."""
    try:
        _authenticate()
    except RuntimeError as e:
        return f"❌ 钱包连接失败: {e}"

    acc = get_account()
    addr = acc.get("data", acc).get("address", "未知")
    name = acc.get("data", acc).get("name", "未知")
    pts = acc.get("data", acc).get("points", {}).get("total", 0)
    balance = acc.get("data", acc).get("balance", "0")

    positions = get_positions()

    lines = ["💳 Predict.fun 钱包"]
    lines.append(f"地址: {addr[:10]}...{addr[-6:]}")
    lines.append(f"名称: {name}  积分: {pts}")
    lines.append(f"余额: {balance} USDC")

    if positions:
        lines.append("")
        lines.append("📊 当前仓位:")
        for p in positions:
            mkt = p.get("marketId", "?")
            side = p.get("side", "?")
            size = p.get("size", 0)
            price = p.get("price", "?")
            pnl = p.get("pnl", "?")
            side_cn = "看涨" if side.upper() == "BUY" else "看跌"
            lines.append(f"  #{mkt} {side_cn} x{size} @ {price}  PnL:{pnl}")
    else:
        lines.append("仓位: 无")

    return "\n".join(lines)
