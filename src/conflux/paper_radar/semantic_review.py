"""P2 batch LLM semantic review (planned P2.8 stage).

After the embedding coarse rank, a bounded candidate pool is reviewed by the
LLM for project relevance, research value, and evidence quality.  Review
failures are recorded as needs_review (unreviewed semantics) and are never
auto-promoted; the deterministic coarse-rank score remains the fallback order
signal but the paper stays flagged as unreviewed.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

from conflux.core.p2_contracts import ProjectResearchContext

# Layered review thresholds (coarse-rank combined score):
# >= REVIEW_THRESHOLD_HIGH is accepted directly (no LLM call, avoids LLM
# down-weighting high-confidence candidates); < REVIEW_THRESHOLD_LOW is
# rejected directly; the fuzzy band in between is sent to the LLM.
REVIEW_THRESHOLD_HIGH = 0.35
REVIEW_THRESHOLD_LOW = 0.25


SEMANTIC_REVIEW_SYSTEM = (
    "You are a research reviewer.  Given one paper and a project research "
    "context, judge how the paper helps the project.  Output only valid JSON."
)

SEMANTIC_REVIEW_PROMPT = """Analyze the paper below against the project research context and return a JSON review.

## Project research context
- Overall goal: {overall_goal}
- Research questions:
{research_questions}
- Keywords: {keywords}

## Paper
- Title: {title}
- Abstract: {abstract}

## Output schema (JSON only)
{{
  "relevance": 0.0,
  "research_value": 0.0,
  "evidence_quality": 0.0,
  "reasoning": "one or two sentences",
  "confidence": 0.0,
  "needs_deeper_review": false,
  "evidence_utility": "method|dataset|baseline|metric|background|counterexample|competitor|none"
}}
- relevance: 0.0-1.0, how directly the paper addresses the project goal/questions.
- research_value: 0.0-1.0, value of the contribution to the project.
- evidence_quality: 0.0-1.0, whether the abstract supports the claimed contribution.
- confidence: 0.0-1.0, reviewer confidence in the judgment.
- needs_deeper_review: true only if the paper is likely relevant but the abstract is insufficient.
"""

SEMANTIC_REVIEW_FEW_SHOT_BLOCK = """
## Examples

### Example 1
Paper: "Extending RTLola with External Data Queries"
The paper extends stream-based runtime monitoring with external data queries and
includes a geospatial backend evaluation. It is not framed as a GIS-agent paper,
but the runtime-monitoring mechanism is directly reusable for agent step
verification and audit (RQ2).
{"relevance": 0.88, "research_value": 0.8, "evidence_quality": 0.7, "reasoning": "Runtime monitoring with external data queries is directly reusable for agent step verification and audit.", "confidence": 0.9, "needs_deeper_review": true, "evidence_utility": "method"}

### Example 2
Paper: "When History Lies: Evaluating and Improving Tool Use under Misleading Multi-Turn Histories"
The paper evaluates and improves tool-calling reliability when multi-turn history
becomes misleading, which directly supports agent verification under realistic
degraded states (RQ2).
{"relevance": 0.88, "research_value": 0.85, "evidence_quality": 0.7, "reasoning": "Tool-use reliability under misleading history directly supports agent verification.", "confidence": 0.9, "needs_deeper_review": false, "evidence_utility": "method"}
"""

SEMANTIC_REVIEW_LISTWISE_PROMPT = """Analyze the papers below against the project research context and return one JSON review per paper.

## Project research context
- Overall goal: {overall_goal}
- Research questions:
{research_questions}
- Keywords: {keywords}

## Papers
{papers_block}

## Output schema (JSON only)
{{
  "reviews": [
    {{
      "paper_id": "id from the paper block",
      "relevance": 0.0,
      "research_value": 0.0,
      "evidence_quality": 0.0,
      "reasoning": "one or two sentences",
      "confidence": 0.0,
      "needs_deeper_review": false,
      "evidence_utility": "method|dataset|baseline|metric|background|counterexample|competitor|none"
    }}
  ]
}}

- relevance: 0.0-1.0, how directly the paper addresses the project goal/questions.
- research_value: 0.0-1.0, value of the contribution to the project.
- evidence_quality: 0.0-1.0, whether the abstract supports the claimed contribution.
- confidence: 0.0-1.0, reviewer confidence in the judgment.
- needs_deeper_review: true only if the paper is likely relevant but the abstract is insufficient.
"""


@dataclass(slots=True)
class SemanticReview:
    paper_id: str
    relevance: float = 0.0
    research_value: float = 0.0
    evidence_quality: float = 0.0
    reasoning: str = ""
    confidence: float = 0.0
    needs_deeper_review: bool = False
    evidence_utility: str = "none"
    reviewed: bool = False
    telemetry: dict[str, Any] = field(default_factory=dict)


def _context_prompt_block(context: ProjectResearchContext, profile_keywords: list[str]) -> dict[str, str]:
    questions = "\n".join(
        f"- {item}" for item in getattr(context, "research_questions", None) or []
    ) or "-"
    return {
        "overall_goal": str(getattr(context, "overall_goal", None) or ""),
        "research_questions": questions,
        "keywords": ", ".join(str(item) for item in profile_keywords or []),
    }


def _parse_review_payload(content: str) -> dict[str, Any] | None:
    start = content.find("{")
    end = content.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        payload = json.loads(content[start:end + 1])
    except (ValueError, TypeError):
        return None
    return payload if isinstance(payload, dict) else None


def _parse_listwise_payload(content: str) -> list[dict[str, Any]]:
    payload = _parse_review_payload(content)
    if payload is None:
        return []
    reviews = payload.get("reviews")
    if isinstance(reviews, list):
        return [item for item in reviews if isinstance(item, dict)]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def _payload_to_review(paper_id: str, payload: dict[str, Any], telemetry: dict[str, Any]) -> SemanticReview:
    def bounded(value: Any, default: float = 0.0) -> float:
        try:
            return max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            return default

    return SemanticReview(
        paper_id=paper_id,
        relevance=bounded(payload.get("relevance")),
        research_value=bounded(payload.get("research_value")),
        evidence_quality=bounded(payload.get("evidence_quality")),
        reasoning=str(payload.get("reasoning") or "")[:500],
        confidence=bounded(payload.get("confidence")),
        needs_deeper_review=bool(payload.get("needs_deeper_review", False)),
        evidence_utility=str(payload.get("evidence_utility") or "none"),
        reviewed=True,
        telemetry=telemetry,
    )


def review_one_paper(
    paper_dict: dict[str, Any],
    context: ProjectResearchContext,
    llm_model: Any,
    *,
    profile_keywords: list[str] | None = None,
    few_shot: bool = False,
) -> SemanticReview:
    telemetry = {"calls": 1, "total_tokens": 0, "elapsed_ms": 0, "fell_back": False}
    started = time.monotonic()
    block = _context_prompt_block(context, profile_keywords or [])
    prompt = SEMANTIC_REVIEW_PROMPT.format(
        overall_goal=block["overall_goal"] or "(none)",
        research_questions=block["research_questions"],
        keywords=block["keywords"] or "(none)",
        title=str(paper_dict.get("title") or ""),
        abstract=str(paper_dict.get("abstract") or "（无摘要）"),
    )
    if few_shot:
        prompt += SEMANTIC_REVIEW_FEW_SHOT_BLOCK
    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        response = llm_model.invoke([
            SystemMessage(content=SEMANTIC_REVIEW_SYSTEM),
            HumanMessage(content=prompt),
        ])
        content = str(response.content) if hasattr(response, "content") else str(response)
        usage = getattr(response, "usage_metadata", None) or {}
        telemetry["total_tokens"] = int(usage.get("total_tokens") or 0)
    except Exception:
        telemetry["elapsed_ms"] = int((time.monotonic() - started) * 1000)
        telemetry["fell_back"] = True
        return SemanticReview(paper_id=str(paper_dict.get("id") or ""), telemetry=telemetry)

    telemetry["elapsed_ms"] = int((time.monotonic() - started) * 1000)
    payload = _parse_review_payload(content)
    if payload is None:
        telemetry["fell_back"] = True
        return SemanticReview(paper_id=str(paper_dict.get("id") or ""), telemetry=telemetry)
    return _payload_to_review(str(paper_dict.get("id") or ""), payload, telemetry)


def batch_semantic_review(
    papers: list[dict[str, Any]],
    context: ProjectResearchContext,
    llm_model: Any,
    *,
    max_papers: int,
    profile_keywords: list[str] | None = None,
    stats: Any = None,
    mode: str = "pointwise",
    few_shot: bool = False,
    chunk_size: int = 8,
) -> dict[str, SemanticReview]:
    """Review up to max_papers papers; record telemetry on stats.

    ``mode="pointwise"`` keeps the original one-call-per-paper behavior.
    ``mode="listwise"`` batches papers into chunks and asks for one JSON array
    per chunk, reducing repeated project-context tokens.
    """
    reviews: dict[str, SemanticReview] = {}
    selected = list(papers[:max_papers])
    if mode == "listwise":
        for start in range(0, len(selected), chunk_size):
            chunk = selected[start:start + chunk_size]
            batch_reviews, telemetry = review_batch_listwise(
                chunk,
                context,
                llm_model,
                profile_keywords=profile_keywords,
                few_shot=few_shot,
            )
            reviewed_ids = set()
            for review in batch_reviews:
                reviews[str(review.paper_id)] = review
                reviewed_ids.add(str(review.paper_id))
            for paper in chunk:
                paper_id = str(paper.get("id") or "")
                if paper_id not in reviewed_ids:
                    reviews[paper_id] = SemanticReview(
                        paper_id=paper_id, telemetry=telemetry
                    )
            if stats is not None:
                stats.semantic_review_calls += telemetry.get("calls", 0)
                stats.semantic_review_tokens += telemetry.get("total_tokens", 0)
                stats.semantic_review_elapsed_ms += telemetry.get("elapsed_ms", 0)
                if telemetry.get("fell_back"):
                    stats.semantic_review_failed += 1
        return reviews

    for paper in selected:
        review = review_one_paper(
            paper,
            context,
            llm_model,
            profile_keywords=profile_keywords,
            few_shot=few_shot,
        )
        reviews[str(paper.get("id") or "")] = review
        if stats is not None:
            stats.semantic_review_calls += review.telemetry.get("calls", 0)
            stats.semantic_review_tokens += review.telemetry.get("total_tokens", 0)
            stats.semantic_review_elapsed_ms += review.telemetry.get("elapsed_ms", 0)
            if review.telemetry.get("fell_back") or not review.reviewed:
                stats.semantic_review_failed += 1
    return reviews


def review_batch_listwise(
    papers: list[dict[str, Any]],
    context: ProjectResearchContext,
    llm_model: Any,
    *,
    profile_keywords: list[str] | None = None,
    few_shot: bool = False,
) -> tuple[list[SemanticReview], dict[str, Any]]:
    """Review a batch of papers in one LLM call and return reviews + telemetry."""
    telemetry = {"calls": 1, "total_tokens": 0, "elapsed_ms": 0, "fell_back": False}
    if not papers:
        return [], telemetry
    started = time.monotonic()
    block = _context_prompt_block(context, profile_keywords or [])
    papers_block = "\n\n".join(
        f"[{index}] id={paper.get('id') or ''}\n"
        f"Title: {paper.get('title') or ''}\n"
        f"Abstract: {paper.get('abstract') or '（无摘要）'}"
        for index, paper in enumerate(papers, 1)
    )
    prompt = SEMANTIC_REVIEW_LISTWISE_PROMPT.format(
        overall_goal=block["overall_goal"] or "(none)",
        research_questions=block["research_questions"],
        keywords=block["keywords"] or "(none)",
        papers_block=papers_block,
    )
    if few_shot:
        prompt += SEMANTIC_REVIEW_FEW_SHOT_BLOCK
    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        response = llm_model.invoke([
            SystemMessage(content=SEMANTIC_REVIEW_SYSTEM),
            HumanMessage(content=prompt),
        ])
        content = str(response.content) if hasattr(response, "content") else str(response)
        usage = getattr(response, "usage_metadata", None) or {}
        telemetry["total_tokens"] = int(usage.get("total_tokens") or 0)
    except Exception:
        telemetry["elapsed_ms"] = int((time.monotonic() - started) * 1000)
        telemetry["fell_back"] = True
        return [], telemetry

    telemetry["elapsed_ms"] = int((time.monotonic() - started) * 1000)
    payloads = _parse_listwise_payload(content)
    if not payloads:
        telemetry["fell_back"] = True
        return [], telemetry
    by_id = {str(item.get("paper_id") or ""): item for item in payloads}
    reviews = []
    for paper in papers:
        paper_id = str(paper.get("id") or "")
        payload = by_id.get(paper_id)
        if payload is None:
            telemetry["fell_back"] = True
            reviews.append(SemanticReview(paper_id=paper_id, telemetry=telemetry))
            continue
        reviews.append(_payload_to_review(paper_id, payload, telemetry))
    return reviews, telemetry
