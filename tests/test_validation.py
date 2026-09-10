from __future__ import annotations

import pytest
from pydantic import ValidationError

from pipeline.config import load_config
from pipeline.content.schemas import (
    ChapterPlan,
    Scene,
    SceneType,
    VisualAction,
    VisualActionType,
)
from pipeline.validation.validator import validate_chapter


def _plan(scenes: list[Scene]) -> ChapterPlan:
    return ChapterPlan(
        courseTitle="Course",
        chapterNumber=1,
        chapterTitle="Chapter",
        fps=30,
        width=1920,
        height=1080,
        scenes=scenes,
    )


def _scene(**overrides) -> Scene:
    data = dict(
        id="scene-001",
        type=SceneType.EXPLANATION,
        title="A fine title",
        screenText="Concise screen text.",
        voiceover="Narration for this scene is present and complete.",
        durationSeconds=10.0,
    )
    data.update(overrides)
    return Scene.model_validate(data)


def test_valid_plan_passes():
    scene = _scene()
    scene.audio = None
    result = validate_chapter(_plan([scene]), load_config())
    assert result.ok, result.errors


def test_missing_narration_is_fatal():
    scene = _scene(voiceover="")
    result = validate_chapter(_plan([scene]), load_config())
    assert not result.ok
    assert any("narration" in e.message for e in result.errors)


def test_broken_image_path_is_fatal():
    scene = _scene(image="C:/definitely/missing/image.png")
    result = validate_chapter(_plan([scene]), load_config())
    assert not result.ok
    assert any("image" in e.message for e in result.errors)


def test_unknown_action_is_fatal():
    with pytest.raises(ValidationError):
        _scene(
            visualActions=[
                VisualAction(type="explode", target="x", startSec=0.5, durationSec=0.5)
            ]
        )


def test_action_after_scene_end_is_fatal():
    scene = _scene(
        durationSeconds=5.0,
        keyConcepts=[{"id": "term", "text": "TERM", "importance": "high"}],
        visualActions=[
            VisualAction(type=VisualActionType.UNDERLINE, target="term", startSec=6.0, durationSec=0.5)
        ],
    )
    result = validate_chapter(_plan([scene]), load_config())
    assert not result.ok
    assert any("after scene end" in e.message for e in result.errors)


def test_invalid_target_reference_is_fatal():
    scene = _scene(
        visualActions=[
            VisualAction(type=VisualActionType.UNDERLINE, target="ghost", startSec=1.0, durationSec=0.5)
        ]
    )
    result = validate_chapter(_plan([scene]), load_config())
    assert not result.ok
    assert any("unknown id" in e.message for e in result.errors)


def test_long_title_warns():
    scene = _scene(title="T" * 81)
    result = validate_chapter(_plan([scene]), load_config())
    assert result.ok
    assert any("80" in w.message for w in result.warnings)


def test_scene_too_long_warns():
    scene = _scene(durationSeconds=60.0)
    result = validate_chapter(_plan([scene]), load_config())
    assert result.ok
    assert any("scene >" in w.message and "45" in w.message for w in result.warnings)
