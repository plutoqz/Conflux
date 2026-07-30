"""Conflux core — runtime protocols, registry, policy, and storage ports.

This package defines stable contracts that plugins and adapters depend on.
It must not import plugin implementations or workbench internals.
"""

from .contracts import (
    ApiVersion,
    ApprovalRequest,
    ArtifactRef,
    CapabilityMode,
    CapabilitySpec,
    PluginContext,
    PluginManifest,
    PluginPermission,
    RunContext,
    StepResult,
    StepStatus,
    TraceEvent,
    WorkflowDefinition,
    WorkflowStepSpec,
)
from .p2_contracts import (
    Cadence,
    EvidenceGap,
    EvidenceUtility,
    ImpactSuggestionType,
    P2_PROTOCOL_VERSION,
    PaperIdentity,
    PaperLinkStatus,
    PaperSource,
    ProjectImpactSuggestion,
    ProjectPaperLink,
    ProjectResearchConfig,
    ProjectResearchContext,
    QuerySpec,
    RadarRunResult,
    RadarRunStats,
    SearchIntent,
    SearchIntentType,
    Track,
    TrackQuery,
)
from .dynamic_source import (
    get_source_result,
    init_source_results,
    merge_legacy_fields,
    merge_source_result,
    merge_source_results_reducer,
    source_ids,
)
from .executor import execute_capability, sanitize_error
from .policy import (
    PolicyViolation,
    check_budget,
    check_permissions,
    check_step_schema,
    check_workflow_steps,
    validate_capability_input,
    validate_output,
    validate_workflow_inputs,
)
from .registry import (
    PluginRecord,
    PluginRegistry,
    get_registry,
    reset_registry,
)
from .workflow_compiler import (
    CompilationIssue,
    CompilationResult,
    compile_workflow,
    dry_run_workflow,
    execute_workflow,
    workflow_text_graph,
)

__all__ = [
    # contracts
    "ApiVersion",
    "ApprovalRequest",
    "ArtifactRef",
    "CapabilityMode",
    "CapabilitySpec",
    "PluginContext",
    "PluginManifest",
    "PluginPermission",
    "RunContext",
    "StepResult",
    "StepStatus",
    "TraceEvent",
    "WorkflowDefinition",
    "WorkflowStepSpec",
    # p2_contracts
    "Cadence",
    "EvidenceGap",
    "EvidenceUtility",
    "ImpactSuggestionType",
    "P2_PROTOCOL_VERSION",
    "PaperIdentity",
    "PaperLinkStatus",
    "PaperSource",
    "ProjectImpactSuggestion",
    "ProjectPaperLink",
    "ProjectResearchConfig",
    "ProjectResearchContext",
    "QuerySpec",
    "RadarRunResult",
    "RadarRunStats",
    "SearchIntent",
    "SearchIntentType",
    "Track",
    "TrackQuery",
    # executor
    "execute_capability",
    "sanitize_error",
    # policy
    "PolicyViolation",
    "check_budget",
    "check_permissions",
    "check_step_schema",
    "check_workflow_steps",
    "validate_capability_input",
    # workflows
    "CompilationIssue",
    "CompilationResult",
    "compile_workflow",
    "dry_run_workflow",
    "execute_workflow",
    "workflow_text_graph",
    # registry
    "PluginRecord",
    "PluginRegistry",
    "get_registry",
    "reset_registry",
]
