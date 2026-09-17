"""Turn a single DOCX paragraph into neutral source blocks."""

from __future__ import annotations

from pathlib import Path

from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph

from pipeline.content.schemas import (
    SourceBlock,
    SourceBlockType,
)

from .image_extractor import (
    extract_images_from_paragraph,
)


class ListKind:
    NONE = ""
    BULLET = "bullet"
    NUMBERED = "numbered"


def is_list_paragraph(
    paragraph: Paragraph,
) -> str:
    """Return the list type when the paragraph is a list item."""

    style_name = (
        (paragraph.style.name or "").lower()
        if paragraph.style
        else ""
    )

    if (
        "list number" in style_name
        or "numbered" in style_name
    ):
        return ListKind.NUMBERED

    if (
        "list bullet" in style_name
        or "bullet" in style_name
    ):
        return ListKind.BULLET

    num_pr = (
        paragraph._p.pPr.find(
            qn("w:numPr")
        )
        if paragraph._p.pPr is not None
        else None
    )

    if num_pr is not None:
        # Without a style hint we cannot reliably
        # determine the numbering format in V1.
        return ListKind.BULLET

    return ListKind.NONE


def has_equation(
    paragraph: Paragraph,
) -> bool:
    """Return True when the paragraph contains an Office Math equation."""

    equations = paragraph._p.findall(
        ".//{"
        "http://schemas.openxmlformats.org/"
        "officeDocument/2006/math"
        "}oMath"
    )

    return bool(equations)


def paragraph_text(
    paragraph: Paragraph,
) -> str:
    """Return full visible text, including hyperlink runs."""

    pieces: list[str] = []

    for child in paragraph._p.iter():
        tag = child.tag.split("}")[-1]

        if tag == "t":
            pieces.append(
                child.text or ""
            )

    return "".join(
        pieces
    ).strip()


def parse_paragraph(
    paragraph: Paragraph,
    chapter_dir: Path,
    image_counter: list[int],
    list_kind: str = ListKind.NONE,
) -> list[SourceBlock]:
    """Parse one paragraph into source blocks while preserving warnings."""

    text = paragraph_text(
        paragraph
    )

    image_paths = (
        extract_images_from_paragraph(
            paragraph,
            chapter_dir,
            image_counter,
        )
    )

    warnings: list[str] = []

    if has_equation(paragraph):
        warnings.append(
            "Equation found - equations are not "
            "supported in V1 and were skipped"
        )

    blocks: list[SourceBlock] = []

    if text:
        if list_kind == ListKind.NUMBERED:
            blocks.append(
                SourceBlock(
                    type=SourceBlockType.NUMBERED,
                    items=[text],
                    warnings=list(warnings),
                )
            )

        elif list_kind == ListKind.BULLET:
            blocks.append(
                SourceBlock(
                    type=SourceBlockType.BULLETS,
                    items=[text],
                    warnings=list(warnings),
                )
            )

        else:
            blocks.append(
                SourceBlock(
                    type=SourceBlockType.PARAGRAPH,
                    text=text,
                    warnings=list(warnings),
                )
            )

    elif (
        not image_paths
        and warnings
    ):
        # Preserve warnings for unsupported content
        # even when the paragraph has no usable text
        # or images.
        blocks.append(
            SourceBlock(
                type=SourceBlockType.PARAGRAPH,
                text="",
                warnings=list(warnings),
            )
        )

    elif (
        not image_paths
        and not warnings
    ):
        return blocks

    for index, image_path in enumerate(
        image_paths
    ):
        image_warnings = (
            list(warnings)
            if not text and index == 0
            else []
        )

        blocks.append(
            SourceBlock(
                type=SourceBlockType.IMAGE,
                text="",
                path=image_path,
                warnings=image_warnings,
            )
        )

    return blocks