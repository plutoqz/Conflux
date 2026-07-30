"""YAML loading and compatibility mapping for research profiles."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .models import ResearchProfile
from .validators import validate_profile


def load_profile(path: str | Path, *, validate: bool = True) -> ResearchProfile:
    """Load a research profile from YAML."""

    profile_path = Path(path)
    with profile_path.open(encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}

    # AcademyHunter detection: tracks + research_questions (as dict, not list)
    if "tracks" in payload and isinstance(payload.get("research_questions"), dict):
        profile = profile_from_academy_hunter(payload)
    else:
        profile = profile_from_dict(payload)

    if validate:
        validate_profile(profile, base_dir=profile_path.parent)
    return profile


def profile_from_dict(payload: dict[str, Any]) -> ResearchProfile:
    """Create a profile from the native Conflux YAML shape."""

    metadata = dict(payload.get("metadata") or {})
    known = {
        "id",
        "name",
        "fields",
        "research_questions",
        "keywords",
        "negative_keywords",
        "target_venues",
        "tracked_scholars",
        "project_paths",
        "document_paths",
        "paper_sources",
        "report_cadence",
        "tracks",
    }
    for key, value in payload.items():
        if key not in known and key != "metadata":
            metadata[key] = value

    return ResearchProfile(
        id=str(payload.get("id") or ""),
        name=str(payload.get("name") or ""),
        fields=_string_list(payload.get("fields")),
        research_questions=_string_list(payload.get("research_questions")),
        keywords=_string_list(payload.get("keywords")),
        negative_keywords=_string_list(payload.get("negative_keywords")),
        target_venues=_string_list(payload.get("target_venues")),
        tracked_scholars=_string_list(payload.get("tracked_scholars")),
        project_paths=_string_list(payload.get("project_paths")),
        document_paths=_string_list(payload.get("document_paths")),
        paper_sources=_string_list(payload.get("paper_sources")) or ["arxiv"],
        report_cadence=str(payload.get("report_cadence") or "weekly"),
        tracks=list(payload.get("tracks") or []),
        metadata=metadata,
    )


def profile_from_academy_hunter(payload: dict[str, Any]) -> ResearchProfile:
    """Map an AcademyHunter-style profile into the Conflux profile contract."""

    profile_meta = payload.get("profile") or {}
    tracks = payload.get("tracks") or []
    research_questions_payload = payload.get("research_questions") or {}

    fields: list[str] = []
    keywords: list[str] = []
    target_venues: list[str] = []
    for track in tracks:
        if not isinstance(track, dict):
            continue
        fields.extend(_string_list([track.get("name"), track.get("description")]))
        target_venues.extend(_string_list(track.get("venues_priority")))
        for query in track.get("queries") or []:
            if not isinstance(query, dict):
                continue
            keywords.extend(_string_list([query.get("keywords"), query.get("suffix")]))
            keywords.extend(_string_list(query.get("categories")))

    questions: list[str] = []
    for key, value in research_questions_payload.items():
        if isinstance(value, dict):
            question = str(value.get("question") or "").strip()
            if question:
                questions.append(question)
            keywords.extend(_string_list(value.get("key_terms")))
        elif isinstance(value, str):
            questions.append(value)
        else:
            questions.append(str(key))

    negative = []
    filters = payload.get("negative_filters") or {}
    for value in filters.get("title_exclude_any") or []:
        negative.extend(_flatten_keywords(value))
    negative.extend(_string_list(filters.get("abstract_exclude")))

    return ResearchProfile(
        id=str(profile_meta.get("id") or _slug(profile_meta.get("name") or "academy-hunter-profile")),
        name=str(profile_meta.get("name") or "AcademyHunter Research Profile"),
        fields=_dedupe(fields) or ["research"],
        research_questions=_dedupe(questions) or ["Identify high-value papers for the active research direction."],
        keywords=_dedupe(keywords),
        negative_keywords=_dedupe(negative),
        target_venues=_dedupe(target_venues),
        tracked_scholars=_string_list(payload.get("scholars_to_watch")),
        paper_sources=["arxiv"],
        report_cadence="weekly",
        metadata={
            "source_format": "academy_hunter",
            "thesis_short": profile_meta.get("thesis_short", ""),
        },
    )


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, (list, tuple, set)):
        result = []
        for item in value:
            if item is None:
                continue
            if isinstance(item, (list, tuple, set)):
                result.extend(_string_list(item))
            else:
                text = str(item).strip()
                if text:
                    result.append(text)
        return result
    text = str(value).strip()
    return [text] if text else []


def _flatten_keywords(value: Any) -> list[str]:
    return _string_list(value)


def _dedupe(values: list[str]) -> list[str]:
    clean = []
    seen = set()
    for value in values:
        normalized = " ".join(str(value).split())
        key = normalized.lower()
        if normalized and key not in seen:
            seen.add(key)
            clean.append(normalized)
    return clean


def _slug(value: str) -> str:
    chars = []
    for char in value.lower():
        if char.isascii() and char.isalnum():
            chars.append(char)
        elif chars and chars[-1] != "-":
            chars.append("-")
    slug = "".join(chars).strip("-")
    return slug or "research-profile"
