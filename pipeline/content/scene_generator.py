"""Turn parsed chapters into schema-valid scene plans."""

from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from pipeline.config import Config
from pipeline.content.providers import AIProvider, MockProvider, chapter_source_text_from_dict
from pipeline.content.schemas import (
    Chapter,
    ChapterPlan,
    Course,
    Importance,
    KeyConcept,
    Scene,
    SceneType,
)
from pipeline.content.summary_generator import summarize_chapter
from pipeline.content.text_splitter import split_source_block


SCENE_SCHEMA_JSON = json.dumps(
    {
        "id": "scene-001",
        "type": "explanation",
        "title": "Short title",
        "screenText": "Concise on-screen text (10-30 words)",
        "voiceover": "Narration (40-100 words, max 120)",
        "keyConcepts": [
            {"id": "term-1", "text": "TERM", "importance": "high"}
        ],
        "visualStrategy": "none",
        "visualActions": [
            {"type": "underline", "target": "term-1", "startSec": 1.5, "durationSec": 0.8}
        ],
        "image": None,
        "diagram": None,
    },
    indent=2,
)


class ChapterSceneError(RuntimeError):
    """Raised when a chapter's scene plan cannot be produced or validated."""


def _flatten_source_blocks(chapter: Chapter, config: Config) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for section in chapter.sections:
        for block in section.blocks:
            for chunk in split_source_block(block, config):
                blocks.append(chunk.model_dump(mode="json"))
    return blocks


def _source_payload(chapter: Chapter, config: Config) -> dict[str, Any]:
    return {
        "courseTitle": chapter.course_title,
        "chapterNumber": chapter.chapter_number,
        "title": chapter.title,
        "sections": [
            {
                "title": section.title,
                "blocks": [
                    _b.model_dump(mode="json")
                    for block in section.blocks
                    for _b in split_source_block(block, config)
                ]
            }
            for section in chapter.sections
        ],
    }


def _normalize_scene(raw: dict[str, Any], index: int) -> Scene:
    raw.setdefault("id", f"scene-{index:03d}")
    raw.setdefault("type", "explanation")
    raw.setdefault("title", raw.get("screenText", "")[:80] or "Scene")
    raw.setdefault("screenText", "")
    raw.setdefault("voiceover", "")
    raw.setdefault("keyConcepts", [])
    raw.setdefault("visualStrategy", "none")
    raw.setdefault("visualActions", [])
    raw.setdefault("image", None)
    raw.setdefault("diagram", None)
    raw.setdefault("sourceText", raw.get("sourceText", ""))
    return Scene.model_validate(raw)


def _ensure_chapter_intro(chapter: Chapter, scenes: list[Scene], config: Config) -> list[Scene]:
    if scenes and scenes[0].type == SceneType.CHAPTER_INTRO:
        return scenes
    intro = Scene(
        id="scene-000",
        type=SceneType.CHAPTER_INTRO,
        title=chapter.title,
        screenText=chapter.title,
        voiceover=f"Chapter {chapter.chapter_number}. {chapter.title}.",
    )
    return [intro] + scenes


def _ensure_chapter_summary(chapter: Chapter, scenes: list[Scene], provider: AIProvider) -> list[Scene]:
    if scenes and scenes[-1].type == SceneType.CHAPTER_SUMMARY:
        return scenes
    takeaways = summarize_chapter(chapter, provider)
    screen_parts = []
    for takeaway in takeaways[:3]:
        words = takeaway.split()
        screen_parts.append(" ".join(words[:10]))
    summary = Scene(
        id="scene-999",
        type=SceneType.CHAPTER_SUMMARY,
        title="Key Takeaways",
        screenText=" · ".join(screen_parts),
        voiceover="To summarize, " + " ".join(takeaways[:4]),
        keyConcepts=[
            KeyConcept(id=f"takeaway-{i}", text=t[:40].upper(), importance=Importance.MEDIUM)
            for i, t in enumerate(takeaways[:3])
        ],
    )
    return scenes + [summary]


def _renumber(scenes: list[Scene]) -> list[Scene]:
    return [
        scene.model_copy(update={"id": f"scene-{i + 1:03d}"})
        for i, scene in enumerate(scenes)
    ]


def _validate_scene_with_retry(
    raw: dict[str, Any],
    index: int,
    provider: AIProvider,
    attempts_left: int = 1,
) -> Scene:
    try:
        return _normalize_scene(raw, index)
    except ValidationError as first_error:
        if attempts_left <= 0:
            raise ChapterSceneError(
                f"Scene {index + 1} failed schema validation: {first_error}"
            ) from first_error
        try:
            repaired = provider.repair(json.dumps(raw), SCENE_SCHEMA_JSON)
            repaired_data = json.loads(repaired)
            if isinstance(repaired_data, list):
                repaired_data = repaired_data[index] if index < len(repaired_data) else repaired_data[0]
            return _validate_scene_with_retry(repaired_data, index, provider, attempts_left - 1)
        except (json.JSONDecodeError, ValidationError, IndexError) as repair_error:
            raise ChapterSceneError(
                f"Scene {index + 1} invalid after repair: {repair_error}"
            ) from repair_error


def generate_chapter_plan(
    chapter: Chapter,
    provider: AIProvider,
    config: Config,
) -> ChapterPlan:
    """Build the full scene plan for one chapter."""

    payload = _source_payload(chapter, config)
    raw_scenes = provider.build_scenes(payload)
    if not raw_scenes:
        raise ChapterSceneError(f"Chapter {chapter.chapter_number} produced no scenes")

    scenes = [
        _validate_scene_with_retry(raw, i, provider)
        for i, raw in enumerate(raw_scenes)
    ]
    scenes = _ensure_chapter_intro(chapter, scenes, config)
    scenes = _ensure_chapter_summary(chapter, scenes, provider)
    scenes = _renumber(scenes)
    return ChapterPlan(
        courseTitle=chapter.course_title,
        chapterNumber=chapter.chapter_number,
        chapterTitle=chapter.title,
        fps=config.fps,
        width=config.width,
        height=config.height,
        scenes=scenes,
    )


def build_all_plans(course: Course, provider: AIProvider, config: Config) -> dict[int, ChapterPlan]:
    plans: dict[int, ChapterPlan] = {}
    for chapter in course.chapters:
        plans[chapter.chapter_number] = generate_chapter_plan(chapter, provider, config)
    return plans
