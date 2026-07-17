"""Structured trace events and run-ledger helpers."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class TraceEvent:
    """One machine-readable workflow event."""

    stage: str
    status: str
    elapsed_ms: float = 0.0
    source: str | None = None
    summary: str = ""
    run_id: str | None = None
    thread_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def new_run_id() -> str:
    return uuid.uuid4().hex[:12]


def event_from_state_key(
    key: str,
    value: Any,
    *,
    run_id: str | None = None,
    thread_id: str | None = None,
    started_at: float | None = None,
) -> TraceEvent | None:
    """Map a streamed state key to a structured trace event."""

    if not value:
        return None
    mapping = {
        "rag_result": ("rag_agent", "RAG"),
        "web_result": ("web_agent", "Web"),
        "model_result": ("model_agent", "Model"),
        "_merged": ("evidence_merge", None),
        "_arbitration": ("arbitration", None),
        "final_answer": ("synthesize", None),
        "_verified_answer": ("factcheck", "FactCheck"),
        "_deep_research": ("deep_research", None),
    }
    if key not in mapping:
        return None
    stage, source = mapping[key]
    status = "completed"
    text = str(value)
    lowered = text.lower()

    # For agent results, extract the actual SourceResult status from the
    # CONFLUX_SOURCE_RESULT_JSON marker instead of scanning raw text for
    # "failed"/"error" substrings (which may appear in body content).
    if key in ("rag_result", "web_result", "model_result"):
        status = _trace_agent_status(text)
    else:
        if "failed" in lowered or "error" in lowered:
            status = "failed"
        elif "fallback" in lowered:
            status = "fallback"
    elapsed_ms = round((time.time() - started_at) * 1000, 2) if started_at else 0.0
    return TraceEvent(
        stage=stage,
        status=status,
        elapsed_ms=elapsed_ms,
        source=source,
        summary=text[:180].replace("\n", " "),
        run_id=run_id,
        thread_id=thread_id,
        metadata={"state_key": key, "size": len(text)},
    )


def write_trace_jsonl(events: list[TraceEvent], path: str | Path) -> Path:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
    return out_path


def read_trace_jsonl(path: str | Path) -> list[dict[str, Any]]:
    events = []
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    return events


def write_run_summary(summary: dict[str, Any], path: str | Path) -> Path:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


def _trace_agent_status(text: str) -> str:
    """Derive agent-level trace status from the SourceResult payload.

    Scans for the CONFLUX_SOURCE_RESULT_JSON marker and reads the real
    ``status`` field, avoiding false "failed" signals caused by the word
    "failed" appearing in tool output body text.
    """
    from .source_status import parse_source_results

    results = parse_source_results(text)
    if not results:
        return "completed"
    status = results[-1].status
    if status in ("no_evidence", "failed"):
        return "failed"
    if status == "fallback":
        return "fallback"
    if status == "low_relevance":
        return "low_relevance"
    return "completed"
