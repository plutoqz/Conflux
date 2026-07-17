"""Session history index — scans report artifacts for past research runs.

No database required.  Reads every ``<run_id>.summary.json`` under
``reports/`` and builds a lightweight session index suitable for the
workbench's session-history API.

Provides:
    GET /api/sessions          -> list of past sessions
    GET /api/sessions/<run_id> -> full summary for one session
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from conflux.config import PROJECT_ROOT


_REPORTS_ROOT = PROJECT_ROOT / "reports"


def build_session_index() -> list[dict[str, Any]]:
    """Scan the reports tree and return recent sessions, newest first (by mtime)."""
    sessions: list[dict[str, Any]] = []
    if not _REPORTS_ROOT.exists():
        return sessions

    for summary_path in _REPORTS_ROOT.rglob("*.summary.json"):
        try:
            payload = json.loads(summary_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        run_id = payload.get("run_id") or summary_path.stem.replace(".summary", "")
        if not run_id:
            continue

        sessions.append({
            "run_id": run_id,
            "thread_id": payload.get("thread_id", ""),
            "query": payload.get("query") or _find_query_in_payload(payload, summary_path, str(run_id)),
            "answer_preview": _truncate(str(payload.get("final_answer") or ""), 300),
            "checkpoint_backend": payload.get("checkpoint_backend", ""),
            "resumed": payload.get("resumed", False),
            "source_statuses": payload.get("source_statuses", {}),
            "factcheck_status": payload.get("factcheck_status", ""),
            "quality": payload.get("quality", {}),
            "summary_path": _rel(summary_path),
            "modified": int(summary_path.stat().st_mtime),
        })
    # Sort by modification time, newest first, then truncate
    sessions.sort(key=lambda s: s["modified"], reverse=True)
    return sessions[:50]


def get_session_detail(run_id: str) -> dict[str, Any] | None:
    """Return the full summary payload for a specific run, if found.

    Matches *run_id* exactly against the persisted ``run_id`` field in the
    summary JSON.  Report paths are read from the persisted summary fields
    ``report_md_path`` and ``report_html_path``; if absent the function
    falls back to selecting the newest matching file in the summary's
    directory (legacy summaries).
    """
    for summary_path in _REPORTS_ROOT.rglob("*.summary.json"):
        try:
            payload = json.loads(summary_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if payload.get("run_id") != run_id:
            continue

        result = dict(payload)
        result["query"] = payload.get("query") or _find_query_in_payload(payload, summary_path, run_id)
        result["summary_path"] = _rel(summary_path)

        # Trace file
        trace_path = summary_path.parent / f"{run_id}.trace.jsonl"
        result["trace_available"] = trace_path.exists()
        result["trace_path"] = _rel(trace_path) if trace_path.exists() else ""

        # Report paths — prefer persisted values, then verified legacy matches.
        md_path = payload.get("report_md_path")
        html_path = payload.get("report_html_path")
        if md_path:
            resolved_md = _resolve_artifact_path(str(md_path))
            result["report_md_available"] = resolved_md.exists()
            result["report_md_path"] = _rel(resolved_md)
        else:
            legacy_md = _find_legacy_report(summary_path.parent, run_id, ".md")
            result["report_md_available"] = legacy_md is not None
            result["report_md_path"] = _rel(legacy_md) if legacy_md else ""
        if html_path:
            resolved_html = _resolve_artifact_path(str(html_path))
            result["report_html_available"] = resolved_html.exists()
            result["report_html_path"] = _rel(resolved_html)
        else:
            legacy_html = _find_legacy_report(summary_path.parent, run_id, ".html")
            result["report_html_available"] = legacy_html is not None
            result["report_html_path"] = _rel(legacy_html) if legacy_html else ""
        for field in ("report_evidence_path", "report_sources_path", "report_deep_evidence_path"):
            value = payload.get(field)
            if value:
                resolved = _resolve_artifact_path(str(value))
                result[f"{field}_available"] = resolved.exists()
                result[field] = _rel(resolved)
            else:
                result[f"{field}_available"] = False
                result[field] = ""
        return result
    return None


def _find_query_in_payload(payload: dict[str, Any], summary_path: Path, run_id: str) -> str:
    """Extract query text from payload or sibling markdown report."""
    # Some summaries have a 'query' field
    if payload.get("query"):
        return str(payload["query"])[:300]
    # Legacy summaries can only use a report whose embedded Run id matches.
    md = _find_legacy_report(summary_path.parent, run_id, ".md")
    if md:
        try:
            for line in md.read_text(encoding="utf-8").splitlines()[:20]:
                if line.startswith("- 查询："):
                    return line[5:].strip()[:300]
        except OSError:
            pass
    return ""


def _find_legacy_report(directory: Path, run_id: str, suffix: str) -> Path | None:
    """Return one legacy report only when its embedded Run id is verifiable."""
    marker = re.compile(rf"Run id:\s*{re.escape(run_id)}(?=\s|<|$)")
    matches: list[Path] = []
    for candidate in directory.glob(f"*{suffix}"):
        try:
            with candidate.open("r", encoding="utf-8") as handle:
                prefix = handle.read(32768)
        except (OSError, UnicodeDecodeError):
            continue
        if marker.search(prefix):
            matches.append(candidate)
    if len(matches) != 1:
        return None
    return matches[0]


def _resolve_artifact_path(value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else PROJECT_ROOT / path


def _truncate(text: str, max_len: int) -> str:
    return text[:max_len].replace("\n", " ").strip()


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)
