"""TTS abstraction.

ed3hub currently supports five providers:

- KokoroTTS (default): local neural TTS used by ed3hub for production
  narration. Runs locally, requires no API key, and supports curated
  American and British English voices.
- KyutaiTTS: Kyutai Pocket TTS local neural voice. Retained temporarily
  as a fallback while Kokoro becomes the primary engine.
- EdgeTTS: Microsoft neural voices through the edge-tts endpoint.
  Online, no API key, and provides word-level timestamps.
- SapiTTS: Windows built-in System.Speech voices.
- MockTTS: deterministic synthetic audio for tests and demos.
"""

from __future__ import annotations

import asyncio
import json
import math
import os
import re
import shutil
import subprocess
import wave
from pathlib import Path

try:
    import winreg
except ImportError:  # pragma: no cover - non-Windows
    winreg = None

from pipeline.audio.duration import audio_duration
from pipeline.content.schemas import AudioMetadata
from pipeline.content.text_splitter import word_count


class TTSProvider:
    name = "base"
    cache_tag = "base"

    def generate(self, text: str, out_path: Path) -> AudioMetadata:
        raise NotImplementedError


def _encode_to_mp3(
    wav_path: Path,
    final_path: Path,
    *,
    clean_neural_voice: bool = False,
) -> Path:
    """Encode WAV to MP3 with ffmpeg when available; keep WAV otherwise."""

    ffmpeg = shutil.which("ffmpeg")

    if ffmpeg is None:
        return wav_path

    audio_filters = []

    if clean_neural_voice:
        audio_filters.extend(
            [
                "silenceremove="
                "start_periods=1:"
                "start_duration=0.06:"
                "start_threshold=-50dB:"
                "start_silence=0.02",
                "highpass=f=70:p=2",
                "lowpass=f=9000:p=2",
                "afade=t=in:st=0:d=0.10",
                "adelay=120:all=1",
            ]
        )

    audio_filters.append(
        "loudnorm=I=-16:TP=-1.5:LRA=11"
    )

    try:
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-i",
                str(wav_path),
                "-af",
                ",".join(audio_filters),
                "-codec:a",
                "libmp3lame",
                "-q:a",
                "5",
                str(final_path),
            ],
            capture_output=True,
            timeout=120,
            check=True,
        )

        wav_path.unlink(missing_ok=True)
        return final_path

    except (subprocess.SubprocessError, OSError):
        return wav_path


def _finish_audio(final_path: Path) -> AudioMetadata:
    return AudioMetadata(
        path=str(final_path.resolve()),
        durationSeconds=round(audio_duration(final_path), 3),
    )


class MockTTS(TTSProvider):
    """Deterministic offline TTS: gentle spoken-syllable tone + MP3 encode."""

    name = "mock"
    cache_tag = "mock"

    def __init__(self, sample_rate: int = 16000) -> None:
        self.sample_rate = sample_rate

    def generate(self, text: str, out_path: Path) -> AudioMetadata:
        out_path.parent.mkdir(parents=True, exist_ok=True)

        words = max(word_count(text), 1)
        duration = 0.42 * words + 0.55

        wav_path = out_path.with_suffix(".wav")

        self._write_wav(
            text,
            wav_path,
            duration,
        )

        final_path = _encode_to_mp3(
            wav_path,
            out_path,
        )

        return _finish_audio(final_path)

    def _write_wav(
        self,
        text: str,
        wav_path: Path,
        duration: float,
    ) -> None:
        rate = self.sample_rate
        frames = int(duration * rate)
        words = word_count(text)

        with wave.open(str(wav_path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(rate)

            samples = bytearray()

            for i in range(frames):
                t = i / rate

                syllable = int(
                    t / (duration / max(words, 1))
                )

                freq = 160.0 + (syllable % 5) * 24.0

                envelope = (
                    min(1.0, t * 8.0)
                    * math.exp(
                        -3.0
                        * (
                            t
                            % (
                                duration
                                / max(words, 1)
                            )
                        )
                        * 1.4
                    )
                )

                value = int(
                    9000
                    * envelope
                    * math.sin(
                        2
                        * math.pi
                        * freq
                        * t
                    )
                )

                samples.extend(
                    value.to_bytes(
                        2,
                        "little",
                        signed=True,
                    )
                )

            wav.writeframes(bytes(samples))


def _registry_sapi_voices() -> list[str]:
    """Read SAPI5 voice names from the registry."""

    if winreg is None:
        return []

    names: list[str] = []

    roots = (
        r"SOFTWARE\Microsoft\Speech\Voices\Tokens",
        r"SOFTWARE\WOW6432Node\Microsoft\Speech\Voices\Tokens",
    )

    for root in roots:
        try:
            tokens = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                root,
            )
        except OSError:
            continue

        count = winreg.QueryInfoKey(tokens)[0]

        for index in range(count):
            try:
                token = winreg.EnumKey(
                    tokens,
                    index,
                )

                attrs = winreg.OpenKey(
                    tokens,
                    token + r"\Attributes",
                )

                name = winreg.QueryValueEx(
                    attrs,
                    "Name",
                )[0]

            except OSError:
                continue

            if name and name not in names:
                names.append(name)

    return names


def _powershell_sapi_voices() -> list[str]:
    script = (
        "Add-Type -AssemblyName System.Speech; "
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        "$s.GetInstalledVoices() | ForEach-Object { $_.VoiceInfo.Name }; "
        "$s.Dispose()"
    )

    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                script,
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

    except (OSError, subprocess.SubprocessError):
        return []

    if result.returncode != 0:
        return []

    return [
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip()
    ]


def _list_sapi_voices() -> list[str]:
    """Return installed Windows SAPI voice names."""

    voices = _registry_sapi_voices()

    if voices:
        return voices

    return _powershell_sapi_voices()


_PREFERRED_VOICES = (
    "zira",
    "david",
    "mark",
    "hazel",
    "susan",
    "aria",
    "guy",
    "jenny",
)


_SENTENCE_SPLIT_RE = re.compile(
    r"(?<=[.!?])\s+"
)

_WORD_SPLIT_RE = re.compile(
    r"\s+"
)


def _tts_chunks(
    text: str,
    count_tokens,
    max_tokens: int = 45,
) -> list[str]:
    """Split narration into chunks for Pocket TTS.

    This remains for the legacy Kyutai provider.
    """

    sentences = [
        part.strip()
        for part in _SENTENCE_SPLIT_RE.split(text)
        if part.strip()
    ]

    chunks: list[str] = []
    current = ""

    for sentence in sentences:
        sentence_tokens = count_tokens(sentence)

        if sentence_tokens <= max_tokens:
            if (
                current
                and count_tokens(current)
                + sentence_tokens
                > max_tokens
            ):
                chunks.append(current)
                current = sentence

            else:
                current = (
                    f"{current} {sentence}".strip()
                    if current
                    else sentence
                )

            continue

        if current:
            chunks.append(current)
            current = ""

        words = [
            word
            for word in _WORD_SPLIT_RE.split(sentence)
            if word
        ]

        piece = ""

        for word in words:
            candidate = (
                f"{piece} {word}".strip()
                if piece
                else word
            )

            if (
                piece
                and count_tokens(candidate)
                > max_tokens
            ):
                chunks.append(piece)
                piece = word

            else:
                piece = candidate

        if piece:
            current = piece

    if current:
        chunks.append(current)

    return chunks or [text.strip()]


def _pick_voice(
    voices: list[str],
    preferred: str | None,
) -> str | None:
    if preferred:
        needle = preferred.lower()

        for voice in voices:
            if needle in voice.lower():
                return voice

    for token in _PREFERRED_VOICES:
        for voice in voices:
            if token in voice.lower():
                return voice

    return voices[0] if voices else None


class SapiTTS(TTSProvider):
    """Real speech using built-in Windows voices."""

    name = "sapi"

    def __init__(
        self,
        voice: str | None = None,
        rate: int = 0,
    ) -> None:
        self.voice_filter = voice or ""
        self.rate = rate

        installed = _list_sapi_voices()

        if not installed:
            raise RuntimeError(
                "Windows SAPI is unavailable "
                "(no enabled voices). "
                "Install a Windows speech voice "
                "or set TTS_PROVIDER=mock."
            )

        self.voice = (
            _pick_voice(
                installed,
                self.voice_filter,
            )
            or installed[0]
        )

        self.cache_tag = (
            f"sapi:{self.voice}"
        )

    def generate(
        self,
        text: str,
        out_path: Path,
    ) -> AudioMetadata:
        out_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        wav_path = out_path.with_suffix(
            ".wav"
        )

        narration_txt = (
            out_path.parent
            / f"{out_path.stem}.txt"
        )

        narration_txt.write_text(
            text,
            encoding="utf-8-sig",
        )

        self._synthesize(
            narration_txt,
            wav_path,
        )

        narration_txt.unlink(
            missing_ok=True
        )

        final_path = _encode_to_mp3(
            wav_path,
            out_path,
        )

        return _finish_audio(
            final_path
        )

    def _synthesize(
        self,
        narration_txt: Path,
        wav_path: Path,
    ) -> None:
        script = "\n".join(
            [
                "$ErrorActionPreference = 'Stop'",
                "Add-Type -AssemblyName System.Speech",
                "$synth = New-Object "
                "System.Speech.Synthesis.SpeechSynthesizer",
                (
                    "$synth.SetOutputToWaveFile"
                    f"('{_ps_quote(str(wav_path))}')"
                ),
                f"$synth.Rate = {int(self.rate)}",
                (
                    "$text = Get-Content "
                    "-Raw -Encoding UTF8 "
                    f"-LiteralPath "
                    f"'{_ps_quote(str(narration_txt))}'"
                ),
                "$synth.Speak($text)",
                "$synth.Dispose()",
            ]
        )

        script_path = (
            wav_path.parent
            / f"{wav_path.stem}.ps1"
        )

        script_path.write_text(
            script,
            encoding="utf-8-sig",
        )

        try:
            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(script_path),
                ],
                capture_output=True,
                text=True,
                timeout=180,
            )

        finally:
            script_path.unlink(
                missing_ok=True
            )

        if result.returncode != 0:
            detail = (
                result.stderr
                or result.stdout
                or ""
            ).strip()[-800:]

            raise RuntimeError(
                f"SAPI synthesis failed: {detail}"
            )


def _ps_quote(value: str) -> str:
    return value.replace(
        "'",
        "''",
    )


class EdgeTTS(TTSProvider):
    """Microsoft neural voices via edge-tts."""

    name = "edge-tts"

    def __init__(
        self,
        voice: str = "en-GB-RyanNeural",
        rate: int = 0,
    ) -> None:
        self.voice = voice

        self.rate_percent = (
            f"{int(rate):+d}%"
        )

        self.cache_tag = (
            f"edge-tts:"
            f"{voice}:"
            f"{self.rate_percent}"
        )

    def generate(
        self,
        text: str,
        out_path: Path,
    ) -> AudioMetadata:
        out_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        word_path = out_path.with_suffix(
            ".words.json"
        )

        asyncio.run(
            self._synthesize(
                text,
                out_path,
                word_path,
            )
        )

        metadata = _finish_audio(
            out_path
        )

        if word_path.exists():
            metadata = metadata.model_copy(
                update={
                    "wordTimestampsPath": str(
                        word_path
                    )
                }
            )

        return metadata

    async def _synthesize(
        self,
        text: str,
        mp3_path: Path,
        word_path: Path,
    ) -> None:
        import edge_tts

        communicate = edge_tts.Communicate(
            text,
            self.voice,
            rate=self.rate_percent,
            volume="+0%",
            boundary="WordBoundary",
        )

        words: list[dict] = []

        with open(
            mp3_path,
            "wb",
        ) as handle:
            async for chunk in communicate.stream():

                if chunk["type"] == "audio":
                    handle.write(
                        chunk["data"]
                    )

                elif (
                    chunk["type"]
                    == "WordBoundary"
                ):
                    words.append(
                        {
                            "word": (
                                chunk["text"]
                                .strip()
                            ),
                            "start": round(
                                chunk["offset"]
                                / 10_000_000,
                                3,
                            ),
                            "end": round(
                                (
                                    chunk["offset"]
                                    + chunk["duration"]
                                )
                                / 10_000_000,
                                3,
                            ),
                        }
                    )

        if words:
            word_path.write_text(
                json.dumps(
                    words,
                    indent=2,
                ),
                encoding="utf-8",
            )

        if (
            not mp3_path.exists()
            or mp3_path.stat().st_size == 0
        ):
            raise RuntimeError(
                "edge-tts produced "
                "no audio output"
            )


class KokoroTTS(TTSProvider):
    """Primary local neural TTS engine for ed3hub.

    Kokoro synthesizes narration locally at 24 kHz.

    Important:
    document paragraph formatting is normalized before synthesis.
    Punctuation remains intact, but repeated whitespace and newlines
    are collapsed. This prevents artificial long pauses between
    paragraphs while retaining natural sentence-level timing.
    """

    name = "kokoro"

    SAMPLE_RATE = 24000

    CURATED_VOICES = (
        "af_heart",
        "af_bella",
        "af_sarah",
        "am_michael",
        "bf_emma",
        "bm_george",
    )

    def __init__(
        self,
        voice: str = "af_heart",
        rate: int = 0,
    ) -> None:
        self.voice = (
            voice or "af_heart"
        ).strip()

        if (
            self.voice
            not in self.CURATED_VOICES
        ):
            raise RuntimeError(
                f"Kokoro voice "
                f"'{self.voice}' "
                f"is not enabled for ed3hub. "
                f"Available voices: "
                f"{', '.join(self.CURATED_VOICES)}"
            )

        if self.voice.startswith(
            ("af_", "am_")
        ):
            self.lang_code = "a"

        elif self.voice.startswith(
            ("bf_", "bm_")
        ):
            self.lang_code = "b"

        else:
            raise RuntimeError(
                f"Cannot determine Kokoro "
                f"language/accent for voice "
                f"'{self.voice}'."
            )

        # TTS_RATE behaves like a percentage:
        #
        #   0   -> 1.00x
        #   10  -> 1.10x
        #   -10 -> 0.90x
        #
        # Restrict extreme speeds because
        # educational narration should remain
        # intelligible.
        self.speed = max(
            0.70,
            min(
                1.30,
                1.0 + (rate / 100.0),
            ),
        )

        # Increment the version if narration
        # preprocessing changes. This avoids
        # accidentally reusing incompatible
        # cached audio.
        self.cache_tag = (
            f"kokoro:v2:"
            f"{self.voice}:"
            f"{self.speed:.2f}"
        )

        self._pipeline = None

    @staticmethod
    def normalize_narration(
        text: str,
    ) -> str:
        """Normalize narration for natural speech.

        PDF/DOCX paragraph layout should not determine
        how long the narrator pauses.

        Newlines and repeated whitespace are collapsed,
        while punctuation remains untouched.
        """

        return re.sub(
            r"\s+",
            " ",
            text,
        ).strip()

    def _load_pipeline(self):
        if self._pipeline is None:
            try:
                from kokoro import KPipeline

            except ImportError as exc:
                raise RuntimeError(
                    "Kokoro is not installed. "
                    "Run: "
                    "`pip install "
                    "\"kokoro==0.9.4\" "
                    "soundfile "
                    "\"misaki[en]\"`"
                ) from exc

            self._pipeline = KPipeline(
                lang_code=self.lang_code
            )

        return self._pipeline

    def generate(
        self,
        text: str,
        out_path: Path,
    ) -> AudioMetadata:
        try:
            import numpy as np
            import soundfile as sf

        except ImportError as exc:
            raise RuntimeError(
                "Kokoro audio dependencies "
                "are missing. Run: "
                "`pip install numpy soundfile`"
            ) from exc

        out_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        narration = (
            self.normalize_narration(
                text
            )
        )

        if not narration:
            raise RuntimeError(
                "Kokoro received "
                "empty narration."
            )

        pipeline = (
            self._load_pipeline()
        )

        chunks: list = []

        generator = pipeline(
            narration,
            voice=self.voice,
            speed=self.speed,
        )

        for result in generator:
            audio = result.audio

            if audio is None:
                continue

            if hasattr(
                audio,
                "detach",
            ):
                audio = audio.detach()

            if hasattr(
                audio,
                "cpu",
            ):
                audio = audio.cpu()

            if hasattr(
                audio,
                "numpy",
            ):
                audio = audio.numpy()

            audio_array = (
                np.asarray(
                    audio,
                    dtype=np.float32,
                )
                .reshape(-1)
            )

            if audio_array.size:
                chunks.append(
                    audio_array
                )

        if not chunks:
            raise RuntimeError(
                "Kokoro produced "
                "no audio output."
            )

        combined = np.concatenate(
            chunks
        )

        combined = np.clip(
            combined,
            -1.0,
            1.0,
        )

        wav_path = (
            out_path.with_suffix(
                ".wav"
            )
        )

        sf.write(
            wav_path,
            combined,
            self.SAMPLE_RATE,
        )

        final_path = _encode_to_mp3(
            wav_path,
            out_path,
            clean_neural_voice=True,
        )

        return _finish_audio(
            final_path
        )


class KyutaiTTS(TTSProvider):
    """Kyutai Pocket TTS local neural voice.

    This provider is retained temporarily as a fallback.
    Kokoro is now the default ed3hub TTS engine.
    """

    name = "kyutai"

    PRESET_VOICES = (
        "alba",
        "marius",
        "javert",
        "fantine",
        "anna",
        "vera",
        "charles",
        "paul",
        "eponine",
        "azelma",
        "george",
        "mary",
        "jane",
        "michael",
        "eve",
        "bill_boerst",
        "peter_yearsley",
        "stuart_bell",
        "caro_davy",
        "jean",
        "cosette",
    )

    def __init__(
        self,
        voice: str = "marius",
        language: str = "english",
        cache_dir: Path | None = None,
    ) -> None:
        self.voice = (
            voice or "marius"
        ).strip()

        self.language = language
        self.cache_dir = cache_dir

        if self.cache_dir is not None:
            os.environ.setdefault(
                "HF_HOME",
                str(self.cache_dir),
            )

            if (
                self._voice_embedding_cached()
            ):
                os.environ.setdefault(
                    "HF_HUB_OFFLINE",
                    "1",
                )

            else:
                os.environ.pop(
                    "HF_HUB_OFFLINE",
                    None,
                )

        self.cache_tag = (
            f"kyutai:"
            f"{self.voice}:"
            f"{self.language}"
        )

        self._model = None
        self._voice_state = None

    def _voice_embedding_cached(
        self,
    ) -> bool:
        if self.cache_dir is None:
            return False

        hub = (
            self.cache_dir
            / "hub"
            / (
                "models--kyutai--"
                "pocket-tts-without-voice-cloning"
            )
        )

        snapshots = (
            hub
            / "snapshots"
        )

        if not snapshots.is_dir():
            return False

        for snapshot in snapshots.iterdir():
            embedding = (
                snapshot
                / "languages"
                / self.language
                / "embeddings"
                / f"{self.voice}.safetensors"
            )

            if embedding.is_file():
                return True

        return False

    def _load_model(self):
        if self._model is None:
            try:
                import torch
                from pocket_tts import TTSModel

            except ImportError as exc:
                raise RuntimeError(
                    "pocket-tts is not installed. "
                    "Run `pip install pocket-tts` "
                    "and set TTS_PROVIDER=kyutai."
                ) from exc

            torch.set_num_threads(
                max(
                    1,
                    min(
                        8,
                        os.cpu_count() or 4,
                    ),
                )
            )

            self._model = (
                TTSModel.load_model(
                    language=self.language
                )
            )

        return self._model

    def _voice_state_for(
        self,
        model,
    ):
        if self._voice_state is None:
            from pocket_tts.utils.utils import (
                _ORIGINS_OF_PREDEFINED_VOICES,
            )

            if (
                self.voice
                not in _ORIGINS_OF_PREDEFINED_VOICES
            ):
                raise RuntimeError(
                    f"Kyutai voice "
                    f"'{self.voice}' "
                    f"not found for language "
                    f"'{self.language}'. "
                    f"Available presets: "
                    f"{', '.join(self.PRESET_VOICES)}"
                )

            self._voice_state = (
                model.get_state_for_audio_prompt(
                    self.voice
                )
            )

        return self._voice_state

    def generate(
        self,
        text: str,
        out_path: Path,
    ) -> AudioMetadata:
        out_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        model = self._load_model()

        voice_state = (
            self._voice_state_for(
                model
            )
        )

        tokenizer = (
            model
            .flow_lm
            .conditioner
            .tokenizer
        )

        parts = _tts_chunks(
            text,
            lambda value: len(
                tokenizer(value)
                .tokens[0]
                .tolist()
            ),
        )

        if len(parts) == 1:
            audio = model.generate_audio(
                voice_state,
                parts[0],
            )

        else:
            import torch

            audio = torch.cat(
                [
                    model.generate_audio(
                        voice_state,
                        part,
                    )
                    for part in parts
                ],
                dim=0,
            )

        wav_path = (
            out_path.with_suffix(
                ".wav"
            )
        )

        self._write_wav(
            audio,
            wav_path,
            int(model.sample_rate),
        )

        final_path = _encode_to_mp3(
            wav_path,
            out_path,
        )

        return _finish_audio(
            final_path
        )

    @staticmethod
    def _write_wav(
        audio,
        wav_path: Path,
        sample_rate: int,
    ) -> None:
        import numpy as np

        samples = np.clip(
            np.asarray(
                audio,
                dtype=np.float32,
            ),
            -1.0,
            1.0,
        )

        if samples.ndim > 1:
            samples = samples.reshape(
                -1
            )

        pcm = (
            samples
            * 32767
        ).astype(
            np.int16
        )

        with wave.open(
            str(wav_path),
            "wb",
        ) as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(
                sample_rate
            )

            wav.writeframes(
                pcm.tobytes()
            )


def build_tts_provider(
    name: str | None = None,
    voice: str | None = None,
    rate: int = 0,
    cache_dir: Path | None = None,
) -> TTSProvider:
    """Build the configured TTS implementation.

    Kokoro is the default provider.
    """

    provider_name = (
        name or "kokoro"
    ).lower()

    if provider_name in (
        "kokoro",
        "kokoro-tts",
    ):
        return KokoroTTS(
            voice=voice or "af_heart",
            rate=rate,
        )

    if provider_name in (
        "kyutai",
        "pocket-tts",
        "pocket",
    ):
        return KyutaiTTS(
            voice=voice or "marius",
            cache_dir=cache_dir,
        )

    if provider_name in (
        "edge-tts",
        "edge",
    ):
        return EdgeTTS(
            voice=(
                voice
                or "en-GB-RyanNeural"
            ),
            rate=rate,
        )

    if provider_name == "sapi":
        return SapiTTS(
            voice=voice,
            rate=rate,
        )

    if provider_name == "mock":
        return MockTTS()

    raise RuntimeError(
        f"Unsupported TTS provider "
        f"'{provider_name}'. "
        f"Available providers: "
        f"kokoro, kyutai, "
        f"edge-tts, sapi, mock."
    )
