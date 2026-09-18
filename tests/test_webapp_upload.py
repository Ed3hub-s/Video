from __future__ import annotations

import asyncio
import io
from pathlib import Path

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


def test_job_passes_selected_style_to_pipeline(monkeypatch):
    captured = {}

    monkeypatch.setattr(webapp, "_active_job", lambda: None)
    monkeypatch.setattr(
        webapp,
        "_resolve_input_document",
        lambda value: Path(value),
    )
    monkeypatch.setattr(
        webapp,
        "_pipeline_env",
        lambda: {},
    )

    def capture_job(job_id, command, environment):
        captured["job_id"] = job_id
        captured["command"] = command
        captured["environment"] = environment

    monkeypatch.setattr(webapp, "_run_job", capture_job)

    with webapp.JOBS_LOCK:
        webapp.JOBS.clear()

    result = webapp.api_start_job(
        webapp.JobRequest(
            document="input/uploads/course.docx",
            provider="mock",
            voice="mock",
            style="dark",
        )
    )

    style_index = captured["command"].index("--style")
    assert captured["command"][style_index + 1] == "dark"
    assert result["style"] == "dark"
