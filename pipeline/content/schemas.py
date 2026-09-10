"""Strongly typed schemas for every stage of the pipeline.

The boundary between Python and Remotion is structured JSON built from these
models. Scene JSON is data only - it is never executed as code.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator


class SourceBlockType(str, Enum):
    PARAGRAPH = "paragraph"
    IMAGE = "image"
    BULLETS = "bullets"
    NUMBERED = "numbered"


class SourceBlock(BaseModel):
    """Neutral, order-preserving representation of one DOCX block."""

    type: SourceBlockType
    text: str = ""
    items: list[str] = Field(default_factory=list)
    path: Optional[str] = None
    warnings: list[str] = Field(default_factory=list)


class Section(BaseModel):
    """A Heading 2 section inside a chapter."""

    title: str
    blocks: list[SourceBlock] = Field(default_factory=list)


class Chapter(BaseModel):
    """One Heading 1 chapter - becomes exactly one output video."""

    course_title: str
    chapter_number: int
    title: str
    slug: str = ""
    sections: list[Section] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class Course(BaseModel):
    """Full parsed document: ordered chapters under a course title."""

    title: str
    chapters: list[Chapter] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class Importance(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class KeyConcept(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9_-]+$")
    text: str
    importance: Importance = Importance.LOW


class VisualActionType(str, Enum):
    REVEAL = "reveal"
    HANDWRITE = "handwrite"
    UNDERLINE = "underline"
    CIRCLE = "circle"
    DRAW_ARROW = "drawArrow"
    DRAW_BOX = "drawBox"
    HIGHLIGHT = "highlight"
    CROSS_OUT = "crossOut"
    CONNECT = "connect"
    ZOOM_FOCUS = "zoomFocus"
    BUILD_DIAGRAM = "buildDiagram"
    COMPARE = "compare"


class VisualAction(BaseModel):
    """A teaching motion. `type` must be from the approved library."""

    type: VisualActionType
    startSec: float = Field(ge=0)
    durationSec: float = Field(default=0.8, gt=0)
    target: Optional[str] = None
    from_id: Optional[str] = Field(default=None, alias="from")
    to: Optional[str] = None
    emphasis: bool = False

    model_config = {"populate_by_name": True}

    @field_validator("durationSec")
    @classmethod
    def duration_not_zero(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("durationSec must be positive")
        return v


class DiagramNode(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9_-]+$")
    label: str


class DiagramEdge(BaseModel):
    from_id: str = Field(alias="from")
    to: str

    model_config = {"populate_by_name": True}


class Diagram(BaseModel):
    kind: Literal["process", "relationship", "comparison", "input-process-output", "cause-effect"]
    nodes: list[DiagramNode]
    edges: list[DiagramEdge] = Field(default_factory=list)

    @model_validator(mode="after")
    def _edges_reference_existing_nodes(self) -> "Diagram":
        node_ids = {node.id for node in self.nodes}
        for edge in self.edges:
            if edge.from_id not in node_ids:
                raise ValueError(f"diagram edge references unknown 'from' node '{edge.from_id}'")
            if edge.to not in node_ids:
                raise ValueError(f"diagram edge references unknown 'to' node '{edge.to}'")
        return self


class SubtitleCue(BaseModel):
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    text: str

    @field_validator("end")
    @classmethod
    def end_after_start(cls, v: float, info: Any) -> float:
        start = info.data.get("start")
        if start is not None and v <= start:
            raise ValueError("end must be greater than start")
        return v


class AudioMetadata(BaseModel):
    path: str
    durationSeconds: float = Field(gt=0)
    wordTimestampsPath: Optional[str] = None


class SceneType(str, Enum):
    CHAPTER_INTRO = "chapterIntro"
    SECTION_INTRO = "sectionIntro"
    EXPLANATION = "explanation"
    DEFINITION = "definition"
    BULLET_LIST = "bulletList"
    IMAGE_EXPLANATION = "imageExplanation"
    VISUAL_EXPLANATION = "visualExplanation"
    CHAPTER_SUMMARY = "chapterSummary"


SCENE_TYPES = frozenset(t.value for t in SceneType)
VISUAL_ACTION_TYPES = frozenset(t.value for t in VisualActionType)


class Scene(BaseModel):
    """One teachable unit. All timing is seconds; Remotion converts to frames."""

    id: str = Field(pattern=r"^scene-\d{3,}$")
    type: SceneType
    title: str
    screenText: str = ""
    voiceover: str = ""
    keyConcepts: list[KeyConcept] = Field(default_factory=list)
    visualStrategy: str = "none"
    visualActions: list[VisualAction] = Field(default_factory=list)
    image: Optional[str] = None
    diagram: Optional[Diagram] = None
    audio: Optional[AudioMetadata] = None
    subtitles: list[SubtitleCue] = Field(default_factory=list)
    durationSeconds: Optional[float] = None
    sourceText: str = ""
    warnings: list[str] = Field(default_factory=list)


class ChapterPlan(BaseModel):
    """Everything Remotion needs to render one chapter video."""

    courseTitle: str
    chapterNumber: int
    chapterTitle: str
    fps: int
    width: int
    height: int
    scenes: list[Scene]
    totalDurationSeconds: float = 0.0


class RenderManifest(BaseModel):
    chapterNumber: int
    chapterTitle: str
    sceneCount: int
    durationSeconds: float
    sceneFiles: list[str] = Field(default_factory=list)
    outputPath: Optional[str] = None


class ValidationIssue(BaseModel):
    level: Literal["error", "warning"]
    code: str
    message: str
    sceneId: Optional[str] = None


class ValidationResult(BaseModel):
    chapterNumber: int
    chapterTitle: str
    ok: bool
    errors: list[ValidationIssue] = Field(default_factory=list)
    warnings: list[ValidationIssue] = Field(default_factory=list)


class CacheRecord(BaseModel):
    key: str
    value: Any
    created: str
    source_hash: str


SCENE_JSON_KEYS = set(Scene.model_fields.keys())


def scene_from_dict(data: dict[str, Any]) -> Scene:
    """Parse scene JSON with strict schema validation (fatal on failure)."""

    return Scene.model_validate(data)
