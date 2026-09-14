import re
from kokoro import KPipeline
import soundfile as sf
import numpy as np
from pathlib import Path
import time

TEXT = """
Welcome to ed3hub.

In this lesson, we are going to explore how artificial intelligence learns from data,
why neural networks are useful, and how mathematical models can make predictions.

Before we begin, remember that artificial intelligence is a broad field.
Machine learning is one part of artificial intelligence, and deep learning is one
part of machine learning. These terms are related, but they do not mean exactly
the same thing.

Imagine that we want to build a system capable of identifying whether an image
contains a cat or a dog. A traditional computer program would require us to write
specific rules. We might try to describe the shape of the ears, the size of the
nose, the texture of the fur, or the position of the eyes.

The problem is that real images vary enormously. Lighting changes. Camera angles
change. Animals appear in different positions. Some images are blurry, while
others contain complex backgrounds.

Machine learning approaches the problem differently.

Instead of manually writing every rule, we provide the computer with many examples.
Each example contains input data and, during supervised learning, the correct answer.
The model then adjusts its internal parameters so that its predictions become more
accurate over time.

Suppose our training dataset contains ten thousand images. Five thousand contain cats,
and five thousand contain dogs. During training, the model processes these examples
in smaller groups called batches.

For each image, the model produces a prediction.

For example, it might say there is a seventy-eight percent probability that an image
contains a cat and a twenty-two percent probability that it contains a dog.

The model then compares its prediction with the true answer.

This difference is measured using something called a loss function.

The objective of training is to reduce that loss.

One of the most important ideas behind this process is gradient descent.

Gradient descent is an optimization algorithm. It changes the parameters of a model
step by step in a direction that reduces the error.

You can imagine standing on the side of a mountain in heavy fog. You cannot see the
entire landscape, but you can determine which direction slopes downward. By repeatedly
taking small steps downhill, you can eventually approach a low point.

That is conceptually similar to what gradient descent does.

The size of each step is controlled by a value called the learning rate.

For example, a learning rate might be zero point zero zero one.

If the learning rate is too large, the model may repeatedly overshoot the best solution.
If it is too small, training may become unnecessarily slow.

Now let's consider a simple mathematical model.

Suppose the model calculates y equals w times x plus b.

Here, x represents the input.
W represents a weight.
B represents a bias.
And y represents the predicted output.

During training, the algorithm adjusts w and b.

A neural network performs this same general idea on a much larger scale. Instead of
having just one weight and one bias, modern neural networks can contain millions,
or even billions, of parameters.

These parameters are organized into layers.

An input layer receives information. Hidden layers transform that information.
And an output layer produces the final prediction.

Each artificial neuron receives values, multiplies them by weights, combines the
results, adds a bias, and usually applies an activation function.

Common activation functions include ReLU, sigmoid, and hyperbolic tangent.

ReLU stands for Rectified Linear Unit.

For positive values, ReLU usually returns the value itself. For negative values,
it returns zero.

Although this operation is very simple, it helps neural networks learn complex
nonlinear relationships.

Now consider a real-world example.

A university might want to predict whether students are at risk of failing a course.

The input data could include attendance percentage, assignment scores, quiz results,
and previous grades.

Suppose a student has ninety-two percent attendance, an average assignment score
of eighty-one point five percent, and a quiz average of seventy-four percent.

A machine-learning model could analyze these values and estimate the probability
that the student will successfully complete the course.

However, prediction accuracy is not the only important issue.

We must also consider bias, privacy, transparency, and the quality of the training data.

A model trained on incomplete or unrepresentative data can produce misleading results.
For this reason, machine learning systems should not automatically be treated as
objective simply because they use mathematics.

The same principle applies to modern generative artificial intelligence.

Large language models, often abbreviated as LLMs, learn statistical patterns from
very large collections of text.

They do not store every answer as a traditional database would.

Instead, they learn relationships between tokens and use those relationships to
predict what should come next.

When connected to software through an API, or Application Programming Interface,
a language model can become part of a larger application.

For example, an educational platform could send a chapter to an AI system, ask it
to identify the key concepts, generate a structured explanation, create examples,
and then transform that lesson into narration.

That is similar to the architecture we are building in ed3hub.

The document provides the source knowledge.

The lesson director decides how the material should be taught.

The text-to-speech system converts narration into audio.

And the video engine synchronizes the audio with diagrams, captions, animations,
examples, and visual explanations.

The important point is that each component has a specific responsibility.

By separating document processing, lesson planning, narration, and rendering,
the system becomes easier to test, improve, and maintain.

To summarize this lesson, remember three ideas.

First, machine learning uses data to adjust model parameters rather than relying
only on manually written rules.

Second, neural networks are mathematical systems composed of layers, weights,
biases, and activation functions.

And third, successful artificial intelligence systems require more than an accurate
model. They also require good data, appropriate evaluation, responsible design,
and clear communication.

In the next lesson, we would examine neural networks more closely and follow a
single prediction through each layer step by step.
"""
# TTS text should not inherit document paragraph spacing.
# Punctuation controls speech pauses; layout whitespace should not.
TEXT = re.sub(r"\s+", " ", TEXT).strip()

VOICES = [
    ("01_af_bella", "af_bella", "a"),
]

OUTPUT = Path("kokoro_pause_fix_test")
OUTPUT.mkdir(exist_ok=True)

pipelines = {
    "a": KPipeline(lang_code="a"),
    "b": KPipeline(lang_code="b"),
}

print("\nKokoro long-form educational narrationss test")
print("=" * 60)

for index, (filename, voice, lang) in enumerate(VOICES, start=1):

    print(f"\n[{index}/5] Generating {voice}...")

    start = time.perf_counter()
    chunks = []

    try:
        generator = pipelines[lang](
            TEXT,
            voice=voice,
            speed=1.0,
        )

        for result in generator:

            audio = result.audio

            if audio is None:
                continue

            if hasattr(audio, "detach"):
                audio = audio.detach()

            if hasattr(audio, "cpu"):
                audio = audio.cpu()

            if hasattr(audio, "numpy"):
                audio = audio.numpy()

            chunks.append(
                np.asarray(audio).reshape(-1)
            )

        if not chunks:
            raise RuntimeError("No audio generated")

        audio = np.concatenate(chunks)

        output_file = OUTPUT / f"{filename}.wav"

        sf.write(
            output_file,
            audio,
            24000
        )

        duration = len(audio) / 24000
        generation_time = time.perf_counter() - start

        print(f"  Created: {output_file}")
        print(f"  Audio duration: {duration / 60:.2f} minutes")
        print(f"  Generation time: {generation_time:.2f} seconds")

    except Exception as exc:
        print(f"  FAILED: {exc}")

print("\nFinished.")
print(f"Output: {OUTPUT.resolve()}")
