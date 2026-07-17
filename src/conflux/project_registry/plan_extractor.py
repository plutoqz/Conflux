"""Extract reviewable plan candidates from project Markdown files."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

from .models import ProjectDefinition


HEADING_PATTERN = re.compile(r"^(#{1,4})\s+(.+?)\s*$")
LIST_PATTERN = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+|\[[ xX]\]\s*)(.+?)\s*$")
INLINE_PLAN_PATTERN = re.compile(
    r"^\s*(总体目标|项目目标|研究目标|阶段目标|里程碑|下一步|后续计划|goal|objective|milestone|next)\s*[:：]\s*(.+?)\s*$",
    re.IGNORECASE,
)
NEGATIVE_HEADINGS = ("non-goal", "non goal", "非目标", "不包括", "out of scope")
SECTION_TYPES = (
    ("milestone", ("阶段", "里程碑", "roadmap", "milestone", "sprint")),
    ("overall_goal", ("总体目标", "项目目标", "研究目标", "goal", "objective", "purpose")),
    ("next_action", ("下一步", "后续", "计划", "next", "todo")),
)


def extract_plan_suggestions(
    project: ProjectDefinition,
    *,
    max_files: int = 40,
    max_suggestions: int = 80,
) -> list[dict[str, Any]]:
    root = Path(project.path).resolve()
    if not root.is_dir():
        return []
    files = _candidate_files(root, project, max_files=max_files)
    suggestions: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for path in files:
        try:
            if path.stat().st_size > 2_000_000:
                continue
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        active_type = ""
        active_heading = ""
        for line_number, line in enumerate(lines, start=1):
            heading = HEADING_PATTERN.match(line)
            if heading:
                active_heading = heading.group(2).strip()
                active_type = "" if _is_negative_heading(active_heading) else _section_type(active_heading)
                continue
            inline = INLINE_PLAN_PATTERN.match(line)
            if inline and _meaningful(inline.group(2)):
                inline_type = _section_type(inline.group(1))
                _append_suggestion(
                    suggestions,
                    seen,
                    type_=inline_type,
                    title=inline.group(2).strip(),
                    root=root,
                    path=path,
                    line_number=line_number,
                    context=inline.group(1),
                )
                continue
            if not active_type:
                continue
            item = LIST_PATTERN.match(line)
            if item and _meaningful(item.group(1)):
                _append_suggestion(
                    suggestions,
                    seen,
                    type_=active_type,
                    title=item.group(1).strip(),
                    root=root,
                    path=path,
                    line_number=line_number,
                    context=active_heading,
                )
            if len(suggestions) >= max_suggestions:
                return suggestions
    return suggestions


def _candidate_files(root: Path, project: ProjectDefinition, *, max_files: int) -> list[Path]:
    paths: dict[str, Path] = {}
    configured = project.plan.source_documents or project.document_files
    for raw in configured:
        path = (root / raw).resolve()
        if _within(path, root) and path.is_file() and path.suffix.lower() in {".md", ".markdown"}:
            paths[path.as_posix()] = path
    if project.plan.source_documents:
        return list(paths.values())[:max_files]
    for name in ("README.md", "ROADMAP.md", "PLAN.md", "PRODUCT.md"):
        path = root / name
        if path.is_file():
            paths[path.resolve().as_posix()] = path.resolve()
    for raw_dir in project.document_dirs:
        directory = (root / raw_dir).resolve()
        if not _within(directory, root) or not directory.is_dir():
            continue
        for path in directory.rglob("*.md"):
            if len(paths) >= max_files:
                break
            if ".git" not in path.parts and "node_modules" not in path.parts:
                paths[path.resolve().as_posix()] = path.resolve()
    return list(paths.values())[:max_files]


def _section_type(value: str) -> str:
    normalized = value.casefold()
    for type_, keywords in SECTION_TYPES:
        if any(keyword in normalized for keyword in keywords):
            return type_
    return ""


def _is_negative_heading(value: str) -> bool:
    normalized = value.casefold()
    return any(keyword in normalized for keyword in NEGATIVE_HEADINGS)


def _append_suggestion(
    suggestions: list[dict[str, Any]],
    seen: set[tuple[str, str]],
    *,
    type_: str,
    title: str,
    root: Path,
    path: Path,
    line_number: int,
    context: str,
) -> None:
    clean = re.sub(r"\s+", " ", title).strip(" -:#")[:300]
    key = (type_, clean.casefold())
    if not clean or key in seen:
        return
    seen.add(key)
    suggestions.append({
        "type": type_,
        "title": clean,
        "source_path": path.relative_to(root).as_posix(),
        "line": line_number,
        "context": context,
        "status": "pending_confirmation",
    })


def _meaningful(value: str) -> bool:
    clean = str(value or "").strip()
    return 3 <= len(clean) <= 300


def _within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False
