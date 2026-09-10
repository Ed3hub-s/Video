from __future__ import annotations

import pytest
from pydantic import ValidationError

from pipeline.content.schemas import (
    Diagram,
    DiagramEdge,
    DiagramNode,
    Importance,
    KeyConcept,
    Scene,
    SceneType,
    SubtitleCue,
    VisualAction,
    VisualActionType,
)


def _valid_scene() -> Scene:
    return Scene(
        id="scene-001",
        type=SceneType.EXPLANATION,
        title="Title",
        screenText="Short screen text.",
        voiceover="Narration for the scene goes here.",
    )


def test_valid_scene_roundtrip():
    scene = _valid_scene()
    assert Scene.model_validate(scene.model_dump(mode="json")) == scene


def test_unknown_scene_type_rejected():
    with pytest.raises(ValidationError):
        Scene.model_validate({"id": "scene-001", "type": "slideshow", "title": "x"})


def test_negative_timing_rejected():
    with pytest.raises(ValidationError):
        VisualAction(type=VisualActionType.UNDERLINE, target="x", startSec=-1, durationSec=0.5)


def test_bad_scene_id_rejected():
    with pytest.raises(ValidationError):
        Scene.model_validate({"id": "bad id", "type": "explanation", "title": "x"})


def test_invalid_diagram_edge_rejected():
    with pytest.raises(ValidationError):
        Diagram(
            kind="process",
            nodes=[DiagramNode(id="a", label="A")],
            edges=[DiagramEdge(from_id="missing", to="a")],
        )


def test_subtitle_end_must_exceed_start():
    with pytest.raises(ValidationError):
        SubtitleCue(start=5.0, end=4.0, text="bad")


def test_concept_importance_enum():
    concept = KeyConcept(id="term", text="TERM", importance=Importance.HIGH)
    assert concept.importance.value == "high"
