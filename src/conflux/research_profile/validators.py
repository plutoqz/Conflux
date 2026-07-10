"""Validation rules for research profiles."""

from __future__ import annotations

import re
from pathlib import Path

from .models import ResearchProfile


class ProfileValidationError(ValueError):
    """Raised when a research profile is malformed."""


def validate_profile(profile: ResearchProfile, *, base_dir: Path | None = None) -> ResearchProfile:
    """Validate a profile and attach non-fatal path warnings."""

    errors: list[str] = []

    if not profile.id.strip():
        errors.append("id is required")
    elif not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", profile.id):
        errors.append("id must contain only letters, numbers, dots, underscores, or hyphens")

    if not profile.name.strip():
        errors.append("name is required")
    if not profile.fields:
        errors.append("fields must contain at least one item")
    if not profile.research_questions:
        errors.append("research_questions must contain at least one item")
    if not profile.keywords:
        errors.append("keywords must contain at least one item")

    _validate_string_list("fields", profile.fields, errors)
    _validate_string_list("research_questions", profile.research_questions, errors)
    _validate_string_list("keywords", profile.keywords, errors)
    _validate_string_list("negative_keywords", profile.negative_keywords, errors)
    _validate_string_list("target_venues", profile.target_venues, errors)
    _validate_string_list("tracked_scholars", profile.tracked_scholars, errors)
    _validate_string_list("paper_sources", profile.paper_sources, errors)

    if profile.report_cadence and profile.report_cadence not in {"daily", "weekly", "manual"}:
        errors.append("report_cadence must be one of: daily, weekly, manual")

    if errors:
        raise ProfileValidationError("; ".join(errors))

    profile.warnings.clear()
    for label, paths in (
        ("project_paths", profile.normalized_project_paths(base_dir)),
        ("document_paths", profile.normalized_document_paths(base_dir)),
    ):
        for path in paths:
            if not path.exists():
                profile.warnings.append(f"{label}: path does not exist: {path}")

    return profile


def _validate_string_list(name: str, values: list[str], errors: list[str]) -> None:
    for idx, value in enumerate(values):
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{name}[{idx}] must be a non-empty string")
