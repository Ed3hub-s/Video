"""File-backed JSON cache keyed by content hashes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_json(obj: Any) -> str:
    return hash_text(json.dumps(obj, sort_keys=True, default=str))


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class FileCache:
    """Simple deterministic cache: cache/<key-hash>.json."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.hits = 0
        self.misses = 0

    def _path(self, key: str) -> Path:
        return self.root / f"{hash_text(key)}.json"

    def get(self, key: str) -> Any | None:
        path = self._path(key)
        if not path.exists():
            self.misses += 1
            return None
        try:
            with open(path, "r", encoding="utf-8") as handle:
                self.hits += 1
                return json.load(handle)
        except (OSError, json.JSONDecodeError):
            self.misses += 1
            return None

    def put(self, key: str, value: Any) -> Path:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, default=str)
        return path
