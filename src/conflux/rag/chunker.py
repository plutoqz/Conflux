"""RAG 分块模块 — 多粒度分块（L1 父块 + L2 子块 + 自动合并）

Phase 1 实现：固定大小分块 (L1 1024t + L2 256t)
Phase 2 升级：Contextual Retrieval 前缀 + Late Chunking
"""

import tiktoken
from langchain_core.documents import Document


# 默认使用 cl100k_base (GPT-4 / text-embedding-3 系列)
_ENCODING = tiktoken.get_encoding("cl100k_base")


def _count_tokens(text: str) -> int:
    return len(_ENCODING.encode(text))


def chunk_document(
    doc: Document,
    parent_size: int = 1024,
    child_size: int = 256,
    overlap: int = 0,
) -> tuple[list[Document], list[Document]]:
    """将单个文档切分为父块和子块

    Returns:
        (parent_chunks, child_chunks) — 子块自动携带 parent_id 元数据
    """
    text = doc.page_content
    metadata = doc.metadata

    parent_chunks = []
    child_chunks = []
    parent_idx = 0

    # 按 parent_size 切分父块
    for start in range(0, len(text), parent_size):
        parent_text = text[start : start + parent_size]
        if not parent_text.strip():
            continue

        parent_id = f"{metadata.get('source', 'unknown')}#p{parent_idx}"
        parent_chunks.append(Document(
            page_content=parent_text,
            metadata={
                **metadata,
                "chunk_type": "parent",
                "chunk_id": parent_id,
                "char_start": start,
                "char_end": start + len(parent_text),
            },
        ))

        # 按 child_size 切分子块
        child_idx = 0
        for cs in range(0, len(parent_text), child_size):
            child_text = parent_text[cs : cs + child_size]
            if not child_text.strip():
                continue
            child_id = f"{parent_id}#c{child_idx}"
            child_chunks.append(Document(
                page_content=child_text,
                metadata={
                    **metadata,
                    "chunk_type": "child",
                    "chunk_id": child_id,
                    "parent_id": parent_id,
                    "char_start": start + cs,
                    "char_end": start + cs + len(child_text),
                },
            ))
            child_idx += 1

        parent_idx += 1

    return parent_chunks, child_chunks


def chunk_documents(
    docs: list[Document],
    parent_size: int = 1024,
    child_size: int = 256,
) -> tuple[list[Document], list[Document]]:
    """批量切分文档"""
    all_parents = []
    all_children = []
    for doc in docs:
        parents, children = chunk_document(doc, parent_size, child_size)
        all_parents.extend(parents)
        all_children.extend(children)
    return all_parents, all_children
