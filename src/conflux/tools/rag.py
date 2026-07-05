"""RAG retrieval tool wrapped as a LangChain tool for source agents."""

from __future__ import annotations

import re

from langchain_core.tools import tool

from ..query_planner import entity_score, extract_entities, important_terms, overlap_score, plan_queries
from ..rag.retriever import HybridRetriever
from ..source_status import AgentClaim, SourceResult


def create_rag_tool(retriever: HybridRetriever):
    """Create a RAG search tool bound to a specific retriever."""

    @tool
    def search_rag(query: str) -> str:
        """Search the local knowledge base and return chunk-level evidence."""

        plan = plan_queries(query, target="rag")
        try:
            docs = _search_with_plan(retriever, plan.subqueries)
        except Exception as exc:
            return SourceResult(
                source="RAG",
                status="failed",
                detail="Local Chroma hybrid retrieval",
                error=f"{type(exc).__name__}: {exc}",
                content="Local knowledge-base retrieval failed.",
            ).to_tool_text()

        if not docs:
            return SourceResult(
                source="RAG",
                status="no_evidence",
                detail="Local Chroma hybrid retrieval",
                error="No local knowledge-base chunks were found for the planned queries.",
                content="No relevant local knowledge-base chunks were found.",
                metadata={"query_plan": plan.to_dict(), "result_count": 0},
            ).to_tool_text()

        scored_docs = _score_docs(query, docs)
        kept_docs = [item for item in scored_docs if item["score"] >= 0.25]
        top_score = scored_docs[0]["score"] if scored_docs else 0.0
        sources = sorted({str(doc.metadata.get("source", "unknown")) for doc in docs})

        if not kept_docs:
            return SourceResult(
                source="RAG",
                status="no_evidence",
                detail="Local Chroma hybrid retrieval",
                error="Retrieved chunks did not meet the minimum relevance score.",
                content=(
                    "Local retrieval returned chunks, but they were judged off-topic "
                    "and must not be used as RAG evidence.\n"
                    f"Matched documents: {', '.join(sources)}"
                ),
                metadata={
                    "query_plan": plan.to_dict(),
                    "result_count": len(docs),
                    "kept_count": 0,
                    "dropped_count": len(docs),
                    "top_relevance_score": top_score,
                    "matched_sources": sources,
                    "score_breakdown": _score_breakdown_for_metadata(scored_docs),
                },
            ).to_tool_text()

        status = "success" if top_score >= 0.55 else "low_relevance"
        confidence = 0.78 if status == "success" else 0.5
        limitation = "local retrieval hit; verify freshness for time-sensitive claims"
        if status == "low_relevance":
            limitation = "weak local retrieval match; use as contextual evidence only"

        parts: list[str] = []
        claims: list[AgentClaim] = []
        citations: list[dict] = []
        for i, scored in enumerate(kept_docs):
            doc = scored["doc"]
            source = str(doc.metadata.get("source", "unknown"))
            chunk_id = str(doc.metadata.get("chunk_id", ""))
            parent_id = str(doc.metadata.get("parent_id", ""))
            char_start = doc.metadata.get("char_start")
            char_end = doc.metadata.get("char_end")
            evidence_ref = _rag_evidence_ref(source, chunk_id)
            text = doc.page_content.strip()

            citations.append({
                "ref": evidence_ref,
                "source": source,
                "chunk_id": chunk_id,
                "parent_id": parent_id,
                "char_start": char_start,
                "char_end": char_end,
                "text": text[:500],
                "relevance_score": scored["score"],
                "score_breakdown": scored["breakdown"],
            })
            parts.append(
                f"[Source {i + 1}] {evidence_ref} {source} ({chunk_id}) "
                f"relevance={scored['score']:.2f}\n{text}\n"
            )

            claim_text = _claim_from_chunk(text)
            if claim_text:
                claims.append(AgentClaim(
                    claim=claim_text,
                    source="RAG",
                    evidence_refs=[evidence_ref],
                    confidence=confidence,
                    limitations=[limitation],
                ))

        return SourceResult(
            source="RAG",
            status=status,
            detail="Local Chroma hybrid retrieval",
            content="\n".join(parts),
            claims=claims,
            metadata={
                "query_plan": plan.to_dict(),
                "result_count": len(docs),
                "kept_count": len(kept_docs),
                "dropped_count": len(docs) - len(kept_docs),
                "top_relevance_score": top_score,
                "matched_sources": sorted({str(item["doc"].metadata.get("source", "unknown")) for item in kept_docs}),
                "citations": citations,
                "score_breakdown": _score_breakdown_for_metadata(scored_docs),
            },
        ).to_tool_text()

    return search_rag


def _search_with_plan(retriever: HybridRetriever, subqueries: list[str]):
    docs = []
    seen = set()
    for subquery in subqueries:
        for doc in retriever.search(subquery):
            key = str(doc.metadata.get("chunk_id") or doc.metadata.get("source") or doc.page_content[:120])
            if key in seen:
                continue
            seen.add(key)
            metadata = dict(doc.metadata or {})
            metadata.setdefault("matched_query", subquery)
            doc.metadata = metadata
            docs.append(doc)
    return docs


def _rag_evidence_ref(source: str, chunk_id: str) -> str:
    if chunk_id:
        if "#p" in chunk_id:
            source_part, rest = chunk_id.split("#p", 1)
            normalized = f"{source_part}#chunk-p{rest.replace('#c', '-c')}"
        else:
            normalized = chunk_id.replace("#c", "-c")
        return f"[RAG:{normalized}]"
    return f"[RAG:{source}#chunk-unknown]"


def _claim_from_chunk(text: str, max_length: int = 220) -> str:
    for raw in re.split(r"[\n。.!?]+", text):
        cleaned = re.sub(r"\s+", " ", raw).strip(" -\t")
        if len(cleaned) >= 12:
            return cleaned[:max_length]
    cleaned = re.sub(r"\s+", " ", text).strip()
    return cleaned[:max_length]


def _score_docs(query: str, docs) -> list[dict]:
    query_terms = important_terms(query)
    query_entities = extract_entities(query)
    scored = []
    for doc in docs:
        text = doc.page_content or ""
        source = str(doc.metadata.get("source", ""))
        metadata_text = " ".join(
            str(value)
            for key, value in doc.metadata.items()
            if key not in {"matched_query", "query", "subquery"}
        )
        full_text = f"{source}\n{metadata_text}\n{text}"
        lexical = overlap_score(query_terms, full_text)
        entity = entity_score(query_entities, full_text)
        topic = _topic_score(query_terms, query_entities, source)
        dense_hint = _dense_hint(doc)
        final = (0.35 * dense_hint) + (0.30 * lexical) + (0.20 * entity) + (0.15 * topic)
        if entity > 0 and lexical > 0:
            final += 0.08
        scored.append({
            "doc": doc,
            "score": round(min(1.0, final), 3),
            "breakdown": {
                "dense_hint": round(dense_hint, 3),
                "lexical_overlap": round(lexical, 3),
                "entity_match": round(entity, 3),
                "topic_match": round(topic, 3),
            },
        })
    return sorted(scored, key=lambda item: item["score"], reverse=True)


def _topic_score(query_terms: set[str], query_entities: set[str], source: str) -> float:
    source_terms = important_terms(source)
    source_entities = extract_entities(source)
    lexical = len(query_terms & source_terms) / len(query_terms) if query_terms else 0.0
    entity = len(query_entities & source_entities) / len(query_entities) if query_entities else 0.0
    return max(lexical, entity)


def _dense_hint(doc) -> float:
    metadata = doc.metadata or {}
    for key in ("relevance_score", "score", "dense_score", "bm25_score", "rrf_score"):
        raw = metadata.get(key)
        if raw is None:
            continue
        try:
            value = float(raw)
        except (TypeError, ValueError):
            continue
        if key == "score" and value > 1:
            value = 1 / (1 + value)
        return max(0.0, min(1.0, value))
    return 0.5


def _score_breakdown_for_metadata(scored_docs: list[dict]) -> list[dict]:
    payload = []
    for item in scored_docs[:10]:
        doc = item["doc"]
        payload.append({
            "source": str(doc.metadata.get("source", "unknown")),
            "chunk_id": str(doc.metadata.get("chunk_id", "")),
            "score": item["score"],
            "breakdown": item["breakdown"],
        })
    return payload
