"""Subtitle cue generation: sentence-level chunks that fit on screen."""

from __future__ import annotations

from pipeline.audio.timestamps import word_timestamps
from pipeline.content.schemas import SubtitleCue


def _chunk_words(
    words: list[dict[str, float | str]], max_chars: int
) -> list[tuple[list[str], float, float]]:
    chunks: list[tuple[list[str], float, float]] = []
    current: list[str] = []
    current_len = 0
    current_start: float | None = None
    last_end = 0.0
    for word in words:
        text = str(word["word"])
        if current_start is None:
            current_start = float(word["start"])
        add = len(text) + (1 if current else 0)
        if current and current_len + add > max_chars:
            chunks.append((current, current_start, last_end))
            current = [text]
            current_len = len(text)
            current_start = float(word["start"])
        else:
            current.append(text)
            current_len += add
        last_end = float(word["end"])
    if current:
        chunks.append((current, current_start, last_end))
    return chunks


def build_subtitles(
    text: str,
    duration: float,
    offset: float = 0.0,
    max_chars: int = 48,
) -> list[SubtitleCue]:
    """Build screen-friendly subtitle cues (never the full paragraph at once)."""

    words = word_timestamps(text, duration, offset)
    chunks = _chunk_words(words, max_chars)
    cues: list[SubtitleCue] = []
    for chunk_texts, start, end in chunks:
        cues.append(
            SubtitleCue(
                start=round(start, 3),
                end=round(max(end, start + 0.4), 3),
                text=" ".join(chunk_texts),
            )
        )
    return cues


def build_subtitles_from_words(
    words: list[dict],
    offset: float = 0.0,
    max_chars: int = 48,
) -> list[SubtitleCue]:
    """Build subtitle cues from real word-level timestamps (edge-tts)."""

    shifted = [
        {
            "word": item["word"],
            "start": float(item["start"]) + offset,
            "end": float(item["end"]) + offset,
        }
        for item in words
        if item.get("word")
    ]
    chunks = _chunk_words(shifted, max_chars)
    cues: list[SubtitleCue] = []
    for chunk_texts, start, end in chunks:
        cues.append(
            SubtitleCue(
                start=round(start, 3),
                end=round(max(end, start + 0.4), 3),
                text=" ".join(chunk_texts),
            )
        )
    return cues
