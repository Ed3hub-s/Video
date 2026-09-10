from __future__ import annotations

from pipeline.content.providers import classify_explanation
from pipeline.content.schemas import SceneType


def test_definition_classification():
    scene_type, strategy, diagram, concepts = classify_explanation(
        "Machine learning is a method that learns patterns from data."
    )
    assert scene_type == SceneType.DEFINITION
    assert strategy == "definition"


def test_process_classification():
    scene_type, strategy, diagram, _ = classify_explanation(
        "The pipeline is Data -> Model -> Prediction and each stage matters."
    )
    assert scene_type == SceneType.VISUAL_EXPLANATION
    assert strategy == "process-diagram"
    assert diagram is not None
    assert [n.label for n in diagram.nodes] == ["DATA", "MODEL", "PREDICTION"]
    assert len(diagram.edges) == 2


def test_comparison_classification():
    scene_type, strategy, diagram, _ = classify_explanation(
        "The old approach vs the new approach: hand-crafted rules instead of learned features."
    )
    assert scene_type == SceneType.VISUAL_EXPLANATION
    assert strategy == "comparison-diagram"
    assert diagram is not None
    assert diagram.kind == "comparison"
    assert len(diagram.nodes) == 2


def test_plain_explanation_classification():
    scene_type, strategy, diagram, _ = classify_explanation(
        "Neural networks are composed of layers of connected units."
    )
    assert scene_type == SceneType.EXPLANATION
    assert strategy == "none"
    assert diagram is None
