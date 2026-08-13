"""P3.4 RAG coverage — index project documents into the knowledge base and
compute per-document coverage against the active Chroma collection (plan §10.3).

Indexing is user-triggered only; coverage is computed during refresh and
materialized into the snapshot, so page reads never touch Chroma.  Chunk
metadata carries ``doc_content_hash`` (file-level hash from the document
index) — ``content_hash`` is owned by the indexer and hashes chunk text.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any

from conflux.project_registry.models import ProjectDefinition

from .repository import ProjectIntelligence

_SOURCE_PREFIX = "project:"

# TTL cache for the active-collection metadata sweep (46k+ chunks); refresh
# and settings-save can share one read within the window.
_COLLECTION_CACHE_LOCK = threading.Lock()
_COLLECTION_CACHE: dict[str, Any] = {"at": 0.0, "payload": None}
_COLLECTION_TTL_SECONDS = 60.0


def _chunk_source(project_id: str, relative_path: str) -> str:
    normalized = relative_path.replace("\\", "/").lstrip("/")
    return f"{_SOURCE_PREFIX}{project_id}:{normalized}"


def _collection_snapshot() -> dict[str, Any]:
    """Active collection -> {source: set(doc_content_hash)} + diagnostics."""
    with _COLLECTION_CACHE_LOCK:
        cached = _COLLECTION_CACHE["payload"]
        if cached is not None and time.monotonic() - _COLLECTION_CACHE["at"] < _COLLECTION_TTL_SECONDS:
            return cached
    try:
        from conflux.rag.indexer import create_vector_store

        store = create_vector_store()
        by_source: dict[str, set[str]] = {}
        collection_name = ""
        # Chroma rejects un-paged gets on large collections
        # ("too many SQL variables"); page through metadata in batches.
        offset = 0
        while True:
            batch = store.get(include=["metadatas"], limit=5000, offset=offset)
            metadatas = batch.get("metadatas") or []
            if not metadatas:
                break
            for metadata in metadatas:
                metadata = metadata or {}
                source = str(metadata.get("source") or "")
                if not source.startswith(_SOURCE_PREFIX):
                    continue
                file_hash = str(metadata.get("doc_content_hash") or "")
                if file_hash:
                    by_source.setdefault(source, set()).add(file_hash)
            offset += len(metadatas)
        collection_name = str(getattr(getattr(store, "_collection", None), "name", "") or "")
        model = ""
        try:
            collection = store._collection  # type: ignore[attr-defined]
            model = str((collection.metadata or {}).get("conflux_embedding_model") or "")
        except Exception:
            model = ""
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}", "by_source": {}}
    result = {
        "by_source": by_source,
        "collection": collection_name,
        "model": model,
        "error": "",
    }
    with _COLLECTION_CACHE_LOCK:
        _COLLECTION_CACHE["at"] = time.monotonic()
        _COLLECTION_CACHE["payload"] = result
    return result


def compute_coverage(
    intelligence: ProjectIntelligence,
    project: ProjectDefinition,
) -> dict[str, Any]:
    """Per-document RAG status: indexed / stale / missing (P3 §10.3)."""
    snapshot = _collection_snapshot()
    by_source = snapshot.get("by_source") or {}
    per_document: dict[str, str] = {}
    indexed = stale = missing = 0
    for doc in intelligence.documents.list(project.id):
        source = _chunk_source(project.id, doc.path)
        hashes = by_source.get(source, set())
        if not hashes:
            status = "missing"
            missing += 1
        elif doc.content_hash in hashes:
            status = "indexed"
            indexed += 1
        else:
            status = "stale"
            stale += 1
        per_document[doc.path] = status
    return {
        "indexed": indexed,
        "stale": stale,
        "missing": missing,
        "by_document": per_document,
        "collection": snapshot.get("collection") or "",
        "model": snapshot.get("model") or "",
        "index_version": "project-doc-20260813",
        "error": snapshot.get("error") or "",
        "computed_at": time.time(),
    }


def index_project_documents(
    intelligence: ProjectIntelligence,
    project: ProjectDefinition,
    *,
    document_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Index confirmed project documents into the active knowledge base.

    Only confirmed-authority documents are indexed (auto-discovery never
    grants authority, plan §4.5).  Failures are collected and returned
    without blocking the rest of the batch.
    """
    from langchain_core.documents import Document

    from conflux.rag.chunker import chunk_document
    from conflux.rag.indexer import create_vector_store, index_documents

    documents = [
        doc for doc in intelligence.documents.list(project.id)
        if doc.authority.value == "confirmed"
        and (not document_ids or doc.document_id in document_ids)
    ]
    if not documents:
        return {"ok": False, "error": "没有可索引的已确权文档（先在“证据与知识”页确权）。"}

    root = Path(project.path).expanduser().resolve()
    chunks: list[Document] = []
    failed: list[dict[str, str]] = []
    for doc in documents:
        path = (root / doc.path).resolve()
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            failed.append({"path": doc.path, "error": str(exc)})
            continue
        base_metadata = {
            "source": _chunk_source(project.id, doc.path),
            "doc_content_hash": doc.content_hash,
            "project_id": project.id,
            "doc_path": doc.path,
            "doc_kind": doc.kind.value,
            "indexed_at": time.time(),
            "chunk_id": f"{_chunk_source(project.id, doc.path)}#p0",
        }
        parents, children = chunk_document(
            Document(page_content=text, metadata=base_metadata)
        )
        chunks.extend(parents)
        chunks.extend(children)

    if not chunks:
        return {"ok": False, "error": "已确权文档均读取失败。", "failed": failed}

    try:
        indexed = index_documents(create_vector_store(), chunks)
    except Exception as exc:
        return {"ok": False, "error": f"索引写入失败：{type(exc).__name__}: {exc}", "failed": failed}

    with _COLLECTION_CACHE_LOCK:
        _COLLECTION_CACHE["payload"] = None  # coverage must re-read after a write
    return {
        "ok": True,
        "documents": len(documents),
        "chunks": len(chunks),
        "indexed": indexed,
        "failed": failed,
    }
