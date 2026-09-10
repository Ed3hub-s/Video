"""Validate visual actions against the approved library and scene references."""

from __future__ import annotations

from pipeline.content.schemas import (
    Scene,
    SceneType,
    VisualAction,
    VisualActionType,
)


TEACHING_ACTIONS = {
    VisualActionType.HANDWRITE,
    VisualActionType.UNDERLINE,
    VisualActionType.CIRCLE,
    VisualActionType.DRAW_ARROW,
    VisualActionType.DRAW_BOX,
    VisualActionType.HIGHLIGHT,
    VisualActionType.CROSS_OUT,
    VisualActionType.CONNECT,
    VisualActionType.ZOOM_FOCUS,
    VisualActionType.BUILD_DIAGRAM,
    VisualActionType.COMPARE,
}

HIGH_EMPHASIS = {
    VisualActionType.HANDWRITE,
    VisualActionType.CIRCLE,
    VisualActionType.DRAW_BOX,
    VisualActionType.CROSS_OUT,
    VisualActionType.ZOOM_FOCUS,
}


def validate_actions(scene: Scene, max_teaching: int, max_emphasis_per_concept: int) -> list[tuple[str, str]]:
    """Return (severity, message) tuples: 'error' entries are fatal."""

    issues: list[tuple[str, str]] = []
    known_targets = {c.id for c in scene.keyConcepts}
    known_ids = set(known_targets)
    if scene.diagram:
        known_ids |= {n.id for n in scene.diagram.nodes}

    duration = scene.durationSeconds
    teaching_count = 0
    emphasis_per_target: dict[str, int] = {}

    for action in scene.visualActions:
        if action.type not in VisualActionType:
            issues.append(("error", f"Unknown visual action type '{action.type}'"))
            continue
        if action.type in TEACHING_ACTIONS:
            teaching_count += 1
        if action.target:
            if action.target not in known_ids and action.type != VisualActionType.COMPARE:
                issues.append(
                    ("error", f"Visual action '{action.type.value}' targets unknown id '{action.target}'")
                )
            if action.type in HIGH_EMPHASIS:
                emphasis_per_target[action.target] = emphasis_per_target.get(action.target, 0) + 1
        if action.type == VisualActionType.DRAW_ARROW:
            for ref, label in ((action.from_id, "from"), (action.to, "to")):
                if ref and ref not in known_ids:
                    issues.append(
                        ("error", f"drawArrow references unknown {label} id '{ref}'")
                    )
        if action.startSec < 0:
            issues.append(("error", f"Negative timing in '{action.type.value}'"))
        if duration is not None and action.startSec >= duration:
            issues.append(
                ("error", f"Visual action '{action.type.value}' starts after scene end ({duration:.2f}s)")
            )

    for target, count in emphasis_per_target.items():
        if count > max_emphasis_per_concept:
            issues.append(
                ("warning", f"Concept '{target}' has {count} high-emphasis cues (max {max_emphasis_per_concept})")
            )

    if scene.type != SceneType.VISUAL_EXPLANATION and teaching_count > max_teaching:
        issues.append(
            ("warning", f"Scene has {teaching_count} teaching actions (recommended max {max_teaching})")
        )
    return issues
