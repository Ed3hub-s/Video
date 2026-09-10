"""Aggregate validation for a chapter plan."""

from __future__ import annotations

from pipeline.content.schemas import ChapterPlan, ValidationIssue, ValidationResult
from pipeline.visual.action_validator import validate_actions

from .rules import check_plan_rules


def validate_chapter(plan: ChapterPlan, config) -> ValidationResult:
    issues = check_plan_rules(plan, config)
    for scene in plan.scenes:
        issues.extend(
            ("error" if sev == "error" else "warning", msg)
            for sev, msg in validate_actions(
                scene,
                config.max_teaching_actions_per_scene,
                config.max_high_emphasis_cues_per_concept,
            )
        )

    errors = [
        ValidationIssue(level="error", code=slug(code), message=message)
        for code, message in issues
        if code == "error"
    ]
    warnings = [
        ValidationIssue(level="warning", code=slug(code), message=message)
        for code, message in issues
        if code == "warning"
    ]
    return ValidationResult(
        chapterNumber=plan.chapterNumber,
        chapterTitle=plan.chapterTitle,
        ok=not errors,
        errors=errors,
        warnings=warnings,
    )


def slug(text: str) -> str:
    import re

    return re.sub(r"[^a-z0-9-]", "-", text.lower())[:60] or "issue"
