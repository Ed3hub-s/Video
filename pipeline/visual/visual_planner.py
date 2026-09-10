"""Assign teaching motions to important concepts.

Deterministic planner used by demo mode; the live AI provider also emits
actions but they must always pass action validation afterwards.
"""

from __future__ import annotations

from pipeline.content.schemas import (
    Diagram,
    Importance,
    Scene,
    SceneType,
    VisualAction,
    VisualActionType,
)


def _actions_for_diagram(diagram: Diagram) -> list[VisualAction]:
    actions: list[VisualAction] = []
    actions.append(VisualAction(type=VisualActionType.BUILD_DIAGRAM, startSec=0.5, durationSec=1.0))
    for i, node in enumerate(diagram.nodes):
        actions.append(
            VisualAction(type=VisualActionType.REVEAL, target=node.id, startSec=1.2 + i * 1.6, durationSec=0.5)
        )
    for i, edge in enumerate(diagram.edges):
        actions.append(
            VisualAction(
                type=VisualActionType.DRAW_ARROW,
                from_id=edge.from_id,
                to=edge.to,
                startSec=2.0 + i * 1.6,
                durationSec=0.8,
            )
        )
    return actions


def plan_visual_actions(scene: Scene, max_actions: int = 3) -> Scene:
    """Fill in teaching actions for scenes that lack them, then trim excess."""

    if scene.visualActions:
        return scene

    actions: list[VisualAction] = []
    if scene.diagram:
        actions = _actions_for_diagram(scene.diagram)
    elif scene.type == SceneType.DEFINITION:
        high = [c for c in scene.keyConcepts if c.importance == Importance.HIGH]
        if high:
            actions.append(
                VisualAction(type=VisualActionType.UNDERLINE, target=high[0].id, startSec=1.4, durationSec=0.9)
            )
            if len(high) > 1:
                actions.append(
                    VisualAction(type=VisualActionType.HANDWRITE, target=high[-1].id, startSec=3.0, durationSec=1.1)
                )
        elif scene.keyConcepts:
            actions.append(
                VisualAction(type=VisualActionType.HIGHLIGHT, target=scene.keyConcepts[0].id, startSec=1.4, durationSec=1.2)
            )
    elif scene.type == SceneType.EXPLANATION:
        high = [c for c in scene.keyConcepts if c.importance == Importance.HIGH]
        for concept in high[:2]:
            actions.append(
                VisualAction(type=VisualActionType.UNDERLINE, target=concept.id, startSec=1.4, durationSec=0.9)
            )
        if not actions and scene.keyConcepts:
            actions.append(
                VisualAction(type=VisualActionType.HIGHLIGHT, target=scene.keyConcepts[0].id, startSec=1.4, durationSec=1.2)
            )
    elif scene.type == SceneType.IMAGE_EXPLANATION and scene.image:
        actions.append(
            VisualAction(type=VisualActionType.ZOOM_FOCUS, startSec=0.5, durationSec=1.5)
        )
        if scene.keyConcepts:
            actions.append(
                VisualAction(type=VisualActionType.DRAW_BOX, target=scene.keyConcepts[0].id, startSec=3.2, durationSec=1.0)
            )

    if scene.type != SceneType.VISUAL_EXPLANATION:
        actions = actions[:max_actions]
    return scene.model_copy(update={"visualActions": actions})


def fit_actions_to_scene(scene: Scene, outro_padding: float) -> Scene:
    """Scale action timing so no action ends after the scene's real duration.

    Action plans are authored before TTS, so timings are estimates; once the
    audio-derived duration is known they must fit inside the scene.
    """

    if scene.durationSeconds is None or not scene.visualActions:
        return scene
    end_limit = max(0.1, scene.durationSeconds - outro_padding)
    last_end = max((action.startSec + action.durationSec) for action in scene.visualActions)
    if last_end <= end_limit:
        return scene
    scale = end_limit / last_end
    actions = [
        action.model_copy(
            update={
                "startSec": round(action.startSec * scale, 3),
                "durationSec": round(action.durationSec * scale, 3),
            }
        )
        for action in scene.visualActions
    ]
    return scene.model_copy(update={"visualActions": actions})


def align_actions_to_words(scene: Scene, words: list[dict], offset: float) -> Scene:
    """Re-time visual actions so cues land on the narrated word for their target.

    Uses real word-level timestamps (edge-tts). Actions whose target concept
    cannot be matched to a spoken word keep their planned timing.
    """

    if not scene.visualActions or not words:
        return scene

    def word_start_for(target_text: str) -> float | None:
        needle = target_text.lower().strip(" .,;:()\"'-")
        if len(needle) < 3:
            return None
        for item in words:
            word = str(item.get("word", "")).lower().strip(" .,;:()\"'-")
            if len(word) < 3:
                continue
            if word == needle:
                return float(item["start"]) + offset
            if len(needle) >= 4 and needle in word:
                return float(item["start"]) + offset
            if len(word) >= 4 and word in needle:
                return float(item["start"]) + offset
        return None

    by_id = {concept.id: concept for concept in scene.keyConcepts}
    actions: list[VisualAction] = []
    for action in scene.visualActions:
        concept = by_id.get(action.target or "")
        start = word_start_for(concept.text) if concept else None
        if start is not None:
            actions.append(action.model_copy(update={"startSec": round(start, 3)}))
        else:
            actions.append(action)
    return scene.model_copy(update={"visualActions": actions})
