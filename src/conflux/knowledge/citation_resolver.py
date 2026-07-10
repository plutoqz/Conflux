"""Citation helpers for paper-derived knowledge chunks."""

from __future__ import annotations

from .source_models import KnowledgeSource


def paper_citation_ref(metadata: dict) -> str:
    """Build a stable citation ref from paper chunk metadata."""

    paper_id = str(metadata.get("paper_id") or "unknown")
    chunk_id = str(metadata.get("chunk_id") or "")
    if chunk_id:
        return f"LocalPaper:{paper_id}:{chunk_id}"
    return f"LocalPaper:{paper_id}"


def knowledge_source_from_metadata(metadata: dict) -> KnowledgeSource:
    """Round-trip paper chunk metadata into a KnowledgeSource."""

    source_id = str(metadata.get("paper_id") or metadata.get("source") or "unknown")
    return KnowledgeSource(
        id=source_id,
        source_type="LocalPaper",
        title=str(metadata.get("paper_title") or source_id),
        locator=str(metadata.get("paper_url") or metadata.get("source") or ""),
        metadata={
            "paper_id": source_id,
            "chunk_id": str(metadata.get("chunk_id") or ""),
            "citation_ref": paper_citation_ref(metadata),
            "pdf_url": str(metadata.get("pdf_url") or ""),
            "ingestion_action": str(metadata.get("ingestion_action") or ""),
        },
    )
