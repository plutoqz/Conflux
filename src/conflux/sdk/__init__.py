"""Conflux SDK — plugin authoring, manifest tools, and contract-test helpers.

Import from here instead of ``core`` when writing plugins; ``core`` symbols
are re-exported for convenience.
"""

from ..core.contracts import (
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
    WorkflowDefinition,
    WorkflowStepSpec,
)
from .manifest import SDK_VERSION, load_manifest, load_workflow, validate_manifest
from .plugin import Capability, Plugin, capability
from .testing import (
    assert_manifest_valid,
    assert_step_result,
    make_plugin_context,
    manifest_with_bad_cap_id,
    manifest_without_capabilities,
    manifest_with_unknown_api,
    valid_manifest_minimal,
)

__all__ = [
    # re-exported core contracts
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
    "WorkflowDefinition",
    "WorkflowStepSpec",
    # sdk tools
    "Capability",
    "Plugin",
    "capability",
    "load_manifest",
    "load_workflow",
    "validate_manifest",
    "SDK_VERSION",
    "make_plugin_context",
    "assert_manifest_valid",
    "assert_step_result",
    "valid_manifest_minimal",
    "manifest_without_capabilities",
    "manifest_with_bad_cap_id",
    "manifest_with_unknown_api",
]
