"""Aggregate validation for a chapter plan."""

from __future__ import annotations

import re

from pipeline.config import Config
from pipeline.content.schemas import (
    ChapterPlan,
    ValidationIssue,
    ValidationResult,
)
from pipeline.visual.action_validator import validate_actions

from .rules import check_plan_rules


def validate_chapter(
    plan: ChapterPlan,
    config: Config,
) -> ValidationResult:
    """Validate a chapter plan and return structured issues."""

    issues = check_plan_rules(
        plan,
        config,
    )

    for scene in plan.scenes:
        issues.extend(
            (
                "error"
                if severity == "error"
                else "warning",
                message,
            )
            for severity, message in validate_actions(
                scene,
                config.max_teaching_actions_per_scene,
                config.max_high_emphasis_cues_per_concept,
            )
        )

    errors = [
        ValidationIssue(
            level="error",
            code=slug(message),
            message=message,
        )
        for severity, message in issues
        if severity == "error"
    ]

    warnings = [
        ValidationIssue(
            level="warning",
            code=slug(message),
            message=message,
        )
        for severity, message in issues
        if severity == "warning"
    ]

    return ValidationResult(
        chapterNumber=plan.chapterNumber,
        chapterTitle=plan.chapterTitle,
        ok=not errors,
        errors=errors,
        warnings=warnings,
    )


def slug(text: str) -> str:
    """Convert validation text into a readable machine-friendly code."""

    normalized = re.sub(
        r"[^a-z0-9]+",
        "-",
        text.lower(),
    )

    return (
        normalized
        .strip("-")[:60]
        or "issue"
    )