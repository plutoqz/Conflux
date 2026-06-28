"""RAG 检索工具 — 封装为 LangChain Tool，供 Agent 调用"""

import re

from langchain_core.tools import tool

from ..rag.retriever import HybridRetriever
from ..source_status import SourceResult


def create_rag_tool(retriever: HybridRetriever):
    """工厂函数：创建绑定到特定检索器的 RAG 搜索工具"""

    @tool
    def search_rag(query: str) -> str:
        """在本地知识库中搜索与 query 相关的内容。
        返回最相关的文档片段及其来源元数据。
        适用于：需要查找本地存储的文档、报告、笔记等场景。
        """
        try:
            docs = retriever.search(query)
        except Exception as exc:
            return SourceResult(
                source="RAG",
                status="failed",
                detail="Local Chroma hybrid retrieval",
                error=f"{type(exc).__name__}: {exc}",
                content="本地知识库检索失败。",
            ).to_tool_text()
        if not docs:
            return SourceResult(
                source="RAG",
                status="failed",
                detail="Local Chroma hybrid retrieval",
                error="未在本地知识库中找到相关内容。",
                content="未在本地知识库中找到相关内容。",
            ).to_tool_text()

        if not _results_are_relevant(query, [doc.page_content for doc in docs]):
            sources = sorted({str(doc.metadata.get("source", "未知来源")) for doc in docs})
            return SourceResult(
                source="RAG",
                status="failed",
                detail="Local Chroma hybrid retrieval",
                error="检索结果与查询关键词重合度过低，判定为主题不匹配。",
                content=(
                    "本地知识库检索命中了文档，但与当前问题主题不匹配，"
                    "不得作为 RAG success 证据参与共识投票。\n"
                    f"命中文档：{', '.join(sources)}"
                ),
                metadata={"result_count": len(docs), "matched_sources": sources},
            ).to_tool_text()

        parts = []
        for i, doc in enumerate(docs):
            source = doc.metadata.get("source", "未知来源")
            chunk_id = doc.metadata.get("chunk_id", "")
            parts.append(
                f"[来源 {i+1}] {source} ({chunk_id})\n{doc.page_content.strip()}\n"
            )
        content = "\n".join(parts)
        return SourceResult(
            source="RAG",
            status="success",
            detail="Local Chroma hybrid retrieval",
            content=content,
            metadata={"result_count": len(docs)},
        ).to_tool_text()

    return search_rag


def _results_are_relevant(query: str, texts: list[str]) -> bool:
    """Conservative lexical gate to avoid voting on unrelated RAG hits."""

    query_terms = _important_terms(query)
    if not query_terms:
        return True
    combined = " ".join(texts).lower()
    matched = {term for term in query_terms if term.lower() in combined}
    if not matched:
        return False
    return len(matched) / len(query_terms) >= 0.2


def _important_terms(text: str) -> set[str]:
    raw_terms = re.findall(r"[A-Za-z][A-Za-z0-9-]{2,}|[\u4e00-\u9fff]{2,}", text)
    stopwords = {
        "研究", "说明", "结合", "核心", "概念", "流程", "设计", "风险", "控制",
        "工程", "落地", "建议", "系统", "关系", "the", "and", "with", "for",
        "retrieval", "augmented",
    }
    terms = {
        term.lower()
        for term in raw_terms
        if term.lower() not in stopwords and len(term) >= 3
    }
    return terms
