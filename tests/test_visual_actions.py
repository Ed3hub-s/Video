from __future__ import annotations

from pipeline.content.schemas import Scene, SceneType, VisualAction, VisualActionType
from pipeline.visual.action_validator import validate_actions
from pipeline.visual.importance import rebalance_importance
from pipeline.visual.visual_planner import align_actions_to_words, plan_visual_actions


def _scene(**overrides) -> Scene:
    data = dict(
        id="scene-001",
        type=SceneType.DEFINITION,
        title="What is Machine Learning?",
        screenText="DATA -> PATTERNS -> PREDICTION",
        voiceover="Machine learning learns patterns from data.",
        durationSeconds=12.0,
        keyConcepts=[
            {"id": "data", "text": "DATA", "importance": "high"},
            {"id": "patterns", "text": "PATTERNS", "importance": "high"},
            {"id": "prediction", "text": "PREDICTION", "importance": "high"},
        ],
    )
    data.update(overrides)
    return Scene.model_validate(data)


def test_definition_gets_teaching_actions():
    scene = plan_visual_actions(_scene())
    assert scene.visualActions
    assert all(a.type in VisualActionType for a in scene.visualActions)


def test_validator_accepts_planned_actions():
    scene = plan_visual_actions(_scene())
    issues = validate_actions(scene, max_teaching=3, max_emphasis_per_concept=2)
    assert not [sev for sev, _ in issues if sev == "error"]


def test_validator_flags_unknown_target():
    scene = _scene(
        visualActions=[
            VisualAction(type=VisualActionType.UNDERLINE, target="nope", startSec=1.0, durationSec=0.5)
        ]
    )
    issues = validate_actions(scene, max_teaching=3, max_emphasis_per_concept=2)
    assert any(sev == "error" and "unknown id" in msg for sev, msg in issues)


def test_too_many_emphasis_cues_warns():
    scene = _scene(
        visualActions=[
            VisualAction(type=VisualActionType.CIRCLE, target="data", startSec=1.0, durationSec=0.5),
            VisualAction(type=VisualActionType.HANDWRITE, target="data", startSec=2.0, durationSec=0.5),
            VisualAction(type=VisualActionType.DRAW_BOX, target="data", startSec=3.0, durationSec=0.5),
        ]
    )
    issues = validate_actions(scene, max_teaching=3, max_emphasis_per_concept=2)
    assert any(sev == "warning" and "emphasis" in msg for sev, msg in issues)


def test_importance_rebalance_keeps_distribution_sane():
    scene = _scene(
        keyConcepts=[
            {"id": "a", "text": "A", "importance": "high"},
            {"id": "b", "text": "B", "importance": "high"},
            {"id": "c", "text": "C", "importance": "high"},
            {"id": "d", "text": "D", "importance": "high"},
            {"id": "e", "text": "E", "importance": "high"},
        ]
    )
    result = rebalance_importance(scene)
    high = [c for c in result.keyConcepts if c.importance.value == "high"]
    assert len(high) <= max(2, len(result.keyConcepts) // 2)


def test_align_actions_to_words_uses_real_timestamps():
    scene = _scene(
        visualActions=[
            VisualAction(type=VisualActionType.UNDERLINE, target="data", startSec=9.0, durationSec=0.8)
        ]
    )
    words = [
        {"word": word, "start": index * 0.5, "end": index * 0.5 + 0.4}
        for index, word in enumerate(["Machine", "learning", "data", "patterns"])
    ]
    result = align_actions_to_words(scene, words, offset=0.3)
    assert abs(result.visualActions[0].startSec - (2 * 0.5 + 0.3)) < 0.01


def test_align_actions_keeps_timing_when_no_word_match():
    scene = _scene(
        keyConcepts=[{"id": "ghost", "text": "GHOST", "importance": "high"}],
        visualActions=[
            VisualAction(type=VisualActionType.UNDERLINE, target="ghost", startSec=2.0, durationSec=0.8)
        ],
    )
    words = [{"word": "hello", "start": 0.1, "end": 0.5}]
    result = align_actions_to_words(scene, words, offset=0.3)
    assert result.visualActions[0].startSec == 2.0
