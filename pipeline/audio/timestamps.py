"""Estimate word- and sentence-level timestamps from narration + duration."""

from __future__ import annotations

import re


WORD_RE = re.compile(r"\S+")


def word_timestamps(text: str, duration: float, offset: float = 0.0) -> list[dict[str, float | str]]:
    """Evenly distribute narration over its audio duration."""

    words = WORD_RE.findall(text.strip())
    if not words:
        return []
    step = duration / len(words)
    return [
        {
            "word": word,
            "start": round(offset + i * step, 3),
            "end": round(offset + (i + 1) * step, 3),
        }
        for i, word in enumerate(words)
    ]


def sentence_timestamps(text: str, duration: float, offset: float = 0.0) -> list[dict[str, float | str]]:
    words = word_timestamps(text, duration, offset)
    sentences: list[dict[str, float | str]] = []
    current: list[str] = []
    current_start: float | None = None
    for word in words:
        if current_start is None:
            current_start = float(word["start"])
        current.append(str(word["word"]))
        if str(word["word"]).endswith((".", "!", "?", "…")):
            sentences.append(
                {
                    "text": " ".join(current),
                    "start": current_start,
                    "end": float(word["end"]),
                }
            )
            current = []
            current_start = None
    if current:
        sentences.append(
            {
                "text": " ".join(current),
                "start": current_start or offset,
                "end": offset + duration,
            }
        )
    return sentences
