"""Knowledge-source helpers for Graduate Research Copilot."""

from .paper_indexer import (
    PaperPromotionArtifacts,
    PaperPromotionResult,
    load_inbox_payload,
    paper_to_documents,
    promote_inbox,
    write_promoted_papers,
)
from .source_models import KnowledgeSource

__all__ = [
    "KnowledgeSource",
    "PaperPromotionArtifacts",
    "PaperPromotionResult",
    "load_inbox_payload",
    "paper_to_documents",
    "promote_inbox",
    "write_promoted_papers",
]
