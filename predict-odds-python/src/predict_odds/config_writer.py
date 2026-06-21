from __future__ import annotations

import json
from pathlib import Path
import shutil
from typing import Any


def apply_promoted_decision_config(
    config_path: str | Path,
    promotion_path: str | Path,
    *,
    backup: bool = True,
) -> dict[str, Any]:
    config_file = Path(config_path)
    promotion = _load_json(promotion_path)
    if not promotion.get("approved"):
        return {"updated": False, "reason": "promotion is not approved", "backup_path": None}
    decision = promotion.get("decision")
    if not isinstance(decision, dict):
        return {"updated": False, "reason": "promotion has no decision config", "backup_path": None}
    config = _load_json(config_file) if config_file.exists() else {}
    backup_path = None
    if backup and config_file.exists():
        backup_file = config_file.with_suffix(config_file.suffix + ".bak")
        shutil.copyfile(config_file, backup_file)
        backup_path = str(backup_file)
    config["decision"] = decision
    config_file.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"updated": True, "config_path": str(config_file), "backup_path": backup_path, "decision": decision}


def _load_json(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON file must contain an object: {path}")
    return payload
