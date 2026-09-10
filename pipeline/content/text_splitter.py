"""Split long source content into teachable chunks at conceptual boundaries."""

from __future__ import annotations

import re

from pipeline.config import Config
from pipeline.content.schemas import SourceBlock, SourceBlockType


SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])")
WORD_BOUNDARY = re.compile(r"\S+")


def word_count(text: str) -> int:
    return len(WORD_BOUNDARY.findall(text.strip()))


def split_sentences(text: str) -> list[str]:
    parts = SENTENCE_BOUNDARY.split(text.strip())
    return [part.strip() for part in parts if part.strip()]


def split_paragraph_into_chunks(text: str, config: Config) -> list[str]:
    """Split a long paragraph at sentence boundaries, never mid-sentence."""

    hard_max = config.max_narration_words
    if word_count(text) <= hard_max:
        return [text.strip()]

    target_max = config.target_narration_words[1]
    sentences = split_sentences(text)
    chunks: list[str] = []
    current: list[str] = []
    for sentence in sentences:
        if word_count(sentence) > hard_max:
            if current:
                chunks.append(" ".join(current).strip())
                current = []
            chunks.append(sentence.strip())
            continue
        candidate = " ".join(current + [sentence])
        if current and word_count(candidate) > target_max:
            chunks.append(" ".join(current).strip())
            current = [sentence]
        else:
            current.append(sentence)
    if current:
        chunks.append(" ".join(current).strip())
    return chunks


def split_bullets(items: list[str], config: Config) -> list[list[str]]:
    """Group bullets so each block has at most `max_bullets` items."""

    max_bullets = config.max_bullets
    if len(items) <= max_bullets:
        return [items]
    return [items[i : i + max_bullets] for i in range(0, len(items), max_bullets)]


def split_source_block(block: SourceBlock, config: Config) -> list[SourceBlock]:
    """Return one or more teachable source chunks for a block."""

    if block.type == SourceBlockType.PARAGRAPH:
        return [
            block.model_copy(update={"text": chunk, "warnings": list(block.warnings)})
            for chunk in split_paragraph_into_chunks(block.text, config)
        ]
    if block.type in (SourceBlockType.BULLETS, SourceBlockType.NUMBERED):
        return [
            block.model_copy(update={"items": group, "warnings": list(block.warnings)})
            for group in split_bullets(block.items, config)
        ]
    return [block]


def screen_text_from_source(text: str, max_words: int) -> str:
    """Produce concise on-screen text: first sentence, capped at max words."""

    sentence = split_sentences(text)[0]
    words = WORD_BOUNDARY.findall(sentence)
    if len(words) <= max_words:
        return sentence
    return " ".join(words[:max_words]) + "…"
