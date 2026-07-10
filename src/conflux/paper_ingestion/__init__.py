"""Paper ingestion contracts and helpers for Graduate Research Copilot."""

from .dedup import deduplicate_papers
from .filters import apply_negative_filters
from .fixtures import load_paper_fixture
from .ingestion_policy import DEFAULT_POLICY, IngestionPolicyConfig, decide_ingestion, default_policy
from .models import IngestionDecision, PaperAnalysis, PaperRecord
from .pdf_downloader import PDFDownloader, arxiv_pdf_url, safe_pdf_id
from .pdf_text import PDFTextResult, extract_pdf_text, find_local_pdf
from .pipeline import PaperInboxResult, build_inbox, build_inbox_from_arxiv, build_inbox_from_fixture

__all__ = [
    "IngestionDecision",
    "IngestionPolicyConfig",
    "PaperAnalysis",
    "PaperInboxResult",
    "PaperRecord",
    "PDFDownloader",
    "PDFTextResult",
    "DEFAULT_POLICY",
    "apply_negative_filters",
    "arxiv_pdf_url",
    "build_inbox",
    "build_inbox_from_arxiv",
    "build_inbox_from_fixture",
    "decide_ingestion",
    "deduplicate_papers",
    "default_policy",
    "extract_pdf_text",
    "find_local_pdf",
    "load_paper_fixture",
    "safe_pdf_id",
]
