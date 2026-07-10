"""Stable data contracts for paper ingestion."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Literal


IngestionAction = Literal["skip", "metadata_only", "summary_only", "full_text", "pinned"]
ReadingLevel = Literal["deep", "skim", "skip"]
CitationValue = Literal["high", "medium", "low"]


@dataclass(slots=True)
class PaperRecord:
    """A normalized academic paper record from any paper source."""

    id: str
    title: str
    abstract: str = ""
    authors: list[str] = field(default_factory=list)
    published_at: datetime | None = None
    source: str = "unknown"
    url: str = ""
    pdf_url: str = ""
    doi: str = ""
    venue: str = ""
    categories: list[str] = field(default_factory=list)
    matched_queries: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["published_at"] = self.published_at.isoformat() if self.published_at else None
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PaperRecord":
        url = str(payload.get("url") or payload.get("arxiv_url") or "")
        raw_id = str(payload.get("id") or payload.get("paper_id") or "")
        if not url and raw_id.startswith(("http://", "https://")):
            url = raw_id
        return cls(
            id=raw_id,
            title=str(payload.get("title") or ""),
            abstract=str(payload.get("abstract") or payload.get("summary") or ""),
            authors=_string_list(payload.get("authors")),
            published_at=parse_datetime(payload.get("published_at") or payload.get("published")),
            source=str(payload.get("source") or "unknown"),
            url=url,
            pdf_url=str(payload.get("pdf_url") or _pdf_url_from_links(payload.get("links"))),
            doi=str(payload.get("doi") or ""),
            venue=str(payload.get("venue") or ""),
            categories=_string_list(payload.get("categories") or payload.get("primary_category")),
            matched_queries=_string_list(payload.get("matched_queries")),
            metadata=dict(payload.get("metadata") or {}),
        )


@dataclass(slots=True)
class PaperAnalysis:
    """Analysis result attached to a paper after relevance scoring."""

    paper_id: str
    relevance_score: float
    reading_level: ReadingLevel
    matched_questions: list[str] = field(default_factory=list)
    method_summary: str = ""
    novelty: str = ""
    reusable_methods: list[str] = field(default_factory=list)
    reusable_datasets: list[str] = field(default_factory=list)
    citation_value: CitationValue = "medium"
    limitations: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PaperAnalysis":
        return cls(
            paper_id=str(payload.get("paper_id") or ""),
            relevance_score=float(payload.get("relevance_score") or 0.0),
            reading_level=_reading_level(payload.get("reading_level")),
            matched_questions=_string_list(payload.get("matched_questions")),
            method_summary=str(payload.get("method_summary") or ""),
            novelty=str(payload.get("novelty") or ""),
            reusable_methods=_string_list(payload.get("reusable_methods")),
            reusable_datasets=_string_list(payload.get("reusable_datasets")),
            citation_value=_citation_value(payload.get("citation_value")),
            limitations=str(payload.get("limitations") or ""),
            metadata=dict(payload.get("metadata") or {}),
        )


@dataclass(slots=True)
class IngestionDecision:
    """A policy decision describing whether and how a paper enters knowledge storage."""

    paper_id: str
    action: IngestionAction
    reason: str
    priority: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def parse_datetime(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, (list, tuple, set)):
        values = []
        for item in value:
            values.extend(_string_list(item))
        return values
    if isinstance(value, dict):
        for key in ("name", "term", "value", "title"):
            text = str(value.get(key) or "").strip()
            if text:
                return [text]
        return []
    text = str(value).strip()
    return [text] if text else []


def _pdf_url_from_links(value: Any) -> str:
    if not isinstance(value, list):
        return ""
    for item in value:
        if not isinstance(item, dict):
            continue
        href = str(item.get("href") or "")
        title = str(item.get("title") or "").lower()
        link_type = str(item.get("type") or "").lower()
        if href and (title == "pdf" or link_type == "application/pdf" or "/pdf/" in href):
            return href
    return ""


def _reading_level(value: Any) -> ReadingLevel:
    text = str(value or "skip").strip().lower()
    if text in {"deep", "skim", "skip"}:
        return text  # type: ignore[return-value]
    return "skip"


def _citation_value(value: Any) -> CitationValue:
    text = str(value or "medium").strip().lower()
    if text in {"high", "medium", "low"}:
        return text  # type: ignore[return-value]
    return "medium"
