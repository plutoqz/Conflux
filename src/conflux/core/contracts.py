"""Core contracts for the Conflux plugin protocol.

These Pydantic v2 models define the stable boundary between the runtime
and plugins.  Plugins receive only ``PluginContext`` — never raw LangGraph
state, private core objects, or workbench internals.

All models are JSON-serializable and versioned via ``api_version``.
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


# ── versioning ────────────────────────────────────────────────────

class ApiVersion(str, Enum):
    """Supported SDK API versions."""
    V1_ALPHA1 = "conflux.dev/v1alpha1"


# ── manifest ──────────────────────────────────────────────────────

class CapabilityMode(str, Enum):
    """Execution mode for a capability step."""
    DETERMINISTIC = "deterministic"
    AGENTIC = "agentic"
    HUMAN = "human"


class CapabilitySpec(BaseModel):
    """A single capability exposed by a plugin."""
    id: str = Field(description="Namespaced capability id, e.g. 'builtin.rag.search'")
    description: str = Field(default="", description="Human-readable summary")
    mode: CapabilityMode = Field(default=CapabilityMode.DETERMINISTIC)
    input_schema: dict[str, Any] = Field(
        default_factory=dict, description="JSON Schema for inputs"
    )
    output_schema: dict[str, Any] = Field(
        default_factory=dict, description="JSON Schema for outputs"
    )


class PluginPermission(str, Enum):
    """Permissions a plugin may declare.

    In v1alpha1 plugins are trusted in-process code; permissions serve
    validation and audit purposes, **not** sandbox enforcement.
    """
    NETWORK = "network"
    FILESYSTEM_READ = "filesystem:read"
    FILESYSTEM_WRITE = "filesystem:write"
    MODEL_INFERENCE = "model:inference"
    STORAGE_READ = "storage:read"
    STORAGE_WRITE = "storage:write"


class PluginManifest(BaseModel):
    """Manifest that every plugin must provide (YAML or JSON)."""
    api_version: ApiVersion = Field(default=ApiVersion.V1_ALPHA1)
    kind: Literal["Plugin"] = "Plugin"
    id: str = Field(description="Unique plugin id, e.g. 'builtin.rag'")
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    entrypoint: str = Field(
        description="Python import path, e.g. 'conflux.builtin.rag.plugin:plugin'"
    )
    capabilities: list[CapabilitySpec] = Field(default_factory=list)
    permissions: list[PluginPermission] = Field(default_factory=list)
    config_schema: dict[str, Any] = Field(
        default_factory=dict, description="JSON Schema for plugin-specific config"
    )
    timeout_seconds: float = Field(default=30.0, ge=0)
    side_effects: bool = Field(
        default=False, description="Whether capability calls have external side effects"
    )
    sdk_compat: str = Field(
        default=">=0.1.0", description="SDK version range this plugin is compatible with"
    )


# ── workflow ───────────────────────────────────────────────────────

class WorkflowStepSpec(BaseModel):
    """One step in a YAML workflow definition."""
    id: str
    uses: str = Field(description="Capability id, e.g. 'builtin.rag.search'")
    mode: CapabilityMode = CapabilityMode.DETERMINISTIC
    config: dict[str, Any] = Field(default_factory=dict)
    inputs: dict[str, str] = Field(
        default_factory=dict,
        description="Mapping from step input names to workflow-input or prior-step output keys",
    )
    max_iterations: int = Field(default=1, ge=1)
    stop_conditions: list[str] = Field(default_factory=list)


class WorkflowDefinition(BaseModel):
    """A YAML-defined workflow composed of registered capabilities."""
    api_version: ApiVersion = Field(default=ApiVersion.V1_ALPHA1)
    kind: Literal["Workflow"] = "Workflow"
    id: str = Field(description="Workflow id, e.g. 'research.query'")
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    inputs: dict[str, dict[str, Any]] = Field(
        default_factory=dict, description="Input name → JSON Schema property"
    )
    steps: list[WorkflowStepSpec] = Field(default_factory=list)
    policies: dict[str, Any] = Field(
        default_factory=dict,
        description="Budget, evidence gate, retry, and approval policies",
    )


# ── runtime context ────────────────────────────────────────────────

class RunContext(BaseModel):
    """Immutable context injected into every plugin call."""
    run_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    thread_id: str | None = None
    workspace: str = Field(default=".", description="Workspace root path")
    budget_token_limit: int | None = Field(default=None)
    cancel_requested: bool = False


class PluginContext(BaseModel):
    """Restricted context handed to plugins.

    Plugins receive this — never the full LangGraph state, MultiAgentState,
    or workbench handler.

    Service callbacks (logger, model, storage, evidence, artifacts) are
    optional and wired by the runtime.  Plugins should guard with ``hasattr``
    or ``None`` checks before using them.
    """
    model_config = {"arbitrary_types_allowed": True}

    run: RunContext
    config: dict[str, Any] = Field(default_factory=dict)
    secrets: dict[str, str] = Field(
        default_factory=dict,
        description="secret_ref → value; never serialised to logs",
        repr=False,
    )
    logger: Any | None = Field(
        default=None, description="logging.Logger or compatible callable", exclude=True
    )
    model: Any | None = Field(
        default=None, description="LLM model client for agentic plugins", exclude=True
    )
    storage: Any | None = Field(
        default=None, description="Storage backend (file/chroma/etc.)", exclude=True
    )
    register_evidence: Any | None = Field(
        default=None, description="Callback: (evidence_id, payload) → None", exclude=True
    )
    register_artifact: Any | None = Field(
        default=None, description="Callback: (artifact_id, payload) → ArtifactRef", exclude=True
    )
    emit_trace: Any | None = Field(
        default=None, description="Callback receiving TraceEvent for each capability call", exclude=True
    )
    trace_events: list[Any] = Field(
        default_factory=list,
        description="In-process trace sink used when no persistent event store is wired",
        exclude=True,
    )


# ── step result ────────────────────────────────────────────────────

class StepStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    UNREVIEWED = "unreviewed"


class StepResult(BaseModel):
    """Normalised result from one capability execution."""
    status: StepStatus
    output: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[str] = Field(
        default_factory=list, description="Evidence IDs produced or referenced"
    )
    artifact_refs: list[ArtifactRef] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(
        default_factory=dict, description="Latency, tokens, cost, etc."
    )
    error: str = Field(default="", description="Human-readable error; never contains secrets")
    detail: str = Field(default="")
    plugin_id: str = ""
    capability_id: str = ""

    @classmethod
    def success(
        cls,
        output: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> "StepResult":
        return cls(status=StepStatus.SUCCESS, output=output or {}, **kwargs)

    @classmethod
    def failed(cls, error: str, **kwargs: Any) -> "StepResult":
        return cls(status=StepStatus.FAILED, error=error, **kwargs)


# ── artifact ───────────────────────────────────────────────────────

class ArtifactRef(BaseModel):
    """Reference to an immutable artifact stored by the runtime."""
    id: str
    type: str = Field(description="MIME-like type, e.g. 'text/markdown'")
    hash: str = Field(description="Content SHA-256 hex digest")
    location: str = Field(description="Relative path within artifact store")
    source_run_id: str = ""
    source_step_id: str = ""


# ── approval ───────────────────────────────────────────────────────

class ApprovalRequest(BaseModel):
    """A write or state change that requires explicit human confirmation."""
    operation: str = Field(description="e.g. 'knowledge.ingest', 'project.plan.write'")
    diff: dict[str, Any] = Field(default_factory=dict, description="What would change")
    risk: str = Field(default="low", description="low | medium | high")
    input_hash: str = Field(default="", description="SHA-256 of the inputs that produced this")
    result: Literal["pending", "approved", "rejected"] = "pending"


# ── trace ──────────────────────────────────────────────────────────

class TraceEvent(BaseModel):
    """Unified workflow event for the run ledger."""
    stage: str
    status: str
    elapsed_ms: float = 0.0
    run_id: str = ""
    thread_id: str = ""
    plugin_id: str = ""
    capability_id: str = ""
    step_id: str = ""
    source: str | None = None
    summary: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=__import__("time").time)
