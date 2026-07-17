"""Inspect research result and report files without reading arbitrary binaries."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .models import ArtifactRecord


DEFAULT_RESULT_DIRS = ("results", "artifacts", "experiments")
DEFAULT_REPORT_DIRS = ("reports",)
IGNORED_PARTS = {".git", ".venv", "venv", "node_modules", "__pycache__"}
IGNORED_RELATIVE_PREFIXES = ("reports/workbench/progress/",)


def inspect_artifacts(
    project_path: str | Path,
    *,
    result_dirs: Iterable[str] = DEFAULT_RESULT_DIRS,
    report_dirs: Iterable[str] = DEFAULT_REPORT_DIRS,
    max_files: int = 1000,
) -> tuple[list[ArtifactRecord], list[ArtifactRecord]]:
    root = Path(project_path).resolve()
    results = _scan_directories(root, result_dirs, "result", max_files=max_files)
    reports = _scan_directories(root, report_dirs, "report", max_files=max_files)
    return results, reports


def changed_artifacts(
    current: list[ArtifactRecord],
    baseline: list[ArtifactRecord],
) -> list[ArtifactRecord]:
    previous = {item.path: item.fingerprint for item in baseline}
    return [item for item in current if previous.get(item.path) != item.fingerprint]


def _scan_directories(
    root: Path,
    directories: Iterable[str],
    category: str,
    *,
    max_files: int,
) -> list[ArtifactRecord]:
    records: dict[str, ArtifactRecord] = {}
    for raw_directory in directories:
        directory = (root / str(raw_directory)).resolve()
        if not _is_within(directory, root) or not directory.is_dir():
            continue
        for path in directory.rglob("*"):
            if len(records) >= max_files:
                break
            if not path.is_file() or any(part in IGNORED_PARTS for part in path.parts):
                continue
            try:
                stat = path.stat()
            except OSError:
                continue
            relative = path.relative_to(root).as_posix()
            if relative.startswith(IGNORED_RELATIVE_PREFIXES):
                continue
            signature = f"{stat.st_size}:{stat.st_mtime_ns}"
            records[relative] = ArtifactRecord(
                path=relative,
                category=category,
                size_bytes=stat.st_size,
                modified_at=datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                fingerprint=hashlib.sha256(signature.encode("ascii")).hexdigest()[:16],
            )
    return sorted(records.values(), key=lambda item: item.path)


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False
