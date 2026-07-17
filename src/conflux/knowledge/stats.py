"""Knowledge asset statistics for the Conflux workbench dashboard.

Gathers comprehensive stats from the document corpus, ChromaDB vector store,
paper inbox, and report history — all in one machine-readable endpoint.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

# ── Display helpers ────────────────────────────────────────

CATEGORY_LABELS: dict[str, str] = {
    "esri": "Esri 官方文档",
    "nist": "NIST 标准",
    "wiki": "维基百科",
    "zh": "中文资料",
    "synth": "技术综合",
    "qa": "QA 数据集",
    "original": "项目文档",
    "papers": "学术论文",
    "other": "其他",
}

FORMAT_LABELS: dict[str, str] = {
    ".md": "Markdown",
    ".txt": "纯文本",
    ".json": "JSON",
    ".pdf": "PDF",
    ".yaml": "YAML",
    ".yml": "YAML",
}

FORMAT_COLORS: dict[str, str] = {
    ".md": "#059669",
    ".txt": "#6b7280",
    ".json": "#d97706",
    ".pdf": "#dc2626",
    ".yaml": "#7c3aed",
    ".yml": "#7c3aed",
}


def gather_knowledge_stats(project_root: Path) -> dict[str, Any]:
    """Return a comprehensive knowledge-asset statistics payload."""

    docs_dir = project_root / "data" / "documents"
    chroma_dir = project_root / "data" / "chroma_db"
    papers_dir = docs_dir / "papers"
    reports_dir = project_root / "reports"
    manifest_path = docs_dir / "manifest.json"

    stats: dict[str, Any] = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }

    # ── Document corpus ──
    stats["corpus"] = _corpus_stats(docs_dir, manifest_path)

    # ── ChromaDB vector store ──
    stats["vector_store"] = _chroma_stats(chroma_dir)

    # ── Papers ──
    stats["papers"] = _papers_stats(papers_dir)

    # ── Reports ──
    stats["reports"] = _reports_stats(reports_dir)

    # ── Aggregate totals ──
    stats["totals"] = {
        "documents": stats["corpus"]["total_files"],
        "total_size_kb": round(stats["corpus"]["total_size_kb"], 1),
        "vector_chunks": stats["vector_store"].get("estimated_chunks", 0),
        "papers": stats["papers"]["total"],
        "reports": stats["reports"]["total"],
        "categories": len(stats["corpus"]["categories"]),
    }

    return stats


def _corpus_stats(docs_dir: Path, manifest_path: Path) -> dict[str, Any]:
    """Statistics from the current local document corpus.

    The historical manifest is not authoritative because paper promotion writes
    directly into the corpus. A live scan keeps the dashboard consistent after
    every import instead of returning stale manifest totals.
    """

    return _scan_documents(docs_dir)


def _scan_documents(docs_dir: Path) -> dict[str, Any]:
    """Scan the documents directory to build corpus stats."""
    if not docs_dir.exists():
        return {"total_files": 0, "total_size_kb": 0, "formats": {}, "categories": {}, "files": []}

    files = []
    total_size = 0
    formats: dict[str, int] = {}
    for path in sorted(docs_dir.rglob("*")):
        if not path.is_file():
            continue
        if any(p.startswith(".") for p in path.parts):
            continue
        if path.name.startswith("."):
            continue
        size = path.stat().st_size
        total_size += size
        suffix = path.suffix.lower()
        formats[suffix] = formats.get(suffix, 0) + 1
        try:
            rel = path.relative_to(docs_dir).as_posix()
        except ValueError:
            rel = path.name
        files.append({
            "name": path.name,
            "size_kb": round(size / 1024, 1),
            "path": rel,
            "category": _guess_category(rel),
            "format": suffix,
        })

    return {
        "total_files": len(files),
        "total_size_kb": round(total_size / 1024, 1),
        "formats": formats,
        "categories": _group_categories(files),
        "category_labels": {k: CATEGORY_LABELS.get(k, k) for k in _group_categories(files)},
        "format_labels": _format_labels_map(formats),
        "files": files,
        "_source": "filesystem_scan",
    }


def _guess_category(rel_path: str) -> str:
    """Infer category from file path."""
    path_lower = rel_path.lower()
    if "/papers/" in path_lower or path_lower.startswith("papers/"):
        return "papers"
    for prefix in ["esri--", "nist--", "wiki--", "zh-"]:
        if path_lower.startswith(prefix):
            return prefix.rstrip("-")
    if "-" in path_lower.split("/")[-1]:
        return "synth"
    return "other"


def _group_categories(files: list[dict]) -> dict[str, dict]:
    """Group files by category."""
    groups: dict[str, dict] = {}
    for f in files:
        cat = f["category"]
        if cat not in groups:
            groups[cat] = {"count": 0, "total_size_kb": 0}
        groups[cat]["count"] += 1
        groups[cat]["total_size_kb"] += f["size_kb"]
    return groups


def _format_labels_map(formats: dict[str, int]) -> dict[str, dict]:
    """Build format metadata for chart rendering."""
    total = sum(formats.values()) or 1
    return {
        ext: {
            "count": count,
            "label": FORMAT_LABELS.get(ext, ext.lstrip(".").upper()),
            "color": FORMAT_COLORS.get(ext, "#94a3b8"),
            "pct": round(count / total * 100),
        }
        for ext, count in formats.items()
    }


def _chroma_stats(chroma_dir: Path) -> dict[str, Any]:
    """Lightweight ChromaDB stats (no heavy import)."""

    if not chroma_dir.exists():
        return {"exists": False, "estimated_chunks": 0}

    # Count collection directories (each has a UUID name)
    try:
        entries = list(chroma_dir.iterdir())
        collection_dirs = [
            e for e in entries
            if e.is_dir() and len(e.name) == 36 and e.name.count("-") == 4
        ]
    except Exception:
        collection_dirs = []

    # Estimate chunks from the length.bin file (each entry = 4 bytes, so chunks = bytes/4)
    estimated_chunks = 0
    for cd in collection_dirs:
        length_file = cd / "length.bin"
        if length_file.exists():
            try:
                size = length_file.stat().st_size
                estimated_chunks += size // 4
            except Exception:
                pass

    sqlite_path = chroma_dir / "chroma.sqlite3"
    sqlite_size = sqlite_path.stat().st_size if sqlite_path.exists() else 0

    return {
        "exists": True,
        "collections": len(collection_dirs),
        "estimated_chunks": estimated_chunks,
        "sqlite_size_kb": round(sqlite_size / 1024, 1),
    }


def _papers_stats(papers_dir: Path) -> dict[str, Any]:
    """Stats from the promoted paper documents."""

    if not papers_dir.exists():
        return {"total": 0, "by_format": {}, "inbox_available": False}

    markdown_files = list(papers_dir.rglob("*.md"))
    summary_files = [path for path in markdown_files if path.name.endswith("#summary.md")]
    json_files = list(papers_dir.rglob("*.json"))
    total_size = sum(
        (f.stat().st_size for f in markdown_files + json_files if f.is_file()),
        0,
    )

    # Check for inbox JSON
    inbox_path = papers_dir / "paper_inbox.json"
    inbox_available = inbox_path.exists()

    # Check for manifest
    manifest_path = papers_dir / "paper_promotion_manifest.json"
    manifest_data = {}
    if manifest_path.exists():
        try:
            manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    return {
        "total": len(summary_files),
        "markdown": len(markdown_files),
        "json": len(json_files),
        "total_size_kb": round(total_size / 1024, 1),
        "inbox_available": inbox_available,
        "manifest_entries": len(manifest_data) if isinstance(manifest_data, dict) else 0,
        "by_format": {".md": len(markdown_files), ".json": len(json_files)},
    }


def _reports_stats(reports_dir: Path) -> dict[str, Any]:
    """Statistics from the generated reports."""

    if not reports_dir.exists():
        return {"total": 0, "by_type": {}, "recent": []}

    total = 0
    by_type: dict[str, int] = {}
    recent: list[dict] = []

    for path in sorted(reports_dir.rglob("*"), reverse=True):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix not in {".md", ".html", ".json", ".jsonl"}:
            continue
        total += 1
        by_type[suffix] = by_type.get(suffix, 0) + 1
        if len(recent) < 10:
            try:
                rel = path.relative_to(reports_dir).as_posix()
            except ValueError:
                rel = path.name
            recent.append({
                "name": path.name,
                "path": rel,
                "size_kb": round(path.stat().st_size / 1024, 1),
                "modified": int(path.stat().st_mtime),
            })

    return {
        "total": total,
        "by_type": by_type,
        "recent": recent,
    }
