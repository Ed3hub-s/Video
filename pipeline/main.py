"""Course Video Generator - V1 CLI.

Usage:
    python pipeline/main.py input/course.docx
    python pipeline/main.py input/course.pdf
    python pipeline/main.py input/course.docx --preview
    python pipeline/main.py input/course.docx --chapter 3
    python pipeline/main.py input/course.docx --tts-provider kokoro --voice af_heart
"""

from __future__ import annotations

import argparse
import dataclasses
import html
import json
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent

if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from pipeline.audio.duration import media_duration
from pipeline.audio.subtitles import (
    build_subtitles,
    build_subtitles_from_words,
)
from pipeline.audio.tts import build_tts_provider
from pipeline.cache.cache import (
    FileCache,
    hash_file,
    hash_json,
    hash_text,
)
from pipeline.config import STYLES, TRANSITIONS, Config, load_config
from pipeline.content.providers import build_provider
from pipeline.content.scene_generator import (
    ChapterSceneError,
    generate_chapter_plan,
)
from pipeline.content.schemas import (
    Chapter,
    ChapterPlan,
    Course,
    Scene,
)
from pipeline.document_reader import read_document
from pipeline.render.remotion import (
    render_chapter,
    write_render_manifest,
)
from pipeline.run_logging.run_logger import RunLogger
from pipeline.validation.validator import validate_chapter
from pipeline.visual.importance import rebalance_importance
from pipeline.visual.visual_planner import (
    align_actions_to_words,
    fit_actions_to_scene,
    plan_visual_actions,
)


def parse_args(
    argv: list[str] | None = None,
) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="course-video-generator",
        description=(
            "Convert a .docx or .pdf course "
            "into narrated tutorial MP4s."
        ),
    )

    parser.add_argument(
        "input",
        nargs="?",
        default="input/course.docx",
        help="Path to the .docx or .pdf course file",
    )

    parser.add_argument(
        "--preview",
        action="store_true",
        help="Run all stages except final rendering",
    )

    parser.add_argument(
        "--chapter",
        type=int,
        default=None,
        help="Process only this chapter number",
    )

    parser.add_argument(
        "--skip-ai",
        action="store_true",
        help=(
            "Reuse cached scene plans "
            "(fail if none)"
        ),
    )

    parser.add_argument(
        "--skip-tts",
        action="store_true",
        help=(
            "Reuse cached audio "
            "(fail if none)"
        ),
    )

    parser.add_argument(
        "--skip-render",
        action="store_true",
        help="Skip the final render step",
    )

    parser.add_argument(
        "--force-ai",
        action="store_true",
        help=(
            "Regenerate scene plans "
            "ignoring cache"
        ),
    )

    parser.add_argument(
        "--force-tts",
        action="store_true",
        help=(
            "Regenerate audio "
            "ignoring cache"
        ),
    )

    parser.add_argument(
        "--force-render",
        action="store_true",
        help=(
            "Re-render even if "
            "the MP4 exists"
        ),
    )

    parser.add_argument(
        "--provider",
        default=None,
        help=(
            "AI provider: "
            "mock (default) or openai"
        ),
    )

    parser.add_argument(
        "--tts-provider",
        default=None,
        help=(
            "TTS provider: "
            "kokoro (default), "
            "kyutai, edge-tts, "
            "sapi or mock"
        ),
    )

    parser.add_argument(
        "--style",
        default=None,
        choices=STYLES,
        help=(
            "Video style preset: "
            f"{', '.join(STYLES)} "
            "(default: studio)"
        ),
    )

    parser.add_argument(
        "--transition",
        default=None,
        choices=TRANSITIONS,
        help=(
            "Scene transition: "
            f"{', '.join(TRANSITIONS)} "
            "(default: fade)"
        ),
    )

    parser.add_argument(
        "--voice",
        default=None,
        help=(
            "TTS voice. "
            "Curated Kokoro voices: "
            "af_heart, af_bella, af_sarah, "
            "am_michael, bf_emma, bm_george"
        ),
    )

    return parser.parse_args(argv)


def scenes_cache_key(
    chapter: Chapter,
    provider_name: str,
) -> str:
    # Increment when deterministic scene-planning behavior changes so an old
    # plan cannot silently survive a renderer or visual-director improvement.
    return (
        f"scenes:v2:"
        f"{provider_name}:"
        f"{hash_json(chapter.model_dump(mode='json'))}"
    )


def audio_cache_key(
    scene: Scene,
    tts,
    chapter_number: int,
) -> str:
    """Return a chapter-safe cache key for generated narration audio.

    AudioMetadata contains a concrete filesystem path. Reusing a cache entry
    solely because another scene has identical narration can therefore point
    a scene in one chapter at an audio file generated for another chapter.

    Version 2 of the key includes the chapter number and scene id so cached
    metadata always belongs to the same logical output location.
    """

    return (
        f"audio:v2:"
        f"{tts.cache_tag}:"
        f"chapter-{chapter_number:02d}:"
        f"{scene.id}:"
        f"{hash_text(scene.voiceover)}"
    )


def save_json(
    path: Path,
    data: Any,
) -> None:
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
            data,
            handle,
            indent=2,
        )


def build_or_load_plan(
    chapter: Chapter,
    provider,
    config: Config,
    cache: FileCache,
    args: argparse.Namespace,
    logger: RunLogger,
) -> ChapterPlan:
    key = scenes_cache_key(
        chapter,
        provider.name,
    )

    cached = (
        cache.get(key)
        if not args.force_ai
        else None
    )

    if cached is not None:
        logger.add_cache_hit()

        logger.progress(
            f"  Chapter "
            f"{chapter.chapter_number}: "
            f"scene plan from cache"
        )

        scenes = [
            Scene.model_validate(item)
            for item in cached["scenes"]
        ]

        return ChapterPlan(
            courseTitle=cached["courseTitle"],
            chapterNumber=cached["chapterNumber"],
            chapterTitle=cached["chapterTitle"],
            fps=config.fps,
            width=config.width,
            height=config.height,
            scenes=scenes,
        )

    if args.skip_ai:
        raise ChapterSceneError(
            f"Chapter "
            f"{chapter.chapter_number}: "
            f"--skip-ai but no cached "
            f"scene plan exists"
        )

    logger.add_ai_request()

    plan = generate_chapter_plan(
        chapter,
        provider,
        config,
    )

    cache.put(
        key,
        {
            "courseTitle": (
                plan.courseTitle
            ),
            "chapterNumber": (
                plan.chapterNumber
            ),
            "chapterTitle": (
                plan.chapterTitle
            ),
            "scenes": [
                scene.model_dump(
                    mode="json"
                )
                for scene in plan.scenes
            ],
        },
    )

    return plan


def generate_audio_for_scene(
    scene: Scene,
    chapter_number: int,
    config: Config,
    cache: FileCache,
    args: argparse.Namespace,
    logger: RunLogger,
    tts,
) -> None:
    if not scene.voiceover.strip():
        return

    out_path = (
        config.paths.audio
        / f"chapter-{chapter_number:02d}"
        / f"{scene.id}.mp3"
    )

    key = audio_cache_key(
        scene,
        tts,
        chapter_number,
    )

    cached = (
        cache.get(key)
        if not args.force_tts
        else None
    )

    if cached is not None:
        from pipeline.content.schemas import (
            AudioMetadata,
        )

        cached_audio = (
            AudioMetadata.model_validate(
                cached
            )
        )

        cached_path = Path(
            cached_audio.path
        )

        expected_path = (
            out_path.resolve()
        )

        cached_resolved = (
            cached_path.resolve()
        )

        if (
            cached_resolved
            == expected_path
            and cached_path.exists()
        ):
            logger.add_cache_hit()
            scene.audio = cached_audio
            return

        logger.progress(
            f"  Chapter {chapter_number}: "
            f"ignoring stale audio cache "
            f"for scene {scene.id}"
        )

    if args.skip_tts:
        raise RuntimeError(
            f"Chapter {chapter_number}: "
            f"--skip-tts but no valid cached "
            f"audio for scene {scene.id}"
        )

    logger.add_tts_request()

    scene.audio = tts.generate(
        scene.voiceover,
        out_path,
    )

    cache.put(
        key,
        scene.audio.model_dump(
            mode="json"
        ),
    )


def apply_timing_and_subtitles(
    plan: ChapterPlan,
    config: Config,
) -> None:
    total = 0.0

    for index, scene in enumerate(
        plan.scenes
    ):
        words = None

        if scene.audio is not None:
            duration = (
                scene.audio.durationSeconds
            )

            offset = (
                config.scene_intro_padding
            )

            word_path = (
                scene.audio.wordTimestampsPath
            )

            if (
                word_path
                and Path(word_path).exists()
            ):
                try:
                    words = json.loads(
                        Path(word_path).read_text(
                            encoding="utf-8"
                        )
                    )

                    scene.subtitles = (
                        build_subtitles_from_words(
                            words,
                            offset=offset,
                        )
                    )

                except (
                    OSError,
                    json.JSONDecodeError,
                ):
                    words = None

                    scene.subtitles = (
                        build_subtitles(
                            scene.voiceover,
                            duration,
                            offset=offset,
                        )
                    )

            else:
                scene.subtitles = (
                    build_subtitles(
                        scene.voiceover,
                        duration,
                        offset=offset,
                    )
                )

        else:
            duration = 4.0

            scene.subtitles = (
                build_subtitles(
                    scene.voiceover,
                    duration,
                    offset=0.2,
                )
            )

        if words:
            scene = align_actions_to_words(
                scene,
                words,
                config.scene_intro_padding,
            )

        scene.durationSeconds = round(
            duration
            + config.scene_intro_padding
            + config.scene_outro_padding,
            3,
        )

        plan.scenes[index] = (
            fit_actions_to_scene(
                scene,
                config.scene_outro_padding,
            )
        )

        total += (
            scene.durationSeconds
        )

    plan.totalDurationSeconds = round(
        total,
        3,
    )


def preview_report(
    course: Course,
    plans: dict[int, ChapterPlan],
    output: Path,
) -> None:
    rows = []

    for chapter in course.chapters:
        plan = plans.get(
            chapter.chapter_number
        )

        if plan is None:
            continue

        for scene in plan.scenes:
            concepts = ", ".join(
                (
                    f"{concept.text} "
                    f"({concept.importance.value})"
                )
                for concept
                in scene.keyConcepts
            )

            actions = ", ".join(
                (
                    f"{action.type.value}"
                    f"@{action.startSec}s"
                )
                for action
                in scene.visualActions
            )

            rows.append(
                "<tr>"
                f"<td>{chapter.chapter_number}</td>"
                f"<td>{scene.id}</td>"
                f"<td>{scene.type.value}</td>"
                f"<td>{html.escape(scene.title)}</td>"
                f"<td>{html.escape(scene.sourceText[:180])}</td>"
                f"<td>{html.escape(scene.voiceover[:220])}</td>"
                f"<td>{html.escape(scene.screenText)}</td>"
                f"<td>{html.escape(concepts)}</td>"
                f"<td>{html.escape(scene.visualStrategy)}</td>"
                f"<td>{html.escape(actions)}</td>"
                "</tr>"
            )

    document = (
        "<!doctype html>"
        "<html>"
        "<head>"
        "<meta charset='utf-8'>"
        "<title>"
        "Course Video Generator - Preview"
        "</title>"
        "<style>"
        "body{"
        "font-family:sans-serif;"
        "margin:2rem"
        "}"
        "table{"
        "border-collapse:collapse;"
        "width:100%"
        "}"
        "th,td{"
        "border:1px solid #ccc;"
        "padding:6px;"
        "text-align:left;"
        "vertical-align:top;"
        "font-size:13px"
        "}"
        "th{"
        "background:#f0f0f0"
        "}"
        "</style>"
        "</head>"
        "<body>"
        f"<h1>Preview: "
        f"{html.escape(course.title)}"
        f"</h1>"
        f"<p>{len(course.chapters)} chapters</p>"
        "<table>"
        "<thead>"
        "<tr>"
        "<th>Ch</th>"
        "<th>Scene</th>"
        "<th>Type</th>"
        "<th>Title</th>"
        "<th>Source</th>"
        "<th>Voiceover</th>"
        "<th>Screen</th>"
        "<th>Concepts</th>"
        "<th>Strategy</th>"
        "<th>Actions</th>"
        "</tr>"
        "</thead>"
        "<tbody>"
        + "".join(rows)
        + "</tbody>"
        "</table>"
        "</body>"
        "</html>"
    )

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.write_text(
        document,
        encoding="utf-8",
    )


def run_pipeline(
    args: argparse.Namespace,
    config: Config,
) -> int:
    cache = FileCache(
        config.paths.cache
    )

    logger = RunLogger(
        config.paths.logs
    )

    provider = build_provider(
        args.provider
        or config.ai_provider
    )

    tts = build_tts_provider(
        args.tts_provider
        or config.tts_provider,
        voice=config.tts_voice,
        rate=config.tts_rate,
        cache_dir=config.paths.cache,
    )

    input_path = Path(
        args.input
    )

    logger.set_input(
        str(input_path),
        (
            hash_file(input_path)
            if input_path.exists()
            else ""
        ),
    )

    logger.progress(
        "[1/9] Reading document"
    )

    read_started = logger.timer()
    course = read_document(
        input_path,
        config,
    )
    logger.add_stage_timing("document_ingestion", read_started)

    logger.count_chapters(
        len(course.chapters)
    )

    chapters = [
        chapter
        for chapter in course.chapters
        if (
            args.chapter is None
            or chapter.chapter_number
            == args.chapter
        )
    ]

    if not chapters:
        print(
            "No chapters selected "
            f"(document has "
            f"{len(course.chapters)})."
        )

        return 1

    logger.progress(
        "[2/9] Extracting chapters"
    )

    logger.progress(
        "  Render settings: "
        f"style={config.style}, "
        f"voice={config.tts_voice}, "
        f"provider={config.tts_provider}"
    )

    for chapter in chapters:
        logger.progress(
            f"  Chapter "
            f"{chapter.chapter_number}: "
            f"{chapter.title}"
        )

    logger.progress(
        "[3/9] Extracting assets"
    )

    for warning in course.warnings:
        logger.progress(
            f"  ! {warning}"
        )

    plans: dict[
        int,
        ChapterPlan,
    ] = {}

    failures: list[int] = []

    for step, label in (
        (
            4,
            "Building teaching scenes",
        ),
        (
            5,
            "Planning visual cues",
        ),
        (
            6,
            "Generating narration audio",
        ),
        (
            7,
            "Building subtitles and timing",
        ),
        (
            8,
            "Validating",
        ),
        (
            9,
            "Rendering",
        ),
    ):
        stage_started = logger.timer()
        logger.progress(
            f"[{step}/9] {label}"
        )

        for chapter in chapters:
            chapter_number = (
                chapter.chapter_number
            )

            if (
                chapter_number
                in failures
            ):
                continue

            try:
                if step == 4:
                    plan = (
                        build_or_load_plan(
                            chapter,
                            provider,
                            config,
                            cache,
                            args,
                            logger,
                        )
                    )

                    for scene in plan.scenes:
                        save_json(
                            (
                                config.paths.scenes
                                / (
                                    f"chapter-"
                                    f"{chapter_number:02d}"
                                )
                                / f"{scene.id}.json"
                            ),
                            scene.model_dump(
                                mode="json"
                            ),
                        )

                    save_json(
                        (
                            config.paths.chapters
                            / (
                                f"chapter-"
                                f"{chapter_number:02d}"
                                f".json"
                            )
                        ),
                        chapter.model_dump(
                            mode="json"
                        ),
                    )

                    plans[
                        chapter_number
                    ] = plan

                    logger.add_scenes(
                        len(plan.scenes)
                    )

                if step == 5:
                    plan = plans[
                        chapter_number
                    ]

                    plan.scenes = [
                        plan_visual_actions(
                            rebalance_importance(
                                scene
                            )
                        )
                        for scene
                        in plan.scenes
                    ]

                if step == 6:
                    plan = plans[
                        chapter_number
                    ]

                    for scene in plan.scenes:
                        generate_audio_for_scene(
                            scene,
                            chapter_number,
                            config,
                            cache,
                            args,
                            logger,
                            tts,
                        )

                if step == 7:
                    plan = plans[
                        chapter_number
                    ]

                    apply_timing_and_subtitles(
                        plan,
                        config,
                    )

                    save_json(
                        (
                            config.paths.subtitles
                            / (
                                f"chapter-"
                                f"{chapter_number:02d}"
                                f".json"
                            )
                        ),
                        [
                            {
                                "sceneId": (
                                    scene.id
                                ),
                                "subtitles": [
                                    cue.model_dump(
                                        mode="json"
                                    )
                                    for cue
                                    in scene.subtitles
                                ],
                            }
                            for scene
                            in plan.scenes
                        ],
                    )

                    save_json(
                        (
                            config.paths.manifests
                            / (
                                f"chapter-"
                                f"{chapter_number:02d}"
                                f".json"
                            )
                        ),
                        plan.model_dump(
                            mode="json"
                        ),
                    )

                if step == 8:
                    plan = plans[
                        chapter_number
                    ]

                    result = validate_chapter(
                        plan,
                        config,
                    )

                    logger.add_validation(
                        len(result.errors),
                        len(result.warnings),
                    )

                    for warning in (
                        result.warnings
                    ):
                        logger.progress(
                            f"  ! "
                            f"{warning.message}"
                        )

                    if not result.ok:
                        for error in (
                            result.errors
                        ):
                            logger.progress(
                                f"  x "
                                f"{error.message}"
                            )

                        raise ChapterSceneError(
                            f"Chapter "
                            f"{chapter_number} "
                            f"failed validation "
                            f"("
                            f"{len(result.errors)} "
                            f"errors)"
                        )

                if step == 9:
                    if (
                        args.preview
                        or args.skip_render
                    ):
                        write_render_manifest(
                            plans[
                                chapter_number
                            ],
                            config,
                        )

                        logger.progress(
                            f"  Chapter "
                            f"{chapter_number}: "
                            f"render skipped"
                        )

                        continue

                    plan = plans[
                        chapter_number
                    ]

                    output = (
                        config.paths.output
                        / f"{chapter.slug}.mp4"
                    )

                    if (
                        output.exists()
                        and not args.force_render
                    ):
                        existing_duration = (
                            media_duration(
                                output
                            )
                        )

                        if (
                            existing_duration
                            is not None
                            and abs(
                                existing_duration
                                - plan.totalDurationSeconds
                            )
                            <= 1.0
                        ):
                            logger.progress(
                                f"  Chapter "
                                f"{chapter_number}: "
                                f"output exists, "
                                f"skipping "
                                f"(--force-render "
                                f"to rebuild)"
                            )

                            logger.add_render_result(
                                chapter_number,
                                True,
                                str(output),
                            )

                            continue

                        logger.progress(
                            f"  Chapter "
                            f"{chapter_number}: "
                            f"existing output "
                            f"is incomplete "
                            f"("
                            f"{existing_duration}s "
                            f"vs "
                            f"{plan.totalDurationSeconds:.1f}s"
                            f"), re-rendering"
                        )

                    manifest = render_chapter(
                        plan,
                        config,
                        output,
                        progress_cb=(
                            logger.progress
                        ),
                    )

                    logger.add_render_result(
                        chapter_number,
                        True,
                        str(
                            manifest.outputPath
                        ),
                    )

                    logger.progress(
                        f"  OK Chapter "
                        f"{chapter_number} "
                        f"rendered -> "
                        f"{output}"
                    )

            except ChapterSceneError as exc:
                logger.progress(
                    f"  x Chapter "
                    f"{chapter_number} "
                    f"failed: {exc}"
                )

                if (
                    chapter_number
                    not in failures
                ):
                    failures.append(
                        chapter_number
                    )

            except Exception as exc:
                # Per-chapter recovery is
                # intentional so one failed
                # video does not invalidate
                # every other chapter.
                logger.progress(
                    f"  x Chapter "
                    f"{chapter_number} "
                    f"failed: {exc}"
                )

                if (
                    chapter_number
                    not in failures
                ):
                    failures.append(
                        chapter_number
                    )

        elapsed = logger.add_stage_timing(
            label.lower().replace(" ", "_"),
            stage_started,
        )
        logger.progress(
            f"  {label} completed in {elapsed:.2f}s"
        )

    if args.preview:
        report = (
            config.paths.generated
            / "preview.html"
        )

        preview_report(
            course,
            plans,
            report,
        )

        logger.progress(
            f"Preview report: "
            f"{report}"
        )

    successful = (
        len(chapters)
        - len(failures)
    )

    logger.progress("")

    for chapter in chapters:
        ok = (
            chapter.chapter_number
            not in failures
        )

        status = (
            "rendered"
            if ok
            else "failed"
        )

        logger.progress(
            f"{'OK' if ok else 'FAIL'} "
            f"Chapter "
            f"{chapter.chapter_number:02d} "
            f"{status}"
        )

    logger.progress(
        f"\n{successful} successful"
    )

    if failures:
        logger.progress(
            f"{len(failures)} failed"
        )

    log_path = logger.finish()

    logger.progress(
        f"Log: {log_path}"
    )

    return (
        0
        if not failures
        else 1
    )


def main(
    argv: list[str] | None = None,
) -> int:
    args = parse_args(argv)

    config = load_config()

    if args.style:
        config = dataclasses.replace(
            config,
            style=args.style,
        )

    if args.transition:
        config = dataclasses.replace(
            config,
            transition=args.transition,
        )

    if args.voice:
        config = dataclasses.replace(
            config,
            tts_voice=args.voice,
        )

    return run_pipeline(
        args,
        config,
    )


if __name__ == "__main__":
    sys.exit(main())
