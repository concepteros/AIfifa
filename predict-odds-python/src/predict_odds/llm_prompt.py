from __future__ import annotations

import json
from typing import Any


def build_match_analysis_prompt(match_payload: dict[str, Any]) -> str:
    fixture = match_payload.get("fixture", {})
    home = fixture.get("home_team", "home team")
    away = fixture.get("away_team", "away team")
    compact = json.dumps(match_payload, ensure_ascii=False, sort_keys=True)
    return (
        f"Analyze the football match {home} vs {away} using the structured data below.\n"
        "Focus on form, xG profile, injuries, tactical risks, market value, and betting risk.\n"
        "Return JSON with keys: prediction_summary, key_reasons, risk_flags, confidence_adjustment.\n"
        f"Structured data:\n{compact}"
    )
