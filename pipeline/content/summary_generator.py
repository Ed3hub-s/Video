"""Chapter summaries: 3-5 key takeaways."""

from __future__ import annotations

from pipeline.content.providers import AIProvider
from pipeline.content.schemas import Chapter
from pipeline.content.text_splitter import word_count


def summarize_chapter(chapter: Chapter, provider: AIProvider) -> list[str]:
    """Ask the provider for takeaways; fall back to rule-based highlights."""

    source = chapter_source_text(chapter)
    result = provider.summarize(source)
    if result and len(result) >= 3:
        return result[:5]
    return rule_based_takeaways(chapter)


def chapter_source_text(chapter: Chapter) -> str:
    lines: list[str] = [f"Chapter {chapter.chapter_number}: {chapter.title}"]
    for section in chapter.sections:
        lines.append(f"\n## {section.title}")
        for block in section.blocks:
            if block.text:
                lines.append(block.text)
            if block.items:
                lines.extend(f"- {item}" for item in block.items)
    return "\n".join(lines)


def rule_based_takeaways(chapter: Chapter) -> list[str]:
    """Deterministic fallback that keeps demo mode offline-capable."""

    headings = [s.title for s in chapter.sections if s.title]
    if len(headings) >= 3:
        return headings[:5]
    text = chapter_source_text(chapter)
    normalized = text.replace("\n", " ").replace("#", "")
    sentences = [
        s.strip().rstrip(".") + "."
        for s in normalized.split(".")
        if len(s.strip()) > 20
    ]
    if not sentences:
        return [f"{chapter.title} introduces the core ideas of this chapter."]
    picked: list[str] = []
    for sentence in sentences:
        words = sentence.split()
        if len(words) <= 20:
            picked.append(" ".join(words).rstrip(".") + ".")
        if len(picked) >= 3:
            break
    if len(picked) < 3:
        picked = sentences[:5]
    return picked[:5]
