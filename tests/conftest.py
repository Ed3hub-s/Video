from __future__ import annotations

from pathlib import Path

import pytest

from tests.fixtures.generate_course_docx import build_document


@pytest.fixture
def config():
    from pipeline.config import load_config

    return load_config()


@pytest.fixture(scope="session")
def fixture_docx(tmp_path_factory) -> Path:
    path = tmp_path_factory.mktemp("fixture") / "course.docx"
    build_document().save(str(path))
    return path


@pytest.fixture(scope="session")
def sample_course(fixture_docx):
    from pipeline.config import load_config
    from pipeline.docx_parser.reader import read_docx

    config = load_config()
    return read_docx(fixture_docx, config)
