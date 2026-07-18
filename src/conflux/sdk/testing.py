"""SDK testing utilities for contract tests.

These helpers let plugin authors verify their plugin satisfies the
Conflux protocol without a full runtime.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..core.contracts import (
    ApiVersion,
    CapabilitySpec,
    PluginContext,
    PluginManifest,
    PluginPermission,
    RunContext,
    StepResult,
    StepStatus,
)


def make_plugin_context(
    *,
    run_id: str = "test-run-001",
    config: dict[str, Any] | None = None,
    secrets: dict[str, str] | None = None,
    model: Any | None = None,
    storage: Any | None = None,
    emit_trace: Any | None = None,
) -> PluginContext:
    """Build a minimal PluginContext for offline tests."""
    return PluginContext(
        run=RunContext(run_id=run_id),
        config=config or {},
        secrets=secrets or {},
        model=model,
        storage=storage,
        emit_trace=emit_trace,
    )


def assert_manifest_valid(manifest: PluginManifest) -> list[str]:
    """Assert a manifest passes structural validation; returns issue list (empty = OK)."""
    issues: list[str] = []
    if not manifest.id:
        issues.append("id required")
    if not manifest.entrypoint:
        issues.append("entrypoint required")
    if not manifest.capabilities:
        issues.append("at least one capability required")
    for cap in manifest.capabilities:
        if not cap.id:
            issues.append("capability id required")
        if not cap.id.startswith(manifest.id + "."):
            issues.append(f"capability id '{cap.id}' must be prefixed by '{manifest.id}'")
    return issues


def assert_step_result(result: StepResult, expected_status: StepStatus | None = None) -> list[str]:
    """Assert a StepResult is structurally sound; returns issue list (empty = OK)."""
    issues: list[str] = []
    if expected_status is not None and result.status != expected_status:
        issues.append(f"expected status {expected_status.value}, got {result.status.value}")
    if result.status == StepStatus.FAILED and not result.error:
        issues.append("FAILED StepResult must include an error message")
    if result.status == StepStatus.SUCCESS and result.error:
        issues.append("SUCCESS StepResult should not include an error")
    return issues


# ── test fixtures ──────────────────────────────────────────────────

def valid_manifest_minimal() -> PluginManifest:
    """Return the smallest valid manifest for contract tests."""
    return PluginManifest(
        id="test.minimal",
        version="0.1.0",
        entrypoint="test_plugin:plugin",
        capabilities=[
            CapabilitySpec(
                id="test.minimal.echo",
                description="Echo input as output",
            )
        ],
    )


def manifest_without_capabilities() -> PluginManifest:
    """Manifest with no capabilities (invalid)."""
    return PluginManifest(
        id="test.no_caps",
        version="0.1.0",
        entrypoint="test_plugin:plugin",
        capabilities=[],
    )


def manifest_with_bad_cap_id() -> PluginManifest:
    """Manifest where capability id is not prefixed by plugin id (invalid)."""
    return PluginManifest(
        id="test.bad_prefix",
        version="0.1.0",
        entrypoint="test_plugin:plugin",
        capabilities=[
            CapabilitySpec(
                id="other.random.echo",
                description="Wrong prefix",
            )
        ],
    )


def manifest_with_unknown_api() -> dict[str, Any]:
    """Raw dict with unsupported api_version (invalid for parsing)."""
    return {
        "api_version": "conflux.dev/v99unknown",
        "kind": "Plugin",
        "id": "test.bad_api",
        "version": "0.1.0",
        "entrypoint": "test_plugin:plugin",
        "capabilities": [{"id": "test.bad_api.echo"}],
    }
