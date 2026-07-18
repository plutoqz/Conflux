"""Built-in external web source connector (M2)."""

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
from conflux.sdk.plugin import Capability, Plugin
from conflux.source_status import SourceResult, parse_source_results


class WebPlugin(Plugin):
    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            id="builtin.web",
            version="0.1.0",
            entrypoint="conflux.builtin.web.plugin:plugin",
            capabilities=[
                CapabilitySpec(
                    id="builtin.web.search",
                    description="Search public web sources and normalize URL evidence",
                    mode=CapabilityMode.DETERMINISTIC,
                    input_schema={
                        "type": "object",
                        "properties": {"query": {"type": "string"}},
                        "required": ["query"],
                    },
                    output_schema={
                        "type": "object",
                        "properties": {
                            "status": {"type": "string"},
                            "content": {"type": "string"},
                            "citations": {"type": "array"},
                        },
                        "required": ["status", "content", "citations"],
                    },
                )
            ],
            permissions=[PluginPermission.NETWORK],
        )

    def get_capability(self, capability_id: str) -> Capability | None:
        return web_search if capability_id == "builtin.web.search" else None


plugin = WebPlugin()


def web_search(ctx: PluginContext, *, query: str) -> StepResult:
    """Run the existing web tool, or an injected offline search function."""

    try:
        search_fn = ctx.config.get("web_search") if isinstance(ctx.config, dict) else None
        if search_fn is None:
            from conflux.tools.web import search_web

            search_fn = lambda value: search_web.invoke({"query": value})
        raw = search_fn(query)
        parsed = parse_source_results(str(raw))
        result = parsed[-1] if parsed else SourceResult(
            source="Web",
            status="fallback",
            detail="web connector returned no structured result",
            error="Web connector did not return a structured SourceResult.",
            content=str(raw),
        )
        citations = (result.metadata or {}).get("citations") or []
        return StepResult(
            status=StepStatus.FAILED if result.status == "failed" else StepStatus.SUCCESS,
            output={
                "status": result.status,
                "content": result.content,
                "citations": citations,
                "source": "builtin.web",
                "detail": result.detail,
            },
            error=result.error if result.status == "failed" else "",
            plugin_id="builtin.web",
            capability_id="builtin.web.search",
        )
    except Exception as exc:
        return StepResult(
            status=StepStatus.FAILED,
            error=f"Web search failed: {type(exc).__name__}: {exc}",
            plugin_id="builtin.web",
            capability_id="builtin.web.search",
        )
