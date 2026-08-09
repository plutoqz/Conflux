"""A non-source SDK extension that evaluates claim-level evidence coverage."""

from __future__ import annotations

from conflux.core.contracts import CapabilityMode, CapabilitySpec, PluginContext, PluginManifest, StepResult
from conflux.sdk.plugin import Capability, Plugin


class EvidenceCoverageEvaluatorPlugin(Plugin):
    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            id="example.evidence-coverage-evaluator",
            version="0.1.0",
            entrypoint="examples.m5_plugins.evidence_coverage_evaluator.plugin:plugin",
            capabilities=[CapabilitySpec(
                id="example.evidence-coverage-evaluator.score",
                description="Score whether generated claims have explicit evidence references",
                mode=CapabilityMode.DETERMINISTIC,
                input_schema={
                    "type": "object",
                    "properties": {"claims": {"type": "array", "items": {"type": "object"}}},
                    "required": ["claims"],
                },
                output_schema={
                    "type": "object",
                    "properties": {"coverage": {"type": "number"}, "uncovered_claim_ids": {"type": "array"}},
                    "required": ["coverage", "uncovered_claim_ids"],
                },
            )],
        )

    def get_capability(self, capability_id: str) -> Capability | None:
        return score if capability_id == "example.evidence-coverage-evaluator.score" else None


plugin = EvidenceCoverageEvaluatorPlugin()


def score(ctx: PluginContext, *, claims: list[dict]) -> StepResult:
    uncovered = [
        str(item.get("claim_id") or index)
        for index, item in enumerate(claims)
        if not [value for value in item.get("evidence_ids") or [] if str(value).strip()]
    ]
    coverage = round((len(claims) - len(uncovered)) / len(claims), 4) if claims else 1.0
    return StepResult.success(
        {"coverage": coverage, "uncovered_claim_ids": uncovered},
        metrics={"claim_count": len(claims)},
        plugin_id=plugin.manifest.id,
        capability_id="example.evidence-coverage-evaluator.score",
    )
