"""Central configuration for the Course Video Generator.

Values can be overridden through environment variables so the same codebase
runs in demo mode and in a configured production setup.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return float(raw)


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def _env_str(name: str, default: str) -> str:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip()


STYLES = ("studio", "dark", "playful", "minimal", "cinema")


ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Brand:
    """All visual brand identity lives here, never in scene components."""

    name: str = "Course Video Generator"
    background: str = "#F5F5F5"
    foreground: str = "#111111"
    muted: str = "#6B6B6B"
    accent: str = "#FF5A36"
    font_family: str = "Inter, 'Segoe UI', Arial, sans-serif"


@dataclass(frozen=True)
class Paths:
    root: Path = ROOT
    input: Path = field(default_factory=lambda: ROOT / "input")
    assets: Path = field(default_factory=lambda: ROOT / "assets")
    images: Path = field(default_factory=lambda: ROOT / "assets" / "images")
    audio: Path = field(default_factory=lambda: ROOT / "assets" / "audio")
    generated: Path = field(default_factory=lambda: ROOT / "generated")
    source: Path = field(default_factory=lambda: ROOT / "generated" / "source")
    chapters: Path = field(default_factory=lambda: ROOT / "generated" / "chapters")
    scenes: Path = field(default_factory=lambda: ROOT / "generated" / "scenes")
    subtitles: Path = field(default_factory=lambda: ROOT / "generated" / "subtitles")
    manifests: Path = field(default_factory=lambda: ROOT / "generated" / "manifests")
    output: Path = field(default_factory=lambda: ROOT / "output" / "videos")
    cache: Path = field(default_factory=lambda: ROOT / "cache")
    logs: Path = field(default_factory=lambda: ROOT / "logs")
    remotion: Path = field(default_factory=lambda: ROOT / "remotion")

    def ensure(self) -> None:
        for path in (
            self.input,
            self.images,
            self.audio,
            self.generated,
            self.source,
            self.chapters,
            self.scenes,
            self.subtitles,
            self.manifests,
            self.output,
            self.cache,
            self.logs,
        ):
            path.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class Config:
    """Single source of truth for pipeline and render settings."""

    fps: int = field(default_factory=lambda: _env_int("FPS", 30))
    width: int = field(default_factory=lambda: _env_int("VIDEO_WIDTH", 1920))
    height: int = field(default_factory=lambda: _env_int("VIDEO_HEIGHT", 1080))
    codec: str = field(default_factory=lambda: _env_str("CODEC", "h264"))
    style: str = field(default_factory=lambda: _env_str("STYLE", "studio"))
    ai_provider: str = field(default_factory=lambda: _env_str("AI_PROVIDER", "mock"))
    tts_provider: str = field(default_factory=lambda: _env_str("TTS_PROVIDER", "kyutai"))
    tts_voice: str = field(default_factory=lambda: _env_str("TTS_VOICE", "marius"))
    tts_rate: int = field(default_factory=lambda: _env_int("TTS_RATE", 0))
    scene_intro_padding: float = field(
        default_factory=lambda: _env_float("SCENE_INTRO_PADDING", 0.3)
    )
    scene_outro_padding: float = field(
        default_factory=lambda: _env_float("SCENE_OUTRO_PADDING", 0.5)
    )
    max_narration_words: int = 120
    target_narration_words: tuple[int, int] = (40, 100)
    max_screen_words: int = 40
    target_screen_words: tuple[int, int] = (10, 30)
    max_bullets: int = 5
    max_scene_seconds: float = 45.0
    max_teaching_actions_per_scene: int = 3
    max_high_emphasis_cues_per_concept: int = 2
    branding: Brand = field(default_factory=Brand)
    paths: Paths = field(default_factory=Paths)

    @property
    def frame_seconds(self) -> float:
        return 1.0 / self.fps


def load_config() -> Config:
    cfg = Config()
    cfg.paths.ensure()
    return cfg
