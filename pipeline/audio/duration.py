"""Audio duration probing via ffprobe with a pure-Python fallback."""

from __future__ import annotations

import json
import shutil
import subprocess
import wave
from pathlib import Path


def _ffprobe_duration(path: Path) -> float | None:
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        return None
    try:
        result = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "json",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return None
        data = json.loads(result.stdout)
        return float(data["format"]["duration"])
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        return None


def _wave_duration(path: Path) -> float | None:
    try:
        with wave.open(str(path), "rb") as wav:
            return wav.getnframes() / wav.getframerate()
    except (wave.Error, OSError):
        return None


def audio_duration(path: str | Path) -> float:
    """Return duration in seconds, raising if the file cannot be probed."""

    file_path = Path(path)
    duration = _ffprobe_duration(file_path)
    if duration is None:
        duration = _wave_duration(file_path)
    if duration is None or duration <= 0:
        raise RuntimeError(f"Could not determine audio duration for {path}")
    return duration


def media_duration(path: str | Path) -> float | None:
    """Return duration in seconds for any media file, or None when unreadable."""

    try:
        return audio_duration(path)
    except (RuntimeError, OSError):
        return None
