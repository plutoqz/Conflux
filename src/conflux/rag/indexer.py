"""RAG 索引模块 — ChromaDB 向量存储管理"""

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_chroma import Chroma
from langchain_core.documents import Document

from ..config import get
from ..model_factory import create_embedding_model


def create_vector_store() -> Chroma:
    """根据 config 创建 ChromaDB 向量存储"""
    persist_dir = get("vector_store", "persist_dir", default="./data/chroma_db")
    collection_name = get("vector_store", "collection_name", default="conflux_docs")

    embedding = create_embedding_model()

    client = chromadb.PersistentClient(
        path=persist_dir,
        settings=ChromaSettings(anonymized_telemetry=False),
    )

    return Chroma(
        client=client,
        collection_name=collection_name,
        embedding_function=embedding,
    )


def index_documents(
    vector_store: Chroma,
    documents: list[Document],
) -> int:
    """将文档列表索引到向量存储，返回索引数量"""
    if not documents:
        return 0

    # 去重：跳过已有相同 chunk_id 的文档
    existing_ids = set()
    try:
        existing = vector_store.get()
        existing_ids = set(existing.get("ids", []))
    except Exception:
        pass  # 空 collection 报错是正常的

    new_docs = [d for d in documents if d.metadata.get("chunk_id") not in existing_ids]
    if not new_docs:
        return 0

    ids = [d.metadata.get("chunk_id", str(hash(d.page_content))) for d in new_docs]
    vector_store.add_documents(new_docs, ids=ids)
    return len(new_docs)


def clear_index(vector_store: Chroma) -> None:
    """清空索引"""
    try:
        existing = vector_store.get()
        ids = existing.get("ids", [])
        if ids:
            vector_store.delete(ids=ids)
    except Exception:
        pass
