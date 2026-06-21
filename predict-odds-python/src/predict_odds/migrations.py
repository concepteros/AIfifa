from __future__ import annotations

from pathlib import Path
import sqlite3
from typing import Any

CURRENT_SCHEMA_VERSION = 1


def migrate_database(path: str | Path) -> dict[str, Any]:
    db_path = Path(path)
    if db_path.parent:
        db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)")
        row = conn.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
        previous = int(row[0]) if row else 0
        if row is None:
            conn.execute("INSERT INTO schema_version (version) VALUES (?)", (CURRENT_SCHEMA_VERSION,))
        elif previous < CURRENT_SCHEMA_VERSION:
            conn.execute("UPDATE schema_version SET version = ?", (CURRENT_SCHEMA_VERSION,))
        conn.commit()
        return {"database": str(db_path), "previous_version": previous, "version": CURRENT_SCHEMA_VERSION}
    finally:
        conn.close()
