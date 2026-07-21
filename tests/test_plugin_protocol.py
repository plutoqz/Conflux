"""Contract tests for the M1 plugin protocol.

Covers the full protocol surface: manifest validation, registry lifecycle,
policy enforcement, plugin execution, error handling, and secret sanitisation.

All tests are offline — no real API keys, models, or network.
"""

from __future__ import annotations

import json
import pytest

from conflux.core.contracts import (
    ApiVersion,
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
from conflux.core.policy import (
    PolicyViolation,
    check_budget,
    check_permissions,
    check_step_schema,
    check_workflow_steps,
)
from conflux.core.registry import PluginRegistry, get_registry, reset_registry
from conflux.sdk.manifest import load_manifest, validate_manifest
from conflux.sdk.plugin import Plugin, Capability, capability
from conflux.sdk.testing import (
    assert_manifest_valid,
    assert_step_result,
    make_plugin_context,
    manifest_with_bad_cap_id,
    manifest_without_capabilities,
    manifest_with_unknown_api,
    valid_manifest_minimal,
)
from conflux.builtin.text.plugin import plugin as text_plugin


@pytest.fixture
def unavailable_review_model(monkeypatch):
    """Keep no-LLM plugin tests offline and independent of local config/cache."""
    import conflux.builtin.research.plugin as research_plugin
    import conflux.model_factory as model_factory

    monkeypatch.setattr(research_plugin, "_REVIEW_CACHE", {})

    def raise_unavailable(*args, **kwargs):
        raise ValueError("review model intentionally unavailable in offline test")

    monkeypatch.setattr(model_factory, "create_chat_model", raise_unavailable)


# ════════════════════════════════════════════════════════════════════
# Manifest validation
# ════════════════════════════════════════════════════════════════════

class TestManifestValidation:
    """Manifest structural checks — missing fields, bad ids, version."""

    def test_valid_minimal_passes(self):
        m = valid_manifest_minimal()
        issues = assert_manifest_valid(m)
        assert issues == [], f"Expected no issues, got {issues}"

    def test_missing_capabilities_fails(self):
        m = manifest_without_capabilities()
        issues = assert_manifest_valid(m)
        assert len(issues) > 0
        assert any("capability" in i.lower() for i in issues)

    def test_bad_capability_prefix_fails(self):
        m = manifest_with_bad_cap_id()
        issues = assert_manifest_valid(m)
        assert len(issues) > 0
        assert any("prefix" in i.lower() or "prefixed" in i.lower() for i in issues)

    def test_unknown_api_version_rejected(self):
        raw = manifest_with_unknown_api()
        with pytest.raises(Exception):
            PluginManifest.model_validate(raw)

    def test_missing_entrypoint_fails(self):
        m = PluginManifest(id="test.no_entry", version="0.1.0", entrypoint="")
        issues = assert_manifest_valid(m)
        assert any("entrypoint" in i.lower() for i in issues)

    def test_bad_version_format_rejected(self):
        with pytest.raises(Exception):
            PluginManifest(id="test.bad_ver", version="1.0", entrypoint="x:y")

    def test_builtin_text_manifest_is_valid(self):
        m = text_plugin.manifest
        issues = assert_manifest_valid(m)
        assert issues == [], f"Builtin manifest has issues: {issues}"


# ════════════════════════════════════════════════════════════════════
# Registry lifecycle
# ════════════════════════════════════════════════════════════════════

class TestRegistryLifecycle:
    """Register, unregister, lookup, conflict detection."""

    def setup_method(self):
        reset_registry()

    def teardown_method(self):
        reset_registry()

    def test_register_and_lookup(self):
        r = get_registry()
        m = valid_manifest_minimal()
        r.register(m)
        assert r.plugin_count == 1
        assert r.is_registered("test.minimal")
        assert r.get("test.minimal") is not None

    def test_capability_indexed(self):
        r = get_registry()
        m = valid_manifest_minimal()
        r.register(m)
        assert r.get_capability("test.minimal.echo") is not None

    def test_duplicate_plugin_rejected(self):
        r = get_registry()
        m = valid_manifest_minimal()
        r.register(m)
        with pytest.raises(ValueError, match="already registered"):
            r.register(m)

    def test_duplicate_capability_rejected(self):
        r = get_registry()
        m1 = valid_manifest_minimal()
        r.register(m1)
        m2 = PluginManifest(
            id="test.collision",
            version="0.1.0",
            entrypoint="x:y",
            capabilities=[CapabilitySpec(id="test.minimal.echo")],
        )
        with pytest.raises(ValueError, match="conflict"):
            r.register(m2)

    def test_unregister_removes_capabilities(self):
        r = get_registry()
        m = valid_manifest_minimal()
        r.register(m)
        r.unregister("test.minimal")
        assert r.plugin_count == 0
        assert r.capability_count == 0
        assert r.get_capability("test.minimal.echo") is None

    def test_singleton_returns_same_instance(self):
        r1 = get_registry()
        r2 = get_registry()
        assert r1 is r2

    def test_reset_clears_state(self):
        r = get_registry()
        m = valid_manifest_minimal()
        r.register(m)
        reset_registry()
        r2 = get_registry()
        assert r2.plugin_count == 0


# ════════════════════════════════════════════════════════════════════
# Built-in plugin execution
# ════════════════════════════════════════════════════════════════════

class TestBuiltinTextPlugin:
    """The builtin.text plugin works as a standalone capability."""

    def test_keyword_match_returns_step_result(self):
        ctx = make_plugin_context()
        cap = text_plugin.get_capability("builtin.text.keyword_match")
        assert cap is not None
        result = cap(ctx, text="hello world", keywords=["hello", "foo"])
        assert isinstance(result, StepResult)

    def test_keyword_match_success(self):
        ctx = make_plugin_context()
        cap = text_plugin.get_capability("builtin.text.keyword_match")
        result = cap(ctx, text="quantum crypto and RSA", keywords=["quantum", "RSA", "AES"])
        assert result.status == StepStatus.SUCCESS
        assert result.output["matched_keywords"] == ["quantum", "RSA"]
        assert result.output["coverage"] == pytest.approx(2 / 3, abs=0.01)

    def test_keyword_match_empty_input(self):
        ctx = make_plugin_context()
        cap = text_plugin.get_capability("builtin.text.keyword_match")
        result = cap(ctx, text="", keywords=["hello"])
        assert result.status == StepStatus.SUCCESS
        assert result.output["score"] == 0.0

    def test_keyword_match_result_has_plugin_id(self):
        ctx = make_plugin_context()
        cap = text_plugin.get_capability("builtin.text.keyword_match")
        result = cap(ctx, text="x", keywords=["x"])
        assert result.plugin_id == "builtin.text"
        assert result.capability_id == "builtin.text.keyword_match"

    def test_keyword_match_case_sensitive(self):
        ctx = make_plugin_context()
        cap = text_plugin.get_capability("builtin.text.keyword_match")
        result = cap(ctx, text="Hello World", keywords=["hello"], case_sensitive=True)
        assert result.output["matched_keywords"] == []
        result2 = cap(ctx, text="Hello World", keywords=["hello"], case_sensitive=False)
        assert result2.output["matched_keywords"] == ["hello"]

    def test_plugin_registers_through_registry(self):
        reset_registry()
        r = get_registry()
        r.register(text_plugin.manifest, text_plugin)
        cap = r.resolve_capability("builtin.text.keyword_match")
        ctx = make_plugin_context()
        result = cap(ctx, text="test", keywords=["test"])
        assert result.status == StepStatus.SUCCESS


# ════════════════════════════════════════════════════════════════════
# Policy enforcement
# ════════════════════════════════════════════════════════════════════

class TestPolicy:
    """Permission checks, budget, workflow step validation."""

    def test_permissions_ok_when_all_declared(self):
        check_permissions(
            [PluginPermission.NETWORK],
            [PluginPermission.NETWORK, PluginPermission.FILESYSTEM_READ],
            plugin_id="test.p",
        )

    def test_permissions_raise_on_missing(self):
        with pytest.raises(PolicyViolation, match="network"):
            check_permissions(
                [PluginPermission.NETWORK],
                [PluginPermission.FILESYSTEM_READ],
                plugin_id="test.p",
            )

    def test_budget_within_limit_passes(self):
        check_budget(500, 1000)

    def test_budget_exceeded_raises(self):
        with pytest.raises(PolicyViolation, match="exceeds"):
            check_budget(1500, 1000)

    def test_budget_none_limit_passes(self):
        check_budget(1_000_000, None)

    def test_workflow_step_unknown_capability(self):
        reset_registry()
        r = get_registry()
        wf = WorkflowDefinition(
            id="test.wf",
            version="0.1.0",
            steps=[WorkflowStepSpec(id="s1", uses="nonexistent.cap")]
        )
        issues = check_workflow_steps(wf, r)
        assert len(issues) == 1
        assert "nonexistent.cap" in issues[0]

    def test_workflow_step_registered_cap_ok(self):
        reset_registry()
        r = get_registry()
        r.register(text_plugin.manifest, text_plugin)
        wf = WorkflowDefinition(
            id="test.wf",
            version="0.1.0",
            steps=[WorkflowStepSpec(id="s1", uses="builtin.text.keyword_match")]
        )
        issues = check_workflow_steps(wf, r)
        assert issues == []


# ════════════════════════════════════════════════════════════════════
# StepResult — error & secret handling
# ════════════════════════════════════════════════════════════════════

class TestStepResult:
    """StepResult construction, error encapsulation, secret safety."""

    def test_success_factory(self):
        r = StepResult.success(output={"key": "value"})
        assert r.status == StepStatus.SUCCESS
        assert r.output == {"key": "value"}
        assert r.error == ""

    def test_failed_factory(self):
        r = StepResult.failed("something broke", plugin_id="test.p")
        assert r.status == StepStatus.FAILED
        assert r.error == "something broke"
        assert r.output == {}

    def test_failed_requires_error(self):
        r = StepResult(status=StepStatus.FAILED)
        issues = assert_step_result(r, StepStatus.FAILED)
        assert len(issues) > 0

    def test_success_should_not_have_error(self):
        r = StepResult.success(output={}, error="unexpected error")
        issues = assert_step_result(r, StepStatus.SUCCESS)
        assert len(issues) > 0

    def test_json_serializable(self):
        r = StepResult.success(
            output={"key": "value", "list": [1, 2, 3]},
            metrics={"tokens": 100, "latency_ms": 50.5},
        )
        d = r.model_dump()
        js = json.dumps(d)
        reloaded = json.loads(js)
        assert reloaded["status"] == "success"
        assert reloaded["output"]["key"] == "value"

    def test_error_never_contains_secret_ref(self):
        """Errors must be human-readable; secrets live in PluginContext.secrets."""
        r = StepResult.failed("API key invalid — use secret_ref 'openai_key'")
        # Error must not embed the secret value — just a ref is ok
        assert "sk-" not in r.error.lower()  # no real secret pattern
        # But referencing a secret ref name is fine
        assert "secret_ref" in r.error.lower()


# ════════════════════════════════════════════════════════════════════
# PluginContext isolation
# ════════════════════════════════════════════════════════════════════

class TestPluginContext:
    """PluginContext must not expose core internals."""

    def test_context_has_no_langgraph_refs(self):
        ctx = make_plugin_context()
        d = ctx.model_dump()
        # No LangGraph state keys should leak into context
        flat = json.dumps(d)
        assert "rag_result" not in flat
        assert "web_result" not in flat
        assert "MultiAgentState" not in flat

    def test_secrets_included_but_not_in_repr(self):
        ctx = PluginContext(
            run=RunContext(run_id="r1"),
            secrets={"openai_key": "sk-abc123"},
        )
        d = ctx.model_dump()
        assert d["secrets"]["openai_key"] == "sk-abc123"
        # repr should not include the secret value
        r = repr(ctx)
        assert "sk-abc123" not in r


# ════════════════════════════════════════════════════════════════════
# Manifest serialization round-trip
# ════════════════════════════════════════════════════════════════════

class TestManifestRoundTrip:
    """PluginManifest can export/import JSON Schema and round-trip."""

    def test_manifest_json_schema_exportable(self):
        schema = PluginManifest.model_json_schema()
        assert schema["type"] == "object"
        assert "api_version" in schema["properties"]
        assert "capabilities" in schema["properties"]

    def test_capability_spec_schema(self):
        schema = CapabilitySpec.model_json_schema()
        assert "input_schema" in schema["properties"]
        assert "output_schema" in schema["properties"]

    def test_manifest_to_json_and_back(self):
        m = text_plugin.manifest
        js = m.model_dump_json()
        reloaded = PluginManifest.model_validate_json(js)
        assert reloaded.id == m.id
        assert reloaded.version == m.version
        assert len(reloaded.capabilities) == len(m.capabilities)


# ════════════════════════════════════════════════════════════════════
# Atomic registration (P1 fix)
# ════════════════════════════════════════════════════════════════════

class TestAtomicRegistration:
    """Failed registrations must not leave partial state."""

    def setup_method(self):
        reset_registry()

    def teardown_method(self):
        reset_registry()

    def test_conflict_does_not_leave_plugin(self):
        r = get_registry()
        m1 = valid_manifest_minimal()
        r.register(m1)
        assert r.plugin_count == 1

        # Try to register a plugin whose capability conflicts.
        m2 = PluginManifest(
            id="test.collider",
            version="0.1.0",
            entrypoint="x:y",
            capabilities=[CapabilitySpec(id="test.minimal.echo")],
        )
        with pytest.raises(ValueError):
            r.register(m2)

        # Registry must be unchanged.
        assert r.plugin_count == 1
        assert "test.collider" not in [p.id for p in r.list_plugins()]


# ════════════════════════════════════════════════════════════════════
# Executor — exception handling & secret sanitisation
# ════════════════════════════════════════════════════════════════════

class TestExecutor:
    """The execute_capability wrapper must catch exceptions and sanitise secrets."""

    def test_exception_converted_to_step_result(self):
        from conflux.core.executor import execute_capability

        def bad_capability(ctx, **inputs):
            raise RuntimeError("something broke")

        ctx = make_plugin_context()
        result = execute_capability(bad_capability, ctx, capability_id="test.bad")
        assert result.status == StepStatus.FAILED
        assert "RuntimeError" in result.error
        assert "something broke" in result.error
        assert result.metrics.get("elapsed_ms", 0) >= 0

    def test_secret_redacted_from_error(self):
        from conflux.core.executor import execute_capability, sanitize_error

        def leaky_capability(ctx, **inputs):
            raise RuntimeError("API key is sk-live-abc123def456ghi789")

        ctx = make_plugin_context()
        result = execute_capability(leaky_capability, ctx, capability_id="test.leak")
        assert result.status == StepStatus.FAILED
        assert "sk-live" not in result.error
        assert "REDACTED" in result.error

    def test_sanitize_aws_key(self):
        from conflux.core.executor import sanitize_error
        msg = "Bad key: AKIA1234567890ABCDEF"
        sanitized = sanitize_error(msg)
        assert "AKIA" not in sanitized

    def test_configured_secret_redacted_and_trace_emitted(self):
        from conflux.core.executor import execute_capability

        ctx = PluginContext(
            run=RunContext(run_id="trace-run"),
            secrets={"token": "short-secret"},
        )

        def leaky(ctx, **inputs):
            return StepResult.failed("credential=short-secret", output={"token": "short-secret"})

        result = execute_capability(leaky, ctx, capability_id="test.leaky")
        assert "short-secret" not in result.error
        assert "short-secret" not in json.dumps(result.output)
        assert len(ctx.trace_events) == 1
        assert ctx.trace_events[0].capability_id == "test.leaky"


# ════════════════════════════════════════════════════════════════════
# JSON Schema validation
# ════════════════════════════════════════════════════════════════════

class TestSchemaValidation:
    """Real JSON Schema validation for step inputs and workflow inputs."""

    def test_check_step_schema_with_jsonschema(self):
        from conflux.core.policy import check_step_schema

        cap = CapabilitySpec(
            id="test.schema.match",
            input_schema={
                "type": "object",
                "properties": {"text": {"type": "string"}, "keywords": {"type": "array"}},
                "required": ["text"],
            },
        )
        # Step missing required "text".
        step = WorkflowStepSpec(id="s1", uses="test.schema.match", config={"keywords": ["x"]})
        issues = check_step_schema(step, cap)
        # At minimum the required-field mapping check should fire.
        assert len(issues) >= 1

    def test_check_step_schema_valid_passes(self):
        from conflux.core.policy import check_step_schema

        cap = CapabilitySpec(
            id="test.schema.ok",
            input_schema={
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
        )
        step = WorkflowStepSpec(id="s1", uses="test.schema.ok", config={"text": "hello"})
        issues = check_step_schema(step, cap)
        assert issues == []

    def test_validate_output_success(self):
        from conflux.core.policy import validate_output

        output_schema = {
            "type": "object",
            "properties": {"score": {"type": "number"}},
            "required": ["score"],
        }
        issues = validate_output({"score": 0.95}, output_schema)
        assert issues == []

    def test_validate_output_fails(self):
        from conflux.core.policy import validate_output

        output_schema = {
            "type": "object",
            "properties": {"score": {"type": "number"}},
            "required": ["score"],
        }
        issues = validate_output({"score": "not-a-number"}, output_schema)
        assert len(issues) >= 1

    def test_validate_workflow_inputs(self):
        from conflux.core.policy import validate_workflow_inputs

        wf = WorkflowDefinition(
            id="test.wf",
            version="0.1.0",
            inputs={
                "query": {"type": "string", "required": True},
                "depth": {"type": "integer", "required": False},
            },
            steps=[],
        )
        # Missing required "query".
        issues = validate_workflow_inputs(wf, {"depth": 3})
        assert len(issues) >= 1

        # Valid.
        issues2 = validate_workflow_inputs(wf, {"query": "hello"})
        assert issues2 == []


# ════════════════════════════════════════════════════════════════════
# Disabled plugin handling (contract test per §5.5)
# ════════════════════════════════════════════════════════════════════

class TestDisabledPlugin:
    """Registry must support plugin disable/enable without data loss."""

    def setup_method(self):
        reset_registry()

    def teardown_method(self):
        reset_registry()

    def test_unregistered_plugin_not_listed(self):
        r = get_registry()
        m = valid_manifest_minimal()
        r.register(m)
        r.unregister("test.minimal")
        assert r.plugin_count == 0
        assert r.get("test.minimal") is None

    def test_unregistered_capability_unreachable(self):
        r = get_registry()
        m = valid_manifest_minimal()
        r.register(m)
        r.unregister("test.minimal")
        assert r.resolve_capability("test.minimal.echo") is None

    def test_re_register_after_unregister(self):
        r = get_registry()
        m = valid_manifest_minimal()
        r.register(m)
        r.unregister("test.minimal")
        # Re-register must succeed.
        r.register(m)
        assert r.plugin_count == 1


# ════════════════════════════════════════════════════════════════════
# Event / trace recording (contract test per §5.5)
# ════════════════════════════════════════════════════════════════════

class TestTraceEventRecording:
    """TraceEvent model and executor-side recording."""

    def test_trace_event_constructable(self):
        from conflux.core.contracts import TraceEvent
        evt = TraceEvent(
            stage="keyword_match",
            status="success",
            elapsed_ms=12.5,
            run_id="run-1",
            plugin_id="builtin.text",
            capability_id="builtin.text.keyword_match",
            source="text",
        )
        d = evt.model_dump()
        assert d["stage"] == "keyword_match"
        assert d["status"] == "success"
        assert d["run_id"] == "run-1"

    def test_execute_capability_records_metrics(self):
        from conflux.core.executor import execute_capability

        def ok(ctx, **inputs):
            return StepResult.success(output={"done": True})

        ctx = make_plugin_context(run_id="run-metrics")
        result = execute_capability(ok, ctx, capability_id="test.metrics")
        assert result.metrics.get("elapsed_ms", 0) >= 0

    def test_execute_capability_failure_records_metrics(self):
        from conflux.core.executor import execute_capability

        def bad(ctx, **inputs):
            raise RuntimeError("boom")

        ctx = make_plugin_context()
        result = execute_capability(bad, ctx, capability_id="test.fail")
        assert result.status == StepStatus.FAILED
        assert result.metrics.get("elapsed_ms", 0) >= 0


# ════════════════════════════════════════════════════════════════════
# M2 — Dynamic source results
# ════════════════════════════════════════════════════════════════════

class TestDynamicSourceResults:
    """Dynamic source_results collection (M2 protocol)."""

    def test_init_empty(self):
        from conflux.core.dynamic_source import init_source_results
        assert init_source_results() == {}

    def test_merge_adds_source(self):
        from conflux.core.dynamic_source import merge_source_result
        from conflux.source_status import SourceResult

        sr = SourceResult(source="RAG", status="success", content="test")
        col = merge_source_result({}, "builtin.rag", sr)
        assert "builtin.rag" in col
        assert col["builtin.rag"]["status"] == "success"

    def test_merge_overwrites(self):
        from conflux.core.dynamic_source import merge_source_result
        from conflux.source_status import SourceResult

        sr1 = SourceResult(source="RAG", status="success", content="v1")
        sr2 = SourceResult(source="RAG", status="low_relevance", content="v2")
        col = merge_source_result({}, "builtin.rag", sr1)
        col = merge_source_result(col, "builtin.rag", sr2)
        assert col["builtin.rag"]["status"] == "low_relevance"

    def test_reducer_right_wins(self):
        from conflux.core.dynamic_source import merge_source_results_reducer
        left = {"a": {"status": "success"}}
        right = {"a": {"status": "failed"}, "b": {"status": "success"}}
        merged = merge_source_results_reducer(left, right)
        assert merged["a"]["status"] == "failed"
        assert "b" in merged

    def test_source_ids_sorted(self):
        from conflux.core.dynamic_source import source_ids
        col = {"b": {}, "a": {}, "c": {}}
        assert source_ids(col) == ["a", "b", "c"]

    def test_source_payload_uses_namespaced_id(self):
        from conflux.core.dynamic_source import get_source_result, merge_source_result
        from conflux.source_status import SourceResult

        collection = merge_source_result(
            {}, "plugin.example.search", SourceResult(source="Web", status="success", content="x")
        )
        assert collection["plugin.example.search"]["source"] == "plugin.example.search"
        assert get_source_result(collection, "plugin.example.search").source == "plugin.example.search"


# ════════════════════════════════════════════════════════════════════
# M2 — Workflow compiler
# ════════════════════════════════════════════════════════════════════

class TestWorkflowCompiler:
    """YAML workflow compilation and dry-run."""

    def test_compile_valid_workflow(self):
        from conflux.core.workflow_compiler import compile_workflow
        from conflux.core.registry import get_registry, reset_registry
        from conflux.builtin.text.plugin import plugin as text_plugin

        reset_registry()
        r = get_registry()
        r.register(text_plugin.manifest, text_plugin)

        wf = WorkflowDefinition(
            id="test.compile",
            version="0.1.0",
            steps=[
                WorkflowStepSpec(id="s1", uses="builtin.text.keyword_match", config={
                    "text": "hello", "keywords": ["hello"]
                }),
            ],
        )
        result = compile_workflow(wf, r)
        assert result.is_valid
        assert result.execution_order == ["s1"]
        assert "s1" in result.resolved_capabilities

    def test_compile_invalid_capability(self):
        from conflux.core.workflow_compiler import compile_workflow
        from conflux.core.registry import get_registry, reset_registry

        reset_registry()
        r = get_registry()

        wf = WorkflowDefinition(
            id="test.invalid",
            version="0.1.0",
            steps=[WorkflowStepSpec(id="s1", uses="nonexistent.cap")],
        )
        result = compile_workflow(wf, r)
        assert not result.is_valid
        assert len(result.issues) >= 1

    def test_dry_run_produces_text(self):
        from conflux.core.workflow_compiler import dry_run_workflow
        from conflux.core.registry import get_registry, reset_registry
        from conflux.builtin.text.plugin import plugin as text_plugin

        reset_registry()
        r = get_registry()
        r.register(text_plugin.manifest, text_plugin)

        wf = WorkflowDefinition(
            id="test.dry",
            version="0.1.0",
            steps=[
                WorkflowStepSpec(id="s1", uses="builtin.text.keyword_match", config={
                    "text": "x", "keywords": ["x"]
                }),
            ],
        )
        output = dry_run_workflow(wf, r)
        assert "test.dry" in output
        assert "Dry-run" in output

    def test_text_graph(self):
        from conflux.core.workflow_compiler import workflow_text_graph
        wf = WorkflowDefinition(
            id="test.viz",
            version="0.1.0",
            steps=[
                WorkflowStepSpec(id="s1", uses="a.x"),
                WorkflowStepSpec(id="s2", uses="b.y"),
            ],
        )
        graph = workflow_text_graph(wf)
        assert "test.viz" in graph
        assert "├──" in graph
        assert "└──" in graph

    def test_execute_workflow_resolves_inputs_through_executor(self):
        from conflux.core.workflow_compiler import execute_workflow
        from conflux.core.registry import PluginRegistry
        from conflux.builtin.text.plugin import plugin as text_plugin

        registry = PluginRegistry()
        registry.register(text_plugin.manifest, text_plugin)
        workflow = WorkflowDefinition(
            id="test.execute",
            version="0.1.0",
            inputs={"query": {"type": "string", "required": True}},
            steps=[WorkflowStepSpec(
                id="match",
                uses="builtin.text.keyword_match",
                config={"text": "{{query}}", "keywords": ["quantum"]},
            )],
        )
        results = execute_workflow(workflow, registry, {"query": "quantum crypto"})
        assert results["match"].status == StepStatus.SUCCESS
        assert results["match"].output["matched_keywords"] == ["quantum"]

    def test_external_and_local_workflow_fixtures_compile(self):
        from pathlib import Path
        from conflux.adapters.plugin_loader import load_builtin_plugins
        from conflux.core.registry import PluginRegistry
        from conflux.core.workflow_compiler import compile_workflow, dry_run_workflow
        from conflux.sdk.manifest import load_workflow

        registry = load_builtin_plugins(PluginRegistry())
        root = Path(__file__).parent / "fixtures" / "architecture" / "workflows"
        for filename in ("test_query.yaml", "external_research_v2.yaml"):
            workflow = load_workflow(root / filename)
            result = compile_workflow(workflow, registry)
            assert result.is_valid, [str(item) for item in result.issues]
            assert "Dry-run" in dry_run_workflow(workflow, registry)


# ════════════════════════════════════════════════════════════════════
# M2 — Builtin plugins (RAG, Research, Paper)
# ════════════════════════════════════════════════════════════════════

class TestM2BuiltinPlugins:
    """RAG, Research, Paper plugins are registered and loaded."""

    def test_rag_plugin_registered(self):
        from conflux.builtin.rag.plugin import plugin as rag_plugin
        assert rag_plugin.manifest.id == "builtin.rag"
        assert rag_plugin.get_capability("builtin.rag.search") is not None

    def test_research_plugin_registered(self):
        from conflux.builtin.research.plugin import plugin as research_plugin
        assert research_plugin.manifest.id == "builtin.research"
        cap = research_plugin.get_capability("builtin.research.evidence_review")
        assert cap is not None

    def test_evidence_review_unreviewed_on_empty(self):
        from conflux.builtin.research.plugin import evidence_review
        from conflux.sdk.testing import make_plugin_context

        ctx = make_plugin_context()
        result = evidence_review(ctx, query="test", candidates=[])
        assert result.status == StepStatus.SUCCESS
        assert result.output["reviewed_count"] == 0

    def test_evidence_review_unreviewed_without_llm(self, unavailable_review_model):
        """When no review model is available, evidence_review marks all unreviewed."""
        from conflux.builtin.research.plugin import evidence_review
        from conflux.sdk.testing import make_plugin_context

        ctx = make_plugin_context()
        result = evidence_review(
            ctx,
            query="quantum computing",
            candidates=[{"text": "Paper about quantum computing"}],
        )
        assert result.status in (StepStatus.UNREVIEWED, StepStatus.FAILED)
        assert result.output["unreviewed_count"] >= 1

    def test_paper_plugin_registered(self):
        from conflux.builtin.paper.plugin import plugin as paper_plugin
        assert paper_plugin.manifest.id == "builtin.paper"
        cap = paper_plugin.get_capability("builtin.paper.review")
        assert cap is not None

    def test_paper_review_unreviewed_without_llm(self, unavailable_review_model):
        from conflux.builtin.paper.plugin import paper_review
        from conflux.sdk.testing import make_plugin_context

        ctx = make_plugin_context()
        result = paper_review(
            ctx,
            papers=[{"title": "Test Paper", "abstract": "An important result."}],
        )
        assert result.status in (StepStatus.UNREVIEWED, StepStatus.FAILED)
        assert result.output["unreviewed"] >= 1

    def test_research_review_success_is_schema_validated_and_traced(self):
        from types import SimpleNamespace
        from conflux.builtin.research.plugin import evidence_review

        class FakeModel:
            model_name = "fake-review-v1"

            def invoke(self, messages):
                return SimpleNamespace(content=(
                    '[{"relevance":"relevant","research_value":"method",'
                    '"evidence_quality":"direct result","reasoning":"semantic match",'
                    '"confidence":0.9,"needs_deeper_review":false}]'
                ))

        ctx = make_plugin_context()
        ctx.model = FakeModel()
        result = evidence_review(ctx, query="unique-success-query", candidates=[{"text": "candidate"}])
        assert result.status == StepStatus.SUCCESS
        review = result.output["reviews"][0]
        assert review["content_hash"]
        assert review["model_version"] == "fake-review-v1"
        assert review["uncertainty"] == pytest.approx(0.1)
        assert not result.output["unreviewed_count"]

    def test_rag_plugin_success_uses_injected_retriever(self):
        from langchain_core.documents import Document
        from conflux.builtin.rag.plugin import rag_search

        class FakeRetriever:
            def search(self, query):
                return [Document(
                    page_content="Quantum migration evidence",
                    metadata={"source": "fixture.md", "score": 0.9},
                )]

        ctx = make_plugin_context(storage=FakeRetriever())
        result = rag_search(ctx, query="quantum migration", top_k=5)
        assert result.status == StepStatus.SUCCESS
        assert result.output["status"] == "success"
        assert result.output["documents"][0]["source"] == "fixture.md"

    def test_research_review_malformed_response_becomes_unreviewed(self):
        from types import SimpleNamespace
        from conflux.builtin.research.plugin import evidence_review

        class BadModel:
            def invoke(self, messages):
                return SimpleNamespace(content='[{"not_a_review": true}]')

        ctx = make_plugin_context()
        ctx.model = BadModel()
        result = evidence_review(ctx, query="unique-malformed-query", candidates=[{"text": "candidate"}])
        assert result.status == StepStatus.UNREVIEWED
        assert result.output["reviews"][0]["relevance"] == "unreviewed"
        assert result.output["reviews"][0]["next_action"]

    def test_web_plugin_uses_injected_offline_source(self):
        from conflux.builtin.web.plugin import web_search
        from conflux.source_status import SourceResult

        ctx = make_plugin_context(config={
            "web_search": lambda query: SourceResult(
                source="Web", status="success", content="external evidence",
                metadata={"citations": [{"url": "https://example.test"}]},
            ).to_tool_text()
        })
        result = web_search(ctx, query="offline external source")
        assert result.status == StepStatus.SUCCESS
        assert result.output["status"] == "success"
        assert result.output["citations"][0]["url"] == "https://example.test"

    def test_paper_review_success_uses_shared_review_protocol(self):
        from types import SimpleNamespace
        from conflux.builtin.paper.plugin import paper_review

        class FakeModel:
            model_name = "fake-paper-v1"

            def invoke(self, messages):
                return SimpleNamespace(content=(
                    '[{"relevance":"partially_relevant","research_value":"survey",'
                    '"evidence_quality":"abstract evidence","reasoning":"related scope",'
                    '"confidence":0.7,"needs_deeper_review":false}]'
                ))

        ctx = make_plugin_context()
        ctx.model = FakeModel()
        result = paper_review(
            ctx,
            papers=[{"id": "p1", "title": "Paper", "abstract": "Abstract"}],
            profile_id="profile-a",
            profile_version="profile-v1",
        )
        assert result.status == StepStatus.SUCCESS
        review = result.output["reviews"][0]
        assert review["paper_id"] == "p1"
        assert review["profile_id"] == "profile-a"
        assert review["title_hash"]
