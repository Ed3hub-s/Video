"""Per-run structured log with progress output."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class RunLogger:
    def __init__(self, logs_dir: Path) -> None:
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.started = datetime.now().isoformat(timespec="seconds")
        self.record: dict[str, Any] = {
            "input_file": None,
            "input_hash": None,
            "start_time": self.started,
            "chapters_detected": 0,
            "scenes_generated": 0,
            "ai_requests": 0,
            "cache_hits": 0,
            "tts_requests": 0,
            "validation_warnings": 0,
            "validation_errors": 0,
            "render_results": [],
            "output_paths": [],
            "failed_chapters": [],
        }
        self._log_path = None

    def progress(self, message: str) -> None:
        print(message, flush=True)

    def set_input(self, path: str, digest: str) -> None:
        self.record["input_file"] = path
        self.record["input_hash"] = digest

    def count_chapters(self, count: int) -> None:
        self.record["chapters_detected"] = count

    def add_scenes(self, count: int) -> None:
        self.record["scenes_generated"] += count

    def add_ai_request(self) -> None:
        self.record["ai_requests"] += 1

    def add_cache_hit(self) -> None:
        self.record["cache_hits"] += 1

    def add_tts_request(self) -> None:
        self.record["tts_requests"] += 1

    def add_validation(self, errors: int, warnings: int) -> None:
        self.record["validation_errors"] += errors
        self.record["validation_warnings"] += warnings

    def add_render_result(self, chapter: int, ok: bool, output: str | None) -> None:
        self.record["render_results"].append(
            {"chapter": chapter, "ok": ok, "output": output}
        )
        if ok and output:
            self.record["output_paths"].append(output)
        if not ok:
            self.record["failed_chapters"].append(chapter)

    def finish(self) -> Path:
        timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        self._log_path = self.logs_dir / f"run-{timestamp}.json"
        with open(self._log_path, "w", encoding="utf-8") as handle:
            json.dump(self.record, handle, indent=2)
        return self._log_path
