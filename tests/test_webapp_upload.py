from __future__ import annotations

import asyncio
import io

from fastapi import UploadFile

from webapp import app as webapp


def test_upload_preserves_sanitized_original_filename(monkeypatch, tmp_path):
    upload_dir = tmp_path / "input" / "uploads"
    upload_dir.mkdir(parents=True)
    monkeypatch.setattr(webapp, "ROOT", tmp_path)
    monkeypatch.setattr(webapp, "UPLOAD_DIR", upload_dir)
    upload = UploadFile(
        filename="My Course (Final).pdf",
        file=io.BytesIO(b"%PDF-test"),
    )

    result = asyncio.run(webapp.api_upload(upload))

    assert result["name"] == "My_Course_Final_.pdf"
    assert (upload_dir / "My_Course_Final_.pdf").read_bytes() == b"%PDF-test"


def test_reupload_replaces_same_original_filename(monkeypatch, tmp_path):
    upload_dir = tmp_path / "input" / "uploads"
    upload_dir.mkdir(parents=True)
    monkeypatch.setattr(webapp, "ROOT", tmp_path)
    monkeypatch.setattr(webapp, "UPLOAD_DIR", upload_dir)

    first = UploadFile(filename="course.docx", file=io.BytesIO(b"first"))
    second = UploadFile(filename="course.docx", file=io.BytesIO(b"second"))

    asyncio.run(webapp.api_upload(first))
    result = asyncio.run(webapp.api_upload(second))

    assert result["name"] == "course.docx"
    assert (upload_dir / "course.docx").read_bytes() == b"second"
