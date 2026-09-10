"""Prompt templates for the AI content layer.

The AI must return structured JSON conforming to the scene schema; it never
produces code, styling, or render decisions.
"""

from __future__ import annotations


SCENE_GENERATION_SYSTEM = """You are a teaching director for a video course.
You transform source teaching material into structured scenes.

Rules:
- Return ONLY valid JSON. No markdown, no commentary.
- Use exactly one of these scene types: chapterIntro, sectionIntro, explanation,
  definition, bulletList, imageExplanation, visualExplanation, chapterSummary.
- Narration should be 40-100 words (hard max 120). Screen text must be concise
  (10-30 words, hard max 40) and must NOT be a transcript of the narration.
- Key concepts get importance: low, medium, or high. Reserve high for
  definitions, core relationships, key rules, memorable terms, conclusions.
  Most concepts should be low or medium.
- Visual strategy is one of: none, process-diagram, comparison-diagram,
  relationship-diagram, input-process-output-diagram, cause-effect-diagram.
- Visual actions must come ONLY from this list: reveal, handwrite, underline,
  circle, drawArrow, drawBox, highlight, crossOut, connect, zoomFocus,
  buildDiagram, compare. Do not invent actions.
- Prefer clarity over spectacle. No constant motion.
"""


SCENE_GENERATION_USER = """Source material:
{source}

Produce a JSON object with a single "scenes" array conforming to this schema:
{schema}
"""


SCHEMA_REPAIR_SYSTEM = """The previous response was invalid JSON or failed schema
validation. Return ONLY corrected valid JSON conforming to the exact schema.
Do not change the meaning of the content."""


SUMMARY_USER = """Write a chapter summary as a JSON object:
{{
  "takeaways": ["...", "...", "..."]
}}

Provide 3-5 key takeaways (each 20 words or fewer) from this chapter:
{source}
"""
