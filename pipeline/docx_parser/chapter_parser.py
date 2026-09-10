"""Assemble chapters and sections from ordered paragraph blocks."""

from __future__ import annotations

from pipeline.content.schemas import Chapter, Course, Section, SourceBlock, SourceBlockType

from .block_parser import ListKind, is_list_paragraph
from .image_extractor import slugify


class ChapterParser:
    """Builds a Course while preserving exact document order."""

    def __init__(self, course_title: str, warnings: list[str] | None = None) -> None:
        self.course_title = course_title
        self.chapters: list[Chapter] = []
        self.warnings = warnings or []
        self._current_chapter: Chapter | None = None
        self._current_section: Section | None = None
        self._pending_list_kind = ListKind.NONE
        self._pending_items: list[str] = []

    def _flush_pending_list(self) -> None:
        if not self._pending_items:
            return
        if self._current_section is None:
            self._ensure_section()
        block_type = (
            SourceBlockType.NUMBERED
            if self._pending_list_kind == ListKind.NUMBERED
            else SourceBlockType.BULLETS
        )
        self._current_section.blocks.append(
            SourceBlock(type=block_type, items=list(self._pending_items))
        )
        self._pending_items = []
        self._pending_list_kind = ListKind.NONE

    def _ensure_chapter(self, title: str) -> Chapter:
        if self._current_chapter is not None:
            self._flush_pending_list()
        chapter = Chapter(
            course_title=self.course_title,
            chapter_number=len(self.chapters) + 1,
            title=title,
            slug=f"{len(self.chapters) + 1:02d}-{slugify(title)}",
        )
        self.chapters.append(chapter)
        self._current_chapter = chapter
        self._current_section = None
        return chapter

    def _ensure_section(self, title: str = "") -> Section:
        if self._current_chapter is None:
            self._ensure_chapter(self.course_title)
        section = Section(title=title or self._current_chapter.title)
        self._current_chapter.sections.append(section)
        self._current_section = section
        return section

    def add_heading1(self, title: str) -> None:
        self._flush_pending_list()
        self._ensure_chapter(title)

    def add_heading2(self, title: str) -> None:
        self._flush_pending_list()
        self._ensure_section(title)

    def add_heading_other(self, title: str, level: int) -> None:
        self._flush_pending_list()
        self.warnings.append(
            f"Heading {level} ('{title}') is not supported in V1; treated as a paragraph"
        )
        self.add_block(SourceBlock(type=SourceBlockType.PARAGRAPH, text=title))

    def add_block(self, block: SourceBlock) -> None:
        if self._current_section is None:
            self._ensure_section()
        if block.type in (SourceBlockType.BULLETS, SourceBlockType.NUMBERED):
            kind = (
                ListKind.NUMBERED
                if block.type == SourceBlockType.NUMBERED
                else ListKind.BULLET
            )
            if self._pending_list_kind == kind:
                self._pending_items.extend(block.items)
            else:
                self._flush_pending_list()
                self._pending_list_kind = kind
                self._pending_items.extend(block.items)
            return
        self._flush_pending_list()
        self._current_section.blocks.append(block)

    def add_list_item(self, text: str, kind: str) -> None:
        if self._pending_list_kind == kind:
            self._pending_items.append(text)
        else:
            self._flush_pending_list()
            self._pending_list_kind = kind
            self._pending_items.append(text)

    def finish(self) -> Course:
        self._flush_pending_list()
        if self._current_chapter is None:
            self._ensure_chapter(self.course_title)
        return Course(title=self.course_title, chapters=self.chapters, warnings=self.warnings)
