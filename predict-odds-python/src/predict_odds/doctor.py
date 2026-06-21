from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable

from .env_loader import load_env_file
from .workflow import load_workflow_config

Probe = Callable[[], None]


def check_bot_health(
    *,
    config_path: str | Path,
    env_file: str | Path | None = None,
    mode: str = "scan",
    skip_network: bool = True,
    odds_probe: Probe | None = None,
    telegram_probe: Probe | None = None,
) -> dict[str, Any]:
    if env_file:
        load_env_file(env_file)
    checks: list[dict[str, Any]] = []
    config = _load_config_for_mode(config_path, mode, checks)
    if config:
        if mode == "scan":
            _check_env("THE_ODDS_API_KEY", checks)
            _check_files([config["data"].get("fbref"), config["data"].get("transfermarkt")], checks)
            _check_output(config.get("output", {}).get("directory"), checks)
            _check_database(config.get("database", {}).get("path"), checks)
        else:
            _check_files([config["data"].get("fbref"), config["data"].get("transfermarkt"), config["data"].get("odds")], checks)
            _check_output(config.get("output", {}).get("directory"), checks)
        if config.get("telegram", {}).get("enabled", False):
            _check_env("TELEGRAM_BOT_TOKEN", checks)
            _check_env("TELEGRAM_CHAT_ID", checks)
    if not skip_network:
        _run_probe("network:odds", odds_probe, checks)
        _run_probe("network:telegram", telegram_probe, checks)
    return {
        "ok": all(check["ok"] for check in checks),
        "mode": mode,
        "checks": checks,
    }


def _load_config_for_mode(path: str | Path, mode: str, checks: list[dict[str, Any]]) -> dict[str, Any] | None:
    try:
        if mode == "workflow":
            config = load_workflow_config(path)
        else:
            config = _load_scan_config(path)
        checks.append(_ok("config", str(path)))
        return config
    except Exception as exc:
        checks.append(_fail("config", str(exc)))
        return None


def _load_scan_config(path: str | Path) -> dict[str, Any]:
    import json

    with Path(path).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    for key in ("scan", "data", "decision", "output", "database"):
        if key not in payload or not isinstance(payload[key], dict):
            raise ValueError(f"Scan config requires object field: {key}")
    return payload


def _check_env(name: str, checks: list[dict[str, Any]]) -> None:
    if os.environ.get(name):
        checks.append(_ok(f"env:{name}", "set"))
    else:
        checks.append(_fail(f"env:{name}", "missing"))


def _check_files(paths: list[str | None], checks: list[dict[str, Any]]) -> None:
    for raw_path in paths:
        name = f"file:{raw_path}"
        if raw_path and Path(raw_path).exists():
            checks.append(_ok(name, "exists"))
        else:
            checks.append(_fail(name, "missing"))


def _check_output(path: str | None, checks: list[dict[str, Any]]) -> None:
    if not path:
        checks.append(_fail("output", "missing output directory"))
        return
    output_path = Path(path)
    try:
        output_path.mkdir(parents=True, exist_ok=True)
        checks.append(_ok("output", str(output_path)))
    except OSError as exc:
        checks.append(_fail("output", str(exc)))


def _check_database(path: str | None, checks: list[dict[str, Any]]) -> None:
    if not path:
        checks.append(_fail("database", "missing database path"))
        return
    parent = Path(path).parent
    if parent:
        parent.mkdir(parents=True, exist_ok=True)
    checks.append(_ok("database", str(path)))


def _run_probe(name: str, probe: Probe | None, checks: list[dict[str, Any]]) -> None:
    if probe is None:
        checks.append(_ok(name, "skipped"))
        return
    try:
        probe()
        checks.append(_ok(name, "ok"))
    except Exception as exc:
        checks.append(_fail(name, str(exc)))


def _ok(name: str, detail: str) -> dict[str, Any]:
    return {"name": name, "ok": True, "detail": detail}


def _fail(name: str, detail: str) -> dict[str, Any]:
    return {"name": name, "ok": False, "detail": detail}
