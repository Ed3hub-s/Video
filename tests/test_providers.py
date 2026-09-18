from __future__ import annotations

from pipeline.content.providers import MockProvider, classify_explanation
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


def test_short_single_block_chapter_is_not_padded_with_duplicate_scenes():
    scenes = MockProvider().build_scenes(
        {
            "chapterNumber": 1,
            "title": "Web3",
            "sections": [
                {
                    "title": "Web3",
                    "blocks": [
                        {
                            "type": "paragraph",
                            "text": "Web3 gives users direct ownership of digital assets.",
                            "items": [],
                            "warnings": [],
                        }
                    ],
                }
            ],
        }
    )

    assert [scene["type"] for scene in scenes] == [
        "chapterIntro",
        "explanation",
    ]


def test_web_evolution_list_becomes_an_arrow_diagram():
    scenes = MockProvider().build_scenes(
        {
            "chapterNumber": 1,
            "title": "The Evolution of the Web",
            "sections": [
                {
                    "title": "The Evolution of the Web",
                    "blocks": [
                        {
                            "type": "bullets",
                            "text": "",
                            "items": [
                                "Web1 was the read-only era.",
                                "Web2 introduced publishing and social platforms.",
                                "Web3 adds direct digital ownership.",
                            ],
                            "warnings": [],
                        }
                    ],
                }
            ],
        }
    )

    visual = next(
        scene
        for scene in scenes
        if scene["type"] == "visualExplanation"
    )

    assert visual["visualStrategy"] == "process-diagram"
    assert [node["label"] for node in visual["diagram"]["nodes"]] == [
        "WEB1",
        "WEB2",
        "WEB3",
    ]
    assert len(visual["diagram"]["edges"]) == 2
