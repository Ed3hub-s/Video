from __future__ import annotations

from types import SimpleNamespace

import pytest

from pipeline.content.schemas import SourceBlockType
from pipeline.pdf_parser import reader as pdf_reader


class FakePage:
    def __init__(self, text: str, *, has_image: bool = False) -> None:
        self.text = text
        self.has_image = has_image

    def extract_text(self) -> str:
        return self.text

    def get(self, key: str):
        if key != "/Resources" or not self.has_image:
            return None
        image = SimpleNamespace(
            get_object=lambda: {"/Subtype": "/Image"}
        )
        return {"/XObject": {"/Im1": image}}


def _install_fake_reader(monkeypatch, pages, title="PDF Course"):
    class FakeReader:
        is_encrypted = False
        metadata = SimpleNamespace(title=title)

        def __init__(self, _path: str) -> None:
            self.pages = pages

    monkeypatch.setattr(pdf_reader, "PdfReader", FakeReader)


def test_pdf_pages_become_ordered_sections(monkeypatch, tmp_path, config):
    path = tmp_path / "course.pdf"
    path.write_bytes(b"%PDF-fake")
    _install_fake_reader(
        monkeypatch,
        [
            FakePage("First paragraph.\n\nSecond paragraph."),
            FakePage("Third paragraph."),
        ],
    )

    course = pdf_reader.read_pdf(path, config)

    assert course.title == "PDF Course"
    assert len(course.chapters) == 1
    assert [section.title for section in course.chapters[0].sections] == [
        "Page 1",
        "Page 2",
    ]
    blocks = [
        block
        for section in course.chapters[0].sections
        for block in section.blocks
    ]
    assert [block.type for block in blocks] == [
        SourceBlockType.PARAGRAPH,
        SourceBlockType.PARAGRAPH,
        SourceBlockType.PARAGRAPH,
    ]
    assert [block.text for block in blocks] == [
        "First paragraph.",
        "Second paragraph.",
        "Third paragraph.",
    ]


def test_pdf_warns_for_empty_pages_and_images(monkeypatch, tmp_path, config):
    path = tmp_path / "slides.pdf"
    path.write_bytes(b"%PDF-fake")
    _install_fake_reader(
        monkeypatch,
        [FakePage("", has_image=True)],
        title=None,
    )

    course = pdf_reader.read_pdf(path, config)

    assert course.title == "slides"
    assert any("no extractable text" in warning for warning in course.warnings)
    assert any("contains images" in warning for warning in course.warnings)


def test_pdf_missing_file_raises(config, tmp_path):
    with pytest.raises(FileNotFoundError):
        pdf_reader.read_pdf(tmp_path / "missing.pdf", config)
