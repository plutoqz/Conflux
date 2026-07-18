"""Built-in RAG retrieval plugin (M2).

Wraps ``HybridRetriever.search()`` as a deterministic ``builtin.rag.search``
capability registered through the SDK.
"""

from __future__ import annotations

from typing import Any

from conflux.core.contracts import (
    CapabilityMode,
    CapabilitySpec,
    PluginContext,
    PluginManifest,
    PluginPermission,
    StepResult,
    StepStatus,
)
from conflux.sdk.plugin import Plugin, Capability


class RAGPlugin(Plugin):
    """Built-in local RAG retrieval capability."""

    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            id="builtin.rag",
            version="0.1.0",
            entrypoint="conflux.builtin.rag.plugin:plugin",
            capabilities=[
                CapabilitySpec(
                    id="builtin.rag.search",
                    description="Search local document index with hybrid retrieval",
                    mode=CapabilityMode.DETERMINISTIC,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "top_k": {"type": "integer", "default": 5},
                        },
                        "required": ["query"],
                    },
                    output_schema={
                        "type": "object",
                        "properties": {
                            "documents": {"type": "array"},
                            "source_count": {"type": "integer"},
                            "top_score": {"type": "number"},
                            "status": {"type": "string"},
                        },
                    },
                ),
            ],
            permissions=[PluginPermission.FILESYSTEM_READ],
        )

    def get_capability(self, capability_id: str) -> Capability | None:
        if capability_id == "builtin.rag.search":
            return rag_search
        return None


plugin = RAGPlugin()


# ── capability implementation ─────────────────────────────────────

def rag_search(
    ctx: PluginContext,
    *,
    query: str,
    top_k: int = 5,
) -> StepResult:
    """Search the local RAG index and return structured results."""
    try:
        retriever = ctx.storage
        if retriever is None or not hasattr(retriever, "search"):
            from conflux.rag import HybridRetriever, create_vector_store

            retriever = HybridRetriever(create_vector_store())
        docs = list(retriever.search(query))[: max(1, min(top_k, 50))]

        doc_list = []
        for rank, doc in enumerate(docs):
            metadata = dict(getattr(doc, "metadata", {}) or {})
            score = float(metadata.get("score", metadata.get("relevance_score", 1.0 / (rank + 1))))
            doc_list.append({
                "content": getattr(doc, "page_content", str(doc))[:500],
                "source": str(metadata.get("source", "")),
                "score": round(score, 4),
                "metadata": metadata,
            })

        top_score = max((item["score"] for item in doc_list), default=0.0)
        status = "success" if top_score >= 0.55 else "low_relevance" if doc_list else "no_evidence"

        return StepResult(
            status=StepStatus.SUCCESS,
            output={
                "documents": doc_list,
                "source_count": len(doc_list),
                "top_score": round(top_score, 4),
                "status": status,
            },
            plugin_id="builtin.rag",
            capability_id="builtin.rag.search",
        )

    except Exception as exc:
        return StepResult(
            status=StepStatus.FAILED,
            error=f"RAG search failed: {type(exc).__name__}: {exc}",
            plugin_id="builtin.rag",
            capability_id="builtin.rag.search",
        )
