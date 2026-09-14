from kokoro import KPipeline
import soundfile as sf
import numpy as np
from pathlib import Path

TEXT = """
Welcome to ed3hub.

In this lesson, we are going to explore how decentralized finance works,
why smart contracts matter, and how decentralized systems differ from
traditional financial services.

By the end of this lesson, you should understand the basic structure of DeFi,
the role blockchain plays in enabling these applications, and why decentralized
finance has become an important part of the Web3 ecosystem.

Imagine a financial system where you can borrow, lend, trade, and earn interest
without relying on a traditional bank. Instead, software called smart contracts
executes the rules automatically.

Let's begin by understanding what decentralized finance actually means.
"""

VOICES = [
    ("af_bella", "a"),
    ("af_sarah", "a"),
    ("am_michael", "a"),
    ("bf_emma", "b"),
    ("bm_george", "b"),
]

output_dir = Path("kokoro_voice_tests")
output_dir.mkdir(exist_ok=True)

pipelines = {}

for voice, lang_code in VOICES:
    print(f"\nGenerating: {voice}")

    if lang_code not in pipelines:
        pipelines[lang_code] = KPipeline(lang_code=lang_code)

    pipeline = pipelines[lang_code]

    chunks = []

    for result in pipeline(
        TEXT,
        voice=voice,
        speed=1.0,
    ):
        audio = result.audio

        if audio is None:
            continue

        if hasattr(audio, "detach"):
            audio = audio.detach()

        if hasattr(audio, "cpu"):
            audio = audio.cpu()

        if hasattr(audio, "numpy"):
            audio = audio.numpy()

        chunks.append(np.asarray(audio))

    if not chunks:
        print(f"FAILED: {voice}")
        continue

    audio = np.concatenate(chunks)

    filename = output_dir / f"{voice}.wav"
    sf.write(filename, audio, 24000)

    duration = len(audio) / 24000

    print(f"Created: {filename}")
    print(f"Duration: {duration:.2f} seconds")

print("\nDone.")
