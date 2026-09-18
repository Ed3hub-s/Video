from __future__ import annotations

import json
from dataclasses import replace

from pipeline.config import load_config
from pipeline.content.schemas import ChapterPlan, Scene, SceneType
from pipeline.render.remotion import _remotion_cli
from pipeline.render.remotion import write_render_manifest


def test_remotion_cli_prefers_local_install(tmp_path):
    executable = tmp_path / "node_modules" / ".bin" / "remotion.cmd"
    executable.parent.mkdir(parents=True)
    executable.write_text("", encoding="utf-8")

    assert _remotion_cli(tmp_path) == [str(executable)]


def test_selected_style_is_written_to_render_manifest(tmp_path):
    base = load_config()
    paths = replace(
        base.paths,
        manifests=tmp_path / "manifests",
        remotion=tmp_path / "remotion",
    )
    config = replace(
        base,
        style="dark",
        paths=paths,
    )
    plan = ChapterPlan(
        courseTitle="Course",
        chapterNumber=1,
        chapterTitle="Chapter",
        fps=30,
        width=1920,
        height=1080,
        scenes=[
            Scene(
                id="scene-001",
                type=SceneType.CHAPTER_INTRO,
                title="Chapter",
                screenText="Chapter",
                voiceover="Welcome.",
            )
        ],
    )

    path = write_render_manifest(plan, config)
    data = json.loads(path.read_text(encoding="utf-8"))

    assert data["manifest"]["style"] == "dark"
