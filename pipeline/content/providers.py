"""AI provider abstraction.

V1 ships two providers:
- MockProvider (default): deterministic, offline, returns schema-valid JSON.
- OpenAIProvider: optional live provider behind an API key (never hard-coded).
"""

from __future__ import annotations

import json
import os
import re
import urllib.request
from typing import Any

from pipeline.content.prompt_templates import (
    SCENE_GENERATION_SYSTEM,
    SCENE_GENERATION_USER,
    SCHEMA_REPAIR_SYSTEM,
    SUMMARY_USER,
)
from pipeline.content.schemas import (
    Diagram,
    DiagramEdge,
    DiagramNode,
    Importance,
    KeyConcept,
    Scene,
    SceneType,
    VisualAction,
    VisualActionType,
)
from pipeline.content.text_splitter import screen_text_from_source, split_sentences, word_count


class AIProvider:
    """Interface for the teaching content layer."""

    name = "base"

    def build_scenes(self, chapter: dict[str, Any]) -> list[dict[str, Any]]:
        raise NotImplementedError

    def summarize(self, source: str) -> list[str]:
        raise NotImplementedError

    def repair(self, raw: str, schema_hint: str) -> str:
        raise NotImplementedError


def _parse_json_object(raw: str) -> dict[str, Any]:
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return json.loads(cleaned)


class MockProvider(AIProvider):
    """Deterministic rule-based teaching director (demo mode, offline)."""

    name = "mock"

    def build_scenes(self, chapter: dict[str, Any]) -> list[dict[str, Any]]:
        scenes: list[dict[str, Any]] = []
        chapter_number = int(chapter["chapterNumber"])
        scenes.append(
            Scene(
                id=f"scene-{len(scenes) + 1:03d}",
                type=SceneType.CHAPTER_INTRO,
                title=chapter["title"],
                screenText=chapter["title"],
                voiceover=f"Chapter {chapter_number}. {chapter['title']}.",
                keyConcepts=[],
            ).model_dump(mode="json")
        )

        for section in chapter.get("sections", []):
            scenes.append(
                Scene(
                    id=f"scene-{len(scenes) + 1:03d}",
                    type=SceneType.SECTION_INTRO,
                    title=section["title"],
                    screenText=section["title"],
                    voiceover=section["title"] + ".",
                    keyConcepts=[],
                ).model_dump(mode="json")
            )
            for block in section.get("blocks", []):
                scenes.extend(self._scenes_for_block(block, len(scenes) + 1))

        summary = self.summarize(chapter_source_text_from_dict(chapter))
        screen_parts = []
        for takeaway in summary[:3]:
            words = takeaway.split()
            screen_parts.append(" ".join(words[:10]))
        scenes.append(
            Scene(
                id=f"scene-{len(scenes) + 1:03d}",
                type=SceneType.CHAPTER_SUMMARY,
                title="Key Takeaways",
                screenText=" · ".join(screen_parts),
                voiceover="To summarize, " + " ".join(summary[:4]),
                keyConcepts=[
                    KeyConcept(id=f"takeaway-{i}", text=item[:40].upper(), importance=Importance.MEDIUM)
                    for i, item in enumerate(summary[:3])
                ],
            ).model_dump(mode="json")
        )
        return scenes

    def _scenes_for_block(self, block: dict[str, Any], scene_number: int) -> list[dict[str, Any]]:
        block_type = block.get("type")
        if block_type == "image":
            return [
                Scene(
                    id=f"scene-{scene_number:03d}",
                    type=SceneType.IMAGE_EXPLANATION,
                    title="Image",
                    screenText=block.get("text") or "Focus on this image",
                    voiceover=(block.get("text") or "Let's look closely at this image."),
                    image=block["path"],
                    keyConcepts=[],
                    visualStrategy="image-focus",
                    visualActions=[
                        VisualAction(type=VisualActionType.ZOOM_FOCUS, startSec=0.6, durationSec=1.2)
                    ],
                ).model_dump(mode="json")
            ]

        if block_type in ("bullets", "numbered"):
            items = block.get("items", [])
            concepts = [
                KeyConcept(
                    id=f"point-{i}",
                    text=_concept_text(item),
                    importance=Importance.HIGH if i == 0 and len(items) <= 5 else Importance.MEDIUM,
                )
                for i, item in enumerate(items)
            ]
            return [
                Scene(
                    id=f"scene-{scene_number:03d}",
                    type=SceneType.BULLET_LIST,
                    title="Key Points",
                    screenText="\n".join(items),
                    voiceover=("Here are the key points. " + " ".join(items)),
                    keyConcepts=concepts,
                    visualStrategy="sequential-reveal",
                    visualActions=[
                        VisualAction(type=VisualActionType.REVEAL, target=f"point-{i}", startSec=1.0 + i * 2.0)
                        for i in range(len(items))
                    ],
                ).model_dump(mode="json")
            ]

        text = block.get("text", "")
        if not text:
            return []
        scene_type, strategy, diagram, concepts = classify_explanation(text, len(block.get("warnings", [])))
        return [
            Scene(
                id=f"scene-{scene_number:03d}",
                type=scene_type,
                title=_scene_title(text),
                screenText=screen_text_from_source(text, 40),
                voiceover=text,
                keyConcepts=concepts,
                visualStrategy=strategy,
                visualActions=[],
                diagram=diagram,
                sourceText=text,
            ).model_dump(mode="json")
        ]

    def summarize(self, source: str) -> list[str]:
        normalized = re.sub(r"#{1,6}\s*", "", source)
        normalized = re.sub(r"[\n\r]+", " ", normalized)
        sentences = [s for s in split_sentences(normalized) if s]
        long = [s for s in sentences if 8 <= word_count(s) <= 24]
        picked = long[:4] if len(long) >= 3 else sentences[:5]
        result: list[str] = []
        for item in picked[:5]:
            words = item.split()
            short = " ".join(words[:20]).rstrip(".") + "."
            if short not in result:
                result.append(short)
        return result[:5]

    def repair(self, raw: str, schema_hint: str) -> str:
        return raw


class OpenAIProvider(AIProvider):
    """Minimal live provider (no SDK dependency; plain JSON over HTTPS)."""

    name = "openai"

    def __init__(self) -> None:
        self.api_key = os.environ.get("OPENAI_API_KEY", "")
        self.model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        self.base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is required when AI_PROVIDER=openai")

    def _chat(self, system: str, user: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.4,
            "response_format": {"type": "json_object"},
        }
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]

    def build_scenes(self, chapter: dict[str, Any]) -> list[dict[str, Any]]:
        from pipeline.content.scene_generator import SCENE_SCHEMA_JSON

        source = chapter_source_text_from_dict(chapter)
        raw = self._chat(
            SCENE_GENERATION_SYSTEM,
            SCENE_GENERATION_USER.format(source=source, schema=SCENE_SCHEMA_JSON),
        )
        return _parse_json_object(raw).get("scenes", [])

    def summarize(self, source: str) -> list[str]:
        raw = self._chat("Return ONLY valid JSON.", SUMMARY_USER.format(source=source))
        return _parse_json_object(raw).get("takeaways", [])

    def repair(self, raw: str, schema_hint: str) -> str:
        return self._chat(SCHEMA_REPAIR_SYSTEM, f"Schema:\n{schema_hint}\n\nPrevious response:\n{raw}")


def chapter_source_text_from_dict(chapter: dict[str, Any]) -> str:
    lines = [f"Chapter {chapter['chapterNumber']}: {chapter['title']}"]
    for section in chapter.get("sections", []):
        lines.append(f"\n## {section['title']}")
        for block in section.get("blocks", []):
            if block.get("text"):
                lines.append(block["text"])
            for item in block.get("items", []):
                lines.append(f"- {item}")
    return "\n".join(lines)


def _concept_text(item: str) -> str:
    words = [w for w in re.split(r"\W+", item) if w]
    return " ".join(words[:3]).upper()[:32]


def _scene_title(text: str) -> str:
    sentence = split_sentences(text)[0]
    if len(sentence) <= 80:
        return sentence
    return sentence[:77] + "..."


def classify_explanation(
    text: str, warning_count: int = 0
) -> tuple[SceneType, str, Diagram | None, list[KeyConcept]]:
    """Deterministic teaching classification used by the mock provider."""

    lowered = text.lower()
    concepts = _extract_concepts(text)

    if any(
        marker in lowered
        for marker in (
            "what is ",
            " is defined as ",
            " means ",
            " is a method ",
            " is a technique ",
            " is an approach ",
            " is a system ",
            " is the process of ",
            " is the branch ",
        )
    ):
        return SceneType.DEFINITION, "definition", None, concepts

    if any(marker in lowered for marker in (" -> ", " → ")):
        nodes = _diagram_nodes(text)
        diagram = Diagram(
            kind="process",
            nodes=nodes,
            edges=[DiagramEdge(from_id=nodes[i].id, to=nodes[i + 1].id) for i in range(len(nodes) - 1)],
        )
        return SceneType.VISUAL_EXPLANATION, "process-diagram", diagram, concepts

    if any(marker in lowered for marker in (" vs ", " versus ", " compared to ", " instead of ")):
        nodes = _comparison_nodes(text)
        diagram = Diagram(kind="comparison", nodes=nodes, edges=[])
        return SceneType.VISUAL_EXPLANATION, "comparison-diagram", diagram, concepts

    if " causes " in lowered or " leads to " in lowered or " results in " in lowered:
        nodes = _diagram_nodes(text, count=2)
        diagram = Diagram(
            kind="cause-effect",
            nodes=nodes,
            edges=[DiagramEdge(from_id=nodes[0].id, to=nodes[1].id)],
        )
        return SceneType.VISUAL_EXPLANATION, "cause-effect-diagram", diagram, concepts

    return SceneType.EXPLANATION, "none", None, concepts


def _extract_concepts(text: str) -> list[KeyConcept]:
    words = [w.strip(" ,.;:()") for w in re.split(r"\s+", text)]
    candidates = [w for w in words if w and len(w) >= 4 and w.lower() not in _STOPWORDS]
    seen: set[str] = set()
    concepts: list[KeyConcept] = []
    for word in candidates[:8]:
        key = word.lower()
        if key in seen:
            continue
        seen.add(key)
        importance = Importance.HIGH if key in _HIGH_TERMS else (Importance.MEDIUM if len(concepts) < 3 else Importance.LOW)
        concepts.append(KeyConcept(id=f"c{len(concepts) + 1}", text=word.upper()[:24], importance=importance))
    return concepts


def _diagram_nodes(text: str, count: int | None = None) -> list[DiagramNode]:
    for marker in (" → ", " -> "):
        if marker in text:
            parts = [p.strip() for p in text.split(marker) if p.strip()][:5]
            nodes: list[DiagramNode] = []
            for i, part in enumerate(parts):
                words = part.split()
                if i == 0:
                    label = words[-1]
                elif i == len(parts) - 1:
                    label = words[0]
                else:
                    label = " ".join(words) if len(words) <= 3 else words[-1]
                label = label.strip(" ,.;:()")[:18].upper()
                nodes.append(DiagramNode(id=f"node-{len(nodes) + 1}", label=label))
            return nodes
    tokens = [t for t in re.split(r"\s+", text) if len(t) > 3][:5]
    if count:
        tokens = tokens[:count]
    return [
        DiagramNode(id=f"node-{i + 1}", label=t.strip(" ,.;:").upper()[:18])
        for i, t in enumerate(tokens)
        if t
    ]


def _comparison_nodes(text: str) -> list[DiagramNode]:
    for marker in (" vs ", " versus ", " compared to ", " instead of "):
        if marker in text:
            left, right = text.split(marker, 1)
            left_label = " ".join(left.split()[-2:]).strip(" ,.;:()").upper()[:18]
            right_label = " ".join(right.split()[:2]).strip(" ,.;:()").upper()[:18]
            return [
                DiagramNode(id="node-1", label=left_label or "A"),
                DiagramNode(id="node-2", label=right_label or "B"),
            ]
    return _diagram_nodes(text, count=2)


_STOPWORDS = frozenset(
    {
        "this", "that", "with", "from", "into", "about", "which", "where",
        "there", "their", "these", "those", "what", "when", "will", "would",
        "should", "could", "does", "doing", "being", "have", "has", "having",
        "more", "most", "than", "then", "they", "them", "were", "been",
    }
)

_HIGH_TERMS = frozenset(
    {
        "machine", "learning", "data", "prediction", "algorithm", "model",
        "network", "neural", "definition", "process", "input", "output",
    }
)


def build_provider(name: str | None = None) -> AIProvider:
    provider_name = (name or os.environ.get("AI_PROVIDER", "mock")).lower()
    if provider_name == "openai":
        return OpenAIProvider()
    return MockProvider()
