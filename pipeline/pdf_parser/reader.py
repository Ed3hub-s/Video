"""Order-preserving PDF text reader."""

from __future__ import annotations

import re
from pathlib import Path

from pypdf import PdfReader

from pipeline.config import Config
from pipeline.content.schemas import Course, SourceBlock, SourceBlockType
from pipeline.docx_parser.chapter_parser import ChapterParser


def _paragraphs(text: str) -> list[str]:
    """Turn extracted page text into stable paragraph blocks."""

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    groups = re.split(r"\n\s*\n", normalized)
    paragraphs: list[str] = []

    for group in groups:
        lines = [line.strip() for line in group.splitlines() if line.strip()]
        if lines:
            paragraphs.append(" ".join(lines))

    return paragraphs


def _page_has_images(page) -> bool:
    try:
        resources = page.get("/Resources") or {}
        xobjects = resources.get("/XObject") or {}
        for value in xobjects.values():
            obj = value.get_object()
            if obj.get("/Subtype") == "/Image":
                return True
    except (AttributeError, KeyError, TypeError):
        return False

    return False


def read_pdf(input_path: Path, config: Config) -> Course:
    """Parse a PDF into the same Course/SourceBlock model as DOCX.

    PDF files generally do not contain dependable heading semantics, so the
    document becomes one chapter and each page becomes an ordered section.
    This keeps extraction deterministic without guessing at visual headings.
    """

    del config  # Reserved for future image extraction alongside DOCX assets.

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    reader = PdfReader(str(input_path))
    if reader.is_encrypted:
        try:
            unlocked = reader.decrypt("")
        except Exception as exc:  # pypdf exposes backend-specific errors.
            raise ValueError("Encrypted PDF could not be opened") from exc
        if not unlocked:
            raise ValueError("Password-protected PDFs are not supported")

    metadata_title = getattr(reader.metadata, "title", None)
    title = metadata_title.strip() if metadata_title and metadata_title.strip() else input_path.stem
    warnings: list[str] = []
    parser = ChapterParser(course_title=title, warnings=warnings)
    parser.add_heading1(title)

    page_count = len(reader.pages)
    for page_number, page in enumerate(reader.pages, start=1):
        parser.add_heading2(f"Page {page_number}" if page_count > 1 else title)

        try:
            text = page.extract_text() or ""
        except Exception as exc:
            warnings.append(f"Page {page_number} text extraction failed: {exc}")
            text = ""

        page_paragraphs = _paragraphs(text)
        if not page_paragraphs:
            warnings.append(f"Page {page_number} contains no extractable text")

        for paragraph in page_paragraphs:
            parser.add_block(
                SourceBlock(type=SourceBlockType.PARAGRAPH, text=paragraph)
            )

        if _page_has_images(page):
            warnings.append(
                f"Page {page_number} contains images - PDF image extraction is not supported and images were skipped"
            )

    return parser.finish()
