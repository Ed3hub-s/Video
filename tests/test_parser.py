from __future__ import annotations

from pipeline.content.schemas import SourceBlock, SourceBlockType
from pipeline.docx_parser.chapter_parser import ChapterParser


def test_heading1_creates_three_chapters(sample_course):
    assert len(sample_course.chapters) == 3
    assert [c.title for c in sample_course.chapters] == [
        "Introduction to Machine Learning",
        "Supervised Learning",
        "Neural Networks",
    ]


def test_course_title(sample_course):
    assert sample_course.title == "Introduction to Artificial Intelligence"


def test_heading2_creates_sections(sample_course):
    first = sample_course.chapters[0]
    assert [s.title for s in first.sections] == [
        "What is Machine Learning?",
        "Why It Matters",
    ]


def test_paragraph_order_preserved(sample_course):
    chapter = sample_course.chapters[0]
    texts = [
        b.text
        for section in chapter.sections
        for b in section.blocks
        if b.type == SourceBlockType.PARAGRAPH
    ]
    assert texts[0].startswith("Machine learning is a method")
    assert texts[1].startswith("Instead of writing rules by hand")


def test_bullets_grouped_and_split(sample_course):
    chapter = sample_course.chapters[1]
    bullet_blocks = [
        b for section in chapter.sections for b in section.blocks
        if b.type == SourceBlockType.BULLETS
    ]
    assert bullet_blocks, "expected bullet blocks"
    total = sum(len(b.items) for b in bullet_blocks)
    assert total == 7  # the fixture has seven bullet items in one group


def test_numbered_list_extracted(sample_course):
    chapter = sample_course.chapters[1]
    numbered = [
        b for section in chapter.sections for b in section.blocks
        if b.type == SourceBlockType.NUMBERED
    ]
    assert numbered
    assert len(numbered[0].items) == 4


def test_image_extracted(sample_course):
    chapter = sample_course.chapters[2]
    images = [
        b for section in chapter.sections for b in section.blocks
        if b.type == SourceBlockType.IMAGE
    ]
    assert images, "expected an extracted image"
    from pathlib import Path

    assert Path(images[0].path).exists()


def test_table_warning_generated(sample_course):
    assert any("Table" in w for w in sample_course.warnings)


def test_short_leading_course_title_is_folded_into_first_real_chapter():
    parser = ChapterParser(course_title="Web3_chapter_1")
    parser.add_heading1("Web3_chapter_1")
    parser.add_block(
        SourceBlock(
            type=SourceBlockType.PARAGRAPH,
            text="Welcome to Web3. We will introduce the topic before the lesson begins.",
        )
    )
    parser.add_heading1("The Evolution of the Web")
    parser.add_block(
        SourceBlock(
            type=SourceBlockType.PARAGRAPH,
            text=" ".join(["substantive"] * 100),
        )
    )

    course = parser.finish()

    assert len(course.chapters) == 1
    assert course.chapters[0].chapter_number == 1
    assert course.chapters[0].title == "The Evolution of the Web"
    assert course.chapters[0].sections[0].blocks[0].text.startswith("Welcome")
    assert any("folded into Chapter 1" in warning for warning in course.warnings)
