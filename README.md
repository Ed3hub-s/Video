# Course Video Generator

A local-first system that converts a structured `.docx` course document into narrated tutorial videos, one video per chapter.

This is designed as a teaching engine rather than a slide generator. Each meaningful scene can contain narration, concise on-screen text, ranked concepts, diagrams, subtitles, and deliberate teaching actions such as handwriting, underlines, arrows, highlights, boxes, and callouts.

```text
DOCX
  -> Parsing
  -> Chapters / Sections
  -> Scene Planning
  -> Narration
  -> Visual Importance
  -> Visual Actions
  -> TTS Audio
  -> Timing
  -> Subtitles
  -> Validation
  -> Remotion Render
  -> MP4 per chapter
```

---

## System overview

A correctly formatted course document can be processed with:

```bash
python pipeline/main.py input/course.docx
```

The default AI content provider is deterministic and local:

```text
AI_PROVIDER=mock
```

The default narration engine is Kokoro:

```text
TTS_PROVIDER=kokoro
TTS_VOICE=af_heart
```

OpenAI can optionally be used for the content-generation layer when an API key is configured.

The Python pipeline handles document understanding and orchestration. Remotion handles presentation and rendering.

---

## Architecture

The project is divided into two systems connected through structured JSON.

### Python owns the thinking

Python is responsible for:

* DOCX parsing
* unsupported-element detection and warnings
* content normalization
* text splitting
* AI content generation
* scene planning
* concept importance
* visual-action planning
* TTS narration
* audio timing
* subtitles
* validation
* caching
* run logging
* chapter orchestration
* render-manifest generation

### Remotion owns the presentation

Remotion is responsible for:

* layout
* typography
* scene composition
* teaching motion
* transitions
* visual actions
* predefined diagrams
* subtitles
* narration playback
* final MP4 rendering

The primary boundary between Python and Remotion is:

```text
generated/manifests/chapter-XX.json
generated/manifests/chapter-XX-render.json
```

The render manifest is serialized specifically for the TypeScript/Remotion contract, including aliased JSON fields such as `from`.

---

## Repository layout

```text
course-video-generator/
│
├── input/
│   └── uploads/                 # uploaded/source DOCX files
│
├── pipeline/
│   ├── audio/                   # TTS, timing, subtitles
│   ├── cache/                   # content-hash cache implementation
│   ├── content/                 # AI providers, schemas, scene generation
│   ├── docx_parser/             # DOCX parsing and image extraction
│   ├── render/                  # Remotion manifest + render invocation
│   ├── validation/              # chapter validation
│   ├── visual/                  # concept importance + visual planning
│   └── main.py                  # main CLI pipeline
│
├── remotion/                    # React / Remotion renderer
├── webapp/                      # local FastAPI studio
├── assets/
│   ├── audio/
│   └── images/
├── generated/
├── output/
│   └── videos/
├── cache/
├── logs/
├── tests/
├── requirements.txt
├── Makefile
└── README.md
```

---

## Requirements

### Python

Python 3.10 or newer.

Major Python dependencies include:

* `python-docx`
* `pydantic`
* `Pillow`
* `kokoro`
* `soundfile`
* `misaki`
* `pocket-tts`
* `edge-tts`
* `fastapi`
* `uvicorn`
* `python-multipart`
* `pytest`

Install the complete dependency set from `requirements.txt`.

### Node.js

Node.js 18 or newer with npm.

### Rendering

The rendering pipeline may require:

* FFmpeg
* FFprobe
* Chrome, Chromium, or Microsoft Edge

Remotion can use its normal browser/runtime behavior, or system executables can be supplied through environment variables.

---

## Installation

### Python setup

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it.

Windows:

```bat
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Install the dependencies:

```bash
python -m pip install -r requirements.txt
```

---

### Node / Remotion setup

From the repository root:

```bash
cd remotion
npm ci
cd ..
```

`npm ci` uses the committed `package-lock.json` for a reproducible Node installation.

---

## Environment configuration

`pipeline/config.py` reads configuration from environment variables.

`.env.example` documents the available settings and recommended defaults.

If your shell, editor, launcher, or deployment environment loads `.env` files automatically, you can use `.env.example` as the starting point. Otherwise, set the required variables in the process environment directly.

### AI configuration

| Variable          | Default                     | Purpose                                 |
| ----------------- | --------------------------- | --------------------------------------- |
| `AI_PROVIDER`     | `mock`                      | AI content provider: `mock` or `openai` |
| `OPENAI_API_KEY`  | empty                       | Required when using OpenAI              |
| `OPENAI_MODEL`    | `gpt-4o-mini`               | OpenAI model                            |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | OpenAI-compatible API base URL          |

### TTS configuration

| Variable       | Default       | Purpose                                              |
| -------------- | ------------- | ---------------------------------------------------- |
| `TTS_PROVIDER` | `kokoro`      | Narration provider                                   |
| `TTS_VOICE`    | `af_heart`    | Narration voice                                      |
| `TTS_RATE`     | `0`           | Speech-rate adjustment for providers that support it |
| `HF_HOME`      | project cache | Optional model-cache location                        |

Supported TTS backends include:

* `kokoro`
* `kyutai`
* `edge-tts`
* `sapi`
* `mock`

Kokoro is the default narration backend.

Kyutai is also available for local neural narration.

Edge TTS requires internet access.

SAPI is a Windows speech fallback.

The mock provider is intended for deterministic testing and pipeline development.

---

## Rendering configuration

| Variable       | Default |
| -------------- | ------- |
| `FPS`          | `30`    |
| `VIDEO_WIDTH`  | `1920`  |
| `VIDEO_HEIGHT` | `1080`  |
| `CODEC`        | `h264`  |

Default output:

```text
1920 x 1080
30 FPS
H.264
```

---

## Styles

Available video styles:

```text
studio
dark
playful
minimal
cinema
```

Default:

```text
STYLE=studio
```

Example:

```bash
python pipeline/main.py input/course.docx --style dark
```

Styles control presentation properties such as:

* background
* foreground
* accent colors
* typography
* subtitle presentation
* visual treatment

Changing the style does not require regenerating narration.

---

## Transitions

Available scene transitions:

```text
fade
slide
wipe
zoom
```

Default:

```text
TRANSITION=fade
```

A transition is included in the render manifest and interpreted by the Remotion renderer.

---

## Timing

Default timing configuration:

```text
SCENE_INTRO_PADDING=0.3
SCENE_OUTRO_PADDING=0.5
```

These values provide breathing room around scene narration.

---

## Optional Remotion configuration

### FFmpeg

If Remotion needs an explicit FFmpeg executable:

```text
REMOTION_FFMPEG_EXECUTABLE
```

Windows example:

```text
C:\ffmpeg\bin\ffmpeg.exe
```

### Browser

An installed browser can optionally be supplied with:

```text
REMOTION_BROWSER_EXECUTABLE
```

Windows Chrome example:

```text
C:\Program Files\Google\Chrome\Application\chrome.exe
```

The web application only applies known Windows executable paths automatically when those files actually exist. Explicit environment configuration always takes precedence.

### Concurrency

Parallel rendering can be controlled with:

```text
REMOTION_CONCURRENCY
```

Example:

```text
REMOTION_CONCURRENCY=8
```

### Temporary files

Temporary rendering data can be moved to another drive with:

```text
TMP
TEMP
```

This can be useful when the system drive has limited free space.

---

## Supported DOCX structure

The parser interprets normal Word document structure.

```text
Heading 1
    -> starts a chapter
    -> one output video per chapter

Heading 2
    -> starts a section

Normal paragraph
    -> explanatory content

Bullets
    -> grouped concepts or points

Numbered lists
    -> ordered steps or processes

Images
    -> extracted and associated with source content
```

Unsupported elements are detected where possible and surfaced as warnings instead of being silently ignored.

Examples include:

* tables
* equations
* SmartArt
* embedded video
* footnotes
* endnotes
* tracked changes
* unsupported floating content

Equation-only paragraphs also preserve their warning even when they contain no usable text or image.

---

## CLI usage

### Full pipeline

```bash
python pipeline/main.py input/course.docx
```

### Select a style

```bash
python pipeline/main.py input/course.docx --style dark
```

### Select a TTS provider

```bash
python pipeline/main.py input/course.docx --tts-provider kokoro
```

### Select a narration voice

```bash
python pipeline/main.py input/course.docx --voice af_heart
```

Kyutai example:

```bash
python pipeline/main.py input/course.docx --tts-provider kyutai --voice marius
```

### Preview without final rendering

```bash
python pipeline/main.py input/course.docx --preview
```

### Process one chapter

```bash
python pipeline/main.py input/course.docx --chapter 3
```

### Skip pipeline stages

```bash
python pipeline/main.py input/course.docx --skip-ai --skip-tts --skip-render
```

### Force regeneration

```bash
python pipeline/main.py input/course.docx --force-ai --force-tts --force-render
```

---

## Pipeline stages

A normal run processes each chapter through the major stages of the system:

```text
DOCX parsing
    ↓
chapter extraction
    ↓
scene generation
    ↓
visual planning
    ↓
TTS
    ↓
timing
    ↓
subtitles
    ↓
validation
    ↓
render manifest
    ↓
Remotion
    ↓
MP4
```

Chapters are processed independently.

A failure in one chapter does not automatically prevent other chapters from completing.

Structured run logs are written under:

```text
logs/
```

---

## Preview workflow

Preview mode runs the content pipeline without performing the final Remotion render:

```bash
python pipeline/main.py input/course.docx --preview
```

The preview workflow can include:

* parsing
* scene generation
* visual planning
* narration
* timing
* subtitles
* validation

It also produces a human-readable preview report from the generated plan.

---

## Render workflow

The Python renderer writes:

```text
generated/manifests/chapter-XX-render.json
```

It then invokes Remotion using that manifest as the composition props.

A manual equivalent looks like:

```bash
cd remotion
npx remotion render src/index.ts Tutorial ../output/videos/chapter.mp4 --props=../generated/manifests/chapter-XX-render.json --codec=h264
```

Narration and image files required by Remotion are staged under:

```text
remotion/public/media/
```

The generated manifest references those files through public-relative paths suitable for Remotion's `staticFile()` behavior.

---

## Python → Remotion data contract

Python models may use internal field names that differ from the JSON field names consumed by TypeScript.

For example, Python uses:

```text
from_id
```

for fields that must be emitted as:

```text
from
```

in render JSON.

Render manifests therefore serialize Pydantic models using their defined aliases.

The integration test checks that Python-only fields such as `from_id` do not leak into the Remotion manifest.

---

## Narration

### Kokoro

Kokoro is the default narration backend:

```text
TTS_PROVIDER=kokoro
TTS_VOICE=af_heart
```

It provides local neural narration after its required resources are available.

### Kyutai

Kyutai Pocket TTS is also supported.

Example voices include:

```text
alba
marius
javert
fantine
jean
cosette
eponine
azelma
```

### Edge TTS

Edge TTS provides Microsoft neural voices and requires internet connectivity during synthesis.

### SAPI

SAPI is available as a Windows-local speech fallback.

### Mock

The mock TTS backend is intended for automated tests and deterministic development runs.

---

## Web app

A local FastAPI studio is provided under:

```text
webapp/
```

Start it from the repository root:

```bash
python -m uvicorn webapp.app:app --host 127.0.0.1 --port 8000
```

Then open:

```text
http://127.0.0.1:8000
```

The studio can:

1. Upload a `.docx` course document.
2. Select an existing document from `input/`.
3. Select supported web-studio narration options.
4. Preview supported voices.
5. Select a video style.
6. Select one chapter or all chapters.
7. Force narration regeneration.
8. Force rendering.
9. Run without final rendering.
10. Watch live job logs.
11. View generated videos.

The current studio voice selector exposes Kyutai and Edge TTS options.

The CLI configuration supports additional TTS providers, including Kokoro.

Only one render job runs at a time.

Job logs are written under:

```text
logs/site/
```

---

## Web upload handling

Uploads are restricted to `.docx` filenames and stored under:

```text
input/uploads/
```

The upload endpoint:

* sanitizes filenames
* writes data incrementally instead of loading the entire file into RAM
* enforces a 200 MB maximum
* writes through a temporary partial file
* deletes incomplete files when an upload fails
* only publishes the destination file after the upload succeeds

Selected render documents are resolved and verified to remain inside the repository's `input/` directory.

---

## Video styles

Five visual presets live in the Remotion application:

### Studio

Light and clean with the primary accent.

### Dark

Dark navy/black presentation with cyan accents.

### Playful

Warm colors and softer visual treatment.

### Minimal

Restrained black-and-white presentation.

### Cinema

Dark, warm presentation with gold accents.

Changing style affects rendering only. Existing content-generation and narration results can still be reused when their relevant inputs have not changed.

---

## Cache behavior

The project uses deterministic content hashes to avoid repeating expensive work.

Caching includes:

* source/document hashes
* chapter content
* generated scene plans
* narration output

Narration cache identity includes contextual information such as:

* TTS provider
* voice/provider cache tag
* chapter
* scene
* narration text

Cached audio is only reused when its stored path still matches the expected output and the file actually exists.

This prevents one scene from accidentally reusing metadata pointing at another scene's audio file.

Force flags can bypass relevant caches when regeneration is required.

---

## Failure recovery

Chapters are processed independently.

If one chapter fails validation or rendering, the pipeline can continue with other chapters.

A specific chapter can later be retried with:

```bash
python pipeline/main.py input/course.docx --chapter 3
```

Relevant stages can also be forced:

```bash
python pipeline/main.py input/course.docx --chapter 3 --force-tts --force-render
```

---

## Validation

Validation separates fatal errors from warnings.

Fatal problems can include:

* missing scene identifiers
* duplicate scene identifiers
* invalid scene types
* invalid visual actions
* missing narration
* missing required audio
* broken image references
* invalid diagram references
* invalid visual-action targets
* negative timing
* actions occurring outside scene duration
* schema failures

Warnings can include:

* overly long titles
* excessive on-screen text
* excessive narration
* too many bullets
* unusually long scenes
* excessive teaching actions
* low-resolution images

Validation issues receive readable machine-friendly codes derived from their actual messages instead of generic `error` or `warning` identifiers.

---

## Example scene JSON

A source paragraph might become a scene similar to:

```json
{
  "id": "scene-003",
  "type": "definition",
  "title": "Machine learning",
  "screenText": "Machine learning identifies useful patterns in data.",
  "voiceover": "Machine learning allows computers to learn patterns from data and use those patterns to make predictions.",
  "keyConcepts": [
    {
      "id": "c1",
      "text": "Machine learning",
      "importance": "high"
    },
    {
      "id": "c2",
      "text": "Data",
      "importance": "high"
    }
  ],
  "visualStrategy": "definition",
  "visualActions": [
    {
      "type": "underline",
      "target": "c1",
      "startSec": 1.4,
      "durationSec": 0.9
    }
  ],
  "audio": {
    "path": "assets/audio/chapter-01/scene-003.mp3",
    "durationSeconds": 8.4
  },
  "durationSeconds": 9.2
}
```

The exact generated content depends on the selected content provider and source document.

---

## Testing

### Full Python test suite

```bash
python -m pytest tests -q
```

### Unit tests

```bash
python -m pytest tests -m "not integration" -q
```

### Integration tests

```bash
python -m pytest tests -m integration -q
```

### Generate the fixture document

```bash
python tests/fixtures/generate_course_docx.py --out input/course.docx
```

### Remotion type check

```bash
cd remotion
npx tsc --noEmit
cd ..
```

### Remotion smoke render

```bash
cd remotion
npx remotion render src/index.ts TestSuite ../output/test-suite.mp4 --frames=0-30 --codec=h264
cd ..
```

The integration suite exercises the pipeline through:

```text
DOCX
  -> parsed course
  -> scenes
  -> mocked narration
  -> timing
  -> subtitles
  -> validation
  -> render manifest
```

It also verifies that Python-internal schema names do not leak into the Remotion JSON contract.

---

## Makefile

Common developer commands are available through the `Makefile`.

Examples:

```bash
make setup
make fixture
make preview
make render
make test
make remotion-install
make remotion-typecheck
make remotion-smoke
make remotion-preview
make clean
```

The Makefile defaults to:

```text
python
npm
npx
```

These can be overridden when required.

For example:

```bash
make PYTHON=py
```

or on a Windows setup that specifically requires command-wrapper names:

```bash
make NPM=npm.cmd NPX=npx.cmd remotion-install
```

---

## Cleaning generated data

Run:

```bash
make clean
```

The clean target removes generated/runtime directories including:

```text
generated/
output/
cache/
logs/
.tmp/
```

Source code and input documents are not removed by the clean command.

---

## Known V1 limitations

* Tables are detected but are not yet converted into teaching scenes.
* Equations are detected and warned about but are not rendered as mathematical notation.
* SmartArt is unsupported.
* Embedded video is unsupported.
* Footnotes and endnotes are not converted into teaching scenes.
* Tracked changes are not interpreted as final educational content.
* Diagram generation is based on predefined visual families rather than arbitrary free-form diagram generation.
* Kokoro and other local TTS backends do not necessarily provide the same timing metadata as online speech services.
* Edge TTS requires internet access.
* SAPI is Windows-specific.
* The local web studio currently exposes a smaller TTS-provider selection than the CLI.

---

## Security and reliability

The system treats AI output and generated scene plans as data.

Key reliability measures include:

* Pydantic schema validation
* validation before rendering
* isolated chapter processing
* deterministic caching
* expected-path verification for cached audio
* structured run logs
* subprocess commands executed as argument arrays rather than shell strings
* render documents restricted to the `input/` directory
* sanitized upload filenames
* streamed upload-size enforcement
* cleanup of incomplete uploads
* Remotion JSON serialization using explicit schema aliases

OpenAI credentials are read from environment configuration and are not intended to be stored in source code.

---

## Development philosophy

The project keeps responsibilities deliberately separated:

```text
Python decides what should be taught.

Remotion decides how it should be presented.
```

That separation makes the generated teaching plan inspectable, testable, cacheable, and independent from the renderer.
