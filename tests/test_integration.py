from __future__ import annotations

import json

import pytest

from pipeline.audio.tts import build_tts_provider
from pipeline.cache.cache import FileCache, hash_text
from pipeline.config import load_config
from pipeline.content.providers import build_provider
from pipeline.content.scene_generator import generate_chapter_plan
from pipeline.main import apply_timing_and_subtitles
from pipeline.render.remotion import write_render_manifest
from pipeline.validation.validator import validate_chapter
from pipeline.visual.importance import rebalance_importance
from pipeline.visual.visual_planner import plan_visual_actions


pytestmark = pytest.mark.integration


def _assert_no_internal_from_id(value):
    """Ensure Python-only field names never leak into Remotion JSON."""

    if isinstance(value, dict):
        assert "from_id" not in value

        for child in value.values():
            _assert_no_internal_from_id(child)

    elif isinstance(value, list):
        for child in value:
            _assert_no_internal_from_id(child)


def test_docx_to_scenes_to_audio_to_manifest(
    sample_course,
    tmp_path,
):
    config = load_config()
    provider = build_provider("mock")
    tts = build_tts_provider("mock")
    cache = FileCache(tmp_path / "cache")

    total_scenes = 0

    for chapter in sample_course.chapters:
        plan = generate_chapter_plan(
            chapter,
            provider,
            config,
        )

        plan.scenes = [
            plan_visual_actions(
                rebalance_importance(scene)
            )
            for scene in plan.scenes
        ]

        for scene in plan.scenes:
            if scene.voiceover.strip():
                key = (
                    f"audio:"
                    f"{tts.cache_tag}:"
                    f"{hash_text(scene.voiceover)}"
                )

                cached = cache.get(key)

                if cached is None:
                    out = (
                        config.paths.audio
                        / (
                            f"chapter-"
                            f"{chapter.chapter_number:02d}"
                        )
                        / f"{scene.id}.mp3"
                    )

                    scene.audio = tts.generate(
                        scene.voiceover,
                        out,
                    )

                    cache.put(
                        key,
                        scene.audio.model_dump(
                            mode="json"
                        ),
                    )

                else:
                    from pipeline.content.schemas import (
                        AudioMetadata,
                    )

                    scene.audio = (
                        AudioMetadata.model_validate(
                            cached
                        )
                    )

        apply_timing_and_subtitles(
            plan,
            config,
        )

        result = validate_chapter(
            plan,
            config,
        )

        assert result.ok, result.errors

        assert (
            plan.totalDurationSeconds
            > 0
        )

        assert all(
            scene.audio is not None
            for scene in plan.scenes
            if scene.voiceover.strip()
        )

        assert all(
            scene.subtitles
            for scene in plan.scenes
            if scene.voiceover.strip()
        )

        manifest_path = write_render_manifest(
            plan,
            config,
        )

        assert manifest_path.exists()

        with manifest_path.open(
            "r",
            encoding="utf-8",
        ) as handle:
            render_data = json.load(handle)

        assert "manifest" in render_data
        assert "scenes" in render_data["manifest"]

        rendered_scenes = (
            render_data["manifest"]["scenes"]
        )

        assert len(rendered_scenes) == len(
            plan.scenes
        )

        # Python internally calls aliased fields
        # such as `from_id`, while Remotion expects
        # the JSON key `from`.
        #
        # No Python-only `from_id` field should ever
        # cross the Python -> Remotion boundary.
        _assert_no_internal_from_id(
            rendered_scenes
        )

        total_scenes += len(
            plan.scenes
        )

    assert total_scenes >= 3