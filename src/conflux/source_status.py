"""Structured source status payloads used across tools and agents."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Iterator, Literal


SourceName = Literal["RAG", "Web", "Model", "FactCheck", "Synthesize"]
SourceStatus = Literal["success", "low_relevance", "no_evidence", "failed", "fallback"]
EvidenceClass = Literal[
    "peer_reviewed",
    "preprint",
    "authoritative_document",
    "community_content",
    "model_inference",
]
EVIDENCE_STATUSES = {"success", "low_relevance"}
NON_EVIDENCE_STATUSES = {"no_evidence", "failed", "fallback"}

EXTERNAL_EVIDENCE_CLASSES: frozenset[str] = frozenset({
    "peer_reviewed",
    "preprint",
    "authoritative_document",
})
LEGACY_EVIDENCE_CLASSES = {
    "local_document": "authoritative_document",
    "external_source": "community_content",
}

MARKER = "CONFLUX_SOURCE_RESULT_JSON"


@dataclass
class EvidenceItem:
    """A source-backed, claim-level evidence item shared across the pipeline."""

    claim: str
    source: SourceName
    verbatim_quote: str = ""
    paper_id: str = ""
    paper_section: str = ""
    relevance: float = 0.0
    research_type: str = ""
    metric: str = ""
    evidence_refs: list[str] = field(default_factory=list)
    confidence: float = 0.5
    limitations: list[str] = field(default_factory=list)
    evidence_class: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "EvidenceItem":
        source = payload.get("source", "Model")
        return cls(
            claim=str(payload.get("claim") or ""),
            source=source,
            verbatim_quote=str(payload.get("verbatim_quote") or payload.get("quote") or ""),
            paper_id=str(payload.get("paper_id") or ""),
            paper_section=str(payload.get("paper_section") or ""),
            relevance=float(payload.get("relevance", 0.0)),
            research_type=str(payload.get("research_type") or ""),
            metric=str(payload.get("metric") or ""),
            evidence_refs=[str(item) for item in payload.get("evidence_refs") or []],
            confidence=float(payload.get("confidence", 0.5)),
            limitations=[str(item) for item in payload.get("limitations") or []],
            evidence_class=normalize_evidence_class(payload.get("evidence_class"), source),
        )


# Backwards-compatible public name used by existing tools and integrations.
AgentClaim = EvidenceItem


@dataclass
class SourceResult:
    """A normalized result from one information source."""

    source: SourceName
    status: SourceStatus
    content: str
    detail: str = ""
    error: str = ""
    claims: list[EvidenceItem] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    evidence_class: str = ""

    def __post_init__(self) -> None:
        self.evidence_class = normalize_evidence_class(self.evidence_class, self.source)

    @property
    def can_support_external_fact(self) -> bool:
        """Whether this source may underpin external factual claims.

        Model inference is excluded regardless of execution status.
        """

        return self.evidence_class in EXTERNAL_EVIDENCE_CLASSES

    @property
    def is_valid_evidence(self) -> bool:
        """Return whether this result may participate in evidence voting."""

        return self.status in EVIDENCE_STATUSES and bool(self.content.strip())

    @property
    def is_low_relevance(self) -> bool:
        """Return whether this result is weak contextual evidence."""

        return self.status == "low_relevance"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["can_support_external_fact"] = self.can_support_external_fact
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SourceResult":
        claims = []
        for item in payload.get("claims") or []:
            if isinstance(item, dict):
                claims.append(EvidenceItem.from_dict(item))
        source = payload.get("source", "Model")
        return cls(
            source=source,
            status=payload.get("status", "fallback"),
            content=str(payload.get("content") or ""),
            detail=str(payload.get("detail") or ""),
            error=str(payload.get("error") or ""),
            claims=claims,
            metadata=dict(payload.get("metadata") or {}),
            evidence_class=normalize_evidence_class(payload.get("evidence_class"), source),
        )

    def to_tool_text(self) -> str:
        """Serialize for LangChain ToolMessage content while staying readable."""

        payload = json.dumps(self.to_dict(), ensure_ascii=False, separators=(",", ":"))
        body = self.content.strip() or self.error.strip() or "无内容。"
        return f"{MARKER}: {payload}\n\n{body}"


def _iter_source_payloads(text: str) -> Iterator[tuple[int, int, dict[str, Any]]]:
    """Yield marker spans and JSON objects without regex-truncating nested data."""

    decoder = json.JSONDecoder()
    cursor = 0
    prefix = f"{MARKER}:"
    while text:
        marker_start = text.find(prefix, cursor)
        if marker_start < 0:
            return
        json_start = marker_start + len(prefix)
        while json_start < len(text) and text[json_start].isspace():
            json_start += 1
        try:
            payload, length = decoder.raw_decode(text[json_start:])
        except json.JSONDecodeError:
            cursor = json_start
            continue
        end = json_start + length
        if isinstance(payload, dict):
            yield marker_start, end, payload
        cursor = end


def parse_source_results(text: str) -> list[SourceResult]:
    """Extract source result payloads embedded in tool or agent text."""

    results: list[SourceResult] = []
    if not text:
        return results

    for _, _, payload in _iter_source_payloads(text):
        results.append(SourceResult.from_dict(payload))
    return results


def strip_source_markers(text: str) -> str:
    """Remove machine-readable source payloads from text shown to users."""

    if not text:
        return ""
    spans = [(start, end) for start, end, _ in _iter_source_payloads(text)]
    if not spans:
        return text.strip()
    pieces = []
    cursor = 0
    for start, end in spans:
        pieces.append(text[cursor:start])
        cursor = end
    pieces.append(text[cursor:])
    return "".join(pieces).strip()


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
        evidence_class="model_inference",
    )


def normalize_evidence_class(value: Any, source: str) -> str:
    """Normalize legacy/missing values with conservative source-aware defaults."""

    normalized = str(value or "").strip()
    normalized = LEGACY_EVIDENCE_CLASSES.get(normalized, normalized)
    if normalized in {
        "peer_reviewed",
        "preprint",
        "authoritative_document",
        "community_content",
        "model_inference",
    }:
        return normalized
    if source == "RAG":
        return "authoritative_document"
    if source == "Web":
        return "community_content"
    return "model_inference"
