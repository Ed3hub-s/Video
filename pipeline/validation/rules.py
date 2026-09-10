"""Individual validation rules (fatal errors and warnings)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from pipeline.content.schemas import (
    ChapterPlan,
    Scene,
    SceneType,
    VisualActionType,
)
from pipeline.content.text_splitter import word_count


def _screen_line_count(scene: Scene) -> int:
    return len([line for line in scene.screenText.split("\n") if line.strip()])


def check_scene_rules(
    scene: Scene,
    index: int,
    config,
    all_ids: set[str],
) -> list[tuple[str, str]]:
    """Return (severity, message) pairs for one scene."""

    issues: list[tuple[str, str]] = []
    label = f"scene {scene.id}"

    if scene.id in all_ids:
        issues.append(("error", f"Duplicate scene id '{scene.id}'"))
    all_ids.add(scene.id)

    if scene.type not in SceneType:
        issues.append(("error", f"{label}: unknown scene type '{scene.type}'"))
    if scene.type.value not in {t.value for t in SceneType}:
        issues.append(("error", f"{label}: unknown scene type '{scene.type}'"))

    requires_narration = scene.type not in (SceneType.CHAPTER_INTRO, SceneType.SECTION_INTRO)
    if requires_narration and not scene.voiceover.strip():
        issues.append(("error", f"{label}: missing required narration"))

    if not scene.title.strip():
        issues.append(("error", f"{label}: missing title"))
    if len(scene.title) > 80:
        issues.append(("warning", f"{label}: title > 80 characters ({len(scene.title)})"))

    screen_words = word_count(scene.screenText)
    if screen_words > config.max_screen_words:
        issues.append(
            ("warning", f"{label}: screen text > {config.max_screen_words} words ({screen_words})")
        )
    narration_words = word_count(scene.voiceover)
    if narration_words > config.max_narration_words:
        issues.append(
            ("warning", f"{label}: narration > {config.max_narration_words} words ({narration_words})")
        )
    if _screen_line_count(scene) > config.max_bullets:
        issues.append(
            ("warning", f"{label}: more than {config.max_bullets} bullets ({_screen_line_count(scene)})")
        )
    if scene.durationSeconds is not None and scene.durationSeconds > config.max_scene_seconds:
        issues.append(
            ("warning", f"{label}: scene > {config.max_scene_seconds}s ({scene.durationSeconds:.1f}s)")
        )

    high_count = sum(1 for c in scene.keyConcepts if c.importance.value == "high")
    if high_count > max(3, len(scene.keyConcepts) // 2):
        issues.append(("warning", f"{label}: too many high-importance concepts ({high_count})"))

    if scene.image:
        image_path = Path(scene.image)
        if not image_path.exists():
            issues.append(("error", f"{label}: broken image path '{scene.image}'"))
        else:
            try:
                with Image.open(image_path) as img:
                    if min(img.size) < 800:
                        issues.append(
                            ("warning", f"{label}: low-resolution image {img.size}")
                        )
            except OSError:
                issues.append(("error", f"{label}: image file unreadable '{scene.image}'"))

    if scene.diagram:
        node_ids = {node.id for node in scene.diagram.nodes}
        if not node_ids:
            issues.append(("error", f"{label}: diagram has no nodes"))
        for edge in scene.diagram.edges:
            if edge.from_id not in node_ids:
                issues.append(("error", f"{label}: diagram edge references unknown 'from' node '{edge.from_id}'"))
            if edge.to not in node_ids:
                issues.append(("error", f"{label}: diagram edge references unknown 'to' node '{edge.to}'"))

    for action in scene.visualActions:
        if action.type not in VisualActionType:
            issues.append(("error", f"{label}: unknown visual action '{action.type}'"))
        if action.type == VisualActionType.DRAW_ARROW:
            for ref, side in ((action.from_id, "from"), (action.to, "to")):
                if ref and ref not in {c.id for c in scene.keyConcepts} | (
                    {n.id for n in scene.diagram.nodes} if scene.diagram else set()
                ):
                    issues.append(
                        ("error", f"{label}: drawArrow references unknown {side} id '{ref}'")
                    )
        if action.startSec < 0:
            issues.append(("error", f"{label}: negative timing in '{action.type}'"))
        if scene.durationSeconds is not None and action.startSec >= scene.durationSeconds:
            issues.append(
                ("error", f"{label}: action '{action.type}' starts after scene end")
            )

    return issues


def check_plan_rules(plan: ChapterPlan, config) -> list[tuple[str, str]]:
    """Plan-level checks (fatal errors and warnings)."""

    issues: list[tuple[str, str]] = []
    all_ids: set[str] = set()
    for index, scene in enumerate(plan.scenes):
        issues.extend(check_scene_rules(scene, index, config, all_ids))
    if not plan.scenes:
        issues.append(("error", "Chapter plan has no scenes"))
    return issues
