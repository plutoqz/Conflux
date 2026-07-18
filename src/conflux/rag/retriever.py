"""RAG 检索模块 — 混合检索（Dense + Sparse） + RRF 融合"""

from __future__ import annotations

import re

from langchain_chroma import Chroma
from langchain_core.documents import Document
from rank_bm25 import BM25Okapi

from ..config import get


class HybridRetriever:
    """混合检索器：向量检索 (Dense) + BM25 (Sparse) → RRF 融合 → Top-K"""

    def __init__(self, vector_store: Chroma):
        self.vector_store = vector_store
        self._bm25: BM25Okapi | None = None
        self._bm25_docs: list[Document] = []
        self._bm25_ready = False

    def _tokenize(self, text: str) -> list[str]:
        value = str(text or "")
        tokens: list[str] = []
        if re.search(r"[\u4e00-\u9fff]", value):
            try:
                import jieba

                tokens.extend(token.strip().lower() for token in jieba.cut(value) if token.strip())
            except Exception:
                tokens.extend(re.findall(r"[\u4e00-\u9fff]{1,}|[a-z0-9][a-z0-9_.+-]*", value.lower()))
        tokens.extend(re.findall(r"[a-z][a-z0-9_.+-]*", value.lower()))
        return list(dict.fromkeys(token for token in tokens if token))

    def _ensure_bm25(self):
        """惰性加载 BM25 索引（从 ChromaDB 中拉取所有文档）"""
        if self._bm25_ready:
            return
        try:
            result = self.vector_store.get(include=["documents", "metadatas"])
            if result["documents"]:
                self._bm25_docs = [
                    Document(page_content=text, metadata=meta or {})
                    for text, meta in zip(result["documents"], result["metadatas"])
                ]
                tokenized = [self._tokenize(doc.page_content) for doc in self._bm25_docs]
                self._bm25 = BM25Okapi(tokenized)
        except Exception:
            self._bm25_docs = []
            self._bm25 = None
        self._bm25_ready = True

    def search(self, query: str) -> list[Document]:
        """执行混合检索

        1. Dense: ChromaDB 向量相似度
        2. Sparse: BM25 词法匹配
        3. RRF 融合
        4. 返回 top final_k
        """
        top_k = get("retrieval", "top_k", default=10)
        final_k = get("retrieval", "final_k", default=5)
        dense_weight = get("retrieval", "dense_weight", default=0.7)
        bm25_weight = get("retrieval", "bm25_weight", default=0.3)

        # Dense 检索
        dense_results = self.vector_store.similarity_search_with_score(query, k=top_k)
        dense_docs: list[tuple[Document, float]] = []
        for doc, distance in dense_results:
            metadata = dict(doc.metadata or {})
            dense_distance = _as_float(distance)
            dense_score = _distance_to_similarity(dense_distance)
            metadata.update({
                "dense_distance": dense_distance,
                "dense_score": dense_score,
                "query_dense_score": dense_score,
                "score_source": "current_query_dense",
            })
            dense_docs.append((Document(page_content=doc.page_content, metadata=metadata), dense_score))

        # Sparse 检索 (BM25)
        self._ensure_bm25()
        sparse_results: list[tuple[Document, float]] = []
        if self._bm25 is not None:
            tokenized_query = self._tokenize(query)
            scores = self._bm25.get_scores(tokenized_query)
            # 归一化 BM25 分数到 [0, 1]
            max_score = max(scores) if len(scores) > 0 and max(scores) > 0 else 1.0
            ranked_sparse = sorted(
                enumerate(scores),
                key=lambda item: item[1],
                reverse=True,
            )
            for i, score in ranked_sparse[:top_k]:
                if score <= 0:
                    continue
                metadata = dict(self._bm25_docs[i].metadata or {})
                normalized = score / max_score
                metadata["bm25_score"] = normalized
                sparse_results.append((Document(page_content=self._bm25_docs[i].page_content, metadata=metadata), normalized))

        cross_language = _is_cross_language(query, self._bm25_docs)
        effective_dense_weight = float(dense_weight)
        effective_bm25_weight = float(bm25_weight)
        if cross_language:
            effective_dense_weight = max(effective_dense_weight, 0.9)
            effective_bm25_weight = min(effective_bm25_weight, 0.1)

        # RRF (Reciprocal Rank Fusion) 融合
        rrf_scores: dict[str, float] = {}

        for rank, (doc, score) in enumerate(dense_docs):
            chunk_id = doc.metadata.get("chunk_id", doc.page_content)
            rrf = effective_dense_weight * (1.0 / (rank + 60))
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0) + rrf

        for rank, (doc, score) in enumerate(sparse_results):
            chunk_id = doc.metadata.get("chunk_id", doc.page_content)
            rrf = effective_bm25_weight * (1.0 / (rank + 60))
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0) + rrf

        # 按 RRF 分数排序
        all_docs_map = {}
        for doc, _ in dense_docs:
            all_docs_map[doc.metadata.get("chunk_id", doc.page_content)] = doc
        for doc, _ in sparse_results:
            all_docs_map[doc.metadata.get("chunk_id", doc.page_content)] = doc

        sorted_ids = sorted(rrf_scores, key=rrf_scores.get, reverse=True)
        results = []
        for cid in sorted_ids[:final_k]:
            if cid in all_docs_map:
                doc = all_docs_map[cid]
                metadata = dict(doc.metadata or {})
                metadata["rrf_score"] = rrf_scores[cid]
                metadata["retrieval_language"] = "cross_language" if cross_language else "same_language"
                results.append(Document(page_content=doc.page_content, metadata=metadata))

        return results


def _as_float(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _distance_to_similarity(distance: float) -> float:
    """Convert Chroma's lower-is-better distance into a bounded similarity."""

    return round(max(0.0, min(1.0, 1.0 / (1.0 + max(0.0, distance)))), 6)


def _is_cross_language(query: str, docs: list[Document]) -> bool:
    if not docs or not re.search(r"[\u4e00-\u9fff]", str(query or "")):
        return False
    english_docs = sum(
        1 for doc in docs
        if re.search(r"[A-Za-z]", doc.page_content or "")
        and not re.search(r"[\u4e00-\u9fff]", doc.page_content or "")
    )
    return english_docs >= max(1, len(docs) // 2)
