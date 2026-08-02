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
import json
import tempfile
import time
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
    RadarRunStats,
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
    llm_model: Any = None,
    stats: RadarRunStats | None = None,
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
    llm_model: Optional chat model for semantic deep analysis.  When None,
        the deterministic keyword-based analysis is used (legacy behavior).
    stats: Optional RadarRunStats to record LLM telemetry (calls, tokens,
        elapsed ms, fallback count).

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
            llm_model=llm_model,
            stats=stats,
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
    llm_model: Any = None,
    stats: RadarRunStats | None = None,
) -> list[ProjectImpactSuggestion]:
    """Deep-analyze one paper: download → extract → chunk → suggest.

    When ``llm_model`` is provided, a semantic LLM analysis is attempted first
    (abstract-first, full-text chunks when available).  Any failure — network,
    invalid JSON, or empty output — falls back to the deterministic keyword
    analysis so the radar never loses a paper to an LLM outage.
    """
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

    # Step 3: Semantic LLM analysis (abstract-first; full-text chunks when
    # available).  Deterministic analysis remains the safety net.
    if llm_model is not None:
        llm_suggestions, telemetry = _llm_analyze_paper(
            link=link,
            paper_dict=paper_dict,
            context=context,
            chunks=chunks,
            run_id=run_id,
            llm_model=llm_model,
        )
        if stats is not None:
            stats.llm_calls += telemetry["calls"]
            stats.llm_total_tokens += telemetry["total_tokens"]
            stats.llm_elapsed_ms += telemetry["elapsed_ms"]
            stats.llm_fallback_count += 1 if telemetry["fell_back"] else 0
        if llm_suggestions:
            return llm_suggestions

    # Step 4: Deterministic keyword analysis (legacy fallback)
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


# ── LLM deep analysis ──────────────────────────────────────────────

LLM_ANALYSIS_SYSTEM = (
    "你是一名研究雷达分析员。给定一篇论文和项目研究上下文，"
    "判断该论文对项目的价值并给出可执行的建议。"
    "只输出有效 JSON，不要输出其他文字。"
)

LLM_ANALYSIS_PROMPT = """分析以下论文对项目研究的影响，输出结构化建议。

## 项目研究上下文
- 总体目标：{overall_goal}
- 研究问题：{research_questions}
- 活跃里程碑：{milestones}
- 已知证据缺口：{gaps}

## 论文
- 标题：{title}
- 作者：{authors}
- 年份：{year}
- 摘要：{abstract}

## 论文全文节选（按相关性排序，可能截断）
{chunks_text}

## 要求
1. 判断论文与项目研究的相关性 relevance（0.0-1.0）。
2. 给出 1-4 条建议，每条建议必须：
   - type 取值之一：link_evidence / propose_experiment / create_risk / update_search_intent
   - summary：一句话说明论文如何影响项目
   - rationale：具体依据，引用论文内容（1-2 句）
   - evidence_refs：引用上述全文节选中的证据（如 p1:c0），仅摘要可用时填 ["abstract"]
   - confidence：0.0-1.0
   - target_id：命中的缺口 id（如有）或空字符串
3. 仅当论文确实与项目相关时才建议 link_evidence；相关性低于 0.3 时建议数组可为空。

仅输出 JSON：
{{"relevance": 0.0, "suggestions": [{{"type": "link_evidence", "summary": "", "rationale": "", "evidence_refs": [], "confidence": 0.0, "target_id": ""}}]}}"""


def _llm_analyze_paper(
    link: ProjectPaperLink,
    paper_dict: dict[str, Any],
    context: ProjectResearchContext,
    chunks: list[dict[str, Any]],
    run_id: str,
    llm_model: Any,
) -> tuple[list[ProjectImpactSuggestion], dict[str, Any]]:
    """Semantic LLM analysis with deterministic fallback.

    Returns (suggestions, telemetry) where telemetry contains calls,
    total_tokens, elapsed_ms and fell_back.  An empty suggestion list signals
    the caller to fall back to the deterministic analysis.
    """
    telemetry = {"calls": 1, "total_tokens": 0, "elapsed_ms": 0, "fell_back": False}
    started = time.monotonic()

    # Build the prompt — abstract-first, top full-text chunks when available.
    chunks_text = _llm_chunk_preview(chunks)
    abstract = str(paper_dict.get("abstract") or "").strip()
    prompt = LLM_ANALYSIS_PROMPT.format(
        overall_goal=str(context.overall_goal or ""),
        research_questions="\n".join(f"- {rq}" for rq in context.research_questions) or "-",
        milestones="\n".join(f"- {ms}" for ms in context.active_milestones) or "-",
        gaps="\n".join(f"- {g.description}" for g in context.evidence_gaps) or "无",
        title=str(paper_dict.get("title") or ""),
        authors=", ".join(str(a) for a in (paper_dict.get("authors") or [])[:5]) or "未知",
        year=str(paper_dict.get("year") or paper_dict.get("published_at") or "未知"),
        abstract=abstract or "（无摘要）",
        chunks_text=chunks_text,
    )

    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        response = llm_model.invoke([
            SystemMessage(content=LLM_ANALYSIS_SYSTEM),
            HumanMessage(content=prompt),
        ])
        content = str(response.content) if hasattr(response, "content") else str(response)
        # Token telemetry from usage metadata (best-effort).
        usage = getattr(response, "usage_metadata", None) or {}
        telemetry["total_tokens"] = int(usage.get("total_tokens") or 0)
    except Exception:
        telemetry["elapsed_ms"] = int((time.monotonic() - started) * 1000)
        telemetry["fell_back"] = True
        return [], telemetry

    payload = _parse_llm_json(content)
    telemetry["elapsed_ms"] = int((time.monotonic() - started) * 1000)
    if payload is None:
        telemetry["fell_back"] = True
        return [], telemetry

    suggestions = _llm_payload_to_suggestions(
        payload=payload,
        link=link,
        run_id=run_id,
    )
    if not suggestions:
        telemetry["fell_back"] = True
    return suggestions, telemetry


def _llm_chunk_preview(chunks: list[dict[str, Any]], limit: int = 4000) -> str:
    """Build a bounded text preview from the top chunks (abstract-first)."""
    if not chunks:
        return "（无全文）"
    parts = []
    budget = limit
    for chunk in chunks:
        text = str(chunk.get("text") or "").strip()
        if not text:
            continue
        if budget <= 0:
            break
        piece = text[:budget]
        parts.append(f"[p{chunk.get('page', 0)}:c{chunk.get('chunk_idx', 0)}] {piece}")
        budget -= len(piece)
    return "\n".join(parts) or "（无全文）"


def _parse_llm_json(content: str) -> dict[str, Any] | None:
    """Extract the JSON object from a model response, tolerating fences."""
    text = str(content or "").strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None


def _llm_payload_to_suggestions(
    payload: dict[str, Any],
    link: ProjectPaperLink,
    run_id: str,
) -> list[ProjectImpactSuggestion]:
    """Map the LLM JSON payload onto the ProjectImpactSuggestion protocol."""
    suggestions: list[ProjectImpactSuggestion] = []
    raw_items = payload.get("suggestions") or []
    if not isinstance(raw_items, list):
        return suggestions

    valid_types = {t.value for t in ImpactSuggestionType}
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        type_name = str(item.get("type") or "").strip()
        if type_name not in valid_types:
            continue
        summary = str(item.get("summary") or "").strip()
        if not summary:
            continue
        raw = f"{link.project_id}-{link.paper_identity.canonical_id}-{type_name}-{summary[:40]}"
        sid = hashlib.sha256(raw.encode()).hexdigest()[:12]
        try:
            confidence = max(0.0, min(1.0, float(item.get("confidence") or 0.0)))
        except (TypeError, ValueError):
            confidence = 0.0
        suggestions.append(ProjectImpactSuggestion(
            id=sid,
            project_id=link.project_id,
            paper_identity=link.paper_identity,
            type=ImpactSuggestionType(type_name),
            target_id=str(item.get("target_id") or ""),
            summary=summary,
            rationale=str(item.get("rationale") or ""),
            evidence_refs=[str(r) for r in (item.get("evidence_refs") or []) if str(r).strip()],
            confidence=round(confidence, 2),
            status="proposed",
            created_by_run=run_id,
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
