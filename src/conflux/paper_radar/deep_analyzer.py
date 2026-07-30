"""P2 Deep Analyzer — full-text evidence extraction for high-value papers.

Downloads PDFs for shortlisted papers, extracts text, splits into page-tagged
chunks, and produces evidence-backed ProjectImpactSuggestion entries where each
factual claim links to specific page:chunk evidence references.

Evidence strength model (ascending):
  metadata_only  — no full text; evidence from abstract/metadata only
  abstract_only  — evidence from abstract
  full_text_section — evidence from named section + page:chunk
  figure_table    — evidence from figure/table caption
"""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path
from typing import Any

from conflux.core.p2_contracts import (
    EvidenceGap,
    EvidenceUtility,
    ImpactSuggestionType,
    PaperIdentity,
    ProjectImpactSuggestion,
    ProjectPaperLink,
    ProjectResearchContext,
    SearchIntent,
)
from conflux.paper_ingestion.pdf_downloader import PDFDownloader
from conflux.paper_ingestion.pdf_text import extract_pdf_text

# ── chunking constants ─────────────────────────────────────────────

CHUNK_MAX_CHARS = 3000
CHUNK_OVERLAP_CHARS = 300


# ── main entry point ───────────────────────────────────────────────

def run_deep_analysis(
    papers: list[tuple[ProjectPaperLink, dict[str, Any]]],
    context: ProjectResearchContext,
    intents: list[SearchIntent],
    *,
    download_dir: str | Path | None = None,
    max_papers: int = 5,
) -> list[ProjectImpactSuggestion]:
    """Run evidence-backed deep analysis on top-N papers.

    Parameters
    ----------
    papers: List of (ProjectPaperLink, paper_dict) tuples.
        paper_dict is a PaperRecord.to_dict() dict.
    context: Project research context.
    intents: Search intents for the run.
    download_dir: Optional PDF cache directory.
    max_papers: Maximum papers to deep-analyze (config.deep_read_limit).

    Returns a list of ProjectImpactSuggestion objects, each with evidence_refs.
    """
    # Sort by relevance descending, take top N
    sorted_papers = sorted(papers, key=lambda x: x[0].relevance, reverse=True)
    candidates = sorted_papers[:max_papers]

    suggestions: list[ProjectImpactSuggestion] = []
    downloader = _get_downloader(download_dir)

    for link, paper_dict in candidates:
        paper_suggestions = _analyze_one_paper(
            link=link,
            paper_dict=paper_dict,
            context=context,
            intents=intents,
            downloader=downloader,
        )
        suggestions.extend(paper_suggestions)

    return suggestions


def _get_downloader(download_dir: str | Path | None) -> PDFDownloader | None:
    if download_dir:
        return PDFDownloader(download_dir)
    try:
        tmp = Path(tempfile.gettempdir()) / "conflux_pdfs"
        tmp.mkdir(parents=True, exist_ok=True)
        return PDFDownloader(tmp)
    except Exception:
        return None


# ── single-paper analysis ──────────────────────────────────────────

def _analyze_one_paper(
    link: ProjectPaperLink,
    paper_dict: dict[str, Any],
    context: ProjectResearchContext,
    intents: list[SearchIntent],
    downloader: PDFDownloader | None,
) -> list[ProjectImpactSuggestion]:
    """Deep-analyze one paper: download → extract → chunk → suggest."""
    suggestions: list[ProjectImpactSuggestion] = []
    paper_id = paper_dict.get("id", link.paper_identity.canonical_id)
    run_id = hashlib.sha256(f"{paper_id}-{context.project_revision}".encode()).hexdigest()[:8]

    # Step 1: Download PDF if available
    pdf_path = _download_pdf(paper_dict, downloader) if downloader else None

    # Step 2: Extract text and chunk
    evidence_scope = "abstract_only"
    chunks: list[dict[str, Any]] = []

    if pdf_path:
        result = extract_pdf_text(pdf_path, max_pages=30)
        if result.status == "success" and result.text:
            evidence_scope = "full_text_section"
            chunks = _chunk_text(result.text)
    else:
        # Fall back to abstract-based analysis
        abstract = paper_dict.get("abstract", "")
        if abstract:
            chunks = [{"page": 0, "chunk_idx": 0, "text": abstract}]
        evidence_scope = "abstract_only"

    if not chunks:
        evidence_scope = "metadata_only"

    # Step 3: Score sections against research questions
    scored_chunks = _score_chunks(chunks, context)

    # Step 4: Generate suggestions based on evidence

    # Suggestion A: Link to evidence (always — record this paper exists)
    suggestions.append(_make_suggestion(
        link=link,
        paper_dict=paper_dict,
        run_id=run_id,
        s_type=ImpactSuggestionType.LINK_EVIDENCE,
        target_id=_best_intent_id(link),
        summary=f"Found evidence in '{_paper_title(paper_dict)}' relevant to project context.",
        evidence_refs=_top_chunk_refs(scored_chunks, 3),
        confidence=_evidence_confidence(scored_chunks),
    ))

    # Suggestion B: If methodologically strong, propose experiment adaptation
    if _has_method_content(chunks, context):
        suggestions.append(_make_suggestion(
            link=link,
            paper_dict=paper_dict,
            run_id=run_id,
            s_type=ImpactSuggestionType.PROPOSE_EXPERIMENT,
            target_id=_best_milestone_id(context),
            summary=f"Method from '{_paper_title(paper_dict)}' may be adaptable to experimental design.",
            evidence_refs=_top_chunk_refs(scored_chunks, 2),
            confidence=min(0.7, _evidence_confidence(scored_chunks)),
        ))

    # Suggestion C: If matches an evidence gap, flag it
    gap_id = _matching_gap_id(chunks, context)
    if gap_id:
        suggestions.append(_make_suggestion(
            link=link,
            paper_dict=paper_dict,
            run_id=run_id,
            s_type=ImpactSuggestionType.CREATE_RISK
            if any("risk" in g.description.lower() for g in context.evidence_gaps if g.id == gap_id)
            else ImpactSuggestionType.UPDATE_SEARCH_INTENT,
            target_id=gap_id,
            summary=f"Paper addresses evidence gap {gap_id}: may provide needed data.",
            evidence_refs=_top_chunk_refs(scored_chunks, 2),
            confidence=0.5,
        ))

    return suggestions


# ── PDF download ────────────────────────────────────────────────────

def _download_pdf(paper_dict: dict[str, Any], downloader: PDFDownloader) -> Path | None:
    paper_id = str(paper_dict.get("id") or "")
    pdf_url = str(paper_dict.get("pdf_url") or "")

    # Try arXiv URL first if source is arxiv
    if not pdf_url and paper_dict.get("source") == "arxiv":
        from conflux.paper_ingestion.pdf_downloader import arxiv_pdf_url
        pdf_url = arxiv_pdf_url(paper_id)

    if not pdf_url:
        return None

    try:
        return downloader.download(paper_id, pdf_url)
    except Exception:
        return None


# ── text chunking ───────────────────────────────────────────────────

def _chunk_text(text: str) -> list[dict[str, Any]]:
    """Split PDF text into page-tagged chunks."""
    chunks: list[dict[str, Any]] = []
    pages = text.split("\n[[CONFLUX_PAGE:")

    # Handle plain text without page markers
    if len(pages) == 1 and "[[CONFLUX_PAGE:" not in pages[0]:
        for i in range(0, max(1, len(pages[0])), CHUNK_MAX_CHARS - CHUNK_OVERLAP_CHARS):
            chunk_text = pages[0][i:i + CHUNK_MAX_CHARS].strip()
            if len(chunk_text) >= 100:
                chunks.append({"page": 0, "chunk_idx": i // (CHUNK_MAX_CHARS - CHUNK_OVERLAP_CHARS), "text": chunk_text})
        return chunks

    for page_block in pages:
        if not page_block.strip():
            continue
        # page_block looks like "3]]\ntext content..."
        parts = page_block.split("]]\n", 1)
        try:
            page_num = int(parts[0].strip())
        except (ValueError, IndexError):
            page_num = 0
        page_text = parts[1].strip() if len(parts) > 1 else ""

        if not page_text:
            continue

        # Split page into overlapping chunks
        for i in range(0, max(1, len(page_text)), CHUNK_MAX_CHARS - CHUNK_OVERLAP_CHARS):
            chunk_text = page_text[i:i + CHUNK_MAX_CHARS].strip()
            if len(chunk_text) < 100:
                continue
            chunks.append({
                "page": page_num,
                "chunk_idx": i // (CHUNK_MAX_CHARS - CHUNK_OVERLAP_CHARS),
                "text": chunk_text,
            })
    return chunks


# ── section scoring ─────────────────────────────────────────────────

def _score_chunks(
    chunks: list[dict[str, Any]],
    context: ProjectResearchContext,
) -> list[dict[str, Any]]:
    """Score chunks against research questions and keywords.

    Returns chunks with added 'score' and 'matched_terms' fields.
    All deterministic — no LLM calls.
    """
    search_terms = _extract_search_terms(context)
    if not search_terms:
        return chunks

    scored = []
    for chunk in chunks:
        text_lower = chunk["text"].lower()
        matches = []
        score = 0.0
        for term, weight in search_terms:
            count = text_lower.count(term.lower())
            if count:
                matches.append(term)
                score += weight * min(count, 5)  # cap per-term count
        chunk["score"] = round(min(score, 1.0), 3)
        chunk["matched_terms"] = matches
        scored.append(chunk)

    scored.sort(key=lambda c: c.get("score", 0), reverse=True)
    return scored


def _extract_search_terms(context: ProjectResearchContext) -> list[tuple[str, float]]:
    """Extract weighted search terms from project context."""
    terms: list[tuple[str, float]] = []

    # Research questions are highest weight
    for rq in context.research_questions:
        for word in rq.lower().split():
            word = word.strip(",.?\":;!()[]{}")
            if len(word) >= 4 and word not in {"what", "how", "should", "that", "which", "with", "from", "this", "they", "them", "their", "about", "need"}:
                terms.append((word, 0.15))

    # Overall goal
    for word in context.overall_goal.lower().split():
        word = word.strip(",.?\":;!()[]{}")
        if len(word) >= 4:
            terms.append((word, 0.08))

    # Milestone keywords
    for ms in context.active_milestones:
        for word in ms.lower().split():
            word = word.strip(",.?\":;!()[]{}")
            if len(word) >= 4:
                terms.append((word, 0.05))

    # Deduplicate by term — keep highest weight
    deduped: dict[str, float] = {}
    for term, weight in terms:
        deduped[term] = max(deduped.get(term, 0), weight)

    return sorted(deduped.items(), key=lambda x: x[1], reverse=True)[:30]


# ── evidence helpers ────────────────────────────────────────────────

def _top_chunk_refs(scored_chunks: list[dict[str, Any]], n: int) -> list[str]:
    """Return top-N evidence refs in 'page:chunk' format."""
    refs = []
    for chunk in scored_chunks[:n]:
        if chunk.get("score", 0) > 0:
            refs.append(f"p{chunk['page']}:c{chunk['chunk_idx']}")
    return refs if refs else ["abstract"]


def _evidence_confidence(scored_chunks: list[dict[str, Any]]) -> float:
    """Confidence based on top chunk scores and count."""
    if not scored_chunks:
        return 0.1
    top3 = [c.get("score", 0) for c in scored_chunks[:3]]
    avg = sum(top3) / max(1, len(top3))
    count_bonus = min(0.2, len(scored_chunks) * 0.02)
    return round(min(1.0, avg * 0.8 + count_bonus), 2)


def _paper_title(paper_dict: dict[str, Any]) -> str:
    title = str(paper_dict.get("title") or "Unknown")
    return title[:80] + "..." if len(title) > 80 else title


def _best_intent_id(link: ProjectPaperLink) -> str:
    return link.matched_intent_ids[0] if link.matched_intent_ids else ""


def _best_milestone_id(context: ProjectResearchContext) -> str:
    # Use first active milestone if any
    return context.active_milestones[0][:20] if context.active_milestones else ""


def _has_method_content(chunks: list[dict[str, Any]], context: ProjectResearchContext) -> bool:
    """Check if any chunk contains methodological language matching the project."""
    method_signals = [
        "method", "approach", "framework", "algorithm", "pipeline",
        "architecture", "experiment", "evaluation", "benchmark",
    ]
    method_terms = [t for t, _ in _extract_search_terms(context)[:10]]

    for chunk in chunks:
        text_lower = chunk["text"].lower()
        method_hits = sum(1 for s in method_signals if s in text_lower)
        term_hits = sum(1 for t in method_terms if t.lower() in text_lower)
        if method_hits >= 2 and term_hits >= 1:
            return True
    return False


def _matching_gap_id(chunks: list[dict[str, Any]], context: ProjectResearchContext) -> str:
    """Check if paper content addresses any known evidence gap."""
    if not context.evidence_gaps:
        return ""
    for gap in context.evidence_gaps:
        gap_terms = gap.description.lower().split()
        for chunk in chunks:
            text_lower = chunk["text"].lower()
            hits = sum(1 for t in gap_terms if len(t) >= 4 and t in text_lower)
            if hits >= 2:
                return gap.id
    return ""


# ── suggestion factory ──────────────────────────────────────────────

def _make_suggestion(
    link: ProjectPaperLink,
    paper_dict: dict[str, Any],
    run_id: str,
    s_type: ImpactSuggestionType,
    target_id: str,
    summary: str,
    evidence_refs: list[str],
    confidence: float,
) -> ProjectImpactSuggestion:
    """Create a ProjectImpactSuggestion with deterministic id."""
    raw = f"{link.project_id}-{link.paper_identity.canonical_id}-{s_type.value}-{summary[:40]}"
    sid = hashlib.sha256(raw.encode()).hexdigest()[:12]

    return ProjectImpactSuggestion(
        id=sid,
        project_id=link.project_id,
        paper_identity=link.paper_identity,
        type=s_type,
        target_id=target_id,
        summary=summary,
        rationale=f"Based on analysis of {'full text' if evidence_refs[0] != 'abstract' else 'abstract'} analysis. "
                  f"Evidence refs: {', '.join(evidence_refs[:3])}.",
        evidence_refs=evidence_refs,
        confidence=confidence,
        status="proposed",
        created_by_run=run_id,
    )
