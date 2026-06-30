from __future__ import annotations

from pathlib import Path
import json
import sqlite3
from typing import Any


class BotRepository:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        if self.path.parent:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def create_run(self, config: dict[str, Any]) -> int:
        conn = self._connect()
        try:
            cursor = conn.execute(
                "INSERT INTO runs (status, config_json, matches) VALUES (?, ?, ?)",
                ("running", json.dumps(config, ensure_ascii=False), 0),
            )
            conn.commit()
            return int(cursor.lastrowid)
        finally:
            conn.close()

    def save_match_result(self, run_id: int, result: dict[str, Any]) -> None:
        fixture = result["fixture"]
        conn = self._connect()
        try:
            conn.execute(
                """
                INSERT INTO matches
                    (run_id, home_team, away_team, match_date, league, prediction_json, decision_json, result_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    fixture["home_team"],
                    fixture["away_team"],
                    fixture["date"],
                    fixture["league"],
                    json.dumps(result.get("prediction", {}), ensure_ascii=False),
                    json.dumps(result.get("decisions", {}), ensure_ascii=False),
                    result.get("result_path"),
                ),
            )
            conn.execute("UPDATE runs SET matches = matches + 1 WHERE id = ?", (run_id,))
            conn.commit()
        finally:
            conn.close()

    def finish_run(self, run_id: int, *, status: str) -> None:
        conn = self._connect()
        try:
            conn.execute("UPDATE runs SET status = ? WHERE id = ?", (status, run_id))
            conn.commit()
        finally:
            conn.close()

    def list_runs(self) -> list[dict[str, Any]]:
        conn = self._connect()
        try:
            rows = conn.execute("SELECT id, status, matches, config_json FROM runs ORDER BY id DESC").fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def list_match_decisions(self) -> list[dict[str, Any]]:
        conn = self._connect()
        try:
            rows = conn.execute(
                """
                SELECT id, run_id, home_team, away_team, match_date, league, prediction_json, decision_json
                FROM matches
                ORDER BY id ASC
                """
            ).fetchall()
            matches = []
            for row in rows:
                item = dict(row)
                item["prediction"] = json.loads(item.pop("prediction_json"))
                item["decision"] = json.loads(item.pop("decision_json"))
                matches.append(item)
            return matches
        finally:
            conn.close()

    def save_settlement(self, match_id: int, settlement: dict[str, Any]) -> None:
        conn = self._connect()
        try:
            conn.execute(
                """
                INSERT INTO settlements (match_id, market, status, stake, profit, odds, settlement_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    match_id,
                    settlement["market"],
                    settlement["status"],
                    settlement["stake"],
                    settlement["profit"],
                    settlement.get("odds"),
                    json.dumps(settlement, ensure_ascii=False),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def performance_report(self) -> dict[str, Any]:
        conn = self._connect()
        try:
            rows = conn.execute("SELECT market, status, stake, profit, settlement_json FROM settlements ORDER BY id ASC").fetchall()
            settlements = []
            for row in rows:
                item = dict(row)
                details = json.loads(item.pop("settlement_json"))
                item.update(details)
                settlements.append(item)
        finally:
            conn.close()
        total_bets = len(settlements)
        wins = sum(1 for item in settlements if item["status"] == "won")
        pushes = sum(1 for item in settlements if item["status"] == "push")
        stake = round(sum(float(item["stake"]) for item in settlements), 2)
        profit = round(sum(float(item["profit"]) for item in settlements), 2)
        by_market: dict[str, dict[str, Any]] = {}
        by_family: dict[str, dict[str, Any]] = {}
        for item in settlements:
            market = item["market"]
            _add_to_bucket(by_market.setdefault(market, _empty_bucket()), item)
            _add_to_bucket(by_family.setdefault(_market_family(market), _empty_bucket()), item)
        _strip_internal_bucket_fields(by_market)
        _strip_internal_bucket_fields(by_family)
        return {
            "total_bets": total_bets,
            "wins": wins,
            "pushes": pushes,
            "losses": total_bets - wins - pushes,
            "stake": stake,
            "profit": profit,
            "roi": round(profit / stake, 6) if stake else 0.0,
            "avg_clv": _avg_clv(settlements),
            "positive_clv_rate": _positive_clv_rate(settlements),
            "by_market": by_market,
            "by_family": by_family,
        }

    def _init_schema(self) -> None:
        conn = self._connect()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    status TEXT NOT NULL,
                    config_json TEXT NOT NULL,
                    matches INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS matches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL,
                    home_team TEXT NOT NULL,
                    away_team TEXT NOT NULL,
                    match_date TEXT NOT NULL,
                    league TEXT NOT NULL,
                    prediction_json TEXT NOT NULL,
                    decision_json TEXT NOT NULL,
                    result_path TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS settlements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    match_id INTEGER NOT NULL,
                    market TEXT NOT NULL,
                    status TEXT NOT NULL,
                    stake REAL NOT NULL,
                    profit REAL NOT NULL,
                    odds REAL,
                    settlement_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn


def _empty_bucket() -> dict[str, Any]:
    return {
        "bets": 0,
        "wins": 0,
        "pushes": 0,
        "losses": 0,
        "stake": 0.0,
        "profit": 0.0,
        "roi": 0.0,
        "avg_clv": 0.0,
        "positive_clv_rate": 0.0,
        "_clv_values": [],
    }


def _add_to_bucket(bucket: dict[str, Any], item: dict[str, Any]) -> None:
    bucket["bets"] += 1
    bucket["wins"] += 1 if item["status"] == "won" else 0
    bucket["pushes"] += 1 if item["status"] == "push" else 0
    bucket["losses"] += 1 if item["status"] == "lost" else 0
    bucket["stake"] = round(bucket["stake"] + float(item["stake"]), 2)
    bucket["profit"] = round(bucket["profit"] + float(item["profit"]), 2)
    bucket["roi"] = round(bucket["profit"] / bucket["stake"], 6) if bucket["stake"] else 0.0
    if "clv" in item:
        bucket["_clv_values"].append(float(item["clv"]))
    bucket["avg_clv"] = _avg(bucket["_clv_values"])
    bucket["positive_clv_rate"] = _positive_rate(bucket["_clv_values"])


def _market_family(market: str) -> str:
    if market in {"home_win", "draw", "away_win"}:
        return "1x2"
    if market.startswith("over_") or market.startswith("under_"):
        return "totals"
    if "_spread_" in market:
        return "spreads"
    return "other"


def _strip_internal_bucket_fields(buckets: dict[str, dict[str, Any]]) -> None:
    for bucket in buckets.values():
        bucket.pop("_clv_values", None)


def _avg_clv(settlements: list[dict[str, Any]]) -> float:
    return _avg([float(item["clv"]) for item in settlements if "clv" in item])


def _positive_clv_rate(settlements: list[dict[str, Any]]) -> float:
    return _positive_rate([float(item["clv"]) for item in settlements if "clv" in item])


def _avg(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 6)


def _positive_rate(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(1 for value in values if value > 0) / len(values), 6)
