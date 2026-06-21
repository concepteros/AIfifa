from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class TeamAliasResolver:
    def __init__(self, aliases: dict[str, list[str]] | None = None) -> None:
        self.aliases = aliases or {}
        self._lookup = {}
        for canonical, names in self.aliases.items():
            self._lookup[_key(canonical)] = canonical
            for name in names:
                self._lookup[_key(name)] = canonical

    @classmethod
    def from_file(cls, path: str | Path) -> "TeamAliasResolver":
        payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
        if isinstance(payload, dict) and isinstance(payload.get("aliases"), dict):
            payload = payload["aliases"]
        if not isinstance(payload, dict):
            raise ValueError("alias file must contain an object")
        return cls({str(key): [str(item) for item in value] for key, value in payload.items()})

    def resolve(self, name: str) -> str:
        stripped = str(name).strip()
        return self._lookup.get(_key(stripped), stripped)


def _key(value: str) -> str:
    return " ".join(str(value).strip().casefold().replace(".", "").split())
