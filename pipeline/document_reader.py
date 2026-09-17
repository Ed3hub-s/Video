"""Dispatch supported input documents into the normalized Course model."""

from __future__ import annotations

from pathlib import Path

from pipeline.config import Config
from pipeline.content.schemas import Course
from pipeline.docx_parser.reader import read_docx
from pipeline.pdf_parser.reader import read_pdf


SUPPORTED_DOCUMENT_SUFFIXES = frozenset({".docx", ".pdf"})


def read_document(input_path: Path, config: Config) -> Course:
    """Read a supported document without changing downstream structures."""

    suffix = input_path.suffix.lower()
    if suffix == ".docx":
        return read_docx(input_path, config)
    if suffix == ".pdf":
        return read_pdf(input_path, config)
    raise ValueError("Unsupported document format. Expected a .docx or .pdf file")
