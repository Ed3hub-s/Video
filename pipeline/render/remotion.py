"""Invoke Remotion CLI to render one chapter MP4 from a manifest."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from pipeline.config import Config
from pipeline.content.schemas import ChapterPlan, RenderManifest


def resolve_path(path_value: str) -> str:
    """Absolutize a scene file path for the render manifest."""

    path = Path(path_value)
    return str(path.resolve())


def _stage_media(
    source: str,
    dest_dir: Path,
    scene_id: str,
    ext: str,
) -> str | None:
    source_path = Path(source)

    if not source_path.exists():
        return None

    dest_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    dest = (
        dest_dir
        / f"{scene_id}{ext}"
    )

    if (
        not dest.exists()
        or dest.stat().st_size
        != source_path.stat().st_size
    ):
        shutil.copy2(
            source_path,
            dest,
        )

    return dest.name


def write_render_manifest(
    plan: ChapterPlan,
    config: Config,
) -> Path:
    """Write a render manifest with public-relative media for Remotion.

    Remotion cannot load file:// URLs, so audio and images are staged into
    remotion/public/media/<chapter>/ and referenced through staticFile().
    """

    scenes = []

    media_dir = (
        config.paths.remotion
        / "public"
        / "media"
        / f"chapter-{plan.chapterNumber:02d}"
    )

    for scene in plan.scenes:
        data = scene.model_dump(
            mode="json"
        )

        if data.get("audio"):
            staged = _stage_media(
                resolve_path(
                    data["audio"]["path"]
                ),
                media_dir,
                scene.id,
                Path(
                    data["audio"]["path"]
                ).suffix,
            )

            if staged:
                data["audio"]["path"] = (
                    f"media/"
                    f"chapter-{plan.chapterNumber:02d}/"
                    f"{staged}"
                )

        if data.get("image"):
            staged = _stage_media(
                resolve_path(
                    data["image"]
                ),
                media_dir,
                f"{scene.id}-image",
                Path(
                    data["image"]
                ).suffix,
            )

            if staged:
                data["image"] = (
                    f"media/"
                    f"chapter-{plan.chapterNumber:02d}/"
                    f"{staged}"
                )

        scenes.append(data)

    manifest = {
        "courseTitle": plan.courseTitle,
        "chapterNumber": plan.chapterNumber,
        "chapterTitle": plan.chapterTitle,
        "fps": plan.fps,
        "width": plan.width,
        "height": plan.height,
        "scenes": scenes,
        "totalDurationSeconds": (
            plan.totalDurationSeconds
        ),
        "style": config.style,
        "transition": config.transition,
        "theme": config.branding.__dict__,
    }

    path = (
        config.paths.manifests
        / f"chapter-{plan.chapterNumber:02d}-render.json"
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        path,
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(
            {"manifest": manifest},
            handle,
            indent=2,
        )

    return path


def render_chapter(
    plan: ChapterPlan,
    config: Config,
    output_path: Path,
    progress_cb=None,
) -> RenderManifest:
    """Render one chapter video. Returns a RenderManifest on success."""

    remotion_dir = (
        config.paths.remotion
    )

    if not (
        remotion_dir
        / "node_modules"
    ).exists():
        raise RuntimeError(
            "Remotion dependencies are not installed. "
            "Run `npm.cmd install` inside "
            f"{remotion_dir} "
            "(or `make remotion-install`) first."
        )

    manifest_path = (
        write_render_manifest(
            plan,
            config,
        )
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    npx = (
        shutil.which("npx.cmd")
        or shutil.which("npx")
    )

    if npx is None:
        raise RuntimeError(
            "npx not found on PATH"
        )

    command = [
        npx,
        "remotion",
        "render",
        "src/index.ts",
        "Tutorial",
        str(output_path),
        f"--props={manifest_path}",
        "--codec=h264",
        "--pixel-format=yuv420p",
        f"--fps={config.fps}",
    ]

    ffmpeg_executable = (
        os.environ.get(
            "REMOTION_FFMPEG_EXECUTABLE"
        )
    )

    if ffmpeg_executable:
        command.append(
            f"--ffmpeg-executable="
            f"{ffmpeg_executable}"
        )

    browser_executable = (
        os.environ.get(
            "REMOTION_BROWSER_EXECUTABLE"
        )
    )

    if browser_executable:
        command.append(
            f"--browser-executable="
            f"{browser_executable}"
        )

    concurrency = (
        os.environ.get(
            "REMOTION_CONCURRENCY"
        )
    )

    if concurrency:
        command.append(
            f"--concurrency={concurrency}"
        )

    if progress_cb:
        progress_cb(
            f"Rendering chapter "
            f"{plan.chapterNumber} "
            f"with Remotion..."
        )

    result = subprocess.run(
        command,
        cwd=str(remotion_dir),
        capture_output=True,
        text=True,
        timeout=1800,
    )

    if result.returncode != 0:
        tail = (
            (result.stdout or "")[-3000:]
            + (result.stderr or "")[-3000:]
        )

        raise RuntimeError(
            "Remotion render failed:\n"
            f"{tail}"
        )

    if not output_path.exists():
        raise RuntimeError(
            "Remotion reported success "
            "but produced no output file"
        )

    return RenderManifest(
        chapterNumber=plan.chapterNumber,
        chapterTitle=plan.chapterTitle,
        sceneCount=len(plan.scenes),
        durationSeconds=(
            plan.totalDurationSeconds
        ),
        sceneFiles=[
            scene.id
            for scene in plan.scenes
        ],
        outputPath=str(
            output_path
        ),
    )