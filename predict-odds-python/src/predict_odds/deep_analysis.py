"""Deep match analysis: odds, market signals, Poisson, tactical breakdown, bookmaker perspective."""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

BJT = timezone(timedelta(hours=8))


def gather_analysis_context(match_result: dict[str, Any]) -> dict[str, Any]:
    """Extract all structured data from a scan result for deep analysis.

    Returns a context dict ready for LLM prompt building.
    """
    fixture = match_result.get("fixture", {})
    odds_data = match_result.get("odds", {})
    markets = odds_data.get("markets", {})
    prediction = match_result.get("prediction", {})
    features = match_result.get("features", {}).get("features", {})
    decisions = match_result.get("decisions", {})

    # Market-implied probabilities (de-vigged)
    home_odds = markets.get("home_win", 2.0)
    draw_odds = markets.get("draw", 3.0)
    away_odds = markets.get("away_win", 2.0)
    raw_h = 1 / home_odds
    raw_d = 1 / draw_odds
    raw_a = 1 / away_odds
    total_implied = raw_h + raw_d + raw_a

    over_odds = markets.get("over_2_5")
    under_odds = markets.get("under_2_5")

    # Commence time in Beijing
    commence = odds_data.get("commence_time", "")
    commence_bj = ""
    if commence:
        ct = datetime.fromisoformat(commence.replace("Z", "+00:00"))
        commence_bj = ct.astimezone(BJT).strftime("%H:%M")

    context = {
        "fixture": {
            "home_team": fixture.get("home_team", ""),
            "away_team": fixture.get("away_team", ""),
            "league": fixture.get("league", ""),
            "date": fixture.get("date", ""),
            "commence_bj": commence_bj,
        },
        "odds": {
            "home": home_odds,
            "draw": draw_odds,
            "away": away_odds,
            "over_2_5": over_odds,
            "under_2_5": under_odds,
        },
        "market_implied": {
            "home_win": round(raw_h / total_implied, 4),
            "draw": round(raw_d / total_implied, 4),
            "away_win": round(raw_a / total_implied, 4),
        },
        "poisson": {
            "model": prediction.get("model", ""),
            "expected_goals_home": prediction.get("expected_goals", {}).get("home", 0),
            "expected_goals_away": prediction.get("expected_goals", {}).get("away", 0),
            "sources": prediction.get("expected_goals_sources", []),
            "home_win": prediction.get("probabilities", {}).get("home_win", 0),
            "draw": prediction.get("probabilities", {}).get("draw", 0),
            "away_win": prediction.get("probabilities", {}).get("away_win", 0),
            "over_2_5": prediction.get("probabilities", {}).get("over_2_5", 0),
            "most_likely_scores": [
                {"score": s["score"], "prob": s["probability"]}
                for s in prediction.get("most_likely_scores", [])[:5]
            ],
        },
        "team_form": {
            "home_xg_for": features.get("home_xg_for_avg", 0),
            "away_xg_for": features.get("away_xg_for_avg", 0),
            "home_xga": features.get("home_xga_avg", 0),
            "away_xga": features.get("away_xga_avg", 0),
            "home_form": features.get("home_form_sequence", ""),
            "away_form": features.get("away_form_sequence", ""),
            "home_injuries": features.get("home_injured_players", 0),
            "away_injuries": features.get("away_injured_players", 0),
        },
        "decision_recs": [
            {
                "market": r["market"],
                "action": r["action"],
                "edge": r.get("edge", 0),
                "stake": r.get("stake", 0),
            }
            for r in decisions.get("recommendations", [])
        ],
    }

    return context


def build_deep_analysis_prompt(
    context: dict[str, Any],
    polymarket_signals: list[dict[str, Any]] | None = None,
) -> str:
    """Build a comprehensive LLM prompt for deep match analysis.

    Args:
        context: Output from gather_analysis_context()
        polymarket_signals: Optional Polymarket signal data from OpenNews
    """
    f = context["fixture"]
    o = context["odds"]
    mi = context["market_implied"]
    po = context["poisson"]
    tf = context["team_form"]

    prompt = f"""深度分析以下世界杯比赛：

## 比赛信息
{f['home_team']} vs {f['away_team']} | {f['league']} | 北京时间 {f['commence_bj']}

## 赔率数据
- 主胜: {o['home']} (市场隐含 {mi['home_win']:.1%})
- 平局: {o['draw']} (市场隐含 {mi['draw']:.1%})
- 客胜: {o['away']} (市场隐含 {mi['away_win']:.1%})
- 大2.5: {o.get('over_2_5', 'N/A')} / 小2.5: {o.get('under_2_5', 'N/A')}

## Poisson 模型 (poisson_v2, 90%市场权重)
- 预期进球: {f['home_team']} {po['expected_goals_home']:.2f} - {po['expected_goals_away']:.2f} {f['away_team']}
- 胜平负: 主{po['home_win']:.1%} / 平{po['draw']:.1%} / 客{po['away_win']:.1%}
- 大小球: 大2.5 {po['over_2_5']:.1%}
- 最可能比分: {', '.join(f"{s['score']}({s['prob']:.0%})" for s in po['most_likely_scores'][:3])}

## 球队数据（近4场）
- {f['home_team']}: 场均xG {tf['home_xg_for']:.2f} / 场均xGA {tf['home_xga']:.2f} / 最近战绩 {tf['home_form']} / 伤病 {tf['home_injuries']}人
- {f['away_team']}: 场均xG {tf['away_xg_for']:.2f} / 场均xGA {tf['away_xga']:.2f} / 最近战绩 {tf['away_form']} / 伤病 {tf['away_injuries']}人"""

    if polymarket_signals:
        prompt += f"""

## Polymarket 聪明钱信号
{_format_polymarket(polymarket_signals)}"""

    prompt += f"""

## 下注建议（仅参考）
{_format_recs(context['decision_recs'])}

---
请从以下维度给出深度分析（中文，简洁有力）：

1. **盘口解读**：赔率结构说明了什么？庄家意图？
2. **社会舆论/市场情绪**：钱在往哪边流？
3. **实力对比**：xG/战绩/伤病综合评价
4. **战术推演**：打法风格对比，关键对位
5. **爆冷可能性**：什么条件下会爆冷？
6. **庄家收割视角**：如果你是庄家，怎么设计这个盘口收割散户？
7. **最终比分预测**：给出具体比分+理由
"""
    return prompt


def _format_polymarket(signals: list[dict[str, Any]]) -> str:
    lines = []
    for s in signals[:8]:
        text = s.get("text", "")
        # Strip HTML
        import re

        clean = re.sub(r"<[^>]+>", "", text)
        clean = re.sub(r"\s+", " ", clean).strip()[:200]
        lines.append(f"- {clean}")
    return "\n".join(lines) if lines else "暂无信号"


def _format_recs(recs: list[dict[str, Any]]) -> str:
    cn = {
        "home_win": "主胜",
        "away_win": "客胜",
        "draw": "平局",
        "under_2_5": "小2.5",
        "over_2_5": "大2.5",
    }
    lines = []
    for r in recs:
        name = cn.get(r["market"], r["market"])
        action = "✅ 下注" if r["action"] == "bet" else "❌ 不投"
        lines.append(f"- {name}: {action} (edge={r['edge']:+.1%}, 建议{r['stake']:.0f}U)")
    return "\n".join(lines) if lines else "无建议"


def load_match_json(match_path: str | Path) -> dict[str, Any]:
    """Load a match result JSON and return deep analysis context."""
    with open(match_path, encoding="utf-8") as f:
        return json.load(f)
