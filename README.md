# Course Video Generator

Local-first system that converts a structured `.docx` course file into one
narrated tutorial video per chapter. It is a teaching engine, not a slide
generator: every meaningful scene gets narration, concise on-screen text,
importance-ranked key concepts, and deliberate visual actions (handwriting,
underlines, arrows, highlights, diagrams) that reinforce the idea being taught.

```text
DOCX -> Parsing -> Chapters/Sections -> Scene Plan -> Narration
     -> Visual Importance -> Visual Cues -> TTS Audio -> Timing
     -> Subtitles -> Remotion Render -> MP4 per chapter
```

---

## System overview

One CLI command turns a correctly formatted course document into one branded
`1920x1080 @ 30fps` MP4 per chapter:

```bash
python pipeline/main.py input/course.docx
```

Everything runs locally. Demo mode uses a deterministic mock AI director and a
mock TTS provider, so the full pipeline works with **no API keys and no paid
calls**. A live OpenAI provider is available behind an API key for the content
layer.

## Architecture

Two systems separated by structured JSON (never shared code):

**Python owns** (the thinking):

- DOCX parsing and unsupported-element warnings
- Content normalization and text splitting
- AI calls (mock or OpenAI)
- Scene planning, key concepts, importance
- Visual action planning
- TTS audio generation
- Timing and subtitles
- Validation, caching, logging, batch orchestration

**Remotion owns** (the drawing):

- Layout and typography
- Presentation and teaching motion
- Visual cues (handwrite, underline, circle, arrow, box, highlight, cross-out)
- Predefined diagram families
- Subtitles, audio playback, MP4 rendering

The boundary between both systems is `generated/manifests/chapter-XX.json`
(human-readable plan) and `generated/manifests/chapter-XX-render.json` (the
`--props` payload handed to Remotion).

## Repository layout

```text
course-video-generator/
  input/course.docx          # your prepared course file
  pipeline/                  # Python: parsing, scenes, audio, validation, CLI
  remotion/                  # Remotion app: scenes, actions, diagrams, theme
  assets/audio|images/       # generated narration and extracted images
  generated/                 # chapters, scenes, subtitles, manifests, preview
  output/videos/             # final MP4s
  cache/                     # deterministic content-hash cache
  logs/                      # structured run logs (JSON)
  tests/                     # pytest suite + fixture DOCX generator
```

## Requirements

- Python 3.10+ (`python-docx`, `pydantic`, `Pillow`, `pytest`)
- Node.js 18+ and npm
- ffmpeg/ffprobe on `PATH` (used to encode mock TTS audio and probe duration)
- Chrome or Edge (used by Remotion for rendering; a system browser avoids the
  bundled download)

## Installation

### Python setup

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt   # Windows
source .venv/bin/activate && pip install -r requirements.txt  # macOS/Linux
```

### Node / Remotion setup

```bash
cd remotion
npm.cmd install --cache .npm-cache --no-audit --no-fund
cd ..
```

## Environment variables

Copy `.env.example` to `.env` and adjust as needed. Demo mode needs nothing.

| Variable | Default | Purpose |
| --- | --- | --- |
| `AI_PROVIDER` | `mock` | `mock` or `openai` |
| `OPENAI_API_KEY` | empty | Required when `AI_PROVIDER=openai` |
| `OPENAI_MODEL` | `gpt-4o-mini` | Content model |
| `TTS_PROVIDER` | `kyutai` | `kyutai` (local neural, offline), `edge-tts` (Microsoft neural, online), `sapi` (Windows speech, offline), or `mock` (tone) |
| `TTS_VOICE` | `marius` | Voice: Kyutai presets (`alba`, `marius`, `javert`, `fantine`, ...) or edge-tts names (e.g. `en-GB-RyanNeural`) |
| `TTS_RATE` | `0` | Speech rate, -10..10 (edge-tts and SAPI; calmer teaching pace: -5 to -1) |
| `HF_HOME` | `cache/` | Where Kyutai downloads its model on first use (keep off C: on Windows) |
| `FPS` / `VIDEO_WIDTH` / `VIDEO_HEIGHT` / `CODEC` | 30 / 1920 / 1080 / h264 | Render settings |
| `SCENE_INTRO_PADDING` / `SCENE_OUTRO_PADDING` | 0.3 / 0.5 | Silence around narration |
| `REMOTION_FFMPEG_EXECUTABLE` | none | System ffmpeg path (recommended on Windows) |
| `REMOTION_BROWSER_EXECUTABLE` | none | System Chrome/Edge path (recommended on Windows) |
| `REMOTION_CONCURRENCY` | Remotion default | Parallel render workers (e.g. `8`) |

On Windows, `TMP`/`TEMP` can be pointed at a drive with free space (e.g.
`D:\remotion\.tmp`) because Remotion writes render frames to the OS temp dir.

## Supported DOCX structure

```text
Heading 1  -> starts a chapter  (one output video per Heading 1)
Heading 2  -> starts a section  (transition scene inside the chapter)
Normal     -> explanatory paragraph
Bullets    -> grouped points (revealed progressively, max 5 per scene)
Numbered   -> ordered processes
Images     -> extracted to assets/images/<chapter>/ and taught in place
```

Not supported in V1 (warned, never silent): tables, equations, SmartArt,
embedded video, footnotes, endnotes, tracked changes, floating shapes,
PowerPoint/PDF input.

## CLI commands

```bash
# Full pipeline (all chapters)
python pipeline/main.py input/course.docx

# Pick a video style before rendering (studio | dark | playful | minimal | cinema)
python pipeline/main.py input/course.docx --style dark

# Pick the narration voice before rendering (Kyutai preset or edge-tts name)
python pipeline/main.py input/course.docx --voice marius
python pipeline/main.py input/course.docx --voice javert

# Preview: everything except final rendering + HTML report
python pipeline/main.py input/course.docx --preview

# Single chapter (recovery after a failure)
python pipeline/main.py input/course.docx --chapter 3

# Stage skips / force rebuilds
python pipeline/main.py input/course.docx --skip-ai --skip-tts --skip-render
python pipeline/main.py input/course.docx --force-ai --force-tts --force-render
```

The pipeline prints the nine stages, per-chapter results, a summary
(`3 successful / 1 failed`), and writes a structured log to `logs/run-*.json`.
One failing chapter never blocks the others.

### Preview workflow

`--preview` runs parsing, scene generation, visual planning, audio, timing,
subtitles and validation, skips rendering, and writes
`generated/preview.html` with every scene's type, source text, voiceover,
screen text, concepts, importance, strategy and actions.

### Render workflow

The final stage invokes Remotion per chapter:

```bash
cd remotion
npx.cmd remotion render src/index.ts Tutorial ../output/videos/<chapter>.mp4 \
  --props=../generated/manifests/chapter-XX-render.json --codec=h264
```

The pipeline stages narration audio and extracted images into
`remotion/public/media/` and rewrites the manifest to public-relative paths
because Remotion loads local media through `staticFile()`.

`kyutai` (the default) runs Pocket TTS locally: a neural voice that sounds
human, works fully offline on CPU, and needs no API key. The first narration
run downloads the model once into `cache/` (or `HF_HOME`), then every scene is
synthesized on this machine; audio is cached by narration text + voice so each
line is generated once. `edge-tts` needs internet at narration time and returns
real word-level timestamps for exact subtitle sync; `sapi` is the offline
Windows fallback and `mock` the headless tone.

## Web app (local studio)

A local web app wraps the pipeline so you can pick a document, voice and style
in the browser and start a render with one click - no terminal needed.

```bash
# From the repo root, either double-click webapp\start.cmd or run:
.venv\Scripts\python.exe -m uvicorn webapp.app:app --host 127.0.0.1 --port 8000
```

Then open <http://127.0.0.1:8000>. The studio lets you:

1. Drop in a `.docx` course file (or pick an existing one from `input/`).
2. Choose the narration voice - Kyutai presets with a **Preview voice** button,
   or an online Edge voice. First use of a new voice downloads its small
   embedding once; the model itself stays cached.
3. Choose the video style (`studio`, `dark`, `playful`, `minimal`, `cinema`)
   with live palette swatches.
4. Pick a chapter or render all, optionally forcing new narration / re-render,
   or previewing without rendering.
5. Click **Start creating video** - nothing renders before that click. The
   job panel streams live logs, and finished videos appear in the library with
   inline playback and download links.

Jobs run one at a time; a second click while one is running is rejected until
the first finishes. Logs are written to `logs/site/`.

The web UI follows the Linear-inspired design system documented in
[`DESIGN.md`](DESIGN.md) at the repo root: a near-black canvas with a
four-step surface ladder, hairline borders, Inter typography, and a lavender
accent reserved for the brand mark, primary CTA, focus rings and links.

## Video styles

Five style presets live in `remotion/src/styles.ts` and are selected at render
time with `--style` (or `STYLE` in `.env`): `studio` (light default), `dark`
(navy/cyan), `playful` (warm pastels), `minimal` (black & white serif), and
`cinema` (warm black & gold). Styles control colors, fonts, background
treatment, subtitle style, transition softness and the chapter watermark.
Switching styles is a visual-only change: cached scene plans and narration
audio are reused, and only the render reruns.

## Cache behavior

Deterministic content-hash caching covers every expensive stage:

- DOCX file hash
- Chapter content hash -> scene plans
- Narration text + voice + provider -> TTS audio

If narration text is unchanged, audio is reused. If only visual styling
changes, neither AI nor TTS rerun - only the render does. `--force-*` flags
bypass each layer; `--skip-*` flags fail clearly when no cached output exists.

## Failure recovery

Chapters are processed independently. If chapter 3 fails validation, chapters
1, 2 and 4 still render, and the summary shows exactly what failed. Rerun only
the failed chapter with `--chapter 3`; existing valid MP4s are reused unless
`--force-render` is passed (and a truncated/partial MP4 is detected and
re-rendered automatically).

## Validation

Fatal errors block only the affected chapter: missing/duplicate scene id,
unknown scene type, unknown visual action, missing narration or audio, broken
image path, invalid diagram/target references, negative timing, action after
scene end, schema failures.

Warnings (never blocking): long titles, long screen text or narration, more
than 5 bullets, scenes over 45s, too many high-importance concepts, too many
teaching animations, low-resolution images.

## Example: DOCX source to scene JSON

Source paragraph in the fixture:

```text
Machine learning is a method that allows computers to learn patterns from data
and use those patterns to make predictions without being explicitly programmed
for every individual decision.
```

Becomes this definition scene (see `generated/scenes/chapter-01/scene-003.json`
in a real run):

```json
{
  "id": "scene-003",
  "type": "definition",
  "title": "Machine learning is a method that allows computers to learn...",
  "screenText": "Machine learning is a method that allows computers to learn patterns from data and use those patterns to make predictions.",
  "voiceover": "Machine learning is a method that allows computers to learn patterns from data and use those patterns to make predictions without being explicitly programmed for every individual decision.",
  "keyConcepts": [
    {"id": "c1", "text": "MACHINE", "importance": "high"},
    {"id": "c2", "text": "LEARNING", "importance": "high"},
    {"id": "c3", "text": "DATA", "importance": "medium"}
  ],
  "visualStrategy": "definition",
  "visualActions": [
    {"type": "underline", "target": "c1", "startSec": 1.4, "durationSec": 0.9},
    {"type": "handwrite", "target": "c2", "startSec": 3.0, "durationSec": 1.1}
  ],
  "audio": {
    "path": "assets/audio/chapter-01/scene-003.mp3",
    "durationSeconds": 13.42
  },
  "subtitles": [
    {"start": 0.3, "end": 3.0, "text": "Machine learning is a method that allows computers"},
    {"start": 3.0, "end": 6.1, "text": "to learn patterns from data and use those patterns"}
  ],
  "durationSeconds": 14.22
}
```

## Testing

```bash
# Python unit + integration tests (parse -> scenes -> mocked TTS -> validation)
python -m pytest tests -q

# Regenerate the 3-chapter fixture document
python tests/fixtures/generate_course_docx.py --out input/course.docx

# Remotion type check
cd remotion && npx.cmd tsc --noEmit

# Remotion render smoke (all scene + action types, short frame range)
cd remotion && npx.cmd remotion render src/index.ts TestSuite ../output/test-suite.mp4 \
  --frames=0-30 --codec=h264
```

The integration test (`tests/test_integration.py`) runs the whole chain through
`DOCX -> parsed JSON -> scenes -> mocked TTS -> render manifest`, asserting
zero validation errors, audio for every narrated scene, subtitles, and a
positive total duration.

## Known V1 limitations

- Tables, equations, SmartArt, video, footnotes, endnotes and tracked changes
  are detected and warned about but not taught.
- One concrete AI provider (mock, plus optional OpenAI); TTS ships with four
  providers (kyutai, edge-tts, sapi, mock).
- Kyutai has no word-level timestamps, so subtitle timing is estimated
  deterministically from narration length; edge-tts supplies real word timings.
- Diagram families are predefined (process, relationship, comparison,
  input-process-output, cause-effect); arbitrary diagram generation is out of
  scope for V1.
- `TTS_PROVIDER=kyutai` uses Kyutai Pocket TTS (local neural voice, offline,
  presets: alba, marius, javert, fantine, jean, cosette, eponine, azelma);
  `edge-tts` uses Microsoft neural voices and needs internet at narration time;
  `sapi` uses real Windows speech offline; `mock` is a tone for headless demos.

## Security / reliability

- AI output and scene JSON are data only; nothing is ever executed.
- Every external AI output passes Pydantic schema validation, with one repair
  retry and a hard chapter stop on a second failure.
- File paths are resolved against the workspace; no arbitrary code runs from
  DOCX content.
