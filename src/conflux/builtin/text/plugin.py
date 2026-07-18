"""Built-in text processing plugin.

This is a first-party plugin that validates the SDK protocol.
It provides deterministic keyword matching — wrapping the same logic
used by ``paper_ingestion.scorer`` but through the plugin interface.
"""

from __future__ import annotations

import re
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


# ── plugin definition ──────────────────────────────────────────────

class TextPlugin(Plugin):
    """Built-in text utilities — keyword matching, cleaning, chunking."""

    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            id="builtin.text",
            version="0.1.0",
            entrypoint="conflux.builtin.text.plugin:plugin",
            capabilities=[
                CapabilitySpec(
                    id="builtin.text.keyword_match",
                    description="Match keywords in text and return coverage score",
                    mode=CapabilityMode.DETERMINISTIC,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "keywords": {"type": "array", "items": {"type": "string"}},
                            "case_sensitive": {"type": "boolean", "default": False},
                        },
                        "required": ["text", "keywords"],
                    },
                    output_schema={
                        "type": "object",
                        "properties": {
                            "matched_keywords": {"type": "array", "items": {"type": "string"}},
                            "coverage": {"type": "number"},
                            "score": {"type": "number"},
                        },
                    },
                ),
            ],
            permissions=[PluginPermission.FILESYSTEM_READ],
        )

    def get_capability(self, capability_id: str) -> Capability | None:
        if capability_id == "builtin.text.keyword_match":
            return keyword_match
        return None


# ── singleton ──────────────────────────────────────────────────────

plugin = TextPlugin()


# ── capability implementations ─────────────────────────────────────

def keyword_match(
    ctx: PluginContext,
    *,
    text: str,
    keywords: list[str],
    case_sensitive: bool = False,
) -> StepResult:
    """Match keywords in text and return coverage + score."""
    if not text or not keywords:
        return StepResult(
            status=StepStatus.SUCCESS,
            output={"matched_keywords": [], "coverage": 0.0, "score": 0.0},
            plugin_id="builtin.text",
            capability_id="builtin.text.keyword_match",
        )

    matched: list[str] = []
    search_text = text if case_sensitive else text.lower()

    for kw in keywords:
        term = kw if case_sensitive else kw.lower()
        if term in search_text:
            matched.append(kw)

    coverage = len(matched) / len(keywords) if keywords else 0.0
    score = min(1.0, coverage * (1.0 + 0.1 * len(matched)))

    return StepResult(
        status=StepStatus.SUCCESS,
        output={
            "matched_keywords": matched,
            "coverage": round(coverage, 4),
            "score": round(score, 4),
        },
        plugin_id="builtin.text",
        capability_id="builtin.text.keyword_match",
    )
