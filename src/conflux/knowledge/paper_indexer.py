"""Promote paper inbox entries into traceable knowledge documents."""

from __future__ import annotations

import json
import hashlib
import re
import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from langchain_core.documents import Document

from conflux.paper_ingestion.ingestion_policy import default_policy, decide_ingestion
from conflux.paper_ingestion.models import IngestionDecision, PaperAnalysis, PaperRecord
from conflux.paper_ingestion.pdf_downloader import PDFDownloader
from conflux.paper_ingestion.pdf_text import extract_pdf_text, find_local_pdf

from .citation_resolver import knowledge_source_from_metadata, paper_citation_ref
from .source_models import KnowledgeSource


@dataclass(slots=True)
class PaperPromotionArtifacts:
    """Files written by a paper promotion run."""

    documents_dir: Path
    manifest_path: Path
    sources_path: Path


@dataclass(slots=True)
class PaperPromotionResult:
    """In-memory result of promoting a paper inbox."""

    documents: list[Document]
    decisions: list[IngestionDecision]
    sources: list[KnowledgeSource]
    artifacts: PaperPromotionArtifacts | None = None
    indexed_count: int = 0


def load_inbox_payload(path: str | Path) -> list[tuple[PaperRecord, PaperAnalysis]]:
    """Load `paper_inbox.json` into typed paper and analysis objects."""

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = payload.get("papers")
    if not isinstance(rows, list):
        raise ValueError(f"Paper inbox must contain a papers list: {path}")

    entries: list[tuple[PaperRecord, PaperAnalysis]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        paper_payload = row.get("paper") or {}
        analysis_payload = row.get("analysis") or {}
        paper = PaperRecord.from_dict(paper_payload)
        analysis = PaperAnalysis.from_dict(analysis_payload)
        entries.append((paper, analysis))
    return entries


def paper_to_documents(
    paper: PaperRecord,
    analysis: PaperAnalysis,
    decision: IngestionDecision,
    *,
    full_text: str = "",
    full_text_status: str = "not_requested",
) -> list[Document]:
    """Convert one selected paper into RAG-ready LangChain documents."""

    if decision.action == "skip":
        return []
    if decision.action == "metadata_only":
        return []

    content = _summary_content(paper, analysis, decision)
    metadata = _document_metadata(
        paper,
        analysis,
        decision,
        "summary",
        content_scope="summary",
        full_text_status=full_text_status,
        content=content,
        paper_section="summary",
    )
    documents = [Document(page_content=content, metadata=metadata)]
    if decision.action == "full_text" and full_text.strip():
        documents.extend(_full_text_documents(paper, analysis, decision, full_text))
    return documents


def promote_inbox(
    inbox_path: str | Path,
    *,
    out_dir: str | Path | None = None,
    policy_name: str = "default",
    allow_full_text: bool = False,
    pinned_ids: list[str] | None = None,
    index: bool = False,
    pdf_dir: str | Path | None = None,
    download_pdfs: bool = False,
) -> PaperPromotionResult:
    """Promote an inbox to knowledge documents and optionally index them."""

    if policy_name != "default":
        raise ValueError(f"Unsupported paper promotion policy: {policy_name}")

    policy = default_policy(allow_full_text=allow_full_text)
    documents: list[Document] = []
    decisions: list[IngestionDecision] = []
    sources: list[KnowledgeSource] = []

    for paper, analysis in load_inbox_payload(inbox_path):
        decision = decide_ingestion(paper, analysis, policy=policy, pinned_ids=pinned_ids or [])
        decisions.append(decision)
        full_text, full_text_status = _load_full_text(
            paper,
            decision,
            pdf_dir=pdf_dir,
            download_pdfs=download_pdfs,
            out_dir=out_dir,
        )
        docs = paper_to_documents(
            paper,
            analysis,
            decision,
            full_text=full_text,
            full_text_status=full_text_status,
        )
        documents.extend(docs)
        for doc in docs:
            sources.append(knowledge_source_from_metadata(doc.metadata))

    if index:
        for document in documents:
            document.metadata["full_text_indexed"] = bool(
                document.metadata.get("content_scope") == "full_text"
                and document.metadata.get("full_text_extracted")
            )
    indexed_count = _index_documents(documents) if index else 0
    artifacts = write_promoted_papers(documents, decisions, sources, out_dir=out_dir) if out_dir else None
    return PaperPromotionResult(
        documents=documents,
        decisions=decisions,
        sources=sources,
        artifacts=artifacts,
        indexed_count=indexed_count,
    )


def write_promoted_papers(
    documents: list[Document],
    decisions: list[IngestionDecision],
    sources: list[KnowledgeSource],
    *,
    out_dir: str | Path,
) -> PaperPromotionArtifacts:
    """Materialize promoted paper documents and manifests for review/indexing."""

    root = Path(out_dir)
    docs_dir = root / "papers"
    docs_dir.mkdir(parents=True, exist_ok=True)

    written_docs = []
    for doc in documents:
        chunk_id = str(doc.metadata.get("chunk_id") or "paper-summary")
        path = docs_dir / f"{_safe_filename(chunk_id)}.md"
        path.write_text(_document_markdown(doc), encoding="utf-8")
        written_docs.append({
            "path": str(path),
            "chunk_id": chunk_id,
            "citation_ref": paper_citation_ref(doc.metadata),
            "paper_section": doc.metadata.get("paper_section", ""),
            "full_text_requested": bool(doc.metadata.get("full_text_requested")),
            "full_text_downloaded": bool(doc.metadata.get("full_text_downloaded")),
            "full_text_extracted": bool(doc.metadata.get("full_text_extracted")),
            "full_text_indexed": bool(doc.metadata.get("full_text_indexed")),
            "content_hash": doc.metadata.get("content_hash", ""),
        })

    manifest_path = root / "paper_promotion_manifest.json"
    sources_path = root / "paper_knowledge_sources.json"
    manifest_path.write_text(
        json.dumps({
            "documents": written_docs,
            "decisions": [decision.to_dict() for decision in decisions],
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    sources_path.write_text(
        json.dumps([source.to_dict() for source in sources], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return PaperPromotionArtifacts(
        documents_dir=docs_dir,
        manifest_path=manifest_path,
        sources_path=sources_path,
    )


def _summary_content(
    paper: PaperRecord,
    analysis: PaperAnalysis,
    decision: IngestionDecision,
) -> str:
    reasons = _as_list(analysis.metadata.get("score_reasons"))
    matched_keywords = _as_list(analysis.metadata.get("matched_keywords"))
    matched_fields = _as_list(analysis.metadata.get("matched_fields"))
    matched_questions = analysis.matched_questions

    lines = [
        f"# {paper.title}",
        "",
        "## Paper Metadata",
        f"- Source type: LocalPaper",
        f"- Paper ID: {paper.id}",
        f"- Source: {paper.source}",
        f"- URL: {paper.url or 'not available'}",
        f"- PDF: {paper.pdf_url or 'not available'}",
        f"- Authors: {', '.join(paper.authors) if paper.authors else 'Unknown'}",
        f"- Published: {paper.published_at.isoformat() if paper.published_at else 'not available'}",
        f"- Categories: {', '.join(paper.categories) if paper.categories else 'not available'}",
        "",
        "## Abstract",
        paper.abstract or "No abstract available.",
        "",
        "## Paper Radar Analysis",
        f"- Ingestion action: {decision.action}",
        f"- Relevance score: {analysis.relevance_score:.3f}",
        f"- Reading level: {analysis.reading_level}",
        f"- Citation value: {analysis.citation_value}",
        f"- Matched keywords: {', '.join(matched_keywords) if matched_keywords else 'not available'}",
        f"- Matched fields: {', '.join(matched_fields) if matched_fields else 'not available'}",
        f"- Matched research questions: {'; '.join(matched_questions) if matched_questions else 'not available'}",
        f"- Reusable methods: {', '.join(analysis.reusable_methods) if analysis.reusable_methods else 'not available'}",
        f"- Reusable datasets: {', '.join(analysis.reusable_datasets) if analysis.reusable_datasets else 'not available'}",
        f"- Selection reasons: {'; '.join(reasons) if reasons else decision.reason}",
        "",
        "## Method Summary",
        analysis.method_summary or "No method summary available.",
        "",
        "## Novelty And Limitations",
        analysis.novelty or "Novelty not available.",
        "",
        analysis.limitations or "Limitations not available.",
    ]
    return "\n".join(lines).rstrip() + "\n"


def _document_metadata(
    paper: PaperRecord,
    analysis: PaperAnalysis,
    decision: IngestionDecision,
    scope: str,
    *,
    content_scope: str,
    full_text_status: str = "not_requested",
    content: str = "",
    paper_section: str = "",
    char_start: int | None = None,
    char_end: int | None = None,
) -> dict[str, Any]:
    safe_id = _safe_paper_id(paper.id)
    chunk_id = f"paper:{safe_id}#{scope}"
    full_text_requested = decision.action == "full_text"
    full_text_downloaded = full_text_status in {"downloaded", "extracted", "success"} or bool(content_scope == "full_text" and content.strip())
    full_text_extracted = bool(content_scope == "full_text" and content.strip()) or full_text_status in {"extracted", "success"}
    metadata = {
        "source_type": "LocalPaper",
        "paper_id": paper.id,
        "paper_title": paper.title,
        "paper_url": paper.url,
        "pdf_url": paper.pdf_url,
        "paper_source": paper.source,
        "authors": "; ".join(paper.authors),
        "categories": "; ".join(paper.categories),
        "published_at": paper.published_at.isoformat() if paper.published_at else "",
        "reading_level": analysis.reading_level,
        "relevance_score": float(analysis.relevance_score),
        "citation_value": analysis.citation_value,
        "ingestion_action": decision.action,
        "ingestion_priority": int(decision.priority),
        "chunk_id": chunk_id,
        "source": f"papers/{safe_id}/{scope}",
        "content_scope": content_scope,
        "full_text_status": full_text_status,
        "full_text_requested": full_text_requested,
        "full_text_downloaded": full_text_downloaded,
        "full_text_extracted": full_text_extracted,
        "full_text_indexed": False,
        "paper_section": paper_section or content_scope,
        "content_hash": hashlib.sha256(content.encode("utf-8")).hexdigest(),
    }
    if char_start is not None:
        metadata["char_start"] = char_start
    if char_end is not None:
        metadata["char_end"] = char_end
    return metadata


def _full_text_documents(
    paper: PaperRecord,
    analysis: PaperAnalysis,
    decision: IngestionDecision,
    full_text: str,
    *,
    chunk_chars: int = 3500,
) -> list[Document]:
    chunks = _sectioned_text_chunks(full_text, chunk_chars=chunk_chars)
    documents = []
    for idx, (chunk, section, char_start, char_end) in enumerate(chunks):
        scope = f"fulltext-{idx}"
        metadata = _document_metadata(
            paper,
            analysis,
            decision,
            scope,
            content_scope="full_text",
            full_text_status="success",
            content=chunk,
            paper_section=section,
            char_start=char_start,
            char_end=char_end,
        )
        page_start, page_end = _page_range_for_offsets(full_text, char_start, char_end)
        if page_start is not None:
            metadata["page_start"] = page_start
        if page_end is not None:
            metadata["page_end"] = page_end
        content = "\n".join([
            f"# {paper.title}",
            "",
            f"Full-text chunk {idx + 1} of {len(chunks)}.",
            "",
            chunk.strip(),
            "",
        ])
        documents.append(Document(page_content=content, metadata=metadata))
    return documents


def _document_markdown(doc: Document) -> str:
    metadata = doc.metadata
    front_matter = {
        "source_type": metadata.get("source_type", ""),
        "paper_id": metadata.get("paper_id", ""),
        "chunk_id": metadata.get("chunk_id", ""),
        "citation_ref": paper_citation_ref(metadata),
        "ingestion_action": metadata.get("ingestion_action", ""),
        "paper_section": metadata.get("paper_section", ""),
        "full_text_requested": bool(metadata.get("full_text_requested")),
        "full_text_downloaded": bool(metadata.get("full_text_downloaded")),
        "full_text_extracted": bool(metadata.get("full_text_extracted")),
        "full_text_indexed": bool(metadata.get("full_text_indexed")),
        "content_hash": metadata.get("content_hash", ""),
    }
    serialized = yaml.safe_dump(
        front_matter,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    ).rstrip()
    return f"---\n{serialized}\n---\n\n{doc.page_content.rstrip()}\n"


def _index_documents(documents: list[Document]) -> int:
    from conflux.rag.indexer import create_vector_store, index_documents

    return index_documents(create_vector_store(), documents)


def _load_full_text(
    paper: PaperRecord,
    decision: IngestionDecision,
    *,
    pdf_dir: str | Path | None,
    download_pdfs: bool,
    out_dir: str | Path | None,
) -> tuple[str, str]:
    if decision.action != "full_text":
        return "", "not_requested"

    pdf_path = find_local_pdf(paper.id, pdf_dir) if pdf_dir else None
    if pdf_path is None and download_pdfs:
        target_dir = Path(pdf_dir) if pdf_dir else Path(out_dir or "data/documents/papers") / "pdfs"
        pdf_path = PDFDownloader(target_dir).download(paper.id, paper.pdf_url)
    if pdf_path is None:
        return "", "not_downloaded"

    result = extract_pdf_text(pdf_path)
    if result.text.strip():
        return result.text, "extracted"
    return "", f"extraction_{result.status}"


def _safe_paper_id(value: str) -> str:
    text = value.strip()
    if "/abs/" in text:
        text = text.rsplit("/abs/", 1)[1]
    if "/pdf/" in text:
        text = text.rsplit("/pdf/", 1)[1]
    if text.endswith(".pdf"):
        text = text[:-4]
    return _safe_filename(text or "unknown")


def _safe_filename(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.#-]+", "-", value.strip())
    return safe.strip("-") or "unknown"


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value if str(item)]
    return [str(value)]


def _text_chunks(text: str, *, chunk_chars: int) -> list[str]:
    return [chunk for chunk, _, _, _ in _sectioned_text_chunks(text, chunk_chars=chunk_chars)]


def _sectioned_text_chunks(text: str, *, chunk_chars: int) -> list[tuple[str, str, int, int]]:
    clean = text.strip()
    if not clean:
        return []
    headings: list[tuple[int, str]] = []
    heading_pattern = re.compile(
        r"^(?:#{1,6}\s+|\d+(?:\.\d+)*\.?\s+)(.+?)\s*$",
        flags=re.MULTILINE,
    )
    inherited_section = "full_text"
    canonical_sections = {
        "abstract", "introduction", "method", "results", "limitations",
        "discussion", "future_work", "conclusion",
    }
    for match in heading_pattern.finditer(clean):
        normalized = _normalize_paper_section(match.group(1))
        if normalized in canonical_sections:
            inherited_section = normalized
        headings.append((match.start(), inherited_section if inherited_section != "full_text" else normalized))

    chunks: list[tuple[str, str, int, int]] = []
    start = 0
    while start < len(clean):
        end = min(len(clean), start + chunk_chars)
        if end < len(clean):
            boundary = clean.rfind("\n\n", start, end)
            if boundary > start + 500:
                end = boundary
        chunk = clean[start:end].strip()
        if chunk:
            section = "full_text"
            for position, heading in headings:
                if position <= start:
                    section = heading or section
                else:
                    break
            actual_start = start
            while actual_start < end and clean[actual_start].isspace():
                actual_start += 1
            chunks.append((chunk, section, actual_start, min(end, len(clean))))
        start = end
    return chunks


def _normalize_paper_section(value: str) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip().casefold()
    if not text:
        return "full_text"
    aliases = (
        ("abstract", "abstract"),
        ("introduction", "introduction"),
        ("method", "method"),
        ("approach", "method"),
        ("experiment", "results"),
        ("result", "results"),
        ("evaluation", "results"),
        ("limitation", "limitations"),
        ("challenge", "limitations"),
        ("failure", "limitations"),
        ("discussion", "discussion"),
        ("future", "future_work"),
        ("conclusion", "conclusion"),
    )
    for marker, normalized in aliases:
        if marker in text:
            return normalized
    return text[:80]


def _page_range_for_offsets(text: str, start: int, end: int) -> tuple[int | None, int | None]:
    markers = [
        (match.start(), int(match.group(1)))
        for match in re.finditer(r"\[\[CONFLUX_PAGE:(\d+)\]\]", text)
    ]
    if not markers:
        return None, None
    page_start = markers[0][1]
    page_end = page_start
    for position, page in markers:
        if position <= start:
            page_start = page
        if position <= end:
            page_end = page
        else:
            break
    return page_start, page_end
