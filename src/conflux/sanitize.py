"""Untrusted-content sanitization shared by web and RAG evidence paths.

Any content that originates outside the system (web pages, fetched PDFs,
local documents) may contain instruction-like text intended to manipulate
the research pipeline.  The sanitizer removes instruction-like lines while
preserving factual body content, and reports whether anything was removed so
callers can annotate evidence and limitations.
"""

from __future__ import annotations

import re


_NON_EVIDENCE_MARKERS = (
    "ingestion action:",
    "relevance score:",
    "press enter to search",
    "advanced search",
    "provide your assessment in the following json format",
    "relevance_scores",
    "you are an expert in ai safety and fact-checking",
)


def is_admissible_evidence_text(text: str) -> bool:
    """Return whether extracted text is safe and substantive grounding material."""

    normalized = re.sub(r"\s+", " ", str(text or "")).strip()
    lowered = normalized.casefold()
    return len(normalized) >= 80 and not any(marker in lowered for marker in _NON_EVIDENCE_MARKERS)


def sanitize_untrusted_content(text: str) -> tuple[str, bool]:
    """Remove instruction-like lines while preserving factual body content.

    Returns ``(sanitized_text, detected)`` where ``detected`` is True when at
    least one instruction-like line was removed.
    """

    patterns = (
        r"ignore (?:all |any )?(?:previous|prior) instructions",
        r"system prompt",
        r"developer message",
        r"reveal (?:your |the )?(?:prompt|secret|api key)",
        r"忽略(?:以上|之前|所有)指令",
        r"系统提示词",
        r"开发者消息",
        r"泄露.*(?:密钥|提示词)",
    )
    kept = []
    detected = False
    for raw_line in str(text or "").splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line:
            continue
        if any(re.search(pattern, line, flags=re.IGNORECASE) for pattern in patterns):
            detected = True
            continue
        kept.append(line)
    return "\n".join(kept), detected
