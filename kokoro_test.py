from kokoro import KPipeline
import soundfile as sf

pipeline = KPipeline(lang_code="a")

text = """
Welcome to ed3hub.

In this lesson, we are going to explore how decentralized finance works,
why smart contracts matter, and how decentralized systems differ from
traditional financial services.

By the end of this lesson, you should understand the basic structure of DeFi
and the role blockchain plays in enabling these applications.
"""

generator = pipeline(
    text,
    voice="af_heart",
    speed=1.0,
)

for i, (_, _, audio) in enumerate(generator):
    filename = f"kokoro-test-{i}.wav"
    sf.write(filename, audio, 24000)
    print(f"Created {filename}")
