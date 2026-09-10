from __future__ import annotations

from pathlib import Path

from pipeline.audio.subtitles import build_subtitles, build_subtitles_from_words
from pipeline.audio.timestamps import sentence_timestamps, word_timestamps
from pipeline.audio.tts import MockTTS, SapiTTS


def test_word_timestamps_cover_duration():
    words = word_timestamps("one two three four five", 5.0)
    assert len(words) == 5
    assert words[-1]["end"] == 5.0


def test_sentence_timestamps_group_sentences():
    sentences = sentence_timestamps("First sentence here. Second sentence here.", 4.0)
    assert len(sentences) == 2
    assert sentences[0]["text"].startswith("First sentence")


def test_subtitles_never_single_giant_chunk():
    text = " ".join([f"word{i}" for i in range(60)])
    cues = build_subtitles(text, 10.0)
    assert len(cues) > 1
    assert all(len(c.text) <= 48 for c in cues)


def test_subtitles_from_word_timestamps_apply_offset():
    words = [
        {"word": f"word{i}", "start": i * 0.4, "end": i * 0.4 + 0.3}
        for i in range(20)
    ]
    cues = build_subtitles_from_words(words, offset=0.3)
    assert len(cues) > 1
    assert all(len(c.text) <= 48 for c in cues)
    assert cues[0].start >= 0.3


def test_mock_tts_produces_audio(tmp_path):
    tts = MockTTS()
    metadata = tts.generate("Machine learning learns patterns from data.", tmp_path / "scene-001.mp3")
    assert metadata.durationSeconds > 1.0
    assert metadata.path.endswith((".mp3", ".wav"))


def test_sapi_tts_produces_speech(tmp_path):
    try:
        tts = SapiTTS()
    except RuntimeError as exc:
        import pytest

        pytest.skip(f"SAPI unavailable: {exc}")
    try:
        metadata = tts.generate(
            "Machine learning learns patterns from data.",
            tmp_path / "scene-001.mp3",
        )
    except RuntimeError as exc:
        import pytest

        pytest.skip(f"SAPI synthesis blocked in this environment: {exc}")
    assert metadata.durationSeconds > 1.0
    assert metadata.path.endswith((".mp3", ".wav"))
    assert tts.cache_tag.startswith("sapi:")


def test_edge_tts_produces_speech(tmp_path):
    import pytest

    try:
        import edge_tts  # noqa: F401
    except ImportError:
        pytest.skip("edge-tts is not installed")
    from pipeline.audio.tts import EdgeTTS

    try:
        tts = EdgeTTS(voice="en-GB-RyanNeural")
        metadata = tts.generate(
            "Machine learning learns patterns from data.",
            tmp_path / "scene-001.mp3",
        )
    except Exception as exc:  # network/endpoint unavailable
        pytest.skip(f"edge-tts synthesis unavailable: {exc}")
    assert metadata.durationSeconds > 1.0
    assert metadata.path.endswith((".mp3", ".wav"))
    assert tts.cache_tag.startswith("edge-tts:")


def test_kyutai_presets_and_cache_tag():
    from pipeline.audio.tts import KyutaiTTS

    tts = KyutaiTTS(voice="javert")
    assert tts.cache_tag.startswith("kyutai:javert:")
    assert {"alba", "marius", "javert", "fantine"} <= set(KyutaiTTS.PRESET_VOICES)


def test_kyutai_narration_split_respects_max_tokens():
    from pipeline.audio.tts import _tts_chunks

    narration = "First sentence of the narration. " + " ".join(["word"] * 60) + "."
    parts = _tts_chunks(narration, count_tokens=lambda value: len(value.split()))
    assert len(parts) >= 2
    assert all(len(p.split()) <= 45 for p in parts)


def test_kyutai_tts_produces_speech(tmp_path):
    import pytest

    try:
        import pocket_tts  # noqa: F401
    except ImportError:
        pytest.skip("pocket-tts is not installed")

    from pipeline.audio.tts import KyutaiTTS

    cache_dir = Path(__file__).resolve().parents[1] / "cache"
    model_dir = cache_dir / "hub" / "models--kyutai--pocket-tts-without-voice-cloning"
    if not model_dir.exists():
        pytest.skip("Kyutai model not downloaded yet (run the pipeline once to fetch it)")

    try:
        tts = KyutaiTTS(voice="marius", cache_dir=cache_dir)
        metadata = tts.generate(
            "Machine learning learns patterns from data.",
            tmp_path / "scene-001.mp3",
        )
    except Exception as exc:  # synthesis/model unavailable
        pytest.skip(f"Kyutai synthesis unavailable: {exc}")

    assert metadata.durationSeconds > 1.0
    assert metadata.path.endswith((".mp3", ".wav"))
    assert tts.cache_tag.startswith("kyutai:")
