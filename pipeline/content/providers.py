"""AI provider abstraction.

V1 ships two providers:

- MockProvider (default): deterministic, offline teaching director that returns
  schema-valid scene JSON.
- OpenAIProvider: optional live provider behind an API key.

The mock provider also acts as a lightweight visual director. It selectively
turns source material into diagrams when the relationship is materially easier
to understand visually.

The goal is not to turn every paragraph into a graphic. A strong lesson should
mix clean explanatory scenes, definitions, lists, images, diagrams, and
transitions.
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
from pipeline.content.text_splitter import (
    screen_text_from_source,
    split_sentences,
    word_count,
)


class AIProvider:
    """Interface for the teaching content layer."""

    name = "base"

    def build_scenes(
        self,
        chapter: dict[str, Any],
    ) -> list[dict[str, Any]]:
        raise NotImplementedError

    def summarize(
        self,
        source: str,
    ) -> list[str]:
        raise NotImplementedError

    def repair(
        self,
        raw: str,
        schema_hint: str,
    ) -> str:
        raise NotImplementedError


def _parse_json_object(
    raw: str,
) -> dict[str, Any]:
    cleaned = raw.strip()

    cleaned = re.sub(
        r"^```(?:json)?\s*",
        "",
        cleaned,
    )

    cleaned = re.sub(
        r"\s*```$",
        "",
        cleaned,
    )

    return json.loads(cleaned)


class MockProvider(AIProvider):
    """Deterministic offline teaching and visual director."""

    name = "mock"

    def build_scenes(
        self,
        chapter: dict[str, Any],
    ) -> list[dict[str, Any]]:
        scenes: list[dict[str, Any]] = []

        chapter_number = int(
            chapter["chapterNumber"]
        )

        scenes.append(
            Scene(
                id=f"scene-{len(scenes) + 1:03d}",
                type=SceneType.CHAPTER_INTRO,
                title=chapter["title"],
                screenText=chapter["title"],
                voiceover=_chapter_intro_voiceover(
                    chapter
                ),
                keyConcepts=[],
            ).model_dump(
                mode="json"
            )
        )

        substantive_count = max(
            _count_substantive_paragraphs(
                chapter
            ),
            _count_content_units(
                chapter
            ),
        )

        visual_budget = (
            _visual_budget(
                substantive_count
            )
        )

        selected_visual_blocks = (
            _select_visual_blocks(
                chapter,
                visual_budget,
            )
        )

        for section_index, section in enumerate(
            chapter.get(
                "sections",
                [],
            )
        ):
            section_blocks = section.get(
                "blocks",
                [],
            )

            section_title = section.get("title", "").strip()
            chapter_title = chapter.get("title", "").strip()

            if (
                section_title
                and _normalized_heading(section_title)
                != _normalized_heading(chapter_title)
            ):
                scenes.append(
                    Scene(
                        id=(
                            f"scene-"
                            f"{len(scenes) + 1:03d}"
                        ),
                        type=SceneType.SECTION_INTRO,
                        title=section_title,
                        screenText=section_title,
                        voiceover=_section_intro_voiceover(
                            section_title,
                            section_index,
                        ),
                        keyConcepts=[],
                    ).model_dump(
                        mode="json"
                    )
                )

            for block_index, block in enumerate(
                section_blocks
            ):
                allow_visual = (
                    (
                        section_index,
                        block_index,
                    )
                    in selected_visual_blocks
                )

                block_scenes = (
                    self._scenes_for_block(
                        block,
                        len(scenes) + 1,
                        allow_visual=allow_visual,
                        section_title=section["title"],
                        block_index=block_index,
                        block_count=len(section_blocks),
                    )
                )

                scenes.extend(
                    block_scenes
                )

        summary = _chapter_takeaways(
            chapter,
            limit=4,
        )

        screen_parts: list[str] = []

        for takeaway in summary[:3]:
            words = takeaway.split()

            screen_parts.append(
                " ".join(
                    words[:10]
                )
            )

        if _count_content_units(chapter) >= 2:
            scenes.append(
                Scene(
                    id=f"scene-{len(scenes) + 1:03d}",
                    type=SceneType.CHAPTER_SUMMARY,
                    title="Key Takeaways",
                    screenText=(
                        " · ".join(
                            screen_parts
                        )
                    ),
                    voiceover=(
                        "To recap: "
                        + " ".join(
                            summary[:4]
                        )
                    ),
                    keyConcepts=[
                        KeyConcept(
                            id=(
                                f"takeaway-{i}"
                            ),
                            text=_concept_text(
                                item
                            ),
                            importance=(
                                Importance.MEDIUM
                            ),
                        )
                        for i, item
                        in enumerate(
                            summary[:3]
                        )
                    ],
                ).model_dump(
                    mode="json"
                )
            )

        return scenes

    def _scenes_for_block(
        self,
        block: dict[str, Any],
        scene_number: int,
        allow_visual: bool = False,
        section_title: str = "",
        block_index: int = 0,
        block_count: int = 1,
    ) -> list[dict[str, Any]]:
        block_type = block.get(
            "type"
        )

        if block_type == "image":
            return [
                Scene(
                    id=(
                        f"scene-"
                        f"{scene_number:03d}"
                    ),
                    type=(
                        SceneType
                        .IMAGE_EXPLANATION
                    ),
                    title="Image",
                    screenText=(
                        block.get("text")
                        or "Focus on this image"
                    ),
                    voiceover=(
                        block.get("text")
                        or (
                            "Let's look closely "
                            "at this image."
                        )
                    ),
                    image=block["path"],
                    keyConcepts=[],
                    visualStrategy=(
                        "image-focus"
                    ),
                    visualActions=[
                        VisualAction(
                            type=(
                                VisualActionType
                                .ZOOM_FOCUS
                            ),
                            startSec=0.6,
                            durationSec=1.2,
                        )
                    ],
                ).model_dump(
                    mode="json"
                )
            ]

        if block_type in (
            "bullets",
            "numbered",
        ):
            items = block.get(
                "items",
                [],
            )

            concepts = [
                KeyConcept(
                    id=f"point-{i}",
                    text=(
                        _concept_text(
                            item
                        )
                    ),
                    importance=(
                        Importance.HIGH
                        if (
                            i == 0
                            and len(items) <= 5
                        )
                        else Importance.MEDIUM
                    ),
                )
                for i, item
                in enumerate(items)
            ]

            if allow_visual and len(items) >= 3:
                diagram = _diagram_for_list(
                    section_title,
                    items,
                    numbered=(block_type == "numbered"),
                )

                if diagram is not None:
                    return [
                        Scene(
                            id=(
                                f"scene-"
                                f"{scene_number:03d}"
                            ),
                            type=(
                                SceneType
                                .VISUAL_EXPLANATION
                            ),
                            title=(
                                section_title
                                or "Key Points"
                            ),
                            screenText=(
                                " · ".join(
                                    node.label
                                    for node
                                    in diagram.nodes
                                )
                            ),
                            voiceover=(
                                "Here are the key points. "
                                + " ".join(items)
                            ),
                            keyConcepts=concepts,
                            visualStrategy=(
                                f"{diagram.kind}-diagram"
                            ),
                            visualActions=[],
                            diagram=diagram,
                            sourceText=(
                                "\n".join(items)
                            ),
                        ).model_dump(
                            mode="json"
                        )
                    ]

            return [
                Scene(
                    id=(
                        f"scene-"
                        f"{scene_number:03d}"
                    ),
                    type=(
                        SceneType
                        .BULLET_LIST
                    ),
                    title="Key Points",
                    screenText=(
                        "\n".join(
                            items
                        )
                    ),
                    voiceover=(
                        "Here are the key points. "
                        + " ".join(
                            items
                        )
                    ),
                    keyConcepts=concepts,
                    visualStrategy=(
                        "sequential-reveal"
                    ),
                    visualActions=[
                        VisualAction(
                            type=(
                                VisualActionType
                                .REVEAL
                            ),
                            target=(
                                f"point-{i}"
                            ),
                            startSec=(
                                1.0
                                + i * 2.0
                            ),
                        )
                        for i
                        in range(
                            len(items)
                        )
                    ],
                ).model_dump(
                    mode="json"
                )
            ]

        text = block.get(
            "text",
            "",
        ).strip()

        if not text:
            return []

        (
            scene_type,
            strategy,
            diagram,
            concepts,
        ) = classify_explanation(
            text,
            len(
                block.get(
                    "warnings",
                    [],
                )
            ),
        )

        if (
            scene_type
            == SceneType.VISUAL_EXPLANATION
            and not allow_visual
        ):
            scene_type = (
                SceneType.EXPLANATION
            )

            strategy = "none"
            diagram = None

        return [
            Scene(
                id=(
                    f"scene-"
                    f"{scene_number:03d}"
                ),
                type=scene_type,
                title=(
                    _scene_title(
                        text
                    )
                ),
                screenText=(
                    screen_text_from_source(
                        text,
                        12,
                    )
                ),
                voiceover=_narration_for_text(
                    text,
                    section_title=section_title,
                    block_index=block_index,
                    block_count=block_count,
                ),
                keyConcepts=concepts,
                visualStrategy=strategy,
                visualActions=[],
                diagram=diagram,
                sourceText=text,
            ).model_dump(
                mode="json"
            )
        ]

    def summarize(
        self,
        source: str,
    ) -> list[str]:
        normalized = re.sub(
            r"#{1,6}\s*",
            "",
            source,
        )

        normalized = re.sub(
            r"[\n\r]+",
            " ",
            normalized,
        )

        sentences = [
            sentence
            for sentence
            in split_sentences(
                normalized
            )
            if sentence
        ]

        long_sentences = [
            sentence
            for sentence
            in sentences
            if (
                8
                <= word_count(sentence)
                <= 24
            )
        ]

        picked = (
            long_sentences[:4]
            if len(
                long_sentences
            ) >= 3
            else sentences[:5]
        )

        result: list[str] = []

        for item in picked[:5]:
            words = item.split()

            short = (
                " ".join(
                    words[:20]
                )
                .rstrip(".")
                + "."
            )

            if short not in result:
                result.append(
                    short
                )

        return result[:5]

    def repair(
        self,
        raw: str,
        schema_hint: str,
    ) -> str:
        return raw


class OpenAIProvider(AIProvider):
    """Minimal live provider using JSON over HTTPS."""

    name = "openai"

    def __init__(self) -> None:
        self.api_key = os.environ.get(
            "OPENAI_API_KEY",
            "",
        )

        self.model = os.environ.get(
            "OPENAI_MODEL",
            "gpt-4o-mini",
        )

        self.base_url = (
            os.environ.get(
                "OPENAI_BASE_URL",
                "https://api.openai.com/v1",
            )
            .rstrip("/")
        )

        if not self.api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is required "
                "when AI_PROVIDER=openai"
            )

    def _chat(
        self,
        system: str,
        user: str,
    ) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": system,
                },
                {
                    "role": "user",
                    "content": user,
                },
            ],
            "temperature": 0.4,
            "response_format": {
                "type": "json_object"
            },
        }

        request = (
            urllib.request.Request(
                (
                    f"{self.base_url}"
                    f"/chat/completions"
                ),
                data=json.dumps(
                    payload
                ).encode(
                    "utf-8"
                ),
                headers={
                    "Authorization": (
                        "Bearer "
                        f"{self.api_key}"
                    ),
                    "Content-Type": (
                        "application/json"
                    ),
                },
                method="POST",
            )
        )

        with urllib.request.urlopen(
            request,
            timeout=120,
        ) as response:
            data = json.loads(
                response.read().decode(
                    "utf-8"
                )
            )

        return (
            data["choices"][0]
            ["message"]["content"]
        )

    def build_scenes(
        self,
        chapter: dict[str, Any],
    ) -> list[dict[str, Any]]:
        from pipeline.content.scene_generator import (
            SCENE_SCHEMA_JSON,
        )

        source = (
            chapter_source_text_from_dict(
                chapter
            )
        )

        raw = self._chat(
            SCENE_GENERATION_SYSTEM,
            SCENE_GENERATION_USER.format(
                source=source,
                schema=SCENE_SCHEMA_JSON,
            ),
        )

        return (
            _parse_json_object(
                raw
            )
            .get(
                "scenes",
                [],
            )
        )

    def summarize(
        self,
        source: str,
    ) -> list[str]:
        raw = self._chat(
            "Return ONLY valid JSON.",
            SUMMARY_USER.format(
                source=source
            ),
        )

        return (
            _parse_json_object(
                raw
            )
            .get(
                "takeaways",
                [],
            )
        )

    def repair(
        self,
        raw: str,
        schema_hint: str,
    ) -> str:
        return self._chat(
            SCHEMA_REPAIR_SYSTEM,
            (
                f"Schema:\n"
                f"{schema_hint}\n\n"
                f"Previous response:\n"
                f"{raw}"
            ),
        )


def chapter_source_text_from_dict(
    chapter: dict[str, Any],
) -> str:
    lines = [
        (
            f"Chapter "
            f"{chapter['chapterNumber']}: "
            f"{chapter['title']}"
        )
    ]

    for section in chapter.get(
        "sections",
        [],
    ):
        lines.append(
            f"\n## {section['title']}"
        )

        for block in section.get(
            "blocks",
            [],
        ):
            if block.get("text"):
                lines.append(
                    block["text"]
                )

            for item in block.get(
                "items",
                [],
            ):
                lines.append(
                    f"- {item}"
                )

    return "\n".join(
        lines
    )


def _normalized_heading(value: str) -> str:
    return "".join(
        character.lower()
        for character in value
        if character.isalnum()
    )


def _count_content_units(
    chapter: dict[str, Any],
) -> int:
    units = 0

    for section in chapter.get("sections", []):
        for block in section.get("blocks", []):
            if block.get("text", "").strip():
                units += 1

            units += len(
                [
                    item
                    for item in block.get("items", [])
                    if str(item).strip()
                ]
            )

    return units


def _clean_narration_text(text: str) -> str:
    """Normalize spacing and terminal punctuation for speech."""

    cleaned = re.sub(r"\s+", " ", str(text or "")).strip()
    cleaned = re.sub(r"\s+([,.;:!?])", r"\1", cleaned)
    cleaned = re.sub(r"\?+\.+$", "?", cleaned)
    cleaned = re.sub(r"!+\.+$", "!", cleaned)
    cleaned = re.sub(r"\.{2,}$", ".", cleaned)
    return cleaned


def _ensure_terminal_punctuation(text: str) -> str:
    cleaned = _clean_narration_text(text)
    if not cleaned or cleaned[-1] in ".!?":
        return cleaned
    return cleaned + "."


def _topic_phrase(text: str) -> str:
    cleaned = _clean_narration_text(text).rstrip(".!?")
    if not cleaned:
        return ""

    first_word = cleaned.split(maxsplit=1)[0]
    if (
        not any(char.isdigit() for char in first_word)
        and not first_word.isupper()
    ):
        cleaned = cleaned[0].lower() + cleaned[1:]
    return cleaned


def _chapter_intro_voiceover(
    chapter: dict[str, Any],
) -> str:
    title = _topic_phrase(chapter.get("title", ""))
    if title.lower().startswith("understanding "):
        title = title[len("understanding "):]

    if not title:
        return "In this lesson, we'll work through the main ideas step by step."

    return (
        f"In this lesson, we'll explore {title}. "
        "We'll build the idea step by step."
    )


def _section_intro_voiceover(
    title: str,
    section_index: int,
) -> str:
    cleaned = _clean_narration_text(title)
    if not cleaned:
        return ""

    lowered = cleaned.lower()
    topic = _topic_phrase(cleaned)

    if cleaned.endswith("?"):
        prefix = (
            "Let's start with a question: "
            if section_index == 0
            else "Next, consider this question: "
        )
        return prefix + cleaned

    if lowered.startswith("how "):
        prefix = (
            "Let's start by seeing "
            if section_index == 0
            else "Next, let's see "
        )
        return prefix + topic + "."

    if lowered.startswith("why "):
        prefix = (
            "Let's start by looking at "
            if section_index == 0
            else "Next, let's look at "
        )
        return prefix + topic + "."

    prefix = (
        "Let's start with "
        if section_index == 0
        else "Next, let's look at "
    )
    return prefix + topic + "."


def _lower_after_connector(text: str) -> str:
    cleaned = _clean_narration_text(text)
    for prefix in ("A ", "An ", "The ", "This ", "These ", "It "):
        if cleaned.startswith(prefix):
            return prefix[0].lower() + cleaned[1:]
    return cleaned


def _narration_for_text(
    text: str,
    section_title: str,
    block_index: int,
    block_count: int,
) -> str:
    """Add light connective language while preserving source meaning."""

    cleaned = _ensure_terminal_punctuation(text)
    if not cleaned:
        return ""

    section_lowered = section_title.lower()
    process_section = any(
        marker in section_lowered
        for marker in (
            "how ",
            "process",
            "workflow",
            "transaction",
            "steps",
            "procedure",
            "works",
        )
    )

    if process_section and block_count > 1:
        if block_index <= 0:
            connector = "First"
        elif block_index >= block_count - 1:
            connector = "Finally"
        else:
            connector = ("Next", "Then", "After that")[
                min(block_index - 1, 2)
            ]
        return f"{connector}, {_lower_after_connector(cleaned)}"

    if block_index <= 0:
        return cleaned

    lowered = cleaned.lower()
    if (
        "non-" in lowered
        and any(
            marker in section_lowered
            for marker in (" and ", " versus ", " vs ")
        )
    ):
        return "By contrast, " + _lower_after_connector(cleaned)

    if lowered.startswith(("it ", "this ", "these ", "they ", "that ")):
        return cleaned

    return "Also, " + _lower_after_connector(cleaned)


def _compact_takeaway(
    text: str,
    max_words: int = 12,
) -> str:
    cleaned = _ensure_terminal_punctuation(text)
    sentences = split_sentences(cleaned)
    if sentences:
        cleaned = _ensure_terminal_punctuation(sentences[0])

    words = cleaned.split()
    if len(words) <= max_words:
        return cleaned

    clipped = words[:max_words]
    fillers = {
        "a", "an", "and", "by", "for", "from", "in",
        "of", "on", "or", "the", "through", "to", "with",
    }
    while (
        len(clipped) > 4
        and clipped[-1].strip(" ,.;:!?").lower() in fillers
    ):
        clipped.pop()

    return " ".join(clipped).rstrip(" ,.;:!?") + "."


def _chapter_takeaways(
    chapter: dict[str, Any],
    limit: int = 4,
) -> list[str]:
    """Select one concise content takeaway per section, excluding headings."""

    takeaways: list[str] = []

    for section in chapter.get("sections", []):
        candidate = ""

        for block in section.get("blocks", []):
            candidate = _clean_narration_text(block.get("text", ""))
            if not candidate:
                items = block.get("items", [])
                if items:
                    candidate = _clean_narration_text(items[0])

            if candidate:
                break

        compact = _compact_takeaway(candidate, max_words=12)
        if compact and compact not in takeaways:
            takeaways.append(compact)

        if len(takeaways) >= limit:
            break

    return takeaways


def _count_substantive_paragraphs(
    chapter: dict[str, Any],
) -> int:
    count = 0

    for section in chapter.get(
        "sections",
        [],
    ):
        for block in section.get(
            "blocks",
            [],
        ):
            if (
                block.get("type")
                != "paragraph"
            ):
                continue

            text = block.get(
                "text",
                "",
            ).strip()

            if word_count(text) >= 5:
                count += 1

    return count


def _visual_budget(
    substantive_count: int,
) -> int:
    """Return a chapter-wide visual budget tuned for lesson length.

    Short lessons need a noticeably richer visual rhythm because section
    intros, subtitles, and narration already create plenty of text-only
    moments. Strong short-form visual candidates may therefore all be used.

    Long chapters remain selective so diagrams do not become repetitive.
    The selector still requires a paragraph to score as genuinely visual;
    this function only sets the upper limit.
    """

    if substantive_count <= 0:
        return 0

    if substantive_count <= 5:
        return substantive_count

    if substantive_count <= 8:
        return 4

    if substantive_count <= 12:
        return 5

    if substantive_count <= 20:
        return 6

    return max(
        6,
        min(
            24,
            round(
                substantive_count
                * 0.15
            ),
        ),
    )


def _select_visual_blocks(
    chapter: dict[str, Any],
    budget: int,
) -> set[tuple[int, int]]:
    """Select the strongest visual candidates across the whole chapter.

    Selection happens globally rather than simply accepting the first visual
    candidates. This prevents early paragraphs from consuming the entire
    visual budget.

    Adjacent paragraph blocks in the same section are avoided where possible
    so the video alternates naturally between visual and non-visual teaching.
    """

    if budget <= 0:
        return set()

    candidates: list[
        tuple[int, int, int]
    ] = []

    for section_index, section in enumerate(
        chapter.get(
            "sections",
            [],
        )
    ):
        for block_index, block in enumerate(
            section.get(
                "blocks",
                [],
            )
        ):
            block_type = block.get("type")

            if block_type == "paragraph":
                text = block.get(
                    "text",
                    "",
                ).strip()

                if not text:
                    continue

                score = _visual_score(
                    text
                )

            elif block_type in (
                "bullets",
                "numbered",
            ):
                score = _list_visual_score(
                    section.get("title", ""),
                    block.get("items", []),
                    numbered=(
                        block_type == "numbered"
                    ),
                )

            else:
                continue

            if score >= 4:
                candidates.append(
                    (
                        score,
                        section_index,
                        block_index,
                    )
                )

    candidates.sort(
        key=lambda item: (
            -item[0],
            item[1],
            item[2],
        )
    )

    selected: set[
        tuple[int, int]
    ] = set()

    for (
        _score,
        section_index,
        block_index,
    ) in candidates:
        if len(selected) >= budget:
            break

        previous = (
            section_index,
            block_index - 1,
        )

        following = (
            section_index,
            block_index + 1,
        )

        if (
            previous in selected
            or following in selected
        ):
            continue

        selected.add(
            (
                section_index,
                block_index,
            )
        )

    # If avoiding adjacency leaves us far below the intended budget,
    # fill from remaining strong candidates.
    if len(selected) < budget:
        for (
            _score,
            section_index,
            block_index,
        ) in candidates:
            if len(selected) >= budget:
                break

            key = (
                section_index,
                block_index,
            )

            if key not in selected:
                selected.add(
                    key
                )

    return selected


def _list_visual_score(
    section_title: str,
    items: list[str],
    *,
    numbered: bool,
) -> int:
    if len(items) < 3:
        return 0

    lowered_title = section_title.lower()

    if numbered:
        return 10

    if all(
        re.search(r"\bweb\s*\d+\b", item, re.IGNORECASE)
        for item in items[:3]
    ):
        return 10

    if any(
        marker in lowered_title
        for marker in (
            "evolution",
            "history",
            "process",
            "steps",
            "workflow",
            "lifecycle",
            "journey",
        )
    ):
        return 9

    labelled_items = sum(
        1
        for item in items
        if re.match(r"^[^:]{1,32}:", item.strip())
    )

    if labelled_items >= 3:
        return 8

    if len(items) <= 5:
        return 5

    return 0


def _visual_score(
    text: str,
) -> int:
    """Score how useful a diagram would be for this paragraph."""

    lowered = text.lower()

    if word_count(text) < 5:
        return 0

    score = 0

    if (
        " -> " in text
        or " → " in text
    ):
        score = max(
            score,
            10,
        )

    if _contains_comparison(
        lowered
    ):
        score = max(
            score,
            8,
        )

    if _contains_cause_effect(
        lowered
    ):
        score = max(
            score,
            9,
        )

    roles = _role_labels(
        text
    )

    if len(roles) >= 3:
        score = max(
            score,
            9,
        )

    categories = (
        _category_labels(
            text
        )
    )

    if len(categories) >= 3:
        score = max(
            score,
            8,
        )

    analysis_items = (
        _analysis_labels(
            text
        )
    )

    if len(analysis_items) >= 3:
        score = max(
            score,
            8,
        )

    entities = _entity_nodes(
        text
    )

    if (
        _is_knowledge_cluster(
            lowered
        )
        and len(entities) >= 3
    ):
        score = max(
            score,
            8,
        )

    if (
        _contains_process_flow(
            lowered
        )
        and len(entities) >= 3
    ):
        score = max(
            score,
            9,
        )

    if (
        _contains_relationship(
            lowered
        )
        and len(entities) >= 3
    ):
        score = max(
            score,
            7,
        )

    if (
        "," in text
        and len(
            roles
            + categories
            + analysis_items
        ) >= 4
    ):
        score = max(
            score,
            8,
        )

    return score


def classify_explanation(
    text: str,
    warning_count: int = 0,
) -> tuple[
    SceneType,
    str,
    Diagram | None,
    list[KeyConcept],
]:
    """Choose the teaching representation for one explanatory paragraph."""

    del warning_count

    lowered = text.lower()

    concepts = _extract_concepts(
        text
    )

    # Simple definitions remain primarily textual.
    if _is_definition(
        lowered
    ):
        return (
            SceneType.DEFINITION,
            "definition",
            None,
            concepts,
        )

    # Explicit source-authored flow.
    if (
        " -> " in text
        or " → " in text
    ):
        nodes = _diagram_nodes(
            text
        )

        if len(nodes) >= 2:
            return (
                SceneType
                .VISUAL_EXPLANATION,
                "process-diagram",
                _chain_diagram(
                    "process",
                    nodes,
                ),
                concepts,
            )

    # Comparison.
    if _contains_comparison(
        lowered
    ):
        nodes = (
            _comparison_nodes(
                text
            )
        )

        if len(nodes) >= 2:
            return (
                SceneType
                .VISUAL_EXPLANATION,
                "comparison-diagram",
                Diagram(
                    kind="comparison",
                    nodes=nodes[:2],
                    edges=[],
                ),
                concepts,
            )

    # Cause and effect must be checked before generic relationship rules.
    if _contains_cause_effect(
        lowered
    ):
        nodes = (
            _cause_effect_nodes(
                text
            )
        )

        if len(nodes) >= 2:
            return (
                SceneType
                .VISUAL_EXPLANATION,
                "cause-effect-diagram",
                Diagram(
                    kind="cause-effect",
                    nodes=nodes[:2],
                    edges=[
                        DiagramEdge(
                            from_id=(
                                nodes[0].id
                            ),
                            to=(
                                nodes[1].id
                            ),
                        )
                    ],
                ),
                concepts,
            )

    # Job-role clusters:
    #
    # WEB3 PROJECT
    #   ├─ DEVELOPERS
    #   ├─ DESIGNERS
    #   ├─ MARKETERS
    #   └─ ANALYSTS
    role_labels = (
        _role_labels(
            text
        )
    )

    if len(role_labels) >= 3:
        center = (
            _central_subject_label(
                text,
                fallback="WEB3 PROJECT",
            )
        )

        return (
            SceneType
            .VISUAL_EXPLANATION,
            "relationship-diagram",
            _hub_diagram(
                center,
                role_labels[:4],
            ),
            concepts,
        )

    # Category/talent clusters.
    category_labels = (
        _category_labels(
            text
        )
    )

    if len(category_labels) >= 3:
        center = (
            _central_subject_label(
                text,
                fallback="WEB3 ECOSYSTEM",
            )
        )

        return (
            SceneType
            .VISUAL_EXPLANATION,
            "relationship-diagram",
            _hub_diagram(
                center,
                category_labels[:4],
            ),
            concepts,
        )

    # Analytics / research activity cluster.
    analysis_labels = (
        _analysis_labels(
            text
        )
    )

    if len(analysis_labels) >= 3:
        return (
            SceneType
            .VISUAL_EXPLANATION,
            "relationship-diagram",
            _hub_diagram(
                "ON-CHAIN ANALYSIS",
                analysis_labels[:4],
            ),
            concepts,
        )

    entities = _entity_nodes(
        text
    )

    # Statements such as:
    #
    # "A frontend developer needs to understand wallets,
    # transaction signing, smart contracts and networks."
    #
    # are concept clusters, not chronological processes.
    if (
        _is_knowledge_cluster(
            lowered
        )
        and len(entities) >= 3
    ):
        center = (
            _central_subject_label(
                text,
                fallback="CORE KNOWLEDGE",
            )
        )

        satellites = [
            node.label
            for node
            in entities
            if node.label != center
        ]

        if len(satellites) >= 2:
            return (
                SceneType
                .VISUAL_EXPLANATION,
                "relationship-diagram",
                _hub_diagram(
                    center,
                    satellites[:4],
                ),
                concepts,
            )

    # Input -> processing -> output.
    if (
        "input" in lowered
        and "output" in lowered
        and any(
            marker in lowered
            for marker in (
                "process",
                "model",
                "system",
                "receives",
                "produces",
                "returns",
                "transforms",
            )
        )
    ):
        nodes = (
            _ordered_process_nodes(
                text
            )
        )

        if len(nodes) < 3:
            nodes = [
                DiagramNode(
                    id="node-1",
                    label="INPUT",
                ),
                DiagramNode(
                    id="node-2",
                    label="PROCESS",
                ),
                DiagramNode(
                    id="node-3",
                    label="OUTPUT",
                ),
            ]

        return (
            SceneType
            .VISUAL_EXPLANATION,
            (
                "input-process-"
                "output-diagram"
            ),
            _chain_diagram(
                "input-process-output",
                nodes[:5],
            ),
            concepts,
        )

    # Genuine flow/process. This deliberately requires actual movement or
    # sequential language; merely mentioning transactions is not enough.
    if (
        _contains_process_flow(
            lowered
        )
        and len(entities) >= 3
    ):
        nodes = (
            _ordered_process_nodes(
                text
            )
        )

        if len(nodes) >= 3:
            return (
                SceneType
                .VISUAL_EXPLANATION,
                "process-diagram",
                _chain_diagram(
                    "process",
                    nodes[:5],
                ),
                concepts,
            )

    # Generic multi-component relationship.
    if (
        _contains_relationship(
            lowered
        )
        and len(entities) >= 3
    ):
        center = (
            _central_subject_label(
                text,
                fallback=(
                    entities[0].label
                ),
            )
        )

        satellites = [
            node.label
            for node
            in entities
            if node.label != center
        ]

        if len(satellites) >= 2:
            return (
                SceneType
                .VISUAL_EXPLANATION,
                "relationship-diagram",
                _hub_diagram(
                    center,
                    satellites[:4],
                ),
                concepts,
            )

    return (
        SceneType.EXPLANATION,
        "none",
        None,
        concepts,
    )


def _is_definition(
    lowered: str,
) -> bool:
    return any(
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
    )


def _contains_comparison(
    lowered: str,
) -> bool:
    padded = f" {lowered} "

    if (
        "custodial" in lowered
        and (
            "non-custodial" in lowered
            or "non custodial" in lowered
            or "noncustodial" in lowered
        )
    ):
        return True

    return any(
        marker in padded
        for marker in (
            " vs ",
            " versus ",
            " compared to ",
            " compared with ",
            " difference between ",
            " differs from ",
            " different from ",
            " unlike ",
            " rather than ",
            " on the other hand ",
            " in contrast ",
            " whereas ",
            " while ",
        )
    )


def _contains_cause_effect(
    lowered: str,
) -> bool:
    padded = f" {lowered} "

    return any(
        marker in padded
        for marker in (
            " causes ",
            " cause ",
            " caused by ",
            " leads to ",
            " lead to ",
            " can lead to ",
            " resulting in ",
            " results in ",
            " results from ",
            " triggers ",
            " produces ",
            " because ",
            " therefore ",
            " consequently ",
            " if ",
        )
    )


def _contains_process_flow(
    lowered: str,
) -> bool:
    padded = (
        f" {lowered} "
    )

    return any(
        marker in padded
        for marker in (
            " first ",
            " then ",
            " next ",
            " finally ",
            " sends ",
            " send ",
            " sent to ",
            " transfers ",
            " transfer ",
            " routes ",
            " route ",
            " flows to ",
            " flows through ",
            " moves to ",
            " moves through ",
            " passes to ",
            " passes through ",
            " connects to ",
            " connects a ",
            " prepares ",
            " prepare ",
            " signs ",
            " sign ",
            " validates ",
            " validate ",
            " records ",
            " record ",
            " broadcasts ",
            " broadcast ",
            " submitted to ",
            " forwarded to ",
            " received by ",
        )
    )


def _contains_relationship(
    lowered: str,
) -> bool:
    padded = (
        f" {lowered} "
    )

    return any(
        marker in padded
        for marker in (
            " connects ",
            " connected ",
            " interacts ",
            " interact ",
            " interacting ",
            " interaction ",
            " communicates ",
            " works with ",
            " depends on ",
            " relies on ",
            " ecosystem ",
            " consists of ",
            " includes ",
            " combines ",
        )
    )


def _is_knowledge_cluster(
    lowered: str,
) -> bool:
    return any(
        marker in lowered
        for marker in (
            "needs to understand",
            "need to understand",
            "must understand",
            "needs knowledge of",
            "requires knowledge",
            "needs experience with",
            "requires experience",
            "needs skills in",
            "requires skills",
        )
    )


def _extract_concepts(
    text: str,
) -> list[KeyConcept]:
    words = [
        word.strip(
            " ,.;:()"
        )
        for word
        in re.split(
            r"\s+",
            text,
        )
    ]

    candidates = [
        word
        for word in words
        if (
            word
            and len(word) >= 4
            and word.lower()
            not in _STOPWORDS
        )
    ]

    seen: set[str] = set()

    concepts: list[
        KeyConcept
    ] = []

    for word in candidates[:4]:
        key = word.lower()

        if key in seen:
            continue

        seen.add(
            key
        )

        importance = (
            Importance.HIGH
            if key in _HIGH_TERMS
            else (
                Importance.MEDIUM
                if len(concepts) < 3
                else Importance.LOW
            )
        )

        concepts.append(
            KeyConcept(
                id=(
                    f"c"
                    f"{len(concepts) + 1}"
                ),
                text=(
                    word.upper()[:24]
                ),
                importance=importance,
            )
        )

    return concepts


def _diagram_nodes(
    text: str,
    count: int | None = None,
) -> list[DiagramNode]:
    for marker in (
        " → ",
        " -> ",
    ):
        if marker not in text:
            continue

        parts = [
            part.strip()
            for part
            in text.split(
                marker
            )
            if part.strip()
        ][:5]

        nodes: list[
            DiagramNode
        ] = []

        for i, part in enumerate(
            parts
        ):
            words = part.split()

            if i == 0:
                label = (
                    words[-1]
                )

            elif (
                i
                == len(parts) - 1
            ):
                label = (
                    words[0]
                )

            else:
                label = (
                    " ".join(words)
                    if len(words) <= 3
                    else words[-1]
                )

            label = (
                label
                .strip(
                    " ,.;:()"
                )
                .upper()[:22]
            )

            nodes.append(
                DiagramNode(
                    id=(
                        f"node-"
                        f"{len(nodes) + 1}"
                    ),
                    label=label,
                )
            )

        return nodes

    entities = _entity_nodes(
        text
    )

    if count is not None:
        entities = (
            entities[:count]
        )

    return entities


def _comparison_nodes(
    text: str,
) -> list[DiagramNode]:
    lowered = text.lower()

    if (
        "custodial" in lowered
        and (
            "non-custodial" in lowered
            or "non custodial" in lowered
            or "noncustodial" in lowered
        )
    ):
        return [
            DiagramNode(
                id="node-1",
                label="CUSTODIAL WALLET",
            ),
            DiagramNode(
                id="node-2",
                label="NON-CUSTODIAL WALLET",
            ),
        ]

    markers = (
        " vs ",
        " versus ",
        " compared to ",
        " compared with ",
        " difference between ",
        " differs from ",
        " different from ",
        " unlike ",
        " rather than ",
    )

    for marker in markers:
        position = lowered.find(
            marker
        )

        if position < 0:
            continue

        left = text[
            :position
        ]

        right = text[
            position
            + len(marker):
        ]

        left_label = (
            _semantic_label(
                left,
                prefer_end=True,
            )
        )

        right_label = (
            _semantic_label(
                right,
                prefer_end=False,
            )
        )

        if (
            left_label
            and right_label
        ):
            return [
                DiagramNode(
                    id="node-1",
                    label=left_label,
                ),
                DiagramNode(
                    id="node-2",
                    label=right_label,
                ),
            ]

    return _entity_nodes(
        text
    )[:2]


def _cause_effect_nodes(
    text: str,
) -> list[DiagramNode]:
    lowered = text.lower()

    if (
        "private key" in lowered
        and any(
            marker in lowered
            for marker in (
                "exposes",
                "exposed",
                "leaks",
                "leaked",
                "reveals",
                "revealed",
                "shares",
                "shared",
            )
        )
        and any(
            marker in lowered
            for marker in (
                "attacker",
                "unauthorized",
                "gain access",
                "gains access",
            )
        )
    ):
        return [
            DiagramNode(
                id="node-1",
                label="EXPOSED PRIVATE KEY",
            ),
            DiagramNode(
                id="node-2",
                label="UNAUTHORIZED WALLET ACCESS",
            ),
        ]

    if (
        "smart contract" in lowered
        and "mistake" in lowered
        and "financial loss" in lowered
    ):
        return [
            DiagramNode(
                id="node-1",
                label=(
                    "SMART CONTRACT "
                    "MISTAKE"
                ),
            ),
            DiagramNode(
                id="node-2",
                label=(
                    "FINANCIAL LOSS"
                ),
            ),
        ]

    if (
        "infrastructure" in lowered
        and any(
            term in lowered
            for term in (
                "fails",
                "failure",
                "failed",
            )
        )
    ):
        return [
            DiagramNode(
                id="node-1",
                label=(
                    "INFRASTRUCTURE "
                    "FAILURE"
                ),
            ),
            DiagramNode(
                id="node-2",
                label=(
                    "APP PROBLEMS"
                ),
            ),
        ]

    pattern = re.compile(
        (
            r"\bcan lead to\b"
            r"|\bleads to\b"
            r"|\blead to\b"
            r"|\bcauses\b"
            r"|\bcause\b"
            r"|\bresults in\b"
            r"|\bresulting in\b"
            r"|\btriggers\b"
            r"|\bproduces\b"
        ),
        flags=re.IGNORECASE,
    )

    match = pattern.search(
        text
    )

    if match:
        left = text[
            :match.start()
        ]

        right = text[
            match.end():
        ]

        left_label = (
            _semantic_label(
                left,
                prefer_end=True,
            )
        )

        right_label = (
            _semantic_label(
                right,
                prefer_end=False,
            )
        )

        if (
            left_label
            and right_label
        ):
            return [
                DiagramNode(
                    id="node-1",
                    label=left_label,
                ),
                DiagramNode(
                    id="node-2",
                    label=right_label,
                ),
            ]

    # Basic if/then style relationship.
    if lowered.startswith(
        "if "
    ):
        parts = re.split(
            r",\s*",
            text,
            maxsplit=1,
        )

        if len(parts) == 2:
            return [
                DiagramNode(
                    id="node-1",
                    label=(
                        _semantic_label(
                            parts[0][3:],
                            prefer_end=True,
                        )
                        or "CONDITION"
                    ),
                ),
                DiagramNode(
                    id="node-2",
                    label=(
                        _semantic_label(
                            parts[1],
                            prefer_end=False,
                        )
                        or "RESULT"
                    ),
                ),
            ]

    entities = _entity_nodes(
        text
    )

    if len(entities) >= 2:
        return entities[:2]

    return []


def _ordered_process_nodes(
    text: str,
) -> list[DiagramNode]:
    """Extract process components in source order.

    This is intentionally only used after strong process language has already
    been detected. Merely mentioning a wallet, user and protocol does not make
    a sentence a process.
    """

    entities = (
        _entity_nodes(
            text
        )
    )

    return [
        DiagramNode(
            id=f"node-{i + 1}",
            label=node.label,
        )
        for i, node
        in enumerate(
            entities[:5]
        )
    ]


def _entity_nodes(
    text: str,
) -> list[DiagramNode]:
    matches: list[
        tuple[int, str]
    ] = []

    patterns = (
        (
            r"\bnon[- ]custodial wallet(?:s)?\b",
            "NON-CUSTODIAL WALLET",
        ),
        (
            r"\bcustodial wallet(?:s)?\b",
            "CUSTODIAL WALLET",
        ),
        (
            r"\bprivate key(?:s)?\b",
            "PRIVATE KEY",
        ),
        (
            r"\battacker(?:s)?\b",
            "ATTACKER",
        ),
        (
            r"\basset(?:s)?\b",
            "ASSETS",
        ),
        (
            r"\bdecentralized application(?:s)?\b",
            "DAPP",
        ),
        (
            r"\bdapp(?:s)?\b",
            "DAPP",
        ),
        (
            r"\bdecentralized exchange\b",
            "EXCHANGE",
        ),
        (
            r"\bsmart contract(?:s)?\b",
            "SMART CONTRACT",
        ),
        (
            r"\bliquidity pool(?:s)?\b",
            "LIQUIDITY POOL",
        ),
        (
            r"\bcommunity manager(?:s)?\b",
            "COMMUNITY MANAGER",
        ),
        (
            r"\bproject manager(?:s)?\b",
            "PROJECT MANAGER",
        ),
        (
            r"\bfrontend developer(?:s)?\b",
            "FRONTEND DEV",
        ),
        (
            r"\buser interface\b",
            "USER INTERFACE",
        ),
        (
            r"\bblockchain(?:s)?\b",
            "BLOCKCHAIN",
        ),
        (
            r"\bprotocol(?:s)?\b",
            "PROTOCOL",
        ),
        (
            r"\bwallet(?:s)?\b",
            "WALLET",
        ),
        (
            r"\btransaction(?:s)?\b",
            "TRANSACTION",
        ),
        (
            r"\bnetwork(?:s)?\b",
            "NETWORK",
        ),
        (
            r"\binfrastructure\b",
            "INFRASTRUCTURE",
        ),
        (
            r"\bapplication(?:s)?\b",
            "APPLICATION",
        ),
        (
            r"\bfrontend\b",
            "FRONTEND",
        ),
        (
            r"\btoken(?:s)?\b",
            "TOKEN",
        ),
        (
            r"\bexchange(?:s)?\b",
            "EXCHANGE",
        ),
        (
            r"\bborrower(?:s)?\b",
            "BORROWER",
        ),
        (
            r"\blender(?:s)?\b",
            "LENDER",
        ),
        (
            r"\bclient(?:s)?\b",
            "CLIENT",
        ),
        (
            r"\bserver(?:s)?\b",
            "SERVER",
        ),
        (
            r"\bdatabase(?:s)?\b",
            "DATABASE",
        ),
        (
            r"\bAPI(?:s)?\b",
            "API",
        ),
        (
            r"\buser(?:s)?\b",
            "USER",
        ),
        (
            r"\binput(?:s)?\b",
            "INPUT",
        ),
        (
            r"\bdata\b",
            "DATA",
        ),
        (
            r"\bmodel(?:s)?\b",
            "MODEL",
        ),
        (
            r"\bprediction(?:s)?\b",
            "PREDICTION",
        ),
        (
            r"\boutput(?:s)?\b",
            "OUTPUT",
        ),
    )

    for pattern, label in patterns:
        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if match:
            matches.append(
                (
                    match.start(),
                    label,
                )
            )

    matches.sort(
        key=lambda item: (
            item[0]
        )
    )

    seen: set[str] = set()

    labels: list[str] = []

    for _, label in matches:
        if label in seen:
            continue

        # Avoid redundant generic entities when a specific entity is already
        # present.
        if (
            label == "USER"
            and "USER INTERFACE"
            in seen
        ):
            continue

        if (
            label == "FRONTEND"
            and "FRONTEND DEV"
            in seen
        ):
            continue

        seen.add(
            label
        )

        labels.append(
            label
        )

    return [
        DiagramNode(
            id=f"node-{i + 1}",
            label=label,
        )
        for i, label
        in enumerate(
            labels[:6]
        )
    ]


def _role_labels(
    text: str,
) -> list[str]:
    patterns = (
        (
            r"\bsmart contract developer(?:s)?\b",
            "SMART CONTRACT DEV",
        ),
        (
            r"\bfrontend developer(?:s)?\b",
            "FRONTEND DEV",
        ),
        (
            r"\bblockchain engineer(?:s)?\b",
            "BLOCKCHAIN ENGINEER",
        ),
        (
            r"\binfrastructure engineer(?:s)?\b",
            "INFRA ENGINEER",
        ),
        (
            r"\bcommunity manager(?:s)?\b",
            "COMMUNITY MANAGER",
        ),
        (
            r"\bproject manager(?:s)?\b",
            "PROJECT MANAGER",
        ),
        (
            r"\bproduct manager(?:s)?\b",
            "PRODUCT MANAGER",
        ),
        (
            r"\bdeveloper(?:s)?\b",
            "DEVELOPERS",
        ),
        (
            r"\bdesigner(?:s)?\b",
            "DESIGNERS",
        ),
        (
            r"\bmarketer(?:s)?\b",
            "MARKETERS",
        ),
        (
            r"\banalyst(?:s)?\b",
            "ANALYSTS",
        ),
        (
            r"\bwriter(?:s)?\b",
            "WRITERS",
        ),
        (
            r"\bresearcher(?:s)?\b",
            "RESEARCHERS",
        ),
        (
            r"\beducator(?:s)?\b",
            "EDUCATORS",
        ),
        (
            r"\bcontent creator(?:s)?\b",
            "CONTENT CREATORS",
        ),
    )

    return _ordered_labels(
        text,
        patterns,
    )


def _category_labels(
    text: str,
) -> list[str]:
    patterns = (
        (
            r"\bnon[- ]technical\b",
            "NON-TECHNICAL",
        ),
        (
            r"\btechnical\b",
            "TECHNICAL",
        ),
        (
            r"\bcreative\b",
            "CREATIVE",
        ),
        (
            r"\banalytical\b",
            "ANALYTICAL",
        ),
        (
            r"\boperational\b",
            "OPERATIONAL",
        ),
        (
            r"\bcommunication[- ]based\b",
            "COMMUNICATION",
        ),
        (
            r"\bcommunication\b",
            "COMMUNICATION",
        ),
        (
            r"\bmarketing\b",
            "MARKETING",
        ),
        (
            r"\bdesign\b",
            "DESIGN",
        ),
        (
            r"\bresearch\b",
            "RESEARCH",
        ),
        (
            r"\bcommunity\b",
            "COMMUNITY",
        ),
        (
            r"\bengineering\b",
            "ENGINEERING",
        ),
        (
            r"\bproduct\b",
            "PRODUCT",
        ),
    )

    return _ordered_labels(
        text,
        patterns,
    )


def _analysis_labels(
    text: str,
) -> list[str]:
    lowered = text.lower()

    analysis_verbs = (
        "track",
        "monitor",
        "study",
        "analyze",
        "analyse",
        "evaluate",
    )

    if not any(
        verb in lowered
        for verb
        in analysis_verbs
    ):
        return []

    patterns = (
        (
            r"\bwallet behavior\b",
            "WALLET BEHAVIOR",
        ),
        (
            r"\blarge transfers\b",
            "LARGE TRANSFERS",
        ),
        (
            r"\buser activity\b",
            "USER ACTIVITY",
        ),
        (
            r"\bliquidity\b",
            "LIQUIDITY",
        ),
        (
            r"\bprotocol(?:s)?\b",
            "PROTOCOL VALUE",
        ),
        (
            r"\btransaction(?:s)?\b",
            "TRANSACTIONS",
        ),
        (
            r"\bvolume\b",
            "VOLUME",
        ),
    )

    return _ordered_labels(
        text,
        patterns,
    )


def _ordered_labels(
    text: str,
    patterns: tuple[
        tuple[str, str],
        ...,
    ],
) -> list[str]:
    matches: list[
        tuple[int, str]
    ] = []

    for pattern, label in patterns:
        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if match:
            matches.append(
                (
                    match.start(),
                    label,
                )
            )

    matches.sort(
        key=lambda item: (
            item[0]
        )
    )

    labels: list[str] = []

    seen: set[str] = set()

    for _, label in matches:
        if label in seen:
            continue

        # Specific roles replace generic role labels.
        if (
            label == "DEVELOPERS"
            and any(
                existing.endswith(
                    "DEV"
                )
                for existing
                in seen
            )
        ):
            continue

        seen.add(
            label
        )

        labels.append(
            label
        )

    return labels


def _central_subject_label(
    text: str,
    fallback: str,
) -> str:
    lowered = text.lower()

    candidates = (
        (
            "frontend web3 developer",
            "FRONTEND DEV",
        ),
        (
            "frontend developer",
            "FRONTEND DEV",
        ),
        (
            "smart contract developer",
            "SMART CONTRACT DEV",
        ),
        (
            "web3 project",
            "WEB3 PROJECT",
        ),
        (
            "web3 ecosystem",
            "WEB3 ECOSYSTEM",
        ),
        (
            "ecosystem",
            "ECOSYSTEM",
        ),
        (
            "web3 careers",
            "WEB3 CAREERS",
        ),
        (
            "web3 career",
            "WEB3 CAREERS",
        ),
        (
            "smart contract",
            "SMART CONTRACT",
        ),
        (
            "application",
            "APPLICATION",
        ),
        (
            "frontend",
            "FRONTEND",
        ),
    )

    for phrase, label in candidates:
        if phrase in lowered:
            return label

    return fallback


def _semantic_label(
    phrase: str,
    prefer_end: bool,
) -> str:
    lowered = phrase.lower()

    known = (
        (
            "unauthorized wallet access",
            "UNAUTHORIZED WALLET ACCESS",
        ),
        (
            "private key",
            "PRIVATE KEY",
        ),
        (
            "attacker",
            "ATTACKER",
        ),
        (
            "non-custodial wallet",
            "NON-CUSTODIAL WALLET",
        ),
        (
            "custodial wallet",
            "CUSTODIAL WALLET",
        ),
        (
            "financial loss",
            "FINANCIAL LOSS",
        ),
        (
            "smart contract",
            "SMART CONTRACT",
        ),
        (
            "liquidity pool",
            "LIQUIDITY POOL",
        ),
        (
            "user funds",
            "USER FUNDS",
        ),
        (
            "digital assets",
            "DIGITAL ASSETS",
        ),
        (
            "failed transactions",
            "FAILED TRANSACTIONS",
        ),
        (
            "pending transactions",
            "PENDING TRANSACTIONS",
        ),
        (
            "blockchain",
            "BLOCKCHAIN",
        ),
        (
            "wallet",
            "WALLET",
        ),
        (
            "protocol",
            "PROTOCOL",
        ),
        (
            "network",
            "NETWORK",
        ),
        (
            "transaction",
            "TRANSACTION",
        ),
        (
            "user",
            "USER",
        ),
    )

    for needle, label in known:
        if needle in lowered:
            return label

    words = [
        re.sub(
            r"[^A-Za-z0-9'-]",
            "",
            word,
        )
        for word
        in phrase.split()
    ]

    words = [
        word
        for word in words
        if (
            word
            and word.lower()
            not in _STOPWORDS
        )
    ]

    if not words:
        return ""

    selected = (
        words[-3:]
        if prefer_end
        else words[:3]
    )

    return (
        " ".join(
            selected
        )
        .upper()[:28]
    )


def _hub_diagram(
    center_label: str,
    satellite_labels: list[str],
) -> Diagram:
    labels: list[str] = [
        center_label
    ]

    for label in satellite_labels:
        if (
            label
            and label not in labels
        ):
            labels.append(
                label
            )

    labels = labels[:5]

    nodes = [
        DiagramNode(
            id=f"node-{i + 1}",
            label=label,
        )
        for i, label
        in enumerate(labels)
    ]

    return Diagram(
        kind="relationship",
        nodes=nodes,
        edges=[
            DiagramEdge(
                from_id=nodes[0].id,
                to=node.id,
            )
            for node
            in nodes[1:]
        ],
    )


def _list_item_label(item: str) -> str:
    cleaned = _clean_narration_text(item).strip('"')

    web_generation = re.search(
        r"\b(web\s*\d+)\b",
        cleaned,
        re.IGNORECASE,
    )

    if web_generation:
        return re.sub(
            r"\s+",
            "",
            web_generation.group(1),
        ).upper()

    if ":" in cleaned:
        prefix = cleaned.split(":", 1)[0]

        if 1 <= len(prefix.split()) <= 4:
            return prefix.upper()[:28]

    cleaned = re.sub(
        r"^(?:then|next|finally|but wait)\b[,! ]*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )

    return _concept_text(cleaned) or "POINT"


def _diagram_for_list(
    section_title: str,
    items: list[str],
    *,
    numbered: bool,
) -> Diagram | None:
    labels: list[str] = []

    for item in items[:5]:
        label = _list_item_label(item)

        if label not in labels:
            labels.append(label)

    if len(labels) < 3:
        return None

    nodes = [
        DiagramNode(
            id=f"node-{index + 1}",
            label=label,
        )
        for index, label in enumerate(labels)
    ]

    lowered_title = section_title.lower()
    is_sequence = (
        numbered
        or all(
            re.fullmatch(r"WEB\d+", label)
            for label in labels[:3]
        )
        or any(
            marker in lowered_title
            for marker in (
                "evolution",
                "history",
                "process",
                "steps",
                "workflow",
                "lifecycle",
                "journey",
            )
        )
    )

    if is_sequence:
        return _chain_diagram(
            "process",
            nodes,
        )

    center = (
        _concept_text(section_title)
        if section_title.strip()
        else "KEY POINTS"
    )

    return _hub_diagram(
        center,
        labels,
    )


def _chain_diagram(
    kind: str,
    nodes: list[DiagramNode],
) -> Diagram:
    normalized = [
        DiagramNode(
            id=f"node-{i + 1}",
            label=node.label,
        )
        for i, node
        in enumerate(nodes)
    ]

    return Diagram(
        kind=kind,
        nodes=normalized,
        edges=[
            DiagramEdge(
                from_id=(
                    normalized[i].id
                ),
                to=(
                    normalized[i + 1].id
                ),
            )
            for i
            in range(
                len(normalized) - 1
            )
        ],
    )


def _concept_text(
    item: str,
) -> str:
    words = [
        word
        for word
        in re.split(
            r"\W+",
            item,
        )
        if word
    ]

    return (
        " ".join(
            words[:3]
        )
        .upper()[:32]
    )


def _scene_title(
    text: str,
) -> str:
    sentences = (
        split_sentences(
            text
        )
    )

    if not sentences:
        return (
            text[:80]
            or "Scene"
        )

    sentence = (
        sentences[0]
    )

    if len(sentence) <= 80:
        return sentence

    return (
        sentence[:77]
        + "..."
    )


_STOPWORDS = frozenset(
    {
        "this",
        "that",
        "with",
        "from",
        "into",
        "about",
        "which",
        "where",
        "there",
        "their",
        "these",
        "those",
        "what",
        "when",
        "will",
        "would",
        "should",
        "could",
        "does",
        "doing",
        "being",
        "have",
        "has",
        "having",
        "more",
        "most",
        "than",
        "then",
        "they",
        "them",
        "were",
        "been",
        "each",
        "using",
        "used",
        "also",
        "such",
        "through",
        "while",
        "because",
        "very",
        "only",
        "can",
        "may",
        "might",
        "must",
        "need",
        "needs",
        "make",
        "makes",
    }
)


_HIGH_TERMS = frozenset(
    {
        "machine",
        "learning",
        "data",
        "prediction",
        "algorithm",
        "model",
        "network",
        "neural",
        "definition",
        "process",
        "input",
        "output",
        "wallet",
        "blockchain",
        "protocol",
        "transaction",
        "contract",
        "token",
        "liquidity",
        "security",
    }
)


def build_provider(
    name: str | None = None,
) -> AIProvider:
    provider_name = (
        name
        or os.environ.get(
            "AI_PROVIDER",
            "mock",
        )
    ).lower()

    if provider_name == "openai":
        return OpenAIProvider()

    return MockProvider()
