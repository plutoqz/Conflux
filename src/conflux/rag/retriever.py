"""RAG 检索模块 — 混合检索（Dense + Sparse） + RRF 融合"""

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
        import jieba
        return list(jieba.cut(text))

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
                sparse_results.append((self._bm25_docs[i], score / max_score))

        # RRF (Reciprocal Rank Fusion) 融合
        rrf_scores: dict[str, float] = {}

        for rank, (doc, score) in enumerate(dense_results):
            chunk_id = doc.metadata.get("chunk_id", doc.page_content)
            rrf = dense_weight * (1.0 / (rank + 60))
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0) + rrf

        for rank, (doc, score) in enumerate(sparse_results):
            chunk_id = doc.metadata.get("chunk_id", doc.page_content)
            rrf = bm25_weight * (1.0 / (rank + 60))
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0) + rrf

        # 按 RRF 分数排序
        all_docs_map = {}
        for doc, _ in dense_results:
            all_docs_map[doc.metadata.get("chunk_id", doc.page_content)] = doc
        for doc, _ in sparse_results:
            all_docs_map[doc.metadata.get("chunk_id", doc.page_content)] = doc

        sorted_ids = sorted(rrf_scores, key=rrf_scores.get, reverse=True)
        results = []
        for cid in sorted_ids[:final_k]:
            if cid in all_docs_map:
                results.append(all_docs_map[cid])

        return results
