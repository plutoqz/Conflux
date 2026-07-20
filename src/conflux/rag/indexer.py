"""RAG 索引模块 — ChromaDB 向量存储管理"""

import hashlib

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

    # Content-hash-aware upsert: an unchanged chunk is skipped, while a
    # changed chunk with the same logical id updates the existing vector.
    existing_hashes: dict[str, str] = {}
    existing_metadatas: dict[str, dict] = {}
    try:
        existing = vector_store.get(include=["documents", "metadatas"])
        for index, item_id in enumerate(existing.get("ids", [])):
            metadata = (existing.get("metadatas") or [])[index] or {}
            content = (existing.get("documents") or [])[index] or ""
            existing_hashes[str(item_id)] = str(
                metadata.get("content_hash") or _content_hash(str(content))
            )
            existing_metadatas[str(item_id)] = dict(metadata)
    except Exception:
        pass  # 空 collection 报错是正常的

    additions: list[tuple[str, Document]] = []
    updates: list[tuple[str, Document]] = []
    for original in documents:
        metadata = dict(original.metadata or {})
        logical_id = str(metadata.get("chunk_id") or _content_hash(original.page_content))
        digest = _content_hash(original.page_content)
        metadata["content_hash"] = digest
        metadata["content_version"] = digest[:16]
        document = Document(page_content=original.page_content, metadata=metadata)
        if logical_id not in existing_hashes:
            additions.append((logical_id, document))
        elif existing_hashes[logical_id] != digest or _metadata_requires_update(existing_metadatas.get(logical_id) or {}, metadata):
            updates.append((logical_id, document))

    if not additions and not updates:
        return 0

    batch_size = 5000
    for start in range(0, len(additions), batch_size):
        batch = additions[start : start + batch_size]
        vector_store.add_documents(
            [document for _, document in batch],
            ids=[item_id for item_id, _ in batch],
        )
    if updates:
        ids = [item_id for item_id, _ in updates]
        docs = [document for _, document in updates]
        try:
            vector_store.update_documents(ids=ids, documents=docs)
        except (AttributeError, TypeError, NotImplementedError):
            # Older Chroma versions lack update_documents; delete/add keeps
            # logical ids stable and remains idempotent.
            vector_store.delete(ids=ids)
            vector_store.add_documents(docs, ids=ids)
    return len(additions) + len(updates)


def clear_index(vector_store: Chroma) -> None:
    """清空索引"""
    try:
        existing = vector_store.get()
        ids = existing.get("ids", [])
        if ids:
            batch_size = 5000
            for start in range(0, len(ids), batch_size):
                vector_store.delete(ids=ids[start : start + batch_size])
    except Exception:
        pass


def _content_hash(text: str) -> str:
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


def _metadata_requires_update(existing: dict, current: dict) -> bool:
    tracked = {
        "content_scope", "full_text_requested", "full_text_downloaded",
        "full_text_extracted", "full_text_indexed", "full_text_status",
        "paper_section", "page_start", "page_end", "char_start", "char_end",
    }
    return any(existing.get(key) != current.get(key) for key in tracked)
