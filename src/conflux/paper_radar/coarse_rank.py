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
# P2.6 down-sampling signals: citation and venue boosts lift milestone/classic
# papers in the coarse rank without LLM cost, so the bounded review pool can
# include high-impact papers outside the recent window.
CITATION_BOOST_WEIGHT = 0.25
VENUE_BOOST_WEIGHT = 0.15


def _citation_boost(paper: PaperRecord) -> float:
    """Bucketed citation-count boost: 0/1-10/11-50/51-200/200+ -> 0/0.1/0.2/0.35/0.5."""
    meta = paper.metadata or {}
    try:
        count = int(meta.get("citation_count") or 0)
    except (TypeError, ValueError):
        return 0.0
    if count <= 0:
        return 0.0
    if count <= 10:
        return 0.1
    if count <= 50:
        return 0.2
    if count <= 200:
        return 0.35
    return 0.5


def _venue_boost(paper: PaperRecord, profile: ResearchProfile) -> float:
    venue = str(paper.venue or "").strip().casefold()
    if not venue:
        return 0.0
    targets = {str(item).casefold() for item in (profile.target_venues or []) if str(item).strip()}
    return 0.15 if venue in targets else 0.0


def _paper_text(paper: PaperRecord) -> str:
    parts = [paper.title or "", paper.abstract or ""]
    return "\n".join(part for part in parts if part.strip())


def _context_query_texts(profile: ResearchProfile, context: Any) -> list[str]:
    """Multiple focused query vectors: goal, each RQ, and keyword block.

    A single combined query vector dilutes topical focus; per-aspect queries
    let a candidate match the aspect it is actually closest to.
    """
    texts: list[str] = []
    goal = getattr(context, "overall_goal", None) or ""
    if str(goal).strip():
        texts.append(str(goal).strip())
    for question in getattr(context, "research_questions", None) or []:
        if str(question).strip():
            texts.append(str(question).strip())
    keywords = [str(item) for item in getattr(profile, "keywords", None) or [] if str(item).strip()]
    if keywords:
        texts.append(" ".join(keywords))
    return texts


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
    query_texts = _context_query_texts(profile, context)
    query_vectors: list[list[float]] = []
    for query_text in query_texts:
        query_key = _embed_key(query_text)
        if query_key not in cache:
            cache[query_key] = embedding_model.embed_query(query_text)
        query_vectors.append(cache[query_key])

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
        dense = max(
            (_cosine(query_vector, vector) for query_vector in query_vectors),
            default=0.0,
        )
        lexical = score_paper(paper, profile).score
        citation_boost = _citation_boost(paper)
        venue_boost = _venue_boost(paper, profile)
        combined = round(
            DENSE_WEIGHT * dense
            + LEXICAL_WEIGHT * lexical
            + CITATION_BOOST_WEIGHT * citation_boost
            + VENUE_BOOST_WEIGHT * venue_boost,
            4,
        )
        ranked.append((paper, combined, {
            "dense": dense,
            "lexical": lexical,
            "citation_boost": citation_boost,
            "venue_boost": venue_boost,
        }))

    ranked.sort(key=lambda item: item[1], reverse=True)
    return ranked
