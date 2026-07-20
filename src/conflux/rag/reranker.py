"""Semantic candidate reranking for P1 RAG retrieval."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage


@dataclass(frozen=True, slots=True)
class RerankDecision:
    candidate_id: str
    relevance: float
    directness: float
    reason: str


class SemanticReranker:
    """Use a chat model to judge query-to-passage relevance and directness."""

    def __init__(self, model: Any, *, batch_size: int = 16) -> None:
        self.model = model
        self.batch_size = max(1, batch_size)

    def rerank(self, query: str, scored_docs: list[dict], *, limit: int | None = None) -> list[dict]:
        if not scored_docs:
            return []
        decisions: dict[str, RerankDecision] = {}
        candidates = scored_docs[:limit] if limit else scored_docs
        try:
            for start in range(0, len(candidates), self.batch_size):
                batch = candidates[start : start + self.batch_size]
                decisions.update(self._rerank_batch(query, batch, offset=start))
        except Exception as exc:
            return [
                {
                    **item,
                    "semantic_score": None,
                    "semantic_directness": None,
                    "semantic_reason": f"unreviewed: {type(exc).__name__}: {exc}",
                    "rerank_status": "unreviewed",
                }
                for item in candidates
            ]

        reranked = []
        for index, item in enumerate(candidates):
            candidate_id = _candidate_id(item, index)
            decision = decisions.get(candidate_id)
            if decision is None:
                reranked.append({
                    **item,
                    "semantic_score": None,
                    "semantic_directness": None,
                    "semantic_reason": "unreviewed: model omitted this candidate",
                    "rerank_status": "unreviewed",
                })
                continue
            reranked.append({
                **item,
                "semantic_score": decision.relevance,
                "semantic_directness": decision.directness,
                "semantic_reason": decision.reason,
                "rerank_status": "reviewed",
            })
        return sorted(
            reranked,
            key=lambda item: (
                item.get("semantic_score") is not None,
                float(item.get("semantic_score") or 0.0),
                float(item.get("semantic_directness") or 0.0),
                float(item.get("score") or 0.0),
            ),
            reverse=True,
        )

    def _rerank_batch(self, query: str, batch: list[dict], *, offset: int) -> dict[str, RerankDecision]:
        payload = []
        for local_index, item in enumerate(batch):
            candidate_id = _candidate_id(item, offset + local_index)
            doc = item["doc"]
            payload.append({
                "id": candidate_id,
                "source": str(doc.metadata.get("source") or ""),
                "paper_section": str(doc.metadata.get("paper_section") or ""),
                "page_start": doc.metadata.get("page_start"),
                "retrieval_score": item.get("score"),
                "text": str(doc.page_content or "")[:1800],
            })
        prompt = f"""Judge how well each candidate directly answers the research query.
Return only a JSON array. Each item must contain:
- id: the provided candidate id
- relevance: number from 0 to 1
- directness: number from 0 to 1
- reason: one concise sentence

Do not reward filename overlap, repeated terminology, or generic background.
Passages that directly state limitations, results, evidence, or conditions relevant
to the query should outrank merely topical passages.

Query: {query}

Candidates:
{json.dumps(payload, ensure_ascii=False)}"""
        response = self.model.invoke([
            SystemMessage(content="You are a strict semantic passage reranker. Output valid JSON only."),
            HumanMessage(content=prompt),
        ])
        parsed = _parse_json_array(str(response.content if hasattr(response, "content") else response))
        decisions = {}
        for item in parsed:
            if not isinstance(item, dict):
                continue
            candidate_id = str(item.get("id") or "")
            if not candidate_id:
                continue
            decisions[candidate_id] = RerankDecision(
                candidate_id=candidate_id,
                relevance=_bounded_float(item.get("relevance")),
                directness=_bounded_float(item.get("directness")),
                reason=str(item.get("reason") or "semantic review"),
            )
        return decisions


def _candidate_id(item: dict, index: int) -> str:
    doc = item["doc"]
    return str(doc.metadata.get("chunk_id") or f"candidate-{index + 1}")


def _parse_json_array(text: str) -> list:
    """Parse model output without treating formatting noise as a review pass.

    Providers may wrap valid JSON in markdown fences, a short preamble, hidden
    reasoning tags, or an object such as ``{"items": [...]}``.  We accept only
    payloads that decode into candidate dictionaries; malformed/empty output
    still raises so the caller records the batch as ``unreviewed``.
    """

    cleaned = _strip_hidden_blocks(str(text or "")).strip()
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE | re.DOTALL).strip()

    # First look for complete JSONL objects. This is intentionally done before
    # the generic scan below so a multi-line JSONL response is not mistaken for
    # a single object.
    objects = []
    for line in cleaned.splitlines():
        line = line.strip().strip(",")
        if not line.startswith("{"):
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            objects.append(value)
    if len(objects) > 1:
        return objects

    decoder = json.JSONDecoder()
    array_context = cleaned.lstrip().startswith("[")
    # Prefer a complete JSON array/object anywhere in the response.  Using
    # raw_decode avoids rfind() being confused by brackets inside prose.
    for index, char in enumerate(cleaned):
        if char not in "[{":
            continue
        try:
            value, _ = decoder.raw_decode(cleaned[index:])
        except json.JSONDecodeError:
            continue
        candidates = _candidate_list(value)
        if candidates and not (array_context and isinstance(value, dict)):
            return candidates
    if objects:
        return objects

    # Providers can hit the output-token cap halfway through an enclosing
    # array. Salvage only individually complete candidate objects; incomplete
    # candidates remain unreviewed in SemanticReranker.rerank(). This preserves
    # the truthfulness of the review status while retaining useful judgments.
    partial_candidates: list[dict] = []
    seen_ids: set[str] = set()
    for index, char in enumerate(cleaned):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(cleaned[index:])
        except json.JSONDecodeError:
            continue
        if not isinstance(value, dict) or not {"id", "relevance", "directness"}.issubset(value):
            continue
        candidate_id = str(value.get("id") or "")
        if candidate_id and candidate_id not in seen_ids:
            seen_ids.add(candidate_id)
            partial_candidates.append(value)
    if partial_candidates:
        return partial_candidates
    raise ValueError("reranker response did not contain a JSON array")


def _candidate_list(value: Any) -> list:
    if isinstance(value, list):
        items = value
    elif isinstance(value, dict):
        items = None
        for key in ("items", "results", "candidates", "data", "reviews"):
            if isinstance(value.get(key), list):
                items = value[key]
                break
        if items is None and {"id", "relevance", "directness"}.issubset(value):
            items = [value]
        if items is None:
            return []
    else:
        return []
    return [item for item in items if isinstance(item, dict)]


def _strip_hidden_blocks(text: str) -> str:
    cleaned = str(text or "")
    for tag in ("think", "analysis", "reasoning"):
        cleaned = re.sub(
            rf"<\s*{tag}\s*>.*?<\s*/\s*{tag}\s*>",
            "",
            cleaned,
            flags=re.IGNORECASE | re.DOTALL,
        )
    return cleaned.strip()


def _bounded_float(value: Any) -> float:
    try:
        return round(max(0.0, min(1.0, float(value))), 3)
    except (TypeError, ValueError):
        return 0.0
