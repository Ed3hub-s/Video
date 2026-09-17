"""Local web app for the Course Video Generator.

Runs the CLI pipeline as background jobs so the user can pick a document,
voice and style from the browser, preview the voice, then render and watch
live logs - fully offline once the TTS model is cached.

Start with:
    .venv\\Scripts\\python.exe -m uvicorn webapp.app:app --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.audio.tts import KokoroTTS, KyutaiTTS, build_tts_provider
from pipeline.config import STYLES, load_config

CONFIG = load_config()

UPLOAD_DIR = ROOT / "input" / "uploads"
LOG_DIR = ROOT / "logs" / "site"
TMP_DIR = ROOT / ".tmp"

MAX_UPLOAD_BYTES = 200 * 1024 * 1024
UPLOAD_CHUNK_BYTES = 1024 * 1024

for directory in (
    UPLOAD_DIR,
    LOG_DIR,
    TMP_DIR,
):
    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

os.environ.setdefault(
    "HF_HOME",
    str(ROOT / "cache"),
)

app = FastAPI(
    title="Course Video Generator",
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# Static + media mounts
# ---------------------------------------------------------------------------

app.mount(
    "/videos",
    StaticFiles(
        directory=str(
            ROOT / "output" / "videos"
        )
    ),
    name="videos",
)

app.mount(
    "/preview",
    StaticFiles(
        directory=str(TMP_DIR)
    ),
    name="preview",
)


# ---------------------------------------------------------------------------
# Catalog data (voices, styles)
# ---------------------------------------------------------------------------

KOKORO_VOICE_INFO: dict[str, str] = {
    "af_heart": "American female, warm and natural",
    "af_bella": "American female, clear",
    "af_sarah": "American female, expressive",
    "am_michael": "American male, balanced",
    "bf_emma": "British female, clear",
    "bm_george": "British male, deep",
}

KYUTAI_VOICE_INFO: dict[str, str] = {
    "alba": "Warm female, clear",
    "marius": "Young male, neutral",
    "javert": "Deep male, authoritative",
    "fantine": "Soft female",
    "anna": "Female",
    "vera": "Female",
    "charles": "Male",
    "paul": "Male",
    "eponine": "Female",
    "azelma": "Female",
    "george": "Male",
    "mary": "Female",
    "jane": "Female",
    "michael": "Male",
    "eve": "Female",
    "bill_boerst": "Male, older",
    "peter_yearsley": "Male, older",
    "stuart_bell": "Male, older",
    "caro_davy": "Female",
    "jean": "Mature male (CC-BY-NC)",
    "cosette": "Female (CC-BY-NC)",
}

EDGE_VOICES = (
    "en-GB-RyanNeural",
    "en-GB-SoniaNeural",
    "en-US-JennyNeural",
    "en-US-GuyNeural",
    "en-AU-WilliamNeural",
)

STYLE_INFO: dict[str, dict[str, Any]] = {
    "studio": {
        "label": "Studio",
        "description": (
            "Light, clean, orange accent - "
            "the default look."
        ),
        "swatches": [
            "#F5F5F5",
            "#111111",
            "#FF5A36",
        ],
    },
    "dark": {
        "label": "Dark",
        "description": (
            "Deep navy-black with a cyan accent - "
            "modern and focused."
        ),
        "swatches": [
            "#10151A",
            "#F2F6F9",
            "#4CC9F0",
        ],
    },
    "playful": {
        "label": "Playful",
        "description": (
            "Warm pastels, rounded corners, "
            "bold and friendly."
        ),
        "swatches": [
            "#FFF7E8",
            "#2B2118",
            "#FF6B35",
        ],
    },
    "minimal": {
        "label": "Minimal",
        "description": (
            "Black and white with serif headings - "
            "one strong accent."
        ),
        "swatches": [
            "#FAFAFA",
            "#111111",
            "#777777",
        ],
    },
    "cinema": {
        "label": "Cinema",
        "description": (
            "Warm black and gold - "
            "dramatic and premium."
        ),
        "swatches": [
            "#0C0A08",
            "#F6F0E4",
            "#E3B25B",
        ],
    },
}


def _sanitize_filename(
    name: str,
) -> str:
    name = re.sub(
        r"[^A-Za-z0-9._-]+",
        "_",
        Path(name).name,
    )

    return name or "document.docx"


def _resolve_input_document(
    document_path: str,
) -> Path:
    """Resolve and validate a document inside the input directory."""

    input_root = (
        ROOT / "input"
    ).resolve()

    document = (
        ROOT / document_path
    ).resolve()

    try:
        document.relative_to(
            input_root
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=(
                "Document must be inside "
                "the input directory"
            ),
        ) from exc

    if (
        not document.exists()
        or not document.is_file()
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Document not found: "
                f"{document_path}"
            ),
        )

    if document.suffix.lower() not in {".docx", ".pdf"}:
        raise HTTPException(
            status_code=400,
            detail=(
                "Only .docx or .pdf documents "
                "can be rendered"
            ),
        )

    return document


# ---------------------------------------------------------------------------
# Job manager
# ---------------------------------------------------------------------------

JOBS: dict[str, dict[str, Any]] = {}
JOBS_LOCK = threading.Lock()


def _pipeline_env() -> dict[str, str]:
    """Build a portable environment for pipeline subprocesses."""

    env = dict(os.environ)

    env.setdefault(
        "HF_HOME",
        str(ROOT / "cache"),
    )

    env.setdefault(
        "TMP",
        str(TMP_DIR),
    )

    env.setdefault(
        "TEMP",
        str(TMP_DIR),
    )

    env.setdefault(
        "REMOTION_CONCURRENCY",
        "8",
    )

    if os.name == "nt":
        ffmpeg_path = Path(
            r"C:\ffmpeg\bin\ffmpeg.exe"
        )

        if ffmpeg_path.exists():
            env.setdefault(
                "REMOTION_FFMPEG_EXECUTABLE",
                str(ffmpeg_path),
            )

        browser_candidates = (
            Path(
                r"C:\Program Files\Google\Chrome"
                r"\Application\chrome.exe"
            ),
            Path(
                r"C:\Program Files (x86)\Google\Chrome"
                r"\Application\chrome.exe"
            ),
            Path(
                r"C:\Program Files\Microsoft\Edge"
                r"\Application\msedge.exe"
            ),
            Path(
                r"C:\Program Files (x86)\Microsoft\Edge"
                r"\Application\msedge.exe"
            ),
        )

        if (
            "REMOTION_BROWSER_EXECUTABLE"
            not in env
        ):
            for browser_path in browser_candidates:
                if browser_path.exists():
                    env[
                        "REMOTION_BROWSER_EXECUTABLE"
                    ] = str(browser_path)
                    break

    return env


def _run_job(
    job_id: str,
    cmd: list[str],
    env: dict[str, str],
) -> None:
    job = JOBS[job_id]

    log_path = (
        LOG_DIR
        / f"{job_id}.log"
    )

    job["logPath"] = str(
        log_path
    )

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
            cwd=str(ROOT),
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    except Exception as exc:
        with JOBS_LOCK:
            job["status"] = "failed"
            job["error"] = str(exc)
            job["finishedAt"] = time.time()

        return

    with JOBS_LOCK:
        job["status"] = "running"
        job["pid"] = proc.pid
        job["startedAt"] = time.time()

    def pump() -> None:
        with open(
            log_path,
            "w",
            encoding="utf-8",
            errors="replace",
        ) as handle:
            assert (
                proc.stdout
                is not None
            )

            for line in proc.stdout:
                handle.write(line)
                handle.flush()

                with JOBS_LOCK:
                    job["log"].append(
                        line.rstrip("\n")
                    )

                    if len(job["log"]) > 600:
                        del job["log"][
                            : len(job["log"])
                            - 600
                        ]

        return_code = proc.wait()

        with JOBS_LOCK:
            job["status"] = (
                "done"
                if return_code == 0
                else "failed"
            )
            job["exitCode"] = return_code
            job["finishedAt"] = time.time()

    threading.Thread(
        target=pump,
        daemon=True,
    ).start()


def _active_job() -> dict[str, Any] | None:
    with JOBS_LOCK:
        for job in JOBS.values():
            if job["status"] in (
                "queued",
                "running",
            ):
                return job

    return None


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


@app.get("/api/config")
def api_config() -> dict[str, Any]:
    return {
        "defaults": {
            "voice": CONFIG.tts_voice,
            "provider": CONFIG.tts_provider,
            "style": CONFIG.style,
        },
        "providers": [
            {
                "id": "kokoro",
                "label": "Kokoro (offline)",
                "note": (
                    "Primary local neural voice - "
                    "runs locally with no API key"
                ),
                "voices": [
                    {
                        "id": voice,
                        "label": voice,
                        "hint": KOKORO_VOICE_INFO.get(
                            voice,
                            "",
                        ),
                        "restricted": False,
                    }
                    for voice
                    in KokoroTTS.CURATED_VOICES
                ],
            },
            {
                "id": "kyutai",
                "label": "Kyutai (offline fallback)",
                "note": (
                    "Local neural voice - "
                    "retained as a fallback provider"
                ),
                "voices": [
                    {
                        "id": voice,
                        "label": voice.capitalize(),
                        "hint": KYUTAI_VOICE_INFO.get(
                            voice,
                            "",
                        ),
                        "restricted": voice in (
                            "jean",
                            "cosette",
                        ),
                    }
                    for voice
                    in KyutaiTTS.PRESET_VOICES
                ],
            },
            {
                "id": "edge-tts",
                "label": "Edge TTS (online)",
                "note": (
                    "Microsoft neural voices - "
                    "needs internet, "
                    "word-level subtitles"
                ),
                "voices": [
                    {
                        "id": voice,
                        "label": voice,
                        "hint": (
                            "Microsoft neural voice"
                        ),
                        "restricted": False,
                    }
                    for voice
                    in EDGE_VOICES
                ],
            },
        ],
        "styles": [
            {
                "id": style_id,
                **STYLE_INFO[style_id],
            }
            for style_id
            in STYLES
        ],
    }


@app.get("/api/documents")
def api_documents() -> dict[str, Any]:
    documents: list[
        dict[str, Any]
    ] = []

    for directory in (
        ROOT / "input",
        UPLOAD_DIR,
    ):
        if not directory.exists():
            continue

        for path in sorted(
            item
            for item in directory.iterdir()
            if item.is_file() and item.suffix.lower() in {".docx", ".pdf"}
        ):
            relative = str(
                path.relative_to(ROOT)
            )

            documents.append(
                {
                    "path": relative,
                    "name": path.name,
                    "sizeBytes": (
                        path.stat().st_size
                    ),
                    "modified": (
                        path.stat().st_mtime
                    ),
                    "isUpload": (
                        directory
                        == UPLOAD_DIR
                    ),
                }
            )

    return {
        "documents": documents
    }


@app.post("/api/upload")
async def api_upload(
    file: UploadFile = File(...),
) -> dict[str, Any]:
    if Path(file.filename or "").suffix.lower() not in {".docx", ".pdf"}:
        raise HTTPException(
            status_code=400,
            detail=(
                "Only .docx or .pdf files "
                "are accepted"
            ),
        )

    safe_name = _sanitize_filename(
        file.filename
        or "document.docx"
    )

    destination = (
        UPLOAD_DIR
        / safe_name
    )

    temporary = (
        UPLOAD_DIR
        / (
            f".{destination.name}."
            f"{uuid.uuid4().hex}.part"
        )
    )

    size_bytes = 0

    try:
        with temporary.open(
            "wb"
        ) as handle:
            while True:
                chunk = await file.read(
                    UPLOAD_CHUNK_BYTES
                )

                if not chunk:
                    break

                size_bytes += len(
                    chunk
                )

                if (
                    size_bytes
                    > MAX_UPLOAD_BYTES
                ):
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "File is larger "
                            "than 200 MB"
                        ),
                    )

                handle.write(
                    chunk
                )

        temporary.replace(
            destination
        )

    except Exception:
        temporary.unlink(
            missing_ok=True
        )
        raise

    finally:
        await file.close()

    return {
        "path": str(
            destination.relative_to(
                ROOT
            )
        ),
        "name": destination.name,
        "sizeBytes": size_bytes,
    }


class PreviewRequest(BaseModel):
    provider: str = CONFIG.tts_provider
    voice: str = CONFIG.tts_voice


@app.post("/api/preview-voice")
def api_preview_voice(
    request: PreviewRequest,
) -> dict[str, str]:
    if request.provider not in (
        "kokoro",
        "kyutai",
        "edge-tts",
    ):
        raise HTTPException(
            status_code=400,
            detail="Unknown provider",
        )

    safe_voice = re.sub(
        r"[^A-Za-z0-9._-]+",
        "-",
        request.voice,
    )

    output = (
        TMP_DIR
        / (
            f"voice-preview-"
            f"{request.provider}-"
            f"{safe_voice}.mp3"
        )
    )

    if not output.exists():
        try:
            tts = build_tts_provider(
                request.provider,
                voice=request.voice,
                rate=CONFIG.tts_rate,
                cache_dir=(
                    ROOT / "cache"
                ),
            )

            tts.generate(
                (
                    "Hello, this is a quick "
                    "preview of the narration "
                    "voice for your course videos."
                ),
                output,
            )

        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=(
                    "Voice preview failed: "
                    f"{exc}"
                ),
            ) from exc

    return {
        "url": (
            f"/preview/{output.name}"
        ),
        "voice": request.voice,
    }


class JobRequest(BaseModel):
    document: str = (
        "input/course.docx"
    )
    provider: str = CONFIG.tts_provider
    voice: str = CONFIG.tts_voice
    style: str = CONFIG.style
    chapter: int | None = None
    forceTts: bool = False
    forceRender: bool = False
    previewOnly: bool = False


@app.post("/api/jobs")
def api_start_job(
    request: JobRequest,
) -> dict[str, Any]:
    if _active_job() is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                "A render is already running - "
                "wait for it to finish"
            ),
        )

    document = _resolve_input_document(
        request.document
    )

    if request.style not in STYLES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unknown style: "
                f"{request.style}"
            ),
        )

    if request.provider not in (
        "kokoro",
        "kyutai",
        "edge-tts",
        "sapi",
        "mock",
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unknown provider: "
                f"{request.provider}"
            ),
        )

    job_id = uuid.uuid4().hex[:12]

    job: dict[str, Any] = {
        "id": job_id,
        "status": "queued",
        "document": request.document,
        "provider": request.provider,
        "voice": request.voice,
        "style": request.style,
        "chapter": request.chapter,
        "previewOnly": request.previewOnly,
        "createdAt": time.time(),
        "log": [],
        "exitCode": None,
    }

    with JOBS_LOCK:
        JOBS[job_id] = job

    cmd = [
        sys.executable,
        "pipeline/main.py",
        str(document),
        "--provider",
        "mock",
        "--tts-provider",
        request.provider,
        "--voice",
        request.voice,
        "--style",
        request.style,
    ]

    if request.chapter is not None:
        cmd += [
            "--chapter",
            str(request.chapter),
        ]

    if request.forceTts:
        cmd += [
            "--force-tts"
        ]

    if request.forceRender:
        cmd += [
            "--force-render"
        ]

    if request.previewOnly:
        cmd += [
            "--skip-render"
        ]

    _run_job(
        job_id,
        cmd,
        _pipeline_env(),
    )

    return api_job(
        job_id
    )


@app.get("/api/jobs")
def api_jobs() -> dict[str, Any]:
    jobs = []

    with JOBS_LOCK:
        for job_id in sorted(
            JOBS,
            reverse=True,
        ):
            job = dict(
                JOBS[job_id]
            )

            job.pop(
                "log",
                None,
            )

            jobs.append(
                job
            )

    return {
        "jobs": jobs
    }


@app.get("/api/jobs/{job_id}")
def api_job(
    job_id: str,
) -> dict[str, Any]:
    with JOBS_LOCK:
        job = JOBS.get(
            job_id
        )

        if job is None:
            raise HTTPException(
                status_code=404,
                detail="Job not found",
            )

        return dict(job)


@app.get("/api/videos")
def api_videos() -> dict[str, Any]:
    videos: list[
        dict[str, Any]
    ] = []

    output_dir = (
        ROOT / "output" / "videos"
    )

    if output_dir.exists():
        for path in sorted(
            output_dir.glob("*.mp4")
        ):
            videos.append(
                {
                    "name": path.name,
                    "sizeBytes": (
                        path.stat().st_size
                    ),
                    "modified": (
                        path.stat().st_mtime
                    ),
                    "url": (
                        f"/videos/{path.name}"
                    ),
                }
            )

    return {
        "videos": videos
    }


@app.get("/api/jobs/{job_id}/log")
def api_job_log(
    job_id: str,
) -> dict[str, Any]:
    with JOBS_LOCK:
        job = JOBS.get(
            job_id
        )

        if job is None:
            raise HTTPException(
                status_code=404,
                detail="Job not found",
            )

        log = list(
            job["log"]
        )

        status = (
            job["status"]
        )

    return {
        "id": job_id,
        "status": status,
        "log": log,
    }


# SPA shell - mounted last so /api/* routes win.
app.mount(
    "/",
    StaticFiles(
        directory=str(
            Path(__file__).parent
            / "static"
        ),
        html=True,
    ),
    name="site",
)
