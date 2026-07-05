"""Structured source status payloads used across tools and agents."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Literal


SourceName = Literal["RAG", "Web", "Model", "FactCheck", "Synthesize"]
SourceStatus = Literal["success", "low_relevance", "no_evidence", "failed", "fallback"]
EVIDENCE_STATUSES = {"success", "low_relevance"}
NON_EVIDENCE_STATUSES = {"no_evidence", "failed", "fallback"}

MARKER = "CONFLUX_SOURCE_RESULT_JSON"


@dataclass
class AgentClaim:
    """A claim-level collaboration payload emitted by a source agent."""

    claim: str
    source: SourceName
    evidence_refs: list[str] = field(default_factory=list)
    confidence: float = 0.5
    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AgentClaim":
        return cls(
            claim=str(payload.get("claim") or ""),
            source=payload.get("source", "Model"),
            evidence_refs=[str(item) for item in payload.get("evidence_refs") or []],
            confidence=float(payload.get("confidence", 0.5)),
            limitations=[str(item) for item in payload.get("limitations") or []],
        )


@dataclass
class SourceResult:
    """A normalized result from one information source."""

    source: SourceName
    status: SourceStatus
    content: str
    detail: str = ""
    error: str = ""
    claims: list[AgentClaim] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_valid_evidence(self) -> bool:
        """Return whether this result may participate in evidence voting."""

        return self.status in EVIDENCE_STATUSES and bool(self.content.strip())

    @property
    def is_low_relevance(self) -> bool:
        """Return whether this result is weak contextual evidence."""

        return self.status == "low_relevance"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SourceResult":
        claims = []
        for item in payload.get("claims") or []:
            if isinstance(item, dict):
                claims.append(AgentClaim.from_dict(item))
        return cls(
            source=payload.get("source", "Model"),
            status=payload.get("status", "fallback"),
            content=str(payload.get("content") or ""),
            detail=str(payload.get("detail") or ""),
            error=str(payload.get("error") or ""),
            claims=claims,
            metadata=dict(payload.get("metadata") or {}),
        )

    def to_tool_text(self) -> str:
        """Serialize for LangChain ToolMessage content while staying readable."""

        payload = json.dumps(self.to_dict(), ensure_ascii=False, separators=(",", ":"))
        body = self.content.strip() or self.error.strip() or "无内容。"
        return f"{MARKER}: {payload}\n\n{body}"


def parse_source_results(text: str) -> list[SourceResult]:
    """Extract source result payloads embedded in tool or agent text."""

    results: list[SourceResult] = []
    if not text:
        return results

    pattern = rf"{re.escape(MARKER)}:\s*(\{{.*?\}})(?=\n|$)"
    for match in re.finditer(pattern, text, flags=re.DOTALL):
        try:
            payload = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            results.append(SourceResult.from_dict(payload))
    return results


def strip_source_markers(text: str) -> str:
    """Remove machine-readable source payloads from text shown to users."""

    if not text:
        return ""
    pattern = rf"{re.escape(MARKER)}:\s*\{{.*?\}}\s*"
    return re.sub(pattern, "", text, flags=re.DOTALL).strip()


def source_status_markdown(statuses: dict[str, dict[str, Any]]) -> str:
    """Render a compact source-status table."""

    if not statuses:
        return "无来源状态记录。"

    lines = [
        "| 来源 | 状态 | 详情 | 说明 |",
        "|---|---|---|---|",
    ]
    for source in ("RAG", "Web", "Model"):
        payload = statuses.get(source) or {}
        status = payload.get("status", "failed")
        detail = str(payload.get("detail") or "")
        error = str(payload.get("error") or "")
        content = str(payload.get("content") or "")
        note = error or content[:80].replace("\n", " ")
        lines.append(f"| {source} | {status} | {detail} | {note} |")
    return "\n".join(lines)


def status_is_evidence(status: str) -> bool:
    """Return whether a status can support evidence, possibly at reduced weight."""

    return status in EVIDENCE_STATUSES


def status_is_non_evidence(status: str) -> bool:
    """Return whether a status must be excluded from factual evidence."""

    return status in NON_EVIDENCE_STATUSES


def fallback_result(source: SourceName, reason: str, content: str = "") -> SourceResult:
    """Create a fallback result for agent text not backed by a successful tool call."""

    return SourceResult(
        source=source,
        status="fallback",
        detail="agent-generated fallback",
        error=reason,
        content=content,
    )
