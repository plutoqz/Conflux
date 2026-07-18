"""RAG retrieval tool wrapped as a LangChain tool for source agents."""

from __future__ import annotations

import re

from langchain_core.tools import tool

from ..config import get
from ..query_planner import (
    QueryRewriteProvider,
    entity_score,
    extract_entities,
    important_terms,
    overlap_score,
    plan_queries,
    rewrite_queries,
)
from ..rag.retriever import HybridRetriever
from ..source_status import AgentClaim, SourceResult


def create_rag_tool(retriever: HybridRetriever, query_rewriter: QueryRewriteProvider | None = None):
    """Create a RAG search tool bound to a specific retriever."""

    @tool
    def search_rag(query: str) -> str:
        """Search the local knowledge base and return chunk-level evidence."""

        plan = plan_queries(query, target="rag")
        rewrite_provider = query_rewriter or QueryRewriteProvider()
        model_rewrites = rewrite_provider.rewrite(query, target="rag")
        retrieval_queries = list(plan.subqueries)
        existing_queries = {item.casefold() for item in retrieval_queries}
        for variant in model_rewrites:
            if variant.casefold() not in existing_queries:
                retrieval_queries.append(variant)
                existing_queries.add(variant.casefold())
        retry_queries: list[str] = []
        try:
            docs = _search_with_plan(retriever, retrieval_queries)
            for attempt in range(1, int(get("research", "max_rewrite_attempts", default=1)) + 1):
                scored_attempt = _score_docs(query, docs, query_variants=model_rewrites)
                top_attempt = scored_attempt[0]["score"] if scored_attempt else 0.0
                if top_attempt >= 0.55:
                    break
                rewritten = rewrite_queries(query, target="rag", attempt=attempt)
                retry_queries.extend(rewritten)
                docs = _merge_documents(docs, _search_with_plan(retriever, rewritten))
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
                metadata={
                    "query_plan": plan.to_dict(),
                    "query_rewrites": model_rewrites,
                    "result_count": 0,
                },
            ).to_tool_text()

        scored_docs = _limit_per_paper(_score_docs(query, docs, query_variants=model_rewrites), limit=2)
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
                    "query_rewrites": model_rewrites,
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
            paper_id = _paper_id(doc.metadata, source)
            paper_section = _paper_section(doc.metadata, text)
            evidence_class = _rag_evidence_class(doc.metadata, source)

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
                "paper_id": paper_id,
                "paper_section": paper_section,
                "evidence_class": evidence_class,
            })
            parts.append(
                f"[Source {i + 1}] {evidence_ref} {source} ({chunk_id}) "
                f"relevance={scored['score']:.2f}\n{text}\n"
            )

            claim_text = _claim_from_chunk(text, preferred_section=paper_section)
            if claim_text:
                claims.append(AgentClaim(
                    claim=claim_text,
                    source="RAG",
                    verbatim_quote=claim_text,
                    paper_id=paper_id,
                    paper_section=paper_section,
                    relevance=scored["score"],
                    research_type=str(doc.metadata.get("research_type") or doc.metadata.get("document_type") or ""),
                    metric=_extract_metric(claim_text),
                    evidence_refs=[evidence_ref],
                    confidence=confidence,
                    limitations=[limitation],
                    evidence_class=evidence_class,
                ))

        return SourceResult(
            source="RAG",
            status=status,
            detail="Local Chroma hybrid retrieval",
            content="\n".join(parts),
            evidence_class=_strongest_evidence_class(claims),
            claims=claims,
            metadata={
                "query_plan": plan.to_dict(),
                "query_rewrites": model_rewrites,
                "retry_queries": retry_queries,
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
    positions: dict[str, int] = {}
    for subquery in subqueries:
        for doc in retriever.search(subquery):
            key = str(doc.metadata.get("chunk_id") or doc.metadata.get("source") or doc.page_content[:120])
            metadata = dict(doc.metadata or {})
            metadata.setdefault("matched_query", subquery)
            doc.metadata = metadata
            if key in positions:
                current_index = positions[key]
                current = docs[current_index]
                current_score = float((current.metadata or {}).get("query_dense_score") or 0.0)
                new_score = float(metadata.get("query_dense_score") or 0.0)
                matched = str((current.metadata or {}).get("matched_query") or "")
                if subquery not in matched and new_score <= current_score:
                    current.metadata["matched_query"] = f"{matched}; {subquery}".strip("; ")
                    continue
                if new_score <= current_score:
                    continue
                metadata["matched_query"] = f"{matched}; {subquery}".strip("; ")
                docs[current_index] = doc
                continue
            positions[key] = len(docs)
            docs.append(doc)
    return docs


def _merge_documents(existing, additional):
    merged = []
    positions: dict[str, int] = {}
    for doc in [*existing, *additional]:
        key = str(doc.metadata.get("chunk_id") or doc.metadata.get("source") or doc.page_content[:120])
        if key in positions:
            index = positions[key]
            current = merged[index]
            current_score = float((current.metadata or {}).get("query_dense_score") or 0.0)
            new_score = float((doc.metadata or {}).get("query_dense_score") or 0.0)
            if new_score > current_score:
                merged[index] = doc
            continue
        positions[key] = len(merged)
        merged.append(doc)
    return merged


def _limit_per_paper(scored_docs: list[dict], limit: int) -> list[dict]:
    kept = []
    counts: dict[str, int] = {}
    for item in scored_docs:
        doc = item["doc"]
        identity = _paper_id(doc.metadata, str(doc.metadata.get("source", "unknown"))).casefold()
        if counts.get(identity, 0) >= limit:
            continue
        counts[identity] = counts.get(identity, 0) + 1
        kept.append(item)
    return kept


def _rag_evidence_ref(source: str, chunk_id: str) -> str:
    if chunk_id:
        if "#p" in chunk_id:
            source_part, rest = chunk_id.split("#p", 1)
            normalized = f"{source_part}#chunk-p{rest.replace('#c', '-c')}"
        else:
            normalized = chunk_id.replace("#c", "-c")
        return f"[RAG:{normalized}]"
    return f"[RAG:{source}#chunk-unknown]"


def _claim_from_chunk(text: str, max_length: int = 220, preferred_section: str = "") -> str:
    """Extract a factual sentence, skipping titles and prioritising paper sections."""

    section = preferred_section.casefold()
    candidates: list[tuple[int, str]] = []
    current_section = section
    priorities = {"results": 5, "result": 5, "limitations": 4, "limitation": 4, "method": 3, "methods": 3, "abstract": 2}
    for line_number, raw_line in enumerate(text.splitlines()):
        line = raw_line.strip()
        heading = re.match(r"^#{1,6}\s+(.+)$", line)
        if heading:
            current_section = heading.group(1).strip().casefold()
            continue
        if not line or _looks_like_title(line, line_number):
            continue
        for raw in re.split(r"(?<=[。.!?])\s*", line):
            cleaned = re.sub(r"\s+", " ", raw).strip(" -*\t")
            if len(cleaned) < 20 or _looks_like_title(cleaned, line_number):
                continue
            priority = max(
                (score for name, score in priorities.items() if name in current_section),
                default=1,
            )
            if re.search(r"\b(result|found|show|demonstrat|improv|reduc|increase|decrease)\w*\b|结果|表明|发现|提升|降低", cleaned, re.IGNORECASE):
                priority += 2
            candidates.append((priority, cleaned[:max_length]))
    if candidates:
        candidates.sort(key=lambda item: item[0], reverse=True)
        return candidates[0][1]
    return ""


def _looks_like_title(text: str, line_number: int) -> bool:
    stripped = text.strip()
    if stripped.startswith("#"):
        return True
    if line_number == 0 and not re.search(r"[。.!?]$", stripped):
        return True
    words = re.findall(r"[A-Za-z]+", stripped)
    return bool(words) and len(words) <= 18 and sum(word[:1].isupper() for word in words) / len(words) > 0.75


def _paper_id(metadata: dict, source: str) -> str:
    return str(
        metadata.get("paper_id")
        or metadata.get("doi")
        or metadata.get("arxiv_id")
        or metadata.get("document_id")
        or source
    ).strip()


def _paper_section(metadata: dict, text: str) -> str:
    explicit = str(metadata.get("paper_section") or metadata.get("section") or "").strip()
    if explicit:
        return explicit.casefold()
    match = re.search(r"^#{1,6}\s+(abstract|methods?|results?|limitations?)\b", text, re.IGNORECASE | re.MULTILINE)
    return match.group(1).casefold() if match else "unknown"


def _rag_evidence_class(metadata: dict, source: str) -> str:
    declared = str(metadata.get("evidence_class") or metadata.get("publication_type") or "").casefold()
    if declared in {"peer_reviewed", "journal", "conference", "proceedings"} or metadata.get("peer_reviewed") is True:
        return "peer_reviewed"
    if declared in {"preprint", "arxiv"} or "arxiv" in source.casefold():
        return "preprint"
    return "authoritative_document"


def _strongest_evidence_class(claims: list[AgentClaim]) -> str:
    rank = {"peer_reviewed": 5, "authoritative_document": 4, "preprint": 3, "community_content": 2, "model_inference": 1}
    if not claims:
        return "authoritative_document"
    return max((claim.evidence_class for claim in claims), key=lambda value: rank.get(value, 0))


def _extract_metric(text: str) -> str:
    match = re.search(r"\b\d+(?:\.\d+)?\s*(?:%|m|cm|mm|km|s|ms|hours?|days?)\b", text, re.IGNORECASE)
    return match.group(0) if match else ""


def _score_docs(query: str, docs, *, query_variants: list[str] | None = None) -> list[dict]:
    bilingual = query_variants if query_variants is not None else QueryRewriteProvider().rewrite(query, target="rag")
    scoring_query = " ".join([query, *bilingual])
    query_terms = important_terms(scoring_query)
    query_entities = extract_entities(scoring_query)
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
        cross_language = _is_cross_language_query(query, text)
        if dense_hint is None:
            # Do not invent a dense score for retriever fakes or legacy docs.
            dense_weight, lexical_weight, entity_weight, topic_weight = (0.0, 0.55, 0.25, 0.20)
        elif cross_language:
            dense_weight, lexical_weight, entity_weight, topic_weight = (0.72, 0.13, 0.05, 0.10)
        else:
            dense_weight, lexical_weight, entity_weight, topic_weight = (0.35, 0.30, 0.20, 0.15)
        dense_value = dense_hint if dense_hint is not None else 0.0
        final = (
            dense_weight * dense_value
            + lexical_weight * lexical
            + entity_weight * entity
            + topic_weight * topic
        )
        if entity > 0 and lexical > 0:
            final += 0.08
        scored.append({
            "doc": doc,
            "score": round(min(1.0, final), 3),
            "breakdown": {
                "dense_hint": round(dense_hint, 3) if dense_hint is not None else None,
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


def _dense_hint(doc) -> float | None:
    metadata = doc.metadata or {}
    # Only scores produced for the current vector query are valid here.
    for key in ("query_dense_score", "dense_score"):
        raw = metadata.get(key)
        if raw is None:
            continue
        try:
            value = float(raw)
        except (TypeError, ValueError):
            continue
        return max(0.0, min(1.0, value))
    return None


def _is_cross_language_query(query: str, text: str) -> bool:
    return bool(
        re.search(r"[\u4e00-\u9fff]", str(query or ""))
        and re.search(r"[A-Za-z]", str(text or ""))
        and not re.search(r"[\u4e00-\u9fff]", str(text or ""))
    )


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
