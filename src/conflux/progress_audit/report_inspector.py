"""Summarize the visible structure of changed text reports."""

from __future__ import annotations

import json
import re
from pathlib import Path

from .models import ArtifactRecord


def summarize_report(project_path: str | Path, report: ArtifactRecord) -> str:
    root = Path(project_path).resolve()
    path = (root / report.path).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        return f"报告已更新：{report.path}"
    if path.suffix.lower() in {".md", ".markdown"}:
        return _markdown_summary(path, report.path)
    if path.suffix.lower() == ".json":
        return _json_summary(path, report.path)
    return f"报告已更新：{report.path}"


def _markdown_summary(path: Path, relative: str) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")[:200_000]
    except OSError:
        return f"报告已更新：{relative}"
    headings = [
        re.sub(r"\s+#+\s*$", "", match.group(1)).strip()
        for match in re.finditer(r"(?m)^#{1,3}\s+(.+)$", text)
    ][:4]
    suffix = f"；章节：{'、'.join(headings)}" if headings else ""
    return f"报告已更新：{relative}{suffix}"


def _json_summary(path: Path, relative: str) -> str:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return f"报告已更新：{relative}"
    keys = list(payload)[:5] if isinstance(payload, dict) else []
    suffix = f"；字段：{'、'.join(str(key) for key in keys)}" if keys else ""
    return f"报告已更新：{relative}{suffix}"
