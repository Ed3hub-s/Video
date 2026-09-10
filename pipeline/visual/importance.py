"""Assign and re-balance importance levels for key concepts."""

from __future__ import annotations

from pipeline.content.schemas import Importance, KeyConcept, Scene, SceneType


HIGH_SIGNAL = frozenset(
    {
        "definition", "means", "defined", "core", "key", "must", "always",
        "never", "important", "conclusion", "rule", "remember",
    }
)


def rebalance_importance(scene: Scene) -> Scene:
    """Deterministic importance adjustment (demo-grade, explainable)."""

    concepts = list(scene.keyConcepts)
    if not concepts:
        return scene

    if scene.type == SceneType.DEFINITION:
        # The defined term itself is the highest-priority concept.
        title_words = [w.lower().strip("?") for w in scene.title.split() if w.lower().strip("?")]
        for concept in concepts:
            if any(w in concept.text.lower() for w in title_words):
                concept.importance = Importance.HIGH

    high_count = sum(1 for c in concepts if c.importance == Importance.HIGH)
    if high_count > max(2, len(concepts) // 2):
        for concept in concepts:
            if concept.importance == Importance.HIGH and high_count > 2:
                concept.importance = Importance.MEDIUM
                high_count -= 1

    return scene.model_copy(update={"keyConcepts": concepts})
