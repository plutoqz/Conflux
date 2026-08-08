"""P2 embedding coarse-rank for paper radar candidates.

Implements the planned "deterministic negative gate + identity dedup ->
Embedding coarse rank -> batch LLM semantic review" stage.  Dense cosine
similarity against the project research context is combined with the lexical
profile score.  There is NO silent fallback: callers must supply an embedding
model, and embedding failures propagate so the caller can decide how to
report them.
"""

from __future__ import annotations

import hashlib
import math
from typing import Any, Callable

from conflux.paper_ingestion.models import PaperRecord
from conflux.paper_ingestion.scorer import score_paper
from conflux.research_profile.models import ResearchProfile


DENSE_WEIGHT = 0.7
LEXICAL_WEIGHT = 0.3


def _paper_text(paper: PaperRecord) -> str:
    parts = [paper.title or "", paper.abstract or ""]
    return "\n".join(part for part in parts if part.strip())


def _context_query_text(profile: ResearchProfile, context: Any) -> str:
    lines: list[str] = []
    goal = getattr(context, "overall_goal", None) or ""
    if goal:
        lines.append(str(goal))
    for question in getattr(context, "research_questions", None) or []:
        lines.append(str(question))
    for keyword in getattr(profile, "keywords", None) or []:
        lines.append(str(keyword))
    return "\n".join(lines)


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return round(dot / (norm_a * norm_b), 4)


def _embed_key(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def embedding_coarse_rank(
    papers: list[PaperRecord],
    profile: ResearchProfile,
    context: Any,
    *,
    embedding_model: Any,
    cache: dict[str, list[float]] | None = None,
) -> list[tuple[PaperRecord, float, dict[str, float]]]:
    """Rank papers by 0.7*dense + 0.3*lexical, descending.

    Returns a list of (paper, combined_score, detail) where detail carries
    the dense similarity and lexical score for auditability.
    """
    cache = {} if cache is None else cache
    query_text = _context_query_text(profile, context)
    query_key = _embed_key(query_text)
    if query_key not in cache:
        cache[query_key] = embedding_model.embed_query(query_text)
    query_vector = cache[query_key]

    texts = [_paper_text(paper) for paper in papers]
    text_keys = [_embed_key(text) for text in texts]
    missing = [
        (index, text)
        for index, text in enumerate(texts)
        if text_keys[index] not in cache
    ]
    if missing:
        vectors = embedding_model.embed_documents([text for _, text in missing])
        for (index, _), vector in zip(missing, vectors):
            cache[text_keys[index]] = vector

    ranked: list[tuple[PaperRecord, float, dict[str, float]]] = []
    for paper, text_key in zip(papers, text_keys):
        vector = cache[text_key]
        dense = _cosine(query_vector, vector)
        lexical = score_paper(paper, profile).score
        combined = round(DENSE_WEIGHT * dense + LEXICAL_WEIGHT * lexical, 4)
        ranked.append((paper, combined, {"dense": dense, "lexical": lexical}))

    ranked.sort(key=lambda item: item[1], reverse=True)
    return ranked
