"""A bounded data-source extension that reads explicit JSONL files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from conflux.core.contracts import (
    CapabilityMode,
    CapabilitySpec,
    PluginContext,
    PluginManifest,
    PluginPermission,
    StepResult,
)
from conflux.sdk.plugin import Capability, Plugin


class LocalJsonlSourcePlugin(Plugin):
    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            id="example.local-jsonl-source",
            version="0.1.0",
            entrypoint="examples.m5_plugins.local_jsonl_source.plugin:plugin",
            capabilities=[CapabilitySpec(
                id="example.local-jsonl-source.search",
                description="Search an explicit workspace-local JSONL corpus",
                mode=CapabilityMode.DETERMINISTIC,
                input_schema={
                    "type": "object",
                    "properties": {"path": {"type": "string"}, "query": {"type": "string"}},
                    "required": ["path", "query"],
                },
                output_schema={
                    "type": "object",
                    "properties": {"items": {"type": "array"}},
                    "required": ["items"],
                },
            )],
            permissions=[PluginPermission.FILESYSTEM_READ],
        )

    def get_capability(self, capability_id: str) -> Capability | None:
        return search if capability_id == "example.local-jsonl-source.search" else None


plugin = LocalJsonlSourcePlugin()


def search(ctx: PluginContext, *, path: str, query: str) -> StepResult:
    workspace = Path(ctx.run.workspace).resolve()
    source = (workspace / path).resolve()
    try:
        source.relative_to(workspace)
    except ValueError:
        return StepResult.failed("path is outside the declared workspace", plugin_id=plugin.manifest.id, capability_id="example.local-jsonl-source.search")
    terms = {term.casefold() for term in query.split() if len(term) >= 2}
    items: list[dict[str, Any]] = []
    for line in source.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        text = json.dumps(item, ensure_ascii=False).casefold()
        if not terms or any(term in text for term in terms):
            items.append(item)
    return StepResult.success(
        {"items": items},
        metrics={"rows": len(items)},
        plugin_id=plugin.manifest.id,
        capability_id="example.local-jsonl-source.search",
    )
